"""كاشفٌ (قراءةٌ فقط): تبويبُ القوائم في «تداول» (statementsTabData) بأنواعه —
هل يحمل سنواتٍ أقدمَ من ملفّات XBRL (2021)؟ لبناء تاريخٍ عميقٍ لنموذج الأبحاث.

    docker exec sp_backend python /app/scripts/audit/stmt_tab_door.py
"""
import asyncio
import json
import re
import sys
from collections import Counter

sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    for sym in ("1120", "2010"):
        url = (row_for(sym) or {}).get("company_url")
        full = X.ORIGIN + url if url and url.startswith("/") else url
        st, page = await fetch(full)
        mb = X._BASE.search(page or "")
        eps = sorted({m.group(1) for m in X._NJ.finditer(page or "")})
        print("@@EPS@@" + json.dumps({"s": sym, "status": st, "endpoints": eps}, ensure_ascii=False))
        ep = next((m.group(0) for m in X._NJ.finditer(page or "") if m.group(1) == "statementsTabData"), None)
        if not (mb and ep):
            continue
        for stype in ("1", "2", "3", "4", "5", "6"):
            for rtype in ("1", "2"):
                s2, body = await fetch(mb.group(1).rstrip("/") + "/" + ep,
                                       params={"statementType": stype, "reportType": rtype, "requestLocale": "en"},
                                       referer=full)
                yrs = Counter(re.findall(r"\b(20[0-2]\d)\b", body or ""))
                txt = re.sub(r"<[^>]+>", " ", body or "")
                txt = re.sub(r"\s+", " ", txt)[:300]
                print("@@TAB@@" + json.dumps({"s": sym, "type": stype, "report": rtype, "status": s2, "len": len(body or ""),
                                              "years": dict(sorted(yrs.items())), "head": txt}, ensure_ascii=False))


asyncio.run(main())
