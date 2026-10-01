"""تنظيف: نصائحُ وهميةٌ حُفظت للمحفظة المضاربية (الفارغة) من اختبارٍ بلا عزل — تُطوى (D573).

    docker exec sp_backend python /app/scripts/audit/advisor_cleanup_pid2.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from sqlalchemy import select, func
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Holding
    from app.services import lastgood
    async with AsyncSessionLocal() as db:
        live = {pid for pid, n in (await db.execute(select(Holding.portfolio_id, func.count()).where(Holding.quantity > 0)
                                                    .group_by(Holding.portfolio_id)
                                                    .execution_options(skip_portfolio_scope=True))).all() if n}
    print("@@LIVE_PIDS@@", live)
    n = 0
    for k in lastgood.keys_with_prefix("advice:"):
        parts = k.split(":")
        if len(parts) == 3 and parts[1].isdigit() and int(parts[1]) not in live:
            a = lastgood.load(k) or {}
            if a.get("status") == "active":
                a["status"] = "superseded"
                lastgood.save(k, a)
                n += 1
    print("@@SUPERSEDED@@", n)


asyncio.run(main())
