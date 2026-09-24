#!/usr/bin/env python3
"""حدّةُ وزن التشابه بين الأقران: أيُّ حصّةٍ ثابتةٍ أقربُ للمحللين؟ قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fvm_sim_floor.py

وزنُ القرين = الحصّةُ الثابتة + (1 − الحصّة) × التشابه. الحصّةُ 1 أوزانٌ متساوية.
يُقاس خطأُ النماذج وحدها (لا المزيج) وخطأُ مضاعفات الأقران، للسوق كلّه ولكلّ قطاع.
"""
import asyncio, collections, math, statistics, sys
sys.path.insert(0, "/app")

FLOORS = (1.0, 0.75, 0.5, 0.25, 0.05)
PEER = {"peer_pe", "peer_pb", "peer_ps", "peer_pocf", "peer_ev_ebit", "peer_ev_sales"}


def err(xs):
    return math.exp(statistics.median(abs(math.log(x)) for x in xs)) - 1 if xs else float("nan")


async def main():
    from app.services import fair_value_models as F
    from app.services.market_screener import get_cached_screener
    rows = [x for x in (get_cached_screener() or [])
            if isinstance(x.get("analyst_target"), (int, float)) and x["analyst_target"] > 0]
    res = {f: collections.defaultdict(list) for f in FLOORS}
    peer = {f: [] for f in FLOORS}
    for f in FLOORS:
        F.SIM_FLOOR = f
        for x in rows:
            try:
                i = await F.gather(x["symbol"])
                r = F.value(i) if i else None
            except Exception:                                      # noqa: BLE001
                r = None
            if r and isinstance(r.get("value"), (int, float)) and r["value"] > 0:
                q = r["value"] / x["analyst_target"]
                res[f]["*"].append(q); res[f][i.sector].append(q)
                peer[f] += [m["value"] / x["analyst_target"] for m in r["models"] if m["key"] in PEER]
    print("الحصّةُ الثابتة → خطأُ السوق · ±25٪ · خطأُ نماذج الأقران")
    for f in FLOORS:
        xs = res[f]["*"]
        print(f"  {f:4}: {err(xs):.0%} · {sum(.75 <= v <= 1.25 for v in xs) / max(len(xs), 1):.0%} · n={len(xs)} · أقران {err(peer[f]):.0%}")
    print("\nلكلّ قطاع:")
    for sec in sorted({k for f in FLOORS for k in res[f] if k != "*"}, key=lambda k: -len(res[1.0][k])):
        print(f"  {sec[:34]:36} n={len(res[1.0][sec]):2} · " + " · ".join(f"{f}: {err(res[f][sec]):.0%}" for f in FLOORS))
    return 0

sys.exit(asyncio.run(main()))
