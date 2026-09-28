#!/usr/bin/env python3
"""قيمةُ كلّ نموذجٍ وافتراضاتُه لرموز المالك الـ22 — للمقارنة نموذجاً بنموذج مع InvestingPro. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fvm_model_dump.py
"""
import asyncio, sys
sys.path.insert(0, "/app")
SYMS = ["2222", "2010", "1302", "1831", "4030", "2340", "1810", "4072", "4003", "4001", "2280",
        "4165", "4013", "4164", "1120", "1111", "8210", "7010", "2082", "4330", "4300", "7203"]


async def main():
    from app.services import fair_value_models as F
    for s in SYMS:
        try:
            r = await F.for_symbol(s) or {}
        except Exception as e:                                     # noqa: BLE001
            print(f"═ {s}: تعذّر {type(e).__name__}"); continue
        b = r.get("blend") or {}
        print(f"═ {s} · سعر {r.get('price')} · المنشور {r.get('value')} · النماذج {r.get('models_value')} "
              f"· المُعايَر {b.get('calibrated')} (α={b.get('alpha')}) · {r.get('reason') or ''}")
        for m in r.get("models") or []:
            a = " | ".join(f"{x[0]}={x[1]}" for x in (m.get("assumptions") or [])[:4])
            print(f"   {m['key']:<16} {m['value']:>9} · {a}")
        for e in r.get("excluded") or []:
            print(f"   ✗ {e.get('key')} {e.get('value')} — {e.get('excluded')}")

asyncio.run(main())
