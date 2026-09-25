#!/usr/bin/env python3
"""شعاراتُ «تداول» وبندُ الإهلاك في XBRL وياهو — قارئٌ فقط (D488 · D489).

    docker exec sp_backend python /app/scripts/audit/tadawul_logo_door.py
"""
import asyncio, re, sys
sys.path.insert(0, "/app")
SYMS = ["2222", "1120", "9510", "4330"]


async def main():
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch, fetch_bytes
    from app.services.tadawul_market import refresh, row_for, usable_rows
    if not (usable_rows()[0] or {}):
        await refresh()
    for sym in SYMS:
        url = (row_for(sym) or {}).get("company_url")
        if not url:
            print(f"═ {sym}: لا رابطَ صفحة"); continue
        full = X.ORIGIN + url if url.startswith("/") else url
        st, page = await fetch(full)
        imgs = sorted(set(re.findall(r"""(?:src|href|data-src)=["']([^"']*(?:logo|Logo|LOGO|CompanyLogos|companyLogo)[^"']*)["']""", page or "")))
        print(f"\n═ {sym} · {st} · صورٌ فيها «logo»: {len(imgs)}")
        for u in imgs[:12]:
            print("   ", u)
        for u in imgs[:3]:
            full_u = u if u.startswith("http") else X.ORIGIN + u
            s, b = await fetch_bytes(full_u, referer=full, timeout=30)
            print(f"    ← {s} · {len(b or b'')} بايت · {full_u[:120]}")


DEP_SYMS = ["2222", "2010", "4030", "1831", "2340", "1810", "4072", "4003", "4001", "2280",
            "4165", "4013", "4164", "1111", "7010", "2082", "4300", "7203", "1302"]


async def dep_labels():
    """كلُّ صفٍّ في أحدث ملفّ XBRL سنويّ فيه إهلاكٌ أو استهلاكٌ أو EBITDA —
    بنصّه كما هو، فيُنقل إلى الخريطة بالحرف لا بالتخمين."""
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch
    seen: dict[str, int] = {}
    for sym in DEP_SYMS:
        files, why = await X.filings_for_ex(sym)
        if not files:
            print(f"  {sym}: لا ملفّات — {why}"); continue
        f = files[0]
        u = f["url"] if f["url"].startswith("http") else X.ORIGIN + f["url"]
        st, html = await fetch(u)
        hits = []
        for tr in X._TR.findall(html or ""):
            cells = [X._clean(c) for c in X._TD.findall(tr)]
            if cells and re.search(r"depreci|amorti|ebitda", cells[0], re.I):
                hits.append((cells[0], cells[1] if len(cells) > 1 else ""))
        print(f"  {sym} ({f['filed']}): {len(hits)}")
        for lbl, v in hits[:8]:
            print(f"      «{lbl}» = {v}")
            seen[X._norm(lbl)] = seen.get(X._norm(lbl), 0) + 1
    print("\n═ الصياغاتُ مرتّبةً بتكرارها:")
    for k, n in sorted(seen.items(), key=lambda x: -x[1])[:30]:
        print(f"   {n:>2} × {k}")
    from app.services.market_data import market_service
    for sym in ("2222", "4001", "7010"):
        try:
            fin = await market_service.get_financials(sym + ".SR")
            per = (fin or {}).get("annual") or (fin or {}).get("periods") or []
            print(f"  ياهو {sym}: إهلاك =", [p.get("depreciation") for p in per[:4]])
        except Exception as e:
            print(f"  ياهو {sym}: تعذّر — {e}")


async def both():
    await main()
    print("\n════ بندُ الإهلاك ════")
    await dep_labels()

asyncio.run(both())
