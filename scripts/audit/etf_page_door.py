"""كاشفٌ للقراءة فقط: بابُ «تداول» لصناديق المؤشرات المتداولة (94xx).

لقطةُ السوق الرئيسة لا تحملها (قِيس: 9400/9405/9408 غائبة). فيُكتشف رابطُ صفحة
الصناديق من صفحة السوق نفسِها، ثمّ أسماءُ خدماتها (=NJ…=) — FETCH_METHOD §٢.

    docker exec sp_backend python /app/scripts/audit/etf_page_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")
from app.services.tadawul_http import fetch               # noqa: E402
from app.services.tadawul_market import PAGE               # noqa: E402

ORIGIN = "https://www.saudiexchange.sa"
EP = re.compile(r"=NJ([A-Za-z]{4,60})=/")


async def main():
    st, body = await fetch(PAGE)
    links = sorted(set(re.findall(r'href="(/wps/portal/saudiexchange/[^"#?]*(?:etf|fund|exchange-traded)[^"#?]*)"', body or "", re.I)))
    print(f"صفحةُ السوق {st} · روابطُ صناديق {len(links)}")
    for l in links[:12]:
        print("   ", l)
    cands = links[:4] + [
        "/wps/portal/saudiexchange/ourmarkets/funds-market-watch",
        "/wps/portal/saudiexchange/ourmarkets/etfs-market-watch",
    ]
    for u in dict.fromkeys(cands):
        s2, b2 = await fetch(ORIGIN + u)
        names = sorted(set(EP.findall(b2 or "")))
        syms = sorted(set(re.findall(r"\b(94\d\d)\b", b2 or "")))
        print(f"\n── {u}: {s2} · {len(b2 or '')} · خدمات {names[:15]} · رموز94 {syms[:12]}")


asyncio.run(main())
