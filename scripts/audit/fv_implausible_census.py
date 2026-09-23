#!/usr/bin/env python3
"""كم ورقةً في المخزن سعرُها العادل خارج 0.4–2.5× السعر، ومن هي (D439). قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fv_implausible_census.py
"""
import sys
sys.path.insert(0, "/app")
from app.services.content_engine import fund_store_load
from app.services import tadawul_market as TM
st = fund_store_load() or {}
bad = []
for sym, r in st.items():
    fv = (r or {}).get("fair_value")
    row = TM.row_for(sym) or {}
    px = row.get("price") or (r or {}).get("price")
    if isinstance(fv, (int, float)) and isinstance(px, (int, float)) and px > 0:
        q = fv / px
        if not (0.4 <= q <= 2.5):
            bad.append((sym, round(fv, 2), px, round(q, 2)))
print(f"مخزن: {len(st)} · خارج النطاق: {len(bad)}")
for b in sorted(bad, key=lambda x: -abs(x[3] - 1)):
    print("  ", b)
