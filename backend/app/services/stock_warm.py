"""‏D581: صفحاتُ أسهم المحفظة والمراقبة جاهزةٌ قبل أن تُفتح.

قِيس (كاشف tabs_timing_door): كلُّ نداءٍ في تبويبات صفحة السهم سريعٌ متى خُزِّن (0.01–0.8 ثانية)، وأوّلُ فتحٍ
بطيء: السلامةُ المالية 30–56 ثانية، وتوصياتُ المحلّلين حتى 41، ونماذجُ القيمة العادلة 21، والمفكرةُ والتحليل
والتوزيعاتُ 4–5 ثوانٍ. فتُحسب مسبقاً لما يفتحه المالكُ فعلاً — شركاتُ المحافظ وقوائمُ المراقبة — صباحاً وبعد الإغلاق.
"""
from __future__ import annotations

import asyncio
import time

from loguru import logger


async def targets() -> list[tuple[str, str]]:
    """(الرمز، الاسم) لشركات المحافظ كلِّها ثمّ قوائم المراقبة — بلا تكرار."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company, Holding
    from app.models.market import Watchlist
    seen: dict[str, str] = {}
    async with AsyncSessionLocal() as db:
        q = select(Company.symbol, Company.company_name).join(Holding, Holding.company_id == Company.id).distinct()
        for s, n in (await db.execute(q.execution_options(skip_portfolio_scope=True))).all():
            if s:
                seen.setdefault(str(s).replace(".SR", ""), n or "")
        q = select(Watchlist.symbol).order_by(Watchlist.sort_order.asc(), Watchlist.id.asc())
        for s, in (await db.execute(q.execution_options(skip_portfolio_scope=True))).all():
            if s:
                seen.setdefault(str(s).replace(".SR", ""), "")
        miss = [s for s, n in seen.items() if not n]
        if miss:
            q = select(Company.symbol, Company.company_name).where(Company.symbol.in_(miss + [m + ".SR" for m in miss]))
            for s, n in (await db.execute(q.execution_options(skip_portfolio_scope=True))).all():
                seen[str(s).replace(".SR", "")] = n or ""
    return list(seen.items())


async def warm_one(sym: str, name: str = "") -> dict:
    from app.api.v1.endpoints import market as M
    from app.services.analysis import analyze_company
    t0, out = time.perf_counter(), {}
    for label, coro in (("company", lambda: analyze_company(f"{sym}.SR", name or None)),
                        ("fvm", lambda: M.get_fair_value_models(sym)),
                        ("health", lambda: M.get_financial_health(sym)),
                        ("recs", lambda: M.get_company_recommendations(sym)),
                        ("events", lambda: M.get_company_events(sym, name or "")),
                        ("divs", lambda: M.get_company_dividends(sym))):
        try:
            await asyncio.wait_for(coro(), timeout=240)       # خلفيٌّ: قطاعُ المواد أكثرُ الأقران (2020 تجاوز 90 ث)
            out[label] = "ok"
        except Exception as e:                                    # noqa: BLE001
            out[label] = type(e).__name__
    out["s"] = round(time.perf_counter() - t0, 1)
    return out


async def warm(conc: int = 2) -> dict:
    ts = await targets()
    sem = asyncio.Semaphore(conc)
    rep: dict = {}

    async def one(sym, name):
        async with sem:
            rep[sym] = await warm_one(sym, name)
    t0 = time.perf_counter()
    await asyncio.gather(*(one(s, n) for s, n in ts))
    fails = {s: {k: v for k, v in r.items() if v not in ("ok",) and k != "s"} for s, r in rep.items()}
    summary = {"companies": len(ts), "seconds": round(time.perf_counter() - t0, 1),
               "failed": {s: f for s, f in fails.items() if f}}
    logger.info(f"تجهيزُ صفحات الأسهم: {summary}")
    # سجلٌّ يُقرأ: متى جرى، وفي أيّ عمليةٍ (الخادمُ الحيُّ لا عمليةٌ أخرى)، وزمنُ كلِّ شركة
    try:
        import os
        from datetime import datetime, timezone
        from app.services import lastgood
        lastgood.save("stock_warm:_last", {**summary, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                           "pid": os.getpid(), "per": {s: r.get("s") for s, r in rep.items()}})
    except Exception:                                             # noqa: BLE001
        pass
    return summary
