"""كاشفٌ يكتب المخزَّنَ وحده: تجهيزُ صفحات أسهم السوق كلِّه الآن، ثمّ قياسُ أوّل فتحٍ لعيّنةٍ من خارج المحافظ — D583.

    docker exec sp_backend python /app/scripts/audit/market_warm_now.py
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, "/app")


async def main():
    from app.services.stock_warm import warm_market, targets
    rep = await warm_market()
    from app.api.v1.endpoints import market as M
    mine = {s for s, _ in await targets()}
    sample = [s for s in ("1180", "2350", "4200", "6010", "8230", "2381") if s not in mine][:4]
    t = {}
    for s in sample:
        r = {}
        for lab, f in (("health", lambda: M.get_financial_health(s)), ("recs", lambda: M.get_company_recommendations(s)),
                       ("events", lambda: M.get_company_events(s, ""))):
            t0 = time.perf_counter(); await f(); r[lab] = round(time.perf_counter() - t0, 2)
        t[s] = r
    print("@@MKT@@ " + json.dumps({"warm": rep, "first_open_after": t}, ensure_ascii=False)[:3000])

asyncio.run(main())
