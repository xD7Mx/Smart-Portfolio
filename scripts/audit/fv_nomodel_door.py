"""كاشفٌ للقراءة فقط: لماذا لا يُخرج المحرّكُ الجديدُ نموذجاً لـ11 شركة؟

    docker exec sp_backend python /app/scripts/audit/fv_nomodel_door.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")
from app.services import fair_value_models as F                  # noqa: E402

SYMS = ["2030", "2140", "4083", "4140", "4144", "4160", "6040", "7204", "8170", "8190", "8240"]


async def main():
    for s in SYMS:
        try:
            i = await F.gather(s)
        except Exception as e:                                     # noqa: BLE001
            print(f"── {s}: gather خطأ {type(e).__name__}: {e}")
            continue
        if not i:
            print(f"── {s}: gather ← لا مدخلات")
            continue
        a = i.annual or []
        last = a[-1] if a else {}
        print(f"── {s}: سعر {i.price} · أسهم {i.shares} · سنوات {len(a)} · نمط {i.archetype} · قطاع {i.sector}"
              f" · آخرُ سنة {last.get('as_of')} إيراد {last.get('revenue')} ربح {last.get('net_income')} حقوق {last.get('equity')}")
        try:
            r = F.value(i) or {}
        except Exception as e:                                     # noqa: BLE001
            print(f"     value خطأ {type(e).__name__}: {e}")
            continue
        print(f"     نماذج {len(r.get('models') or [])} · مستبعد {[(x.get('key'), x.get('reason', '')[:40]) for x in (r.get('excluded') or [])][:6]}"
              f" · سبب {str(r.get('reason'))[:80]}")


asyncio.run(main())
