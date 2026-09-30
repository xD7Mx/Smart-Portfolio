"""كاشفٌ (قراءةٌ فقط): وزنُ الراجحي ريت كما تحسبه صفحةُ التوزيع النسبي نفسُها — حصّتُه من السيولة.

    docker exec sp_backend python /app/scripts/audit/rajhi_reit_weight.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.core.database import AsyncSessionLocal
    from app.api.v1.endpoints.allocation import get_allocation
    async with AsyncSessionLocal() as db:
        res = await get_allocation(db)
    body = json.loads(res.body) if hasattr(res, "body") else res
    d = body.get("data") or body
    rows = d.get("items") or d.get("data") or d.get("holdings") or (d if isinstance(d, list) else [])
    print("@@KEYS@@", list(d.keys()) if isinstance(d, dict) else type(d).__name__)
    tw = 0
    for r in rows:
        tw += r.get("target_weight") or 0
        if r.get("symbol") == "4340":
            print("@@4340@@", json.dumps(r, ensure_ascii=False, default=str))
    print("@@SUM_TARGETS@@", round(tw, 2), "عدد", len(rows))
    print("@@TOTALS@@", json.dumps({k: v for k, v in d.items() if not isinstance(v, list)}, ensure_ascii=False, default=str)[:1500])


asyncio.run(main())
