#!/usr/bin/env python3
"""تشخيص: شركاتُ السوق الرئيسيّ التي لا صفَّ لها في الفرز (فلا يراها المختبر) — ولماذا. قارئٌ فقط."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services.market_screener import get_cached_screener
from app.services.content_engine import fund_store_load

rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
store = fund_store_load()
uni = main_market(MARKET_UNIVERSE)
gap = [s for s in uni if s not in rows]
print(f"الكون {len(uni)} · صفوفُ الفرز {len(rows)} · بلا صفّ {len(gap)}")

async def main():
    from app.services.market_data import market_service
    for s in gap[:20]:
        try:
            pts = await asyncio.wait_for(market_service._yahoo()._fetch_chart_points(f"{s}.SR", "10y", "1d"), 25)
        except Exception as e:                                     # noqa: BLE001
            pts = None
        n = len([p for p in (pts or []) if p.get("close") is not None])
        print(f"  {s} {uni[s].get('name_ar')} · إغلاقاتٌ {n} · مخزن: جودة {(store.get(s) or {}).get('finance_score')} · قيمة {(store.get(s) or {}).get('fair_value')}")
asyncio.run(main())
