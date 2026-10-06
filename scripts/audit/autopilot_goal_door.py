"""كاشف (قراءةٌ فقط · D605–D609): المستشارُ حيّاً على القوائم الجديدة — رأيُه، والعائدُ المركّبُ مقابلَ المؤشرات،
وخطةُ الهدف في أربع سنوات (نقطةُ الخطة والحوار).

    docker exec sp_backend python /app/scripts/audit/autopilot_goal_door.py
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, "/app")


async def main():
    from app.core.portfolio_scope import install_scope_listeners, set_scope
    try:
        install_scope_listeners()
    except Exception:                                             # noqa: BLE001
        pass
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Portfolio
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio).execution_options(skip_portfolio_scope=True))).scalars().all()
    pid = next((p.id for p in ps if p.is_default), ps[0].id if ps else None)
    set_scope(pid, False)
    from app.services.autopilot import opinion, ask
    from app.services.portfolio_return import unified_cagr_pct
    from app.api.v1.endpoints.ai import get_autopilot_plan
    from app.api.v1.endpoints.portfolio import get_portfolio_metrics as _m  # noqa: F401
    t0 = time.perf_counter()
    async with AsyncSessionLocal() as db:
        o = await opinion(db, force=True)
    print("@@AP@@ " + json.dumps({"s": round(time.perf_counter() - t0, 1), **{k: o.get(k) for k in
          ("source", "verdict", "goal", "actions", "flags")}}, ensure_ascii=False, default=str)[:3500], flush=True)
    async with AsyncSessionLocal() as db:
        c = await unified_cagr_pct(db)
        r = await get_autopilot_plan(4, db)
    print("@@CAGR@@", c, flush=True)
    print("@@PLAN@@ " + r.body.decode()[:2000], flush=True)
    async with AsyncSessionLocal() as db:
        a = await ask(db, "اريد الوصول للهدف خلال اربع سنوات ماذا افعل واغير")
    print("@@ASK@@ " + json.dumps(a, ensure_ascii=False, default=str)[:2500], flush=True)

asyncio.run(main())
