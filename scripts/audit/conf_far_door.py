#!/usr/bin/env python3
"""المرشَّح 2.3 · تشخيص: لماذا خرجت أوراقٌ «مرتفعةً» وقيمتُها تبعد عن السعر 66–109٪؟ قارئٌ فقط.

بوابةُ المرشَّح (run 38072848670): لومي +109٪ «مرتفعة» · ذيب +91٪ · الدواء +82٪ · المتحدة الدولية +66٪ — وكانت قاعدةُ
الأربعة تحبسها. فرضيّة: ثلاثةُ نماذج من «المضاعف المبرَّر» (الدفترية والربحية والمبيعات من العائد على الحقوق نفسِه)
تتّفق بالبناء لا بالشهادة. ويُطبع لكلّ ورقة: النماذجُ ومصدرُ كلٍّ منها، ومجموعةُ القطاع وكم أنتجت منها.
"""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None


async def main():
    from app.services.fair_value_models import for_symbol, model_set
    from app.services.analysis import confidence_of
    from app.data.market_universe import MARKET_UNIVERSE as MU
    for s in ("4262", "4261", "4163", "4083", "8010", "1120", "1180", "2280"):
        f = await for_symbol(s) or {}
        ms = f.get("models") or []
        meta = MU.get(s) or {}
        _, allowed = model_set(f.get("sector"), None)
        print(f"═ {s} {meta.get('name_ar')} · {meta.get('sector')} · سعر {f.get('price')} · قيمة {f.get('value')} · "
              f"خام {f.get('model_value')} · نماذج {len(ms)} من مجموعةٍ {len(allowed)} ({f.get('model_set', '')[:40]}) · "
              f"ثقة {confidence_of(f)}")
        for m in ms:
            src = " | ".join(f"{a[0]}={a[1]}" for a in (m.get("assumptions") or [])[1:2])
            print(f"     {m.get('key'):<16} {m.get('family'):<10} {m.get('value'):>9} · {src[:70]}")
        ex = [f"{e.get('key')}" for e in (f.get("excluded") or [])]
        if ex:
            print(f"     مستبعَد: {ex}")


asyncio.run(main())
