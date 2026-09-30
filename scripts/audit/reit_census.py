"""كاشفٌ (قراءةٌ فقط): سعرُنا العادلُ لكلّ صناديق الريت مقابلَ دفتريّتها (صافي أصولها) —
هل التقييمُ مشكوكٌ فيه في الريتات كلّها كما يقول المالك؟

    docker exec sp_backend python /app/scripts/audit/reit_census.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import fair_value_models as F
    from app.services.statement_merge import archetype_of
    from app.services.market_screener import get_cached_screener
    rows = [r for r in get_cached_screener() or [] if archetype_of(str(r.get("symbol"))) == "reit"]
    print("@@N@@", len(rows))
    for r in rows:
        s = str(r["symbol"])
        v = await F.for_symbol(s) or {}
        ms = [(m["key"], m["value"], (m.get("assumptions") or [[None, None, None]])[-1][1]) for m in v.get("models") or []]
        print("@@REIT@@" + json.dumps({"s": s, "name": r.get("name"), "price": r.get("price"), "fv": v.get("value"),
                                       "up": v.get("upside"), "pb": r.get("price_to_book"), "dy": r.get("dividend_yield"),
                                       "models": ms, "why": v.get("reason")}, ensure_ascii=False))


asyncio.run(main())
