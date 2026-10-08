#!/usr/bin/env python3
"""انحيازُ كلِّ نموذجٍ ومحاكاةُ حذفه — بمسطرة البوابة (‏D632). قارئٌ فقط: لا يكتب شيئاً.

لكلّ نموذج: وسيطُ (النموذج ÷ السعر) و(النموذج ÷ الهدف) وعددُه. ثمّ يُحاكى حذفُه من كلّ ورقة: الخامُ متوسّطُ
البقية (‏جمعُ InvestingPro)، والقيمةُ = السعر^0.4 × الخام^0.6 كما في المحرّك، ويُقاس وسيطُ السوق وكلُّ قطاعٍ
مقابل السعر نفسِه. لا يُحذف نموذجٌ إلا إن حسّن السوقَ كلَّه — لا القطاعاتِ الساقطةَ وحدها."""
import asyncio, collections, statistics as st, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services.content_engine import fund_store_load
from app.services.market_screener import get_cached_screener
from app.services.fair_value_models import for_symbol, MARKET_BLEND_K as K

uni = main_market(MARKET_UNIVERSE)
store = fund_store_load()
rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}


async def load():
    out = []
    for s, meta in uni.items():
        r = rows.get(s) or {}
        at, px = r.get("analyst_target"), r.get("price")
        fv = (store.get(s) or {}).get("fair_value")
        if not (isinstance(fv, (int, float)) and isinstance(at, (int, float)) and at > 0 and isinstance(px, (int, float)) and px > 0):
            continue
        f = await for_symbol(s) or {}
        ms = [(m.get("key"), m["value"]) for m in f.get("models") or [] if isinstance(m.get("value"), (int, float)) and m["value"] > 0]
        if ms:
            out.append({"s": s, "sec": meta.get("sector_ar") or meta.get("sector") or "—", "px": px, "at": at, "ms": ms})
    return out


def score(data, drop=frozenset()):
    by = collections.defaultdict(list)
    allv = []
    for x in data:
        vs = [v for k, v in x["ms"] if k not in drop] or [v for _, v in x["ms"]]
        raw = st.fmean(vs)
        val = x["px"] * (raw / x["px"]) ** K
        e = abs(val / x["at"] - 1)
        by[x["sec"]].append(e)
        allv.append(e)
    return st.median(allv), {k: st.median(v) for k, v in by.items() if len(v) >= 5}


def main():
    data = asyncio.run(load())
    px_sec = collections.defaultdict(list)
    for x in data:
        px_sec[x["sec"]].append(abs(x["px"] / x["at"] - 1))
    px_med = {k: st.median(v) for k, v in px_sec.items() if len(v) >= 5}
    print(f"أوراقٌ لها نماذجُ وهدفٌ وسعر: {len(data)}")

    print("\n══ انحيازُ كلِّ نموذج (وسيط) ══")
    bias = collections.defaultdict(lambda: ([], []))
    for x in data:
        for k, v in x["ms"]:
            bias[k][0].append(v / x["px"]); bias[k][1].append(v / x["at"])
    for k, (p, t) in sorted(bias.items(), key=lambda kv: st.median(kv[1][1])):
        print(f"  {k:<16} n={len(p):>3} · ÷السعر {st.median(p):.2f} · ÷الهدف {st.median(t):.2f} · |÷الهدف−1| {st.median([abs(a-1) for a in t]):.0%}")

    base_m, base_s = score(data)
    fails = lambda sm: sorted(k for k, v in sm.items() if k in px_med and v > px_med[k])
    print(f"\n══ الأساس (محاكاةٌ بكلّ النماذج) ══ السوق {base_m:.1%} · الساقطة: {fails(base_s)}")
    print("\n══ حذفُ نموذجٍ واحد ══")
    for k in sorted(bias):
        m, sm = score(data, frozenset({k}))
        print(f"  بلا {k:<16} السوق {m:.1%} ({(m-base_m)*100:+.1f}) · ساقطة {len(fails(sm))}: {fails(sm)}")
    print("\n══ القطاعات: الأساس مقابل السعر نفسِه ══")
    for k in sorted(base_s, key=lambda k: -base_s[k]):
        print(f"  {k:<28} محرّك {base_s[k]:.0%} · السعر {px_med.get(k, float('nan')):.0%}")


main()
