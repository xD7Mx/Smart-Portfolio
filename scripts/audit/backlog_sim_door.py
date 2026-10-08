#!/usr/bin/env python3
"""محاكاةُ أثر سجلّ الأعمال الموقَّع (‏D633) على القيمة العادلة — بمسطرة البوابة (‏D632) قبل أيّ تعديلٍ في المحرّك.

النموُّ الابتدائيّ في نماذج التدفّق = أكبرُ النموّ التاريخيّ ونسبةِ الإيراد السنويّ للعقود الجديدة الموقَّعة المفصَحة
(لا تجديد ولا حصّةَ تحالف ولا ترسيةً بلا توقيع) من آخر إيرادٍ سنويّ — بسقفين 15٪ و25٪. يُلفّ `base_of` في الذاكرة
وحدها: لا يُكتب كاش ولا مخزن، والمحرّكُ المنشور كما هو. قارئٌ فقط."""
import asyncio, collections, statistics as st, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services import fair_value_models as F
from app.services.content_engine import fund_store_load
from app.services.market_screener import get_cached_screener
from app.services.material_events import events_for

CAPS = (0.15, 0.25)
_orig = F.base_of


def run(i, floor):
    def patched(ii):
        b = _orig(ii)
        if b is not None and floor is not None and floor > b.growth:
            b.growth = floor
        return b
    F.base_of = patched
    try:
        r = F.value(i) or {}
    finally:
        F.base_of = _orig
    return r.get("value")


async def main():
    uni = main_market(MARKET_UNIVERSE)
    store = fund_store_load()
    rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    data, hit = [], 0
    for s, meta in uni.items():
        r = rows.get(s) or {}
        at, px = r.get("analyst_target"), r.get("price")
        fv = (store.get(s) or {}).get("fair_value")
        if not (isinstance(fv, (int, float)) and isinstance(at, (int, float)) and at > 0 and isinstance(px, (int, float)) and px > 0):
            continue
        try:
            ev = await events_for(s)
            i = await F.gather(s)
        except Exception as e:                                    # noqa: BLE001
            print(f"  {s} تعذّر: {type(e).__name__} {e}")
            continue
        if not i:
            continue
        ratio = ev.get("backlog_ratio")
        v0 = run(i, None)
        vs = {c: (run(i, min(ratio, c)) if ratio else v0) for c in CAPS}
        if not v0:
            continue
        sec = meta.get("sector_ar") or meta.get("sector") or "—"
        data.append({"s": s, "sec": sec, "px": px, "at": at, "v0": v0, **{f"v{c}": vs[c] for c in CAPS}})
        if ratio:
            hit += 1
            cnt = [e for e in ev["events"] if e.get("counted")]
            print(f"  {s} {meta.get('name_ar')} ({sec}) · عقودٌ معدودة {len(cnt)} · سجلٌّ سنويّ {ev['backlog_annual']/1e6:,.0f} مليون = "
                  f"{ratio:.0%} من الإيراد · قيمة {v0:.2f} ← {vs[0.15]:.2f} / {vs[0.25]:.2f} · سعر {px} · هدف {at}")
    print(f"\nأوراقٌ مقيسة {len(data)} · لها سجلُّ أعمالٍ معدود {hit}")

    def med(key, rows_):
        return st.median([abs(x[key] / x["at"] - 1) for x in rows_]) if rows_ else float("nan")
    keys = ["v0"] + [f"v{c}" for c in CAPS]
    print("\n══ السوق ══ " + " · ".join(f"{k} {med(k, data):.1%}" for k in keys)
          + f" · السعرُ نفسُه {st.median([abs(x['px']/x['at']-1) for x in data]):.1%}")
    by = collections.defaultdict(list)
    for x in data:
        by[x["sec"]].append(x)
    print("\n══ القطاعات (≥ 5) — ✘ أبعدُ عن الهدف من السعر نفسِه ══")
    for sec, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        if len(xs) < 5:
            continue
        p = st.median([abs(x["px"] / x["at"] - 1) for x in xs])
        cells = " · ".join(f"{k} {med(k, xs):.0%}{'✘' if med(k, xs) > p else '✔'}" for k in keys)
        print(f"  {sec:<28} n={len(xs):>3} · {cells} · السعر {p:.0%}")


asyncio.run(main())
