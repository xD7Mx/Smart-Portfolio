"""كاشفٌ يكتب (نتائجُ الإعلانات وحدَها): يقرأ نتائجَ الشركات من إعلانات «تداول» للسوق كلِّه أوّلَ مرّة — D580.

    docker exec sp_backend python /app/scripts/audit/results_ann_fill.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    from app.services import results_announcements as R
    syms = [s for s in sorted(main_market(MARKET_UNIVERSE).keys()) if not R.latest(s)]
    rep = await R.refresh(syms, conc=4)
    have = {s: (R.latest(s) or {}).get("as_of") for s in syms}
    print("@@FILL@@ " + json.dumps({**rep, "with_result": sum(1 for v in have.values() if v),
                                    "jun2026": sum(1 for v in have.values() if v and v >= "2026-06-30"),
                                    "none": [s for s, v in have.items() if not v][:40],
                                    "sample": {s: have.get(s) for s in ("2010", "8210", "2330", "2020", "8010")}}, ensure_ascii=False))

asyncio.run(main())
