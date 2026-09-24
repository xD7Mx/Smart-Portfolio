#!/usr/bin/env python3
"""لماذا لم يُقرأ ملفُّ PDF لورقةٍ ما؟ — أسطرُ صفحات القوائم حول البنود المطلوبة. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/pdf_parse_diag.py
"""
import asyncio, re, sys
sys.path.insert(0, "/app")
SYMS = ["8210", "8020", "2010", "2020", "4330", "1320", "7204", "8200"]
WANT = re.compile(r"revenue|sales|income|profit|per share|total assets|total liabilities|equity|net assets|unit", re.I)


async def main():
    import fitz
    from app.services import tadawul_pdf as P
    from app.services.tadawul_http import fetch_bytes
    from app.services.tadawul_market import refresh, usable_rows
    if not (usable_rows()[0] or {}):
        await refresh()
    for s in SYMS:
        links, why = await P.pdf_links(s)
        print(f"\n═ {s} · روابط {len(links)} {why or ''}")
        for f in links[:6]:
            st, data = await fetch_bytes(f["url"], referer=f["referer"])
            if st != 200 or not data.startswith(b"%PDF"):
                print("   تحميل", st); continue
            r = P.parse_pdf(data)
            if not r.get("annual"):
                continue
            print(f"   {f['filed']} · سنويّ · فترات {len(r['periods'])} · {r.get('reason')}")
            for p in r["periods"]:
                print("     ", {k: p.get(k) for k in ("as_of", "revenue", "net_income", "eps", "equity", "total_assets", "shares_outstanding")},
                      "· الصمّام:", P.valid(p, None))
            doc = fitz.open(stream=data, filetype="pdf")
            for i, pg in enumerate(doc):
                t = pg.get_text()
                k = P._kind_of(t)
                if i < 14:
                    print(f"     ص{i+1}: {len(t)}ح · نوع {k} · رأس: {re.sub(chr(10), ' | ', t[:160])}")
                if k in ("income", "balance"):
                    lines = [l.strip() for l in t.splitlines() if l.strip()]
                    for j, l in enumerate(lines):
                        if WANT.search(l) and not re.match(r"^[\d,().\-]+$", l):
                            print(f"        ‹{l[:80]}› → {lines[j+1:j+4]}")
            break
    return 0

sys.exit(asyncio.run(main()))
