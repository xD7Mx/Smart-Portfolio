"""كاشف (قراءةٌ فقط): هل اكتمل السعرُ العادل؟ — تغطيتُه وثقتُه وأسبابُ امتناعه وشواذُّه، للسوق ولشركات المحافظ.

    docker exec sp_backend python /app/scripts/audit/fv_census_door.py
"""
import asyncio
import json
import sys
from collections import Counter

sys.path.insert(0, "/app")


async def main():
    from app.services.market_screener import get_cached_screener
    from app.services.stock_warm import targets
    rows = get_cached_screener() or []
    has = [r for r in rows if r.get("fair_value")]
    conf = Counter(str(r.get("fair_value_conf")) for r in has)
    why = Counter(str(r.get("fair_value_unavailable") or "بلا سبب")[:70] for r in rows if not r.get("fair_value"))
    def up(r):
        try:
            return float(r["fair_value"]) / float(r["price"]) * 100 - 100
        except Exception:                                         # noqa: BLE001
            return None
    outl = sorted([(r["symbol"], r.get("name"), r.get("price"), r.get("fair_value"), round(up(r), 1), r.get("fair_value_conf"))
                   for r in has if up(r) is not None and (up(r) > 80 or up(r) < -50)], key=lambda x: -abs(x[4]))
    mine = {s for s, _ in await targets()}
    port = [(r["symbol"], r.get("name"), r.get("price"), r.get("fair_value"), round(up(r), 1) if up(r) is not None else None,
             r.get("fair_value_conf"), r.get("fair_value_stale")) for r in rows if str(r.get("symbol")).replace(".SR", "") in mine]
    print("@@FV@@ " + json.dumps({"rows": len(rows), "with_fv": len(has), "conf": conf.most_common(), "missing_why": why.most_common(8),
                                  "outliers": outl[:15], "n_outliers": len(outl), "portfolio": port}, ensure_ascii=False, default=str)[:6000])

asyncio.run(main())
