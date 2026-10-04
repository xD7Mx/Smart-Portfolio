"""كاشف: حوارُ المستشار الآليّ الحقيقيّ بجملة المالك نفسِها — بالوضعين (D589).

    docker exec sp_backend python /app/scripts/audit/autopilot_ask_door.py
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, "/app")
Q = "سدافكو افكر بالخروج منها لانها في مسار هابط وراس مالي هو قرض اريد بديل في مسار متوازن للسنوات المقبلة"


async def main():
    from app.core.portfolio_scope import install_scope_listeners, set_scope, reset_scope
    try:
        install_scope_listeners()
    except Exception:                                             # noqa: BLE001
        pass
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Portfolio
    from app.services.autopilot import ask
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio).execution_options(skip_portfolio_scope=True))).scalars().all()
    pid = next((p.id for p in ps if p.is_default), ps[0].id if ps else None)
    for mode in ("investor",):
        set_scope(pid, False)
        try:
            t0 = time.perf_counter()
            async with AsyncSessionLocal() as db:
                r = await ask(db, Q, mode=mode)
            print("@@ASK@@ " + json.dumps({"mode": mode, "s": round(time.perf_counter() - t0, 1), **r}, ensure_ascii=False, default=str)[:3500])
        finally:
            reset_scope()

asyncio.run(main())
