"""تشخيص (قراءةٌ فقط): ما أُرسل للمالك من المتابعة، ولماذا تطابقت ورقتا المحفظتين، ولماذا قرارُ الراجحي ريت «غير كافية».

    docker exec sp_backend python /app/scripts/audit/advisor_diag2.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from sqlalchemy import select, func
    from app.core.database import AsyncSessionLocal
    from app.core.portfolio_scope import reset_scope, set_scope
    from app.models.market import Notification, Cash
    from app.models.portfolio import Holding, Portfolio
    async with AsyncSessionLocal() as db:
        ns = (await db.execute(select(Notification.created_at, Notification.title, Notification.message)
                               .where(Notification.category == "advisor").order_by(Notification.created_at.desc()).limit(3)
                               .execution_options(skip_portfolio_scope=True))).all()
        for n in ns:
            print("@@SENT@@", n[0], n[1], "\n", n[2][:800])
        rows = (await db.execute(select(Holding.portfolio_id, func.count(), func.sum(Holding.market_value))
                                 .group_by(Holding.portfolio_id).execution_options(skip_portfolio_scope=True))).all()
        print("@@HOLDINGS_BY_PID@@", rows)
        cash = (await db.execute(select(Cash.portfolio_id, Cash.available_cash).execution_options(skip_portfolio_scope=True))).all() \
            if hasattr(Cash, "portfolio_id") else "Cash بلا portfolio_id"
        print("@@CASH@@", cash)
        for pid in (1, 2):
            set_scope(pid, False)
            try:
                c = (await db.execute(select(func.count(), func.sum(Holding.market_value)))).one()
                print("@@SCOPED@@", pid, c)
            finally:
                reset_scope()
        from app.services.analysis import analyze_company
        a = await analyze_company("4340.SR", None, db=db) or {}
        print("@@4340@@", json.dumps({k: a.get(k) for k in ("decision", "fair_value", "fair_value_conf", "fair_value_source",
                                                            "data_quality", "financial")}, ensure_ascii=False, default=str)[:1500])


asyncio.run(main())
