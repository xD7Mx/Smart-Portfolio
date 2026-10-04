"""كاشف (قراءةٌ فقط): من أين يأتي تبويبُ «المعلومات المالية» في صفحة الشركة؟ (قوائمُ ربعيةٌ حتى 2026-06-30
بينما ملفّاتُ XBRL متوقّفة عند 2022 لشركات التأمين) — خدماتُ الصفحة، وأين تظهر عناوينُ القوائم وتواريخُها.

    docker exec sp_backend python /app/scripts/audit/profile_fin_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    from app.services.tadawul_xbrl import ORIGIN, _NJ, _BASE
    for sym in ("8250", "8050"):
        url = (row_for(sym) or {}).get("company_url")
        full = ORIGIN + url if url and url.startswith("/") else url
        st, page = await fetch(full)
        print(f"@@{sym}@@ page {st} len={len(page or '')}", flush=True)
        if not page:
            continue
        names = sorted({m.group(1) for m in _NJ.finditer(page)})
        print("  services:", names, flush=True)
        for kw in ("Balance Sheet", "قائمة المركز المالي", "Total Assets", "إجمالي الموجودات", "2026-06-30",
                   "financialInformation", "FinancialInformation", "balanceSheet", "statementsTabData"):
            for m in list(re.finditer(re.escape(kw), page))[:2]:
                a = max(0, m.start() - 160)
                print(f"  [{kw}] …{page[a:m.end() + 160]!r}", flush=True)
        mb = _BASE.search(page)
        base = mb.group(1).rstrip("/") if mb else None
        # جرّب الخدماتِ التي تحمل «financ» أو «statement» بمعاملاتٍ شائعة
        for m in _NJ.finditer(page):
            n = m.group(1)
            if base and re.search(r"financ|statement|balance|income", n, re.I):
                for params in ({}, {"statementType": "1", "reportType": "2", "requestLocale": "en"},
                               {"statementType": "1", "reportType": "1", "requestLocale": "en"}):
                    s2, b2 = await fetch(base + "/" + m.group(0), params=params, referer=full)
                    print(f"  >> {n} {params} → {s2} len={len(b2 or '')} {str(b2 or '')[:400]!r}", flush=True)
        break

asyncio.run(main())
