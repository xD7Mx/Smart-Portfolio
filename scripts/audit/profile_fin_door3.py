"""كاشف (قراءةٌ فقط): بنودُ جداول «المعلومات المالية» كاملةً لأربعة أنماط — لبناء القارئ عليها.

    docker exec sp_backend python /app/scripts/audit/profile_fin_door3.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")


def tables(html):
    out = []
    for t in re.findall(r"<table.*?</table>", html or "", re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr.*?</tr>", t, re.S | re.I):
            cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                     for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)]
            if any(cells):
                rows.append(cells)
        out.append(rows)
    return out


async def main():
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    from app.services.tadawul_xbrl import ORIGIN
    for s in ("8010", "1150", "2310", "4002"):
        st, page = await fetch(ORIGIN + (row_for(s) or {}).get("company_url"))
        # موضعُ كلِّ جدولٍ بين علامات التبويب: سنويٌّ أم ربعيّ
        print(f"@@{s}@@ marks:", [m.group(0)[:60] for m in re.finditer(r"anualQuater|Annually|Quarterly|id=\"(?:annual|quarter)[^\"]*\"", page or "")][:12], flush=True)
        for i, t in enumerate(tables(page)):
            if not t or not any(re.search(r"20\d\d-\d\d-\d\d", c) for c in t[0]):
                continue
            pos = page.find(t[0][0])
            print(f"  T{i} head={t[0]}", flush=True)
            for r in t[1:]:
                print(f"     {r}", flush=True)

asyncio.run(main())
