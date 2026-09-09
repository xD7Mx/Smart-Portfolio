#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# تشغيلُ القيمة النسبية على السوق الحقيقيّ — **قياسُ مخرَجٍ قبل عرضِه**.
#
# فحصُ `relative_value_check.py` يقيس القراراتِ بمعطياتٍ مُصطنَعة. وهذا
# يشغّل النموذجَ على بيانات السوق كما هي، ويطبع:
#   · كم شركةً أنتجت قيمةً وكم امتنعت وبأيّ سبب
#   · توزيعَ الثقة
#   · وأهمَّ شيء: **مقارنةً بأهداف المحلّلين حيث يجتمعان** — فالنموذجُ
#     الذي يخالف كلَّ محلّلٍ في السوق مشكوكٌ فيه، ولا يُعرف ذلك إلا بالقياس.
#
#   docker exec sp_backend python /app/scripts/audit/relval_run.py
#   docker exec sp_backend python /app/scripts/audit/relval_run.py --show 25
#
# لا يكتب في التطبيق ولا يعرض شيئاً للمستخدم: يقيس ويطبع.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, shutil as _sh, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_REAL_LG = _os.environ.get("LASTGOOD_PATH") or (
    "/app/data/lastgood.json" if _os.path.isdir("/app/data") else "")
_COPY = _os.path.join(_SANDBOX, "lastgood.json")
if _REAL_LG and _os.path.exists(_REAL_LG):
    try:
        _sh.copyfile(_REAL_LG, _COPY)
    except Exception:                                             # noqa: BLE001
        pass
_os.environ["LASTGOOD_PATH"] = _COPY
_os.environ["SP_STATE_DIR"] = _SANDBOX

import statistics
import sys

for _p in ("/app", "backend", "."):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main() -> int:
    from app.services.relative_value import SectorTable, relative_value
    from app.services.content_engine import fund_store_load
    from app.services.market_screener import get_cached_screener
    from app.data.company_sectors import SYMBOL_TO_SECTOR_AR as SEC
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market

    argv = list(sys.argv[1:])
    show = 15
    if "--show" in argv:
        i = argv.index("--show")
        if i + 1 < len(argv) and argv[i + 1].isdigit():
            show = int(argv[i + 1])

    store = fund_store_load()
    if not store:
        print("مخزنُ الأساسيات فارغ — القراءةُ معطوبة، لا السوق. أُوقف.")
        return 2
    screener = get_cached_screener() or []
    price_of = {str(r.get("symbol")): r.get("price") for r in screener
                if r.get("symbol")}
    if not price_of:
        print("لا لقطةَ فرزٍ مخزَّنة — لا أسعار. شغّل السوقَ أوّلاً ثم أعِد.")
        return 2

    uni = main_market(MARKET_UNIVERSE)
    rows = [{"sector": SEC.get(s), "pe": (store.get(s) or {}).get("pe_ratio"),
             "pb": (store.get(s) or {}).get("price_to_book")} for s in uni]
    table = SectorTable(rows)

    made, abstained, by_conf = [], {}, {}
    blocks: dict[str, int] = {}          # أيُّ شرطٍ يخفض الدرجةَ فعلاً
    gaps: list[float] = []
    for s in uni:
        row = store.get(s) or {}
        r = relative_value(sector=SEC.get(s), price=price_of.get(s),
                           pe=row.get("pe_ratio"), pb=row.get("price_to_book"),
                           book_value=row.get("book_value"), table=table)
        tgt = row.get("target_mean_price")
        if r["value"] is None:
            abstained[r["why"]] = abstained.get(r["why"], 0) + 1
            continue
        by_conf[r["confidence"]] = by_conf.get(r["confidence"], 0) + 1
        for b in r.get("confidence_why") or []:
            key = b.split()[0] if " " in b else b
            blocks[key] = blocks.get(key, 0) + 1
        made.append((s, r, tgt, price_of.get(s)))
        if isinstance(tgt, (int, float)) and tgt:
            gaps.append((r["value"] - float(tgt)) / float(tgt) * 100)

    n = len(uni)
    print(f"السوقُ الرئيسي: {n} · أنتجت قيمةً: {len(made)} · امتنعت: {n - len(made)}")
    for why, c in sorted(abstained.items(), key=lambda x: -x[1]):
        print(f"   امتناع — {why}: {c}")
    print("الثقة: " + " · ".join(f"{k} {v}" for k, v in by_conf.items()))
    # ══ لماذا لا تُبلَغ «مرتفعة»؟ ══ لا تُعاير عتبةٌ قبل معرفة القيدِ المُلزِم.
    if blocks:
        print("القيودُ الخافضة: " + " · ".join(
            f"{k} {v}" for k, v in sorted(blocks.items(), key=lambda x: -x[1])))
    print("─" * 74)

    # ══ المحكُّ الحقيقيّ ══
    # حيث يوجد هدفُ محلّلين، يُقارَن به. لا لنُطابقه — النموذجُ ليس محاكياً
    # للمحلّلين — بل لنعرف: أهو في مدى معقولٍ منه أم في عالمٍ آخر؟
    if gaps:
        gaps.sort()
        med = statistics.median(gaps)
        within25 = sum(1 for g in gaps if abs(g) <= 25) * 100 // len(gaps)
        print(f"حيث يجتمع مع هدف المحلّلين ({len(gaps)} شركة):")
        print(f"   وسيطُ الفارق {med:+.1f}٪ · ضمن ±25٪ من الهدف: {within25}٪"
              f" · المدى [{gaps[0]:+.0f}٪ · {gaps[-1]:+.0f}٪]")
        if abs(med) > 30:
            print("   ⚠ انحيازٌ منهجيٌّ كبير — لا يُعرض قبل تفسيره.")
    else:
        print("لا شركةَ يجتمع فيها النموذجُ مع هدفِ محلّلين — لا محكَّ.")

    print("─" * 74)
    print(f"عيّنةٌ من الشركات بلا هدفِ محلّلين (أوّل {show}):")
    shown = 0
    for s, r, tgt, px in made:
        if tgt is not None or shown >= show:
            continue
        shown += 1
        gap = (r["value"] - px) / px * 100 if px else 0
        print(f"   {s:<6} سعر {px:>7.2f} · نسبية {r['value']:>7.2f}"
              f" [{r['low']:>6.1f}–{r['high']:>6.1f}] {gap:+6.1f}٪"
              f" · {r['confidence']} · {'، '.join(r.get('confidence_why') or ['—'])}")

    print("─" * 74)
    print("هذه «قيمةٌ نسبيةٌ إلى القطاع» لا قيمةٌ عادلة: إن غلا القطاعُ كلُّه")
    print("غلت معه. حدٌّ في الطريقة يُقال للمستخدم، لا عيبٌ يُخفى.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
