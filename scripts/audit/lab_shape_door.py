"""كاشف (قراءةٌ فقط · D613): شكلُ ردّ مختبر الأبحاث الحقيقيّ وصفِّ الفرز — لمطابقة الواجهة عليه.

    docker exec sp_backend python /app/scripts/audit/lab_shape_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services.stars_backtest import lab
    from app.services.market_screener import get_cached_screener
    r = await lab(["2222", "1120", "4002"], "2015-01")
    if r:
        r = {**r, "track": (r.get("track") or [])[:3]}
    print("@@LAB@@ " + json.dumps(r, ensure_ascii=False, default=str)[:3000], flush=True)
    rows = get_cached_screener() or []
    one = next((x for x in rows if str(x.get("symbol")).startswith("2222")), rows[0] if rows else {})
    print("@@ROW@@ " + json.dumps({k: (type(v).__name__, str(v)[:80]) for k, v in one.items()}, ensure_ascii=False)[:3000], flush=True)

asyncio.run(main())
