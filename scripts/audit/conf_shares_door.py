#!/usr/bin/env python3
"""المرشَّح 2.3 · تشخيص: هل القيمُ البعيدة عن السعر (+66 إلى +109٪) عددُ أسهمٍ قبل تجزئةٍ أو منحة؟ قارئٌ فقط.

كلُّ نماذج الدواء (10) تقول ضعفَي السعر، ولومي وذيب بمضاعفاتهما التاريخية — وهذا ما يصنعه عددُ أسهمٍ قديمٌ يقسم ربحاً
جديداً. فيُقارن لكلّ ورقة: عددُ الأسهم الذي قيّم به المحرّك، والضمنيُّ من القيمة السوقية ÷ السعر في الفرز، وربحيةُ السهم.
"""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None


async def main():
    from app.services.fair_value_models import gather
    from app.services.market_screener import get_cached_screener
    rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    for s in ("4262", "4261", "4163", "4083", "1835", "4071", "6010", "4327", "1120", "2280"):
        i = await gather(s)
        r = rows.get(s) or {}
        mc, px = r.get("market_cap"), r.get("price")
        implied = (mc / px) if (mc and px) else None
        ni = (i.ttm or {}).get("net_income") if i else None
        hist = {k: (v[-3:] if isinstance(v, list) else v) for k, v in ((i.hist if i else {}) or {}).items()}
        print(f"═ {s} {r.get('name_ar') or r.get('name')} · سعر {px} · أسهمُ المحرّك "
              f"{(i.shares / 1e6 if i and i.shares else 0):,.1f}م · الضمنيّ من القيمة السوقية "
              f"{(implied / 1e6 if implied else 0):,.1f}م · نسبة {((i.shares / implied) if (i and i.shares and implied) else 0):.2f} · "
              f"ربحُ 12 شهراً {(ni / 1e6 if ni else 0):,.0f}م ({i.ttm_source if i else ''})")
        if i:
            print(f"     ربحيةُ السهم {((ni or 0) / i.shares if i.shares else 0):.2f} · مكرّرٌ ضمنيّ {(px / ((ni or 0) / i.shares) if (ni and i.shares and px) else 0):.1f}x"
                  f" · مضاعفاتٌ تاريخية {hist}")


asyncio.run(main())
