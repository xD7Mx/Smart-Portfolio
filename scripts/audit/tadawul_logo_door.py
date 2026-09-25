#!/usr/bin/env python3
"""شعاراتُ الشركات من «تداول»: أين تُنشر في صفحة الشركة — قارئٌ فقط (D488).

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

asyncio.run(main())
