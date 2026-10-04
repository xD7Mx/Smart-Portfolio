"""كاشف (قراءةٌ فقط): تفصيلُ نماذج السعر العادل للشواذّ — أيُّ نموذجٍ رفع القيمةَ أو خفضها، وبأيّ مدخل.
التأمينُ (رسن · سلامة · جي آي جي) والبتروكيماويات (المغذيات · الميثانول) والبقية (المتحدة الدولية · تكوين · نايس ون)
ثمّ الريتاتُ بعد D593.

    docker exec sp_backend python /app/scripts/audit/fv_outlier_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")
SYMS = ["8313", "8050", "8250", "2020", "2001", "4083", "1201", "4193", "1303", "4330", "4335", "4336", "4340"]


async def main():
    from app.services import fair_value_models as F
    from app.services.tadawul_market import row_for
    for s in SYMS:
        try:
            i = await F.gather(s)
            r = await F.for_symbol(s)
        except Exception as e:                                    # noqa: BLE001
            print(f"@@{s}@@ ERR {type(e).__name__}: {e}")
            continue
        row = row_for(s) or {}
        out = {"name": row.get("name"), "price": row.get("price"), "fv": (r or {}).get("value"),
               "set": (r or {}).get("model_set"), "unc": (r or {}).get("uncertainty"),
               "sector": getattr(i, "sector", None), "arch": getattr(i, "archetype", None),
               "shares": getattr(i, "shares", None), "ttm_src": getattr(i, "ttm_source", None),
               "stale": getattr(i, "stale_days", None),
               "ttm": {k: v for k, v in (getattr(i, "ttm", None) or {}).items() if k in
                       ("revenue", "net_income", "operating_income", "ocf", "fcf", "capex")},
               "equity": (getattr(i, "balance", None) or {}).get("equity"),
               "peers": {k: [x if isinstance(x, (tuple, list)) else round(x, 2) for x in v][:6] for k, v in (getattr(i, "peers", None) or {}).items()},
               "peer_syms": (getattr(i, "peer_symbols", None) or [])[:10],
               "models": [(m.get("key"), m.get("value")) for m in (r or {}).get("models") or []],
               "excluded": [(m.get("key"), m.get("value"), m.get("why") or m.get("reason")) for m in (r or {}).get("excluded") or []][:10],
               "notes": (r or {}).get("notes")}
        print(f"@@{s}@@ " + json.dumps(out, ensure_ascii=False, default=str)[:3500])

asyncio.run(main())
