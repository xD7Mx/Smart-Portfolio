"""كاشف (قراءةٌ فقط): بنيةُ جداول «المعلومات المالية» — الصفحةُ نفسُها وخدمةُ statementsTabData
لكلّ نوع قائمةٍ وتقرير: عناوينُ الجداول وتواريخُها وأوّلُ البنود بأرقامها.

    docker exec sp_backend python /app/scripts/audit/profile_fin_door2.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")


def tables(html: str):
    out = []
    for t in re.findall(r"<table.*?</table>", html or "", re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr.*?</tr>", t, re.S | re.I):
            cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                     for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)]
            cells = [c for c in cells if c]
            if cells:
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


async def main():
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    from app.services.tadawul_xbrl import ORIGIN, _NJ, _BASE
    sym = "8250"
    url = (row_for(sym) or {}).get("company_url")
    full = ORIGIN + url
    st, page = await fetch(full)
    print("@@page@@", st, flush=True)
    for i, t in enumerate(tables(page)[:12]):
        if any(re.search(r"20\d\d-\d\d-\d\d", c) for c in t[0]):
            print(f"  page-table{i}: {t[0]} | rows={len(t)} | {[r[:3] for r in t[1:6]]}", flush=True)
    base = _BASE.search(page).group(1).rstrip("/")
    ep = next(m.group(0) for m in _NJ.finditer(page) if m.group(1) == "statementsTabData")
    for stype in ("1", "2", "3", "4", "5", "6"):
        for rtype in ("1", "2"):
            s2, b2 = await fetch(base + "/" + ep, params={"statementType": stype, "reportType": rtype,
                                                            "requestLocale": "en", "symbol": sym}, referer=full)
            ts = tables(b2)
            print(f"@@st{stype} rt{rtype}@@ {s2} len={len(b2 or '')} tables={len(ts)}", flush=True)
            for t in ts[:4]:
                print(f"   head={t[0][:8]} rows={len(t)} first={[r[:4] for r in t[1:5]]}", flush=True)

asyncio.run(main())
