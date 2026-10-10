#!/usr/bin/env python3
"""زمنُ نداء النماذج: مخزَّنٌ أم باردٌ، وكم يستغرق الحسابُ البارد لورقةٍ — مقابل مهلة الواجهة 30 ثانية. قارئٌ فقط (لا يكتب الكاش)."""
import asyncio, sys, time
sys.path.insert(0, "/app")
from app.services import cache
from app.services.fair_value_models import gather, value

async def main():
    for s in ("2270", "2280", "1120", "4190"):
        hit = cache.get(f"fvm:v39:{s}")
        a = cache.get_prefix if hasattr(cache, "get_prefix") else None
        t0 = time.monotonic()
        try:
            i = await asyncio.wait_for(gather(s), 120)
            v = value(i) if i else None
            dt = time.monotonic() - t0
            print(f"{s} · مخزَّن={'نعم' if hit else 'لا'} · حسابٌ بارد {dt:.1f}ث · قيمة {(v or {}).get('value')}")
        except Exception as e:                                    # noqa: BLE001
            print(f"{s} · مخزَّن={'نعم' if hit else 'لا'} · تعذّر بعد {time.monotonic()-t0:.1f}ث: {type(e).__name__} {e}")
asyncio.run(main())
