"""
حزمة المراجعة — تُخرج أرقام المحفظة وحدها في ملفٍّ نصيّ صغير (بضعة كيلوبايت)
كي تُراجَع خارج الخادم بلا نقل قاعدة بيانات ولا أي بيانات شخصية.

لا تكتب في قاعدة البيانات شيئاً. تُشغَّل داخل حاوية backend:
    docker compose exec -T backend python /app/tools/review_export.py
"""
import asyncio, json, sys

sys.path.insert(0, "/app")


async def main() -> None:
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.portfolio import Holding, PortfolioSnapshot
    from app.models.transaction import Transaction, Cash, CashLedger

    out: dict = {}
    async with AsyncSessionLocal() as db:
        async def grab(key, coro):
            try:
                out[key] = await coro
            except Exception as e:                                # noqa: BLE001
                out[key] = {"تعذّر": str(e)[:200]}

        from app.services.integrity import run_integrity_check
        from app.services.performance import compute_performance
        from app.services.portfolio_return import (compute_production,
                                                   compute_reinvestment_pool,
                                                   compute_paid_in_capital)
        await grab("فحص السلامة", run_integrity_check(db))
        await grab("قياس الأداء", compute_performance(db))
        await grab("الإنتاج", compute_production(db))
        await grab("الحوض", compute_reinvestment_pool(db))
        await grab("رأس المال المدفوع", compute_paid_in_capital(db))

        rows = (await db.execute(select(Holding))).scalars().all()
        cos = {c.id: (c.symbol, c.company_name, c.sector) for c in
               (await db.execute(select(__import__("app.models.portfolio",
                fromlist=["Company"]).Company))).scalars().all()}
        out["الحيازات"] = [{
            "الرمز": cos.get(h.company_id, ("?",))[0],
            "القطاع": cos.get(h.company_id, ("", "", None))[2],
            "الكمية": float(h.quantity or 0),
            "متوسط التكلفة": float(h.average_cost or 0),
            "السعر": float(h.last_price or 0),
            "التكلفة": float(h.invested_amount or 0),
            "القيمة السوقية": float(h.market_value or 0),
            "فارق التسوية": float(getattr(h, "cost_basis_adjustment", 0) or 0),
            "أسهم منحة": float(h.total_bonus_shares or 0),
            "توزيعات": float(h.total_dividends_received or 0),
        } for h in rows]

        txs = (await db.execute(select(Transaction))).scalars().all()
        by_type: dict = {}
        for t in txs:
            k = str(t.transaction_type)
            b = by_type.setdefault(k, {"عدد": 0, "إجمالي": 0.0})
            b["عدد"] += 1
            b["إجمالي"] += float(t.total_amount or 0)
        out["العمليات"] = by_type
        out["عمليات موسومة"] = sum(1 for t in txs if t.funding_source)

        cash = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
        out["النقد"] = float(cash.available_cash or 0) if cash else 0.0
        led = (await db.execute(select(CashLedger))).scalars().all()
        out["حركات نقدية"] = len(led)
        out["إجمالي الإيداعات"] = sum(float(e.amount or 0) for e in led
                                      if str(e.kind).endswith("DEPOSIT"))

        snaps = (await db.execute(
            select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date))).scalars().all()
        out["اللقطات"] = {"عدد": len(snaps),
                          "من": snaps[0].snapshot_date.isoformat() if snaps else None,
                          "إلى": snaps[-1].snapshot_date.isoformat() if snaps else None}

    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


asyncio.run(main())
