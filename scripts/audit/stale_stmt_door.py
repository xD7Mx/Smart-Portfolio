"""كاشف (قراءةٌ فقط): الشركاتُ الممتنعة لقِدَم قوائمها — ما عندنا مقابلَ ما في «تداول» (ملفّاتُ XBRL وتواريخُها).

    docker exec sp_backend python /app/scripts/audit/stale_stmt_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")
SYMS = ["2010", "2020", "1810", "2330", "4002", "7030", "8020", "8210", "9400", "1182", "2082", "4001", "8050", "8250",
        "4150", "6014"]


async def main():
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_market import row_for
    for s in SYMS:
        ann = X.for_symbol(s, "annual") or []
        q = X.for_symbol(s, "quarterly") or []
        files, why = await X.filings_for_ex(s)
        print("@@S@@ " + json.dumps({"sym": s, "name": (row_for(s) or {}).get("name"),
                                     "ours_annual": [p.get("as_of") for p in ann][-2:], "ours_q": [p.get("as_of") for p in q][-2:],
                                     "tadawul_files": [f["filed"] for f in files[:4]], "n": len(files), "why": why},
                                    ensure_ascii=False))

asyncio.run(main())
