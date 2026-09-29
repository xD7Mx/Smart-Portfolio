"""كاشفٌ للقراءة فقط: بنودُ الإهلاك كما كتبتها كلُّ شركةٍ ناقصة (نحو ≥90٪).

يُحمَّل أحدثُ ملفّ XBRL لكلّ رمزٍ ناقص وتُطبع صفوفُه التي فيها إهلاكٌ أو
استهلاك — بالحرف، لتُضاف إلى LABELS كما هي لا بالتخمين.

    docker exec sp_backend python /app/scripts/audit/dep_labels_door.py
"""
import asyncio
import re
import sys
from collections import Counter

sys.path.insert(0, "/app")
from app.services import tadawul_xbrl as X            # noqa: E402
from app.services.tadawul_http import fetch            # noqa: E402

MISSING = ["2010", "1211", "2350", "4002", "2002", "2330", "1320", "2220", "3002", "3004",
           "4004", "6013", "6014", "2284", "4010", "2370", "6040", "6070", "1835", "4141",
           "4143", "4144", "4147", "4148", "4327", "6016", "7205"]
PAT = re.compile(r"deprec|amorti|إهلاك|استهلاك", re.I)


async def main():
    seen = Counter()
    for s in MISSING:
        files, why = await X.filings_for_ex(s)
        if not files:
            print(f"── {s}: لا ملفّات ({why})")
            continue
        st, html = await fetch(X.ORIGIN + files[0]["url"])
        if st != 200 or not html:
            print(f"── {s}: HTTP {st}")
            continue
        labels = []
        for tr in X._TR.findall(html):
            cells = [X._clean(c) for c in X._TD.findall(tr)]
            if cells and PAT.search(cells[0] or ""):
                n = X._norm(cells[0])
                labels.append(n)
                seen[n] += 1
        print(f"── {s}: {len(labels)} بنداً")
        for n in labels[:6]:
            print("     ", n)
    print("\n═ الأكثرُ تكراراً:")
    for n, c in seen.most_common(15):
        print(f"   {c:>2} × {n}")


asyncio.run(main())
