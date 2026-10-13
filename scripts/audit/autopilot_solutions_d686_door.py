"""كاشف: ما يراه المالكُ في المستشار الآليّ بعد D686 — الهدفُ المحرَّر ومقدارُه، و«حلولٌ نحو هدفك» ومصادرُها — قراءةٌ فقط.

لا يُجبَر توليدٌ جديد (‏force=False): يُقرأ الرأيُ المحفوظ كما تعرضه الشاشة، فإن لم يكن محفوظاً وُلِّد مرّةً كما يولّده فتحُ الصفحة.

    docker exec sp_backend python /app/scripts/audit/autopilot_solutions_d686_door.py
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
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Portfolio
    from app.services.autopilot import opinion
    from app.services import cache
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio).execution_options(skip_portfolio_scope=True))).scalars().all()
    pid = next((p.id for p in ps if p.is_default), ps[0].id if ps else None)
    set_scope(pid, False)
    try:
        t0 = time.perf_counter()
        async with AsyncSessionLocal() as db:
            o = await opinion(db, force=False, mode="investor")
        sol = o.get("solutions") or []
        print("@@AP@@ " + json.dumps({"s": round(time.perf_counter() - t0, 1), "source": o.get("source"), "goal": o.get("goal"),
                                      "solutions_n": len(sol), "solutions": sol[:6], "verdict": o.get("verdict"),
                                      "actions": (o.get("actions") or [])[:4]}, ensure_ascii=False)[:5000])
        from app.services import autopilot as AP
        try:
            held = {str(x.get("symbol")) for x in (o.get("positions_live") or o.get("positions") or []) if isinstance(x, dict)}
            alt = AP._market_alternatives(held)
            fc = await AP._forecast_digest()
            print("@@FEED@@ " + json.dumps({"alternatives_n": len(alt or []), "alternatives": (alt or [])[:4],
                                            "forecasts_n": len(fc or []), "forecasts": (fc or [])[:3]},
                                           ensure_ascii=False, default=str)[:3000])
        except Exception as e:                                    # noqa: BLE001
            print("@@FEED@@ تعذّر:", type(e).__name__, str(e)[:160])
    finally:
        reset_scope()
    try:
        from app.api.v1.endpoints import goals as G
        print("@@GOAL@@ " + json.dumps(G._load_builtin_cfg(), ensure_ascii=False, default=str)[:600])
    except Exception as e:                                        # noqa: BLE001
        print("@@GOAL@@ تعذّر:", type(e).__name__, str(e)[:120])

asyncio.run(main())
