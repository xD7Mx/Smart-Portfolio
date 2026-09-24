#!/usr/bin/env python3
"""السلامةُ الماليةُ للعثيم 4001 مقابل «InvestingPro» (D469). قارئٌ فقط.

InvestingPro: الكلّ 1.86 عادل · القيمة 2.46 · الزخم 0.56 · التدفّق 1.98 · الربحية 2.45 · النمو 1.88
"""
import asyncio, sys
sys.path.insert(0, "/app")


async def main():
    from app.services.financial_health import for_symbol
    for s in ("4001", "2222", "1120"):
        r = await for_symbol(s) or {}
        print(f"═ {s}: {r.get('score')} {r.get('label')} · القطاع {r.get('sector')} · {r.get('peers')} شركة")
        for p in r.get("pillars") or []:
            print(f"   {p['name']:22} {p['score']:.2f} {p['label']:8} — {p['why']}")
            for m in p["metrics"]:
                print(f"        {m['name']:34} {m['display']:>10} · نقطة {m['percentile']:5.1f}% · {m['score']:.2f}")
    print("InvestingPro لـ4001: 1.86 · القيمة 2.46 · الزخم 0.56 · التدفّق 1.98 · الربحية 2.45 · النمو 1.88")

asyncio.run(main())
