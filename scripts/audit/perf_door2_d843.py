#!/usr/bin/env python3
"""كاشفُ D843 (٢) على الخادم — أين يذهب زمنُ صفحة المحفظة، وأيُّ خطوةٍ تحبس الخادمَ كلَّه (حلقةُ الأحداث) فتنتظرها الطلباتُ الأخرى.
لكلّ خطوة: زمنُها، وأطولُ توقّفٍ للحلقة أثناءها (ساعةٌ تدقّ كلَّ 20ms — إن تأخّرت فشيءٌ متزامنٌ يحبسها). قراءةٌ فقط.

    docker exec sp_backend python /app/scripts/audit/perf_door2_d843.py
"""
import asyncio
import sys
import time

sys.path.insert(0, "/app")


async def main():
    from app.core.database import AsyncSessionLocal
    from app.api.v1.endpoints import portfolio as PE
    from app.api.v1.endpoints import goals as GE
    from app.services import portfolio_return as PR
    from app.services.market_data import market_service as M
    lag = {"max": 0.0}
    stop = False

    async def tick():
        t = time.monotonic()
        while not stop:
            await asyncio.sleep(0.02)
            n = time.monotonic()
            lag["max"] = max(lag["max"], n - t - 0.02)
            t = n
    tk = asyncio.create_task(tick())

    async def step(name, fn):
        lag["max"] = 0.0
        t0 = time.monotonic()
        try:
            async with AsyncSessionLocal() as db:
                await fn(db)
            st = "ok"
        except Exception as e:                                   # noqa: BLE001
            st = type(e).__name__
        print(f"   {name:34} {(time.monotonic() - t0) * 1000:7.0f}ms · أطولُ حبسٍ للخادم {lag['max'] * 1000:6.0f}ms · {st}")

    for rnd in ("أوّلاً", "ثانياً"):
        print(f"══ {rnd}")
        await step("_get_holdings", PE._get_holdings)
        await step("compute_production", PR.compute_production)
        await step("compute_true_total_return_pct", PR.compute_true_total_return_pct)
        await step("compute_reinvestment_pool", PR.compute_reinvestment_pool)
        await step("compute_net_profit", PR.compute_net_profit)
        await step("GET /portfolio/summary", PE.get_portfolio_summary)
        await step("GET /portfolio/metrics", PE.get_portfolio_metrics)
        await step("GET /goals/builtin", GE.get_builtin_goals)
        await step("GET /goals/progress", GE.get_goals_progress)
        await step("GET /goals/income-timeline", GE.get_income_timeline)
        await step("history BZ=F 6mo", lambda db: M.get_history("BZ=F", "6mo"))
        await step("history ^TASI.SR 6mo", lambda db: M.get_history("^TASI.SR", "6mo"))
    print("══ معاً كما يطلبها المتصفّح (المحفظةُ الخمسة)")
    lag["max"] = 0.0
    t0 = time.monotonic()

    async def w(fn):
        async with AsyncSessionLocal() as db:
            await fn(db)
    await asyncio.gather(w(PE.get_portfolio_summary), w(PE.get_portfolio_metrics), w(GE.get_builtin_goals), w(GE.get_goals_progress), w(GE.get_income_timeline),
                         return_exceptions=True)
    print(f"   الخمسة معاً {(time.monotonic() - t0) * 1000:.0f}ms · أطولُ حبسٍ {lag['max'] * 1000:.0f}ms")
    stop = True
    await tk

asyncio.run(main())
