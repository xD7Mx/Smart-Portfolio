"""كاشفٌ (قراءةٌ فقط): ملفُّ قرار «الراجحي ريت» للمالك — مركزُه ووزنُه المستهدف، والمستشارُ،
والمعرفةُ المقروءة، والأقران — ليُبنى الرأيُ على أرقامه لا على افتراض.

    docker exec sp_backend python /app/scripts/audit/rajhi_reit_advisor.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


def out(tag, obj):
    print(f"@@{tag}@@ " + json.dumps(obj, ensure_ascii=False, default=str)[:3000])


async def main():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company, Holding
    from app.models.market import Allocation
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Company.symbol, Holding.portfolio_id, Holding.quantity, Holding.average_cost,
                                        Holding.invested_amount, Holding.market_value, Holding.weight,
                                        Holding.unrealized_profit_pct, Holding.total_dividends_received)
                                 .join(Holding, Holding.company_id == Company.id)
                                 .execution_options(skip_portfolio_scope=True))).all()
        al = (await db.execute(select(Company.symbol, Allocation.target_weight).join(Allocation, Allocation.company_id == Company.id)
                               .execution_options(skip_portfolio_scope=True))).all()
    tot = {}
    for r in rows:
        tot[r[1]] = tot.get(r[1], 0) + float(r[5] or 0)
    for r in rows:
        if r[0] == "4340":
            out("POSITION", {"portfolio": r[1], "qty": r[2], "avg_cost": r[3], "invested": r[4], "value": r[5], "weight": r[6],
                             "pnl_pct": r[7], "divs": r[8], "portfolio_value": tot.get(r[1])})
    out("TARGET", [(s, w) for s, w in al if s == "4340"])
    out("REITS_HELD", [(r[0], r[1], float(r[5] or 0)) for r in rows if r[0].startswith("43")])
    from app.services.reit_advisor import build
    from app.services.tadawul_market import row_for
    px = (row_for("4340") or {}).get("price")
    a = await build("4340", px) or {}
    out("ADVISOR", {k: a.get(k) for k in ("nav", "nav_date", "nav_change", "premium", "ttm", "yield", "trend", "last_amount",
                                          "next_expected", "overdue", "valuations")} | {"price": px})
    out("DISTS", [(d.get("eligibility"), d.get("amount"), d.get("nav")) for d in (a.get("distributions") or [])][-10:])
    from app.services.file_reader import coverage, knowledge
    out("KNOW_COV", coverage("4340"))
    for l in knowledge("4340", 20):
        print("   ", l)
    from app.services.analysis import analyze_company
    an = await analyze_company("4340.SR", None) or {}
    out("DECISION", {k: an.get(k) for k in ("decision", "fair_value", "fair_value_conf", "financial")})
    t = an.get("technical") or {}
    out("TECH", {k: t.get(k) for k in ("rsi", "support", "resistance", "trend", "pct_from_avg", "mean_basis")})


asyncio.run(main())
