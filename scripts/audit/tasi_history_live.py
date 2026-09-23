#!/usr/bin/env python3
"""ما تردّه نقطةُ /market/history لتاسي على الخادم الآن (D438). قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/tasi_history_live.py
"""
import asyncio, sys
sys.path.insert(0, "/app")


async def main():
    try:
        from app.api.v1.endpoints.market import get_price_history
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    for sym in ("^TASI.SR", "BZ=F"):
        for rg in ("1mo", "6mo"):
            r = await get_price_history(sym, rg)
            d = (r.get("data") if isinstance(r, dict) else getattr(r, "body", b"")) or []
            if isinstance(d, (bytes, bytearray)):
                import json; d = json.loads(d).get("data") or []
            print(f"{sym} {rg}: {len(d)} نقطة · أوّل {str(d[:1])[:70]} · آخر {str(d[-1:])[:70]}")
    return 0

sys.exit(asyncio.run(main()))
