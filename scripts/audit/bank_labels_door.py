"""كاشفٌ للقراءة فقط: بنودُ البنوك كما تكتبها «تداول» في XBRL (لتقرير الربع).

المحفظةُ الإقراضية · الودائع · صافي دخل التمويل · الدخلُ التشغيليّ · المخصّصات.
يُطبع كلُّ صفٍّ مطابقٍ بالحرف مع أوّل قيمتين، ليُضاف إلى LABELS كما هو.

    docker exec sp_backend python /app/scripts/audit/bank_labels_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")
from app.services import tadawul_xbrl as X            # noqa: E402
from app.services.tadawul_http import fetch            # noqa: E402

BANKS = ["1120", "1010"]
PAT = re.compile(r"loan|advance|financ|deposit|commission|special|interest|operating income|"
                 r"impairment|credit loss|provision|customer|net income|profit", re.I)


async def main():
    for s in BANKS:
        files, why = await X.filings_for_ex(s)
        if not files:
            print(f"── {s}: لا ملفّات ({why})")
            continue
        for f in files[:2]:
            st, html = await fetch(X.ORIGIN + f["url"])
            print(f"\n══ {s} · {f['filed']} · HTTP {st} · {f['url'][-60:]}")
            if st != 200 or not html:
                continue
            n = 0
            for tr in X._TR.findall(html):
                cells = [X._clean(c) for c in X._TD.findall(tr)]
                if cells and PAT.search(cells[0] or "") and any(X._num(c) is not None for c in cells[1:]):
                    vals = [c for c in cells[1:] if X._num(c) is not None][:2]
                    print(f"   {X._norm(cells[0])[:95]} | {' · '.join(vals)}")
                    n += 1
                    if n >= 70:
                        break


asyncio.run(main())
