"""كاشفٌ (قراءةٌ فقط): عمقُ ملفّات XBRL في «تداول» لكلّ شركة — كم ملفّاً وأقدمُ إيداع —
لمعرفة ما يُتاح لبناء تاريخٍ عميقٍ للقوائم قبل 2023.

    docker exec sp_backend python /app/scripts/audit/xbrl_depth.py
"""
import asyncio
import json
import sys
from collections import Counter

sys.path.insert(0, "/app")

SAMPLE = ["1120", "2222", "2010", "2050", "4200", "1010", "7010", "2280", "4030", "1180", "2380", "4164"]


async def main():
    from app.services import tadawul_xbrl as X
    years = Counter()
    for s in SAMPLE:
        files, why = await X.filings_for_ex(s)
        fl = sorted(f["filed"] for f in files if f.get("filed"))
        years.update({f[:4] for f in fl})
        print("@@DEPTH@@" + json.dumps({"s": s, "n": len(files), "oldest": fl[:1], "newest": fl[-1:], "why": why},
                                       ensure_ascii=False))
    print("@@YEARS@@" + json.dumps(dict(sorted(years.items()))))
    # ملفٌّ قديمٌ واحد: هل يُقرأ بالمحلّل نفسه؟
    files, _ = await X.filings_for_ex("1120")
    old = sorted((f for f in files if f.get("filed")), key=lambda f: f["filed"])[:1]
    if old:
        from app.services.tadawul_http import fetch
        u = old[0]["url"]
        st, html = await fetch(u if u.startswith("http") else X.ORIGIN + u)
        p = X.parse(html or "") if st == 200 else {}
        print("@@OLDPARSE@@" + json.dumps({"filed": old[0]["filed"], "status": st,
                                           "periods": [{k: q.get(k) for k in ("as_of", "revenue", "net_income", "total_assets")}
                                                       for q in (p.get("periods") or [])[:3]]}, ensure_ascii=False))


asyncio.run(main())
