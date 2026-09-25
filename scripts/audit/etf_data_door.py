#!/usr/bin/env python3
"""صناديقُ المؤشرات (94xx): ما الذي يصل منها من كلّ مصدر — قارئٌ فقط (D492).

    docker exec sp_backend python /app/scripts/audit/etf_data_door.py
"""
import asyncio, sys
sys.path.insert(0, "/app")
SYMS = ["9400", "9405", "9408"]


async def main():
    from app.services.tadawul_market import refresh, row_for, usable_rows
    from app.services.market_data import market_service
    if not (usable_rows()[0] or {}):
        await refresh()
    for s in SYMS:
        row = row_for(s) or {}
        print(f"═ {s} · لقطةُ تداول: {'نعم' if row else 'لا'} · سعر {row.get('price')} · رابط {row.get('company_url')}")
        try:
            p = await market_service.get_prices([s + ".SR"])
            print(f"   ياهو سعر: {(p or {}).get(s + '.SR')}")
        except Exception as e:                                     # noqa: BLE001
            print(f"   ياهو سعر: تعذّر {type(e).__name__}")
        try:
            info = await market_service.get_company_info(s + ".SR") or {}
            print(f"   ياهو معلومات: {sorted(k for k, v in info.items() if v)[:15]}")
        except Exception as e:                                     # noqa: BLE001
            print(f"   ياهو معلومات: تعذّر {type(e).__name__}")

asyncio.run(main())
