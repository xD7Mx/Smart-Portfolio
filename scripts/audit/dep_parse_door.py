"""كاشفٌ للقراءة فقط: لماذا لا تُقرأ قيمةُ الإهلاك وصياغتُها معروفة؟

لسابك والمواساة وأنابيب ودي بي اس: الصفُّ الخامُ بخلاياه، وما أخرجه parse()
لكلّ فترة، وأعمدةُ «End Date» — ليُرى أين يسقط الرقم.

    docker exec sp_backend python /app/scripts/audit/dep_parse_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")
from app.services import tadawul_xbrl as X            # noqa: E402
from app.services.tadawul_http import fetch            # noqa: E402

PAT = re.compile(r"deprec|amorti", re.I)


async def main():
    for s in ("2010", "4002", "1320", "7205"):
        files, _ = await X.filings_for_ex(s)
        print(f"\n══ {s}: ملفّات {len(files)} · أوّلُها {files[0].get('filed') if files else None} · {[f.get('kind') for f in files[:4]]}")
        if not files:
            continue
        st, html = await fetch(X.ORIGIN + files[0]["url"])
        n_end = 0
        for tr in X._TR.findall(html or ""):
            cells = [X._clean(c) for c in X._TD.findall(tr)]
            if not cells:
                continue
            h = X._norm(cells[0])
            if h == "end date":
                n_end += 1
                print(f"   End Date #{n_end}: {cells[1:6]}")
            if PAT.search(h) and "accumulated" not in h:
                print(f"   صفّ: {cells[:6]}")
        got = X.parse(html or "")
        print(f"   parse: نوع {got.get('kind')} · فترات {len(got.get('periods') or [])}")
        for p in (got.get("periods") or [])[:2]:
            print(f"     {p.get('as_of')}: dep={p.get('depreciation')} ebitda={p.get('ebitda')} ebit={p.get("ebit")}")
        ann = X.for_symbol(s, "annual")
        if ann:
            a = ann[-1]
            print(f"   المخزَّن آخرُ سنة {a.get('as_of')}: dep={a.get('depreciation')} ebitda={a.get('ebitda')}")


asyncio.run(main())
