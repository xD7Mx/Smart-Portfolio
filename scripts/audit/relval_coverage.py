#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# جدوى التقييم النسبيّ إلى القطاع — **مسبارُ تغطيةٍ قبل بناء**.
#
# ## الفكرة (للمالك)
# ‎124 شركةً لا يغطّيها بيتُ خبرة، فلا هدفَ محلّلين لها ولا يوجد في العالم.
# والبديلُ ألّا ننتظر رقماً غيرَ موجودٍ بل نشتقّه:
#
#     قيمةُ السهم ≈ وسيطُ مضاعفِ قطاعه × مقياسِ الشركة نفسِها
#
# ووسيطُ القطاع يُحسب من شركات السوق أنفسِها — لا يُستورد ولا يُفترض.
#
# ## لماذا مسبارٌ أوّلاً
# لا يُبنى نموذجٌ قبل معرفة كم شركةً تملك مُدخَلَه فعلاً. فيُقاس هنا، من
# **مخزننا القائم** (‏market:fundamentals، مبنيٌّ من نداءاتٍ تمّت أصلاً):
#   · كم شركةً لها مكرّرُ ربحيةٍ صالح · كم لها مضاعفُ قيمةٍ دفترية
#   · كم قطاعاً فيه نظائرُ تكفي لوسيطٍ له معنى
#   · وكم من الـ‎124 «اليتيمة» تنجو بهذا الطريق
#
#   docker exec sp_backend python /app/scripts/audit/relval_coverage.py
#
# لا يحسب قيمةً ولا يكتب شيئاً — يقول أيَغطّي هذا الطريقُ الفراغَ أم لا.
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

MIN_PEERS = 5            # أقلُّ عددِ نظائرَ لوسيطٍ له معنى


def _f(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def main() -> int:
    from app.services.content_engine import fund_store_load
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    # خريطةُ القطاعات في `data.company_sectors` — والمسارُ ليس تفصيلاً:
    # استيرادٌ خاطئٌ يسقط إلى `{}` بصمتٍ فيصير السوقُ كلُّه «غير مصنّف»،
    # ويخرج المسبارُ بحكمٍ مبنيٍّ على لا شيء. فيُصرَّح بالفشل ولا يُبتلع.
    from app.data.company_sectors import SYMBOL_TO_SECTOR_AR as SEC
    if not SEC:
        print("خريطةُ القطاعات فارغة — لا يُقاس تشتّتُ قطاعٍ بلا قطاعات.")
        return 2

    store = fund_store_load()
    if not store:
        print("مخزنُ الأساسيات فارغ — القراءةُ معطوبة، لا السوق. أُوقف.")
        return 2
    uni = main_market(MARKET_UNIVERSE)
    print(f"مخزنُ الأساسيات: {len(store)} رمزاً · السوقُ الرئيسي: {len(uni)}")
    print("─" * 74)

    have_pe = have_pb = have_bv = have_tgt = 0
    orphans: list[str] = []           # بلا هدفِ محلّلين
    by_sector: dict[str, list[float]] = {}
    pb_by_sector: dict[str, list[float]] = {}
    rescued = 0

    for sym in uni:
        row = store.get(sym) or {}
        pe = _f(row.get("pe_ratio"))
        pb = _f(row.get("price_to_book"))
        bv = _f(row.get("book_value"))
        tgt = _f(row.get("target_mean_price"))
        # مكرّرٌ سالبٌ يعني خسارة، ومكرّرٌ فلكيٌّ يعني ربحاً يكاد ينعدم —
        # كلاهما لا يصلح لوسيطٍ ولا يُقيَّم به سهم.
        pe_ok = pe is not None and 0 < pe < 100
        pb_ok = pb is not None and 0 < pb < 20
        have_pe += pe_ok
        have_pb += pb_ok
        have_bv += bv is not None
        have_tgt += tgt is not None
        sec = SEC.get(sym) or "غير مصنّف"
        if pe_ok:
            by_sector.setdefault(sec, []).append(pe)
        if pb_ok:
            pb_by_sector.setdefault(sec, []).append(pb)
        if tgt is None:
            orphans.append(sym)
            if pe_ok or pb_ok:
                rescued += 1

    n = len(uni)
    print(f"هدفُ محلّلين      : {have_tgt:>3} من {n}")
    print(f"مكرّرُ ربحيةٍ صالح : {have_pe:>3} من {n}")
    print(f"مضاعفُ قيمةٍ دفترية: {have_pb:>3} من {n}")
    print(f"قيمةٌ دفتريةٌ للسهم: {have_bv:>3} من {n}")
    print()
    print(f"بلا هدفِ محلّلين  : {len(orphans)}")
    print(f"منها يُنقذها النسبيّ: {rescued}"
          f"  ({rescued * 100 // max(1, len(orphans))}٪)")
    print("─" * 74)

    usable = {s: v for s, v in by_sector.items() if len(v) >= MIN_PEERS}
    print(f"قطاعاتٌ فيها {MIN_PEERS} نظائرَ فأكثر (مكرّر): "
          f"{len(usable)} من {len(by_sector)}")
    for sec in sorted(usable, key=lambda s: -len(usable[s])):
        v = sorted(usable[sec])
        med = statistics.median(v)
        # التشتّتُ يقرّر عرضَ النطاق: قطاعٌ متباعدُ المضاعفات لا يُقيَّم
        # بوسيطه بثقةٍ عالية، ويُقال ذلك بدل إخفائه.
        spread = (v[-1] - v[0]) / med if med else 0
        print(f"   {sec:<26} ن={len(v):<3} وسيط {med:>6.1f} · تشتّت {spread:>4.1f}")
    thin = [s for s, v in by_sector.items() if len(v) < MIN_PEERS]
    if thin:
        print(f"\nقطاعاتٌ رقيقةٌ لا يُؤخذ وسيطُها: {', '.join(thin[:12])}")

    print("─" * 74)
    print("الحكم: يُبنى التقييمُ النسبيّ حيث توجد نظائرُ كافيةٌ ومقياسٌ موجب.")
    print("وما دون ذلك يبقى «غير متوفّر» — لا يُجمَّل الفراغُ برقمٍ ضعيف.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
