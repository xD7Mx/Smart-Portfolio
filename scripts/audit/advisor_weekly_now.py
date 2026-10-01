"""يبني ورقةَ المراجعة الأسبوعية للمحفظة الأولى ويطبعها — **بلا إرسالٍ للمالك** (D571).

    docker exec sp_backend python /app/scripts/audit/advisor_weekly_now.py
"""
import asyncio
import sys
import time

sys.path.insert(0, "/app")


async def main():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.portfolio_scope import reset_scope, set_scope
    from app.models.portfolio import Portfolio
    from app.services.advisor_weekly import review
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio.id, Portfolio.name).where(Portfolio.is_archived.is_(False)).order_by(Portfolio.id))).all()
        print("@@PORTFOLIOS@@", ps)
        pid = ps[0][0]
        set_scope(pid, False)
        t0 = time.time()
        try:
            r = await review(db)
        finally:
            reset_scope()
        print("@@TIME@@", round(time.time() - t0), "ث", "@@ROWS@@", len(r["rows"]), "@@LEN@@", len(r["text"]))
        print(r["text"])


asyncio.run(main())
