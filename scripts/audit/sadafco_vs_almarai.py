"""كاشفٌ (قراءةٌ فقط): سدافكو (2270) مقابل المراعي (2280) لقرار المالك — مركزُه، والقرارُ والدرجةُ
والسعرُ العادل، والفنيّ، والأبحاث، والمعرفةُ المقروءة من الملفّات، والتوزيعات، والمؤتمرات.

    docker exec sp_backend python /app/scripts/audit/sadafco_vs_almarai.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


def out(tag, obj):
    print(f"@@{tag}@@ " + json.dumps(obj, ensure_ascii=False, default=str)[:3500])


async def main():
    from app.core.database import AsyncSessionLocal
    from app.api.v1.endpoints.allocation import get_allocation
    from sqlalchemy import select
    from app.models.portfolio import Company, Holding
    async with AsyncSessionLocal() as db:
        res = await get_allocation(db)
        rows = (await db.execute(select(Company.symbol, Holding.quantity, Holding.average_cost, Holding.invested_amount,
                                        Holding.market_value, Holding.unrealized_profit_pct, Holding.total_dividends_received)
                                 .join(Holding, Holding.company_id == Company.id))).all()
    d = json.loads(res.body)["data"]
    for r in d["items"]:
        if r["symbol"] in ("2270", "2280"):
            out("ALLOC_" + r["symbol"], r)
    for r in rows:
        if r[0] in ("2270", "2280"):
            out("HOLD_" + r[0], list(r))
    out("CAPITAL", {k: d[k] for k in ("investable", "available_cash", "total_market_value")})
    from app.services.analysis import analyze_company
    from app.services.file_reader import coverage, knowledge
    from app.services.research_model import note
    from app.services import investor_calls as IC
    for s in ("2270", "2280"):
        a = await analyze_company(f"{s}.SR", None) or {}
        f = a.get("fundamentals") or {}
        out("DEC_" + s, {"price": a.get("price"), "decision": a.get("decision"), "fv": a.get("fair_value"),
                         "fv_low": a.get("fair_value_low"), "fv_high": a.get("fair_value_high"), "upside": a.get("fair_value_upside_pct"),
                         "conf": a.get("fair_value_conf"), "fin": (a.get("financial") or {}).get("score"),
                         "verdict": (a.get("financial") or {}).get("verdict"),
                         "scores": {k: (v or {}).get("score") for k, v in (a.get("scores") or {}).items() if isinstance(v, dict)},
                         "pe": f.get("pe_ratio"), "pb": f.get("price_to_book"), "dy": f.get("dividend_yield"), "roe": f.get("roe"),
                         "margin": f.get("profit_margin"), "eps_g": f.get("earnings_growth"), "mcap": f.get("market_cap"),
                         "w52": [f.get("week52_low"), f.get("week52_high")], "red": a.get("red_lines")})
        t = a.get("technical") or {}
        out("TECH_" + s, {k: t.get(k) for k in ("rsi", "support", "resistance", "trend", "pct_from_avg", "mean_basis")})
        try:
            n = note(s, a.get("price")) or {}
            out("RES_" + s, {"growth": n.get("growth"), "price": {k: (n.get("price") or {}).get(k) for k in ("since", "cagr", "tasi_cagr", "max_dd", "div")},
                             "pe_band": n.get("pe_band"), "forecast": n.get("forecast")})
        except Exception as e:                                    # noqa: BLE001
            out("RES_ERR_" + s, str(e))
        out("KNOW_COV_" + s, coverage(s))
        for l in knowledge(s, 16):
            print("    ", s, l)
        out("CALLS_" + s, IC.lines(s))


asyncio.run(main())
