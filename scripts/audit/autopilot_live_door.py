"""كاشف: الطيارُ الآليّ الحقيقيّ — يدرس المكتبةَ أوّلاً، ثمّ رأيُ كلّ وضعٍ للمحفظة الافتراضية، بزمنه وذاكرة الخادم (D585–D588).

    docker exec sp_backend python /app/scripts/audit/autopilot_live_door.py
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, "/app")


async def main():
    from app.core.portfolio_scope import install_scope_listeners, set_scope, reset_scope
    try:
        install_scope_listeners()
    except Exception:                                             # noqa: BLE001
        pass
    from app.services.tadawul_pdf import mem_available_mb
    print("@@MEM_START@@", mem_available_mb())
    from app.services.library_wisdom import digest_all, principles
    t0 = time.perf_counter()
    rep = await digest_all()
    print("@@LIB@@ " + json.dumps({**rep, "s": round(time.perf_counter() - t0, 1), "sample": principles(6)}, ensure_ascii=False)[:2500])
    print("@@MEM_AFTER_LIB@@", mem_available_mb())
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Portfolio
    from app.services.autopilot import opinion
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio).execution_options(skip_portfolio_scope=True))).scalars().all()
    pid = next((p.id for p in ps if p.is_default), ps[0].id if ps else None)
    for mode in ("investor",):
        set_scope(pid, False)
        try:
            t0 = time.perf_counter()
            async with AsyncSessionLocal() as db:
                o = await opinion(db, force=True, mode=mode)
            print("@@AP@@ " + json.dumps({"mode": mode, "s": round(time.perf_counter() - t0, 1), **{k: o.get(k) for k in
                  ("source", "verdict", "goal", "points", "actions", "protections", "principles", "flags")}}, ensure_ascii=False)[:4000])
        finally:
            reset_scope()
    print("@@MEM_END@@", mem_available_mb())

asyncio.run(main())
