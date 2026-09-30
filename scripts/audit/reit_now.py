"""يبني مستشارَ الريت الآن لكلّ الصناديق ويطبع قراءتَه (D554).

    docker exec sp_backend python /app/scripts/audit/reit_now.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services.market_screener import get_cached_screener
    from app.services.statement_merge import archetype_of
    from app.services.reit_advisor import build
    from app.services.tadawul_market import row_for
    for r in get_cached_screener() or []:
        s = str(r.get("symbol"))
        if archetype_of(s) != "reit":
            continue
        px = (row_for(s) or {}).get("price")
        a = await build(s, px, force=True) or {}
        print("@@R@@" + json.dumps({"s": s, "name": r.get("name"), "px": px, "nav": a.get("nav"), "nav_date": a.get("nav_date"),
                                    "prem": a.get("premium"), "navchg": a.get("nav_change"), "ttm": a.get("ttm"), "y": a.get("yield"),
                                    "cad": a.get("cadence_days"), "next": a.get("next_expected"), "late": a.get("overdue"),
                                    "n": len(a.get("distributions") or []), "vals": (a.get("valuations") or [])[:2]}, ensure_ascii=False))


asyncio.run(main())
