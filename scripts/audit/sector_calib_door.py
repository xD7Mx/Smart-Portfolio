#!/usr/bin/env python3
"""المعايرةُ الأخيرة للسعر العادل — بالقاعدة المسجَّلة قبل القياس في `docs/ENGINES_V1.md`. قارئٌ فقط.

قائمةٌ مغلقة: الحالي · بلا EPV · بلا عائلة قيمة المنشأة · بلا عائلة التدفّقات · بلا عائلة المضاعفات.
k = 0.6 ثابت. لكلّ قطاعٍ (≥ 5): الخيارُ الأفضل على القطاع كلّه، وخطأُ التحقّق المتقاطع بإسقاط ورقةٍ واحدة
(يُختار الخيارُ على البقية ويُقاس على الساقطة). يُعتمد للقطاع الساقط فقط، وإن تفوّق على السعر نفسِه في التحقّق."""
import asyncio, collections, json, statistics as st, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services.content_engine import fund_store_load
from app.services.market_screener import get_cached_screener
from app.services.fair_value_models import for_symbol, MARKET_BLEND_K as K

EV = {"peer_ev_ebit", "peer_ev_ebitda", "peer_ev_sales"}
MENU = {
    "الحالي": lambda m: False,
    "بلا EPV": lambda m: m["key"] == "epv",
    "بلا قيمة المنشأة": lambda m: m["key"] in EV,
    "بلا التدفّقات": lambda m: m["family"] == "cashflow",
    "بلا المضاعفات": lambda m: m["family"] == "multiples",
}


async def load():
    uni = main_market(MARKET_UNIVERSE)
    store = fund_store_load()
    rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    out = []
    for s, meta in uni.items():
        r = rows.get(s) or {}
        at, px, fv = r.get("analyst_target"), r.get("price"), (store.get(s) or {}).get("fair_value")
        if not (isinstance(fv, (int, float)) and isinstance(at, (int, float)) and at > 0 and isinstance(px, (int, float)) and px > 0):
            continue
        f = await for_symbol(s) or {}
        ms = [{"key": m.get("key"), "family": m.get("family"), "value": m["value"]} for m in f.get("models") or []
              if isinstance(m.get("value"), (int, float)) and m["value"] > 0]
        if ms:
            out.append({"s": s, "sec": meta.get("sector_ar") or meta.get("sector") or "—", "px": px, "at": at, "fv": fv, "ms": ms})
    return out


def err(x, variant):
    drop = MENU[variant]
    vs = [m["value"] for m in x["ms"] if not drop(m)] or [m["value"] for m in x["ms"]]
    val = x["px"] * (st.fmean(vs) / x["px"]) ** K
    return abs(val / x["at"] - 1)


def best(xs):
    return min(MENU, key=lambda v: (st.median([err(x, v) for x in xs]), v != "الحالي"))


def main():
    data = asyncio.run(load())
    by = collections.defaultdict(list)
    for x in data:
        by[x["sec"]].append(x)
    print(f"أوراقٌ لها نماذجُ وهدفٌ وسعر: {len(data)}\n")
    decisions = {}
    for sec, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        if len(xs) < 5:
            continue
        price = st.median([abs(x["px"] / x["at"] - 1) for x in xs])
        published = st.median([abs(x["fv"] / x["at"] - 1) for x in xs])
        cur = st.median([err(x, "الحالي") for x in xs])
        b = best(xs)
        cv = st.median([err(x, best([y for y in xs if y is not x])) for x in xs])
        failing = published > price
        adopt = failing and cv < price
        verdict = ("يجتاز أصلاً — لا يُمسّ" if not failing else
                   f"يُعتمد «{b}»" if adopt else "لم يجتز المعايرة ← ثقةٌ منخفضة واستبعادٌ من ترتيب المختبر")
        decisions[sec] = {"failing": failing, "adopt": b if adopt else None, "flag": failing and not adopt}
        cells = " · ".join(f"{v} {st.median([err(x, v) for x in xs]):.0%}" for v in MENU)
        print(f"  {sec:<28} n={len(xs):>3} · المنشور {published:.0%} · السعر {price:.0%} · محاكاةُ الحالي {cur:.0%}\n"
              f"      {cells}\n      الأفضل «{b}» · التحقّقُ المتقاطع {cv:.0%} ← {verdict}")
    print("\n@@DECISIONS@@" + json.dumps(decisions, ensure_ascii=False))


main()
