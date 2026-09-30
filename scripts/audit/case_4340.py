"""كاشفٌ (قراءةٌ فقط): ملفُّ «الراجحي ريت» 4340 كما يراه التطبيق — القرارُ والدرجةُ والعادلُ
والأركانُ، والسعرُ منذ الإدراج، والتوزيعاتُ، ونموذجُ الأبحاث — لسؤال المالك الواقعيّ.

    docker exec sp_backend python /app/scripts/audit/case_4340.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")
S = "4340"


def out(tag, obj):
    print(f"@@{tag}@@" + json.dumps(obj, ensure_ascii=False, default=str)[:3500])


async def main():
    from app.services.analysis import analyze_company
    a = await analyze_company(f"{S}.SR", None) or {}
    out("DECISION", {k: a.get(k) for k in ("price", "decision", "financial", "fair_value", "fair_value_low", "fair_value_high",
                                           "fair_value_upside_pct", "fair_value_conf", "fair_value_source", "analyst_target",
                                           "red_lines", "strengths", "weaknesses", "valuation")})
    out("SCORES", {k: (v or {}).get("score") if isinstance(v, dict) else v for k, v in (a.get("scores") or {}).items()})
    out("TECH", a.get("technical"))
    out("FUND", {k: (a.get("fundamentals") or {}).get(k) for k in ("pe_ratio", "price_to_book", "dividend_yield", "market_cap",
                                                                      "week52_high", "week52_low")})
    from app.services.market_data import market_service
    pts = await market_service._yahoo()._fetch_chart_points(f"{S}.SR", "max", "1d")
    closes = [(p["date"][:10], p["close"]) for p in pts or [] if p.get("close")]
    if closes:
        lo = min(closes, key=lambda x: x[1]); hi = max(closes, key=lambda x: x[1])
        out("PRICE", {"n": len(closes), "first": closes[0], "last": closes[-1], "min": lo, "max": hi,
                      "last_12m": closes[-260:][::20]})
    from app.services import lastgood
    d = lastgood.load(f"div:tadawul:{S}") or {}
    out("DIV_TADAWUL", (d.get("rows") or [])[-16:])
    from app.services.market_data import market_service as M
    dv = await M.get_dividends(f"{S}.SR") or {}
    out("DIV_YAHOO", (dv.get("history") or [])[-16:])
    from app.services import tadawul_xbrl as X
    for kind in ("annual", "quarterly"):
        out("XBRL_" + kind, [{k: p.get(k) for k in ("as_of", "revenue", "net_income", "total_assets", "equity", "total_debt",
                                                   "operating_cash_flow", "eps", "shares_outstanding")}
                             for p in (X.for_symbol(S, kind) or [])[-8:]])
    try:
        from app.services.research_model import note
        out("RESEARCH", note(S, a.get("price")))
    except Exception as e:                                        # noqa: BLE001
        out("RESEARCH_ERR", str(e))
    from app.services.tadawul_market import row_for
    out("SNAP", row_for(S))


asyncio.run(main())
