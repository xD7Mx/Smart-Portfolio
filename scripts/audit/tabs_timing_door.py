"""كاشف (قراءةٌ فقط): زمنُ كلِّ نداءٍ تطلبه تبويباتُ صفحة السهم — أوّلَ مرّةٍ وثانيَها — داخلَ تطبيقٍ في الذاكرة
بلا مصادقة (تُتجاوز في هذا الكاشف وحدَه)، فيُعرف أيُّ تبويبٍ يُبطئ ولماذا.

    docker exec sp_backend python /app/scripts/audit/tabs_timing_door.py
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, "/app")


async def main():
    import httpx
    from main import app
    from app.core.auth import require_auth
    app.dependency_overrides[require_auth] = lambda: None
    from app.core.portfolio_scope import install_scope_listeners
    try:
        install_scope_listeners()
    except Exception:                                             # noqa: BLE001
        pass
    paths = ["/market/company/{s}.SR", "/market/fair-value-models/{s}", "/market/financials/{s}.SR?period=annual",
             "/market/financials/{s}.SR?period=quarterly", "/market/events/{s}", "/market/quarter-reports/{s}",
             "/market/dividends/{s}", "/market/history/{s}.SR?range=1y", "/market/ownership/{s}",
             "/market/health/{s}", "/market/frames/{s}", "/market/recommendations/{s}", "/market/depth/{s}"]
    out = {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t/api/v1", timeout=120) as c:
        for s in ("1120", "4340", "2280"):
            row = {}
            for p in paths:
                u = p.format(s=s)
                ts = []
                for _ in range(2):
                    t0 = time.perf_counter()
                    try:
                        r = await c.get(u)
                        st = r.status_code
                    except Exception as e:                        # noqa: BLE001
                        st = type(e).__name__
                    ts.append(round(time.perf_counter() - t0, 2))
                row[p.split("/")[2] + ("?q" if "quarterly" in p else "")] = [st] + ts
            out[s] = row
            print("@@T@@ " + json.dumps({s: row}, ensure_ascii=False))

asyncio.run(main())
