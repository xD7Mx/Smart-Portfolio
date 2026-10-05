"""إجراءٌ محصور (D596): قراءةُ جدول «المعلومات المالية» للسوق كلِّه الآن — بدل انتظار الليل.

    docker exec sp_backend python /app/scripts/audit/tfin_fill.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services.tadawul_financials import refresh, read
    rep = await refresh()
    print("@@REPORT@@", rep, flush=True)
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    lat = {}
    for s in main_market(MARKET_UNIVERSE):
        r = read(str(s).replace(".SR", "")) or {}
        q = [p["as_of"] for p in (r.get("quarterly") or []) + (r.get("annual") or [])]
        k = max(q)[:7] if q else "none"
        lat[k] = lat.get(k, 0) + 1
    print("@@LATEST@@", dict(sorted(lat.items(), reverse=True)), flush=True)
    from app.services import cache
    cache.flush()

asyncio.run(main())
