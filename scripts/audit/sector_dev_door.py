#!/usr/bin/env python3
"""انحرافُ القطاعات الساقطة عن هدف المحلّلين، ورقةً ورقة: القيمةُ والخامُ والسعرُ والهدفُ والنماذج. قارئٌ فقط."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services.content_engine import fund_store_load
from app.services.market_screener import get_cached_screener
from app.services.fair_value_models import for_symbol

BAD = ("إدارة وتطوير العقارات", "السلع الرأسمالية", "التطبيقات وخدمات التقنية", "الخدمات الاستهلاكية", "الرعاية الصحية")
uni = main_market(MARKET_UNIVERSE); st = fund_store_load()
rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}

async def main():
    for sec in BAD:
        print(f"══ {sec}")
        for s, m in uni.items():
            if (m.get("sector_ar") or m.get("sector")) != sec:
                continue
            fv, r = (st.get(s) or {}).get("fair_value"), rows.get(s) or {}
            at, px = r.get("analyst_target"), r.get("price")
            if not (isinstance(fv, (int, float)) and isinstance(at, (int, float)) and at > 0):
                continue
            f = await for_symbol(s) or {}
            ms = " ".join(f"{x.get('name') or x.get('key')}={x.get('value')}" for x in f.get("models") or [])
            print(f"  {s} {m.get('name_ar')} · قيمة {fv} · خام {f.get('model_value')} · سعر {px} · هدف {at} · "
                  f"انحراف {fv/at-1:+.0%} · سعر÷هدف {px/at-1 if px else 0:+.0%} · {f.get('weights_kind')} · {ms}")
asyncio.run(main())
