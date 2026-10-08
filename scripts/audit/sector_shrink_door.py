#!/usr/bin/env python3
"""قياسُ D646 بالقاعدة المسجَّلة قبل القياس (`docs/ENGINES_V2.md`): وزنُ النماذج للقطاعات الستّة الموسومة. قارئٌ فقط.

القائمة: k ∈ {0.2 · 0.3 · 0.4 · 0.5 · 0.6} × خياراتُ الإصدار الأوّل الخمسة. التحقّقُ المتقاطع بإسقاط ورقة. الاعتماد: خطأُ
التحقّق ≤ خطأ السعر نفسِه − نقطةٌ مئوية كاملة."""
import asyncio, collections, json, statistics as st, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services.analysis import V1_UNCALIBRATED
from app.services.content_engine import fund_store_load
from app.services.market_screener import get_cached_screener
from app.services.fair_value_models import for_symbol

EV = {"peer_ev_ebit", "peer_ev_ebitda", "peer_ev_sales"}
MENU = {"الحالي": lambda m: False, "بلا EPV": lambda m: m["key"] == "epv",
        "بلا قيمة المنشأة": lambda m: m["key"] in EV, "بلا التدفّقات": lambda m: m["family"] == "cashflow",
        "بلا المضاعفات": lambda m: m["family"] == "multiples"}
KS = (0.2, 0.3, 0.4, 0.5, 0.6)
PAIRS = [(k, v) for k in KS for v in MENU]
MARGIN = 0.01


async def load():
    uni = main_market(MARKET_UNIVERSE)
    store = fund_store_load()
    rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    out = collections.defaultdict(list)
    for s, meta in uni.items():
        sec = meta.get("sector")
        if sec not in V1_UNCALIBRATED:
            continue
        r = rows.get(s) or {}
        at, px, fv = r.get("analyst_target"), r.get("price"), (store.get(s) or {}).get("fair_value")
        if not (isinstance(fv, (int, float)) and isinstance(at, (int, float)) and at > 0 and isinstance(px, (int, float)) and px > 0):
            continue
        f = await for_symbol(s) or {}
        ms = [{"key": m.get("key"), "family": m.get("family"), "value": m["value"]} for m in f.get("models") or []
              if isinstance(m.get("value"), (int, float)) and m["value"] > 0]
        if ms:
            out[sec].append({"s": s, "px": px, "at": at, "ms": ms})
    return out


def err(x, pair):
    k, v = pair
    vs = [m["value"] for m in x["ms"] if not MENU[v](m)] or [m["value"] for m in x["ms"]]
    return abs(x["px"] * (st.fmean(vs) / x["px"]) ** k / x["at"] - 1)


def best(xs):
    return min(PAIRS, key=lambda p: (st.median([err(x, p) for x in xs]), -p[0], p[1] != "الحالي"))


def main():
    data = asyncio.run(load())
    decisions = {}
    for sec, xs in sorted(data.items(), key=lambda kv: -len(kv[1])):
        if len(xs) < 5:
            print(f"  {sec}: n={len(xs)} — أقلُّ من خمس، لا يُحكم")
            continue
        price = st.median([abs(x["px"] / x["at"] - 1) for x in xs])
        b = best(xs)
        cv = st.median([err(x, best([y for y in xs if y is not x])) for x in xs])
        ok = cv <= price - MARGIN
        decisions[sec] = {"k": b[0], "variant": b[1], "cv": round(cv, 4), "price": round(price, 4), "adopt": ok}
        top = sorted(PAIRS, key=lambda p: st.median([err(x, p) for x in xs]))[:3]
        print(f"  {sec:<28} n={len(xs):>2} · السعر {price:.1%} · الأفضل k={b[0]} «{b[1]}» · التحقّقُ المتقاطع {cv:.1%} "
              f"← {'يُعتمد' if ok else 'لا يُعتمد'}\n      أعلى ثلاثة: " +
              " · ".join(f"k={p[0]} «{p[1]}» {st.median([err(x, p) for x in xs]):.1%}" for p in top))
    print("\n@@SHRINK@@" + json.dumps(decisions, ensure_ascii=False))


main()
