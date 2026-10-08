#!/usr/bin/env python3
"""عدُّ الشركات ذوات الخطّ الأحمر الحيّ ودرجاتُها، ومفاتيحُ الشركات ذوات الدرجة صفراً. قارئٌ فقط (التحليلُ من الكاش)."""
import asyncio, collections, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market
from app.services.analysis import analyze_company

async def main():
    uni = main_market(MARKET_UNIVERSE)
    red, zero, band = [], [], collections.Counter()
    for s in uni:
        try:
            a = await analyze_company(f"{s}.SR", allow_supplement=False) or {}
        except Exception:                                          # noqa: BLE001
            continue
        sc = (a.get("financial") or {}).get("score")
        rl = a.get("red_lines") or []
        if rl and isinstance(sc, (int, float)) and sc > 0:
            red.append((s, sc, [x.get("id") for x in rl]))
            band["≥65" if sc >= 65 else "45–64" if sc >= 45 else "<45"] += 1
        if not sc:
            f = a.get("financial") or {}
            zero.append((s, {k: f.get(k) for k in list(f)[:12] if not isinstance(f.get(k), (list, dict))},
                         (a.get("governance_provenance") or {}).get("تاريخ الأرقام")))
    print(f"خطٌّ أحمرٌ حيّ مع درجة: {len(red)} · {dict(band)}")
    for x in sorted(red, key=lambda x: -x[1])[:40]:
        print("  ", x)
    print(f"\nدرجةٌ صفرٌ أو غائبة: {len(zero)}")
    for x in zero:
        print("  ", x)
asyncio.run(main())
