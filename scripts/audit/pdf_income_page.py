#!/usr/bin/env python3
"""نصُّ صفحة الدخل كاملاً في أحدث ملفٍّ سنويّ — لأوراقٍ لم يُطابَق فيها صافي الربح. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/pdf_income_page.py
"""
import asyncio, sys
sys.path.insert(0, "/app")
SYMS = ["4330", "4340", "8030"]


async def main():
    import fitz
    from app.services import tadawul_pdf as P
    from app.services.tadawul_http import fetch_bytes
    from app.services.tadawul_market import refresh, usable_rows
    if not (usable_rows()[0] or {}):
        await refresh()
    for s in SYMS:
        links, _ = await P.pdf_links(s)
        for f in links[:6]:
            code, data = await fetch_bytes(f["url"], referer=f["referer"])
            if code != 200 or not data.startswith(b"%PDF"):
                continue
            doc = fitz.open(stream=data, filetype="pdf")
            pages = [pg.get_text() for pg in doc]
            inc = [t for t in pages if P._kind_of(t) == "income"]
            if not inc:
                continue
            print(f"\n═ {s} · {f['filed']}\n{inc[0][:3000]}")
            break
    return 0

sys.exit(asyncio.run(main()))
