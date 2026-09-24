#!/usr/bin/env python3
"""نماذجُ كلّ قطاع على الخادم (D470) — الريت 4340 مقابل «InvestingPro». قارئٌ فقط.

InvestingPro لـ4340: 6.49 (5.00–8.06) · توزيعاتٌ مستقرّة 5.00 · مرحلية 5.06 · السعر/المبيعات 7.82 · السعر/الدفترية 8.06
"""
import asyncio, sys
sys.path.insert(0, "/app")


async def main():
    from app.services.fair_value_models import for_symbol
    for s in ("4340", "4330", "1120", "7203", "2222", "4001"):
        r = await for_symbol(s) or {}
        print(f"═ {s} · {r.get('model_set')} · {r.get('value')} ({r.get('low')}–{r.get('high')}) · السعر {r.get('price')} · نماذج {r.get('count')}")
        for m in r.get("models") or []:
            print(f"     {m['name'][:40]:42} {m['value']:8.2f} ({m['low']:.2f}–{m['high']:.2f})")
        for e in r.get("excluded") or []:
            print(f"     ✗ {e['name']} {e['value']} — {e['excluded']}")
    print("InvestingPro لـ4340: 6.49 (5.00–8.06) · 5.00 · 5.06 · 7.82 · 8.06")

asyncio.run(main())
