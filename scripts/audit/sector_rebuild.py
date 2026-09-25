#!/usr/bin/env python3
"""بناءُ التحليل القطاعي الآن وطباعةُ سبب الفشل إن فشل (D490).

    docker exec sp_backend python /app/scripts/audit/sector_rebuild.py
"""
import asyncio, sys, traceback
sys.path.insert(0, "/app")


async def main():
    from app.services.sector_analysis import compute_sector_analysis
    try:
        rows = await compute_sector_analysis()
    except Exception:                                              # noqa: BLE001
        traceback.print_exc(); return
    print(f"═ القطاعات: {len(rows or [])}")
    for r in rows or []:
        print(f"   {r.get('sector')}: سنة {r.get('1y')} · {r.get('1y_n')} شركة")

asyncio.run(main())
