#!/usr/bin/env python3
"""لماذا يغيب مسارُ مضاعف القطاع عن المحجوبة — مدخلاه كما يصلان المحرّك. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fv_pe_path_why.py
"""
import asyncio, sys
sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_market as TM
    from app.services.sector_multiples import for_symbol
    from app.services import fair_value as F
    got = {}
    _o = F.compute
    def _spy(info, price, spe=None, spb=None, **kw):
        got[kw.get("symbol")] = (info.get("eps"), info.get("eps_source"), spe, kw.get("archetype"), price)
        return _o(info, price, spe, spb, **kw)
    F.compute = _spy
    from app.services.analysis import analyze_company
    from app.services import cache
    for s in ("7200", "2082", "4200", "4291", "2282", "4017", "1111", "8230", "4090", "2223"):
        r = TM.row_for(s)
        cache.delete(f"x") if False else None
        await analyze_company(f"{s}.SR", allow_supplement=False)
        g = got.get(f"{s}.SR")
        print(f"{s}: PER تداول={r.get('pe_ratio')} سعر={r.get('price')} · مضاعفُ القطاع={for_symbol(s)} · وصل المحرّك: {g}")
    return 0

sys.exit(asyncio.run(main()))
