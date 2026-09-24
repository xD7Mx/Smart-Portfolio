#!/usr/bin/env python3
"""تبويبُ القوائم المالية في صفحة الشركة على «تداول»: أيُّ نوعٍ يحمل قوائمَ ما بعد 2022؟ قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/tadawul_statements_door.py

قائمةُ ملفّات XBRL (statementType=6) للمؤمِّنين تقف عند 2022. فيُنادى البابُ نفسُه
بكلّ نوعٍ وتقرير، ويُطبع حجمُ الردّ وأوّلُ نصّه والسنواتُ الظاهرة فيه.
"""
import asyncio, re, sys
sys.path.insert(0, "/app")

SYM = "8010"


async def main():
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import refresh, row_for, usable_rows
    if not (usable_rows()[0] or {}):
        await refresh()
    url = (row_for(SYM) or {}).get("company_url")
    full = X.ORIGIN + url if url.startswith("/") else url
    st, page = await fetch(full)
    print("الصفحة", st, len(page or ""))
    base = X._BASE.search(page).group(1).rstrip("/")
    eps = {m.group(1): m.group(0) for m in X._NJ.finditer(page)}
    print("الخدمات في الصفحة:", sorted(eps))
    ep = eps.get("statementsTabData")
    for stype in ("1", "2", "3", "4", "5", "6", "7"):
        for rtype in ("1", "2"):
            s, body = await fetch(base + "/" + ep, params={"statementType": stype, "reportType": rtype, "requestLocale": "en"}, referer=full)
            txt = re.sub(r"<[^>]+>", " ", body or "")
            txt = re.sub(r"\s+", " ", txt).strip()
            years = sorted(set(re.findall(r"\b(20[12]\d)\b", txt)))
            print(f"\n── نوع {stype} · تقرير {rtype} · HTTP {s} · {len(body or '')} حرفاً · سنوات {years[-6:]}")
            print("   ", txt[:700])
    return 0

sys.exit(asyncio.run(main()))
