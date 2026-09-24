#!/usr/bin/env python3
"""قوائمُ «تداول» بصيغة PDF: روابطُها ونصُّ أحدثها — لبناء القارئ على ما يُنشر فعلاً. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/tadawul_pdf_door.py

لكلّ ورقة: روابطُ تبويب القوائم المالية (statementType=5) بتواريخها، ثمّ أحدثُ
قائمةٍ سنوية: عددُ صفحاتها وأسطرُ البنود الأساسية منها بنصّها.
"""
import asyncio, re, sys
sys.path.insert(0, "/app")

SYMS = ["8010", "1320"]
KEYS = re.compile(r"(insurance revenue|total revenue|revenue|net profit|profit for the (year|period)|net income|"
                  r"total equity|total shareholders|total assets|earnings per share|basic)", re.I)


async def main():
    import fitz
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import refresh, row_for, usable_rows
    if not (usable_rows()[0] or {}):
        await refresh()
    for sym in SYMS:
        url = (row_for(sym) or {}).get("company_url")
        full = X.ORIGIN + url if url.startswith("/") else url
        st, page = await fetch(full)
        base = X._BASE.search(page).group(1).rstrip("/")
        ep = next(m.group(0) for m in X._NJ.finditer(page) if m.group(1) == "statementsTabData")
        s, body = await fetch(base + "/" + ep, params={"statementType": "5", "reportType": "1", "requestLocale": "en"}, referer=full)
        links = re.findall(r"href=[\"']([^\"']+\.pdf)[\"']", body or "", re.I)
        print(f"\n═ {sym} · روابط PDF {len(links)}")
        for l in links[:10]:
            print("   ", l)
        if not links:
            print("   مقطع:", re.sub(r"\s+", " ", body or "")[:1500]); continue
        link = links[0]
        u = link if link.startswith("http") else X.ORIGIN + link
        from app.services.tadawul_http import fetch_bytes
        st, data = await fetch_bytes(u, referer=full)
        print(f"   تحميل {st} · {len(data)} بايت · يبدأ {data[:8]!r}")
        try:
            doc = fitz.open(stream=bytes(data), filetype="pdf")
        except Exception as e:                                     # noqa: BLE001
            print("   لا يُفتح:", e); continue
        print(f"   صفحات {doc.page_count}")
        for i, pg in enumerate(doc):
            t = pg.get_text()
            if i < 14:
                print(f"   ص{i+1}: {len(t)} حرفاً · {re.sub(chr(10), ' | ', t[:90])}")
        want = [i for i, pg in enumerate(doc) if i < 16 and re.search(r"total assets|per share", pg.get_text(), re.I)]
        for i in want[:3]:
            print(f"\n   ─── نصُّ ص{i+1} ───")
            print(doc[i].get_text()[:3500])
    return 0

sys.exit(asyncio.run(main()))
