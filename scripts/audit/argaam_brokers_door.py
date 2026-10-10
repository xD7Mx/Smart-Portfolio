#!/usr/bin/env python3
"""شكلُ جداول آراء بيوت الخبرة في «أرقام» (D664) — قارئٌ فقط: قائمةُ الجهات · روابطُ الصفوف · الترقيم.

    docker exec sp_backend python /app/scripts/audit/argaam_brokers_door.py
"""
import asyncio, collections, html, re, sys
sys.path.insert(0, "/app")
A = "https://www.argaam.com"


def sq(s, n=600):
    return re.sub(r"\s+", " ", s)[:n]


async def main():
    from app.services.tadawul_http import smart_fetch
    st, b = await smart_fetch(A + "/ar/analystestimates/brokeropinions/3/2604", warm=A + "/ar", referer=A + "/ar", timeout=40)
    b = html.unescape(b or "")
    print(f"صفحةُ 2604: {st} · {len(b)}")
    sels = re.findall(r"<select\b[^>]*>(.*?)</select>", b, re.S | re.I)
    print(f"قوائمُ اختيار: {len(sels)}")
    for s in sels[:6]:
        opts = re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]{1,60})</option>', s)
        print(f"  {len(opts)} خياراً — {opts[:40]}")
    ids = sorted(set(re.findall(r"brokeropinions/3/(\d+)", b)))
    print(f"معرّفاتُ وسطاء في الصفحة: {ids[:80]}")
    slugs = sorted(set(re.findall(r"/ar/tadawul/tasi/([a-z0-9\-]+)/researchers-opinions", b)))
    print(f"أسماءُ صفحات آراء: {slugs[:80]}")
    for m in list(re.finditer(r"<table\b", b))[:2]:
        print("جدول:", sq(b[m.start():m.start() + 2500], 2500))
    for kw in ("pageno", "PageNo", "page=", "LoadMore", "loadMore", "brokeropinions", "تحميل"):
        idx = [x.start() for x in re.finditer(kw, b)][:2]
        for i in idx:
            print(f"[{kw}] …{sq(b[max(0, i - 250):i + 250], 500)}")
    st2, c = await smart_fetch(A + "/ar/bf/budget-saudi/analyst-estimates", warm=A + "/ar", referer=A + "/ar", timeout=40)
    c = html.unescape(c or "")
    for m in list(re.finditer(r"<tr\b", c))[1:3]:
        print("صفُّ شركة:", sq(c[m.start():m.start() + 1500], 1500))
    hrefs = collections.Counter(re.sub(r"\d+", "#", h) for h in re.findall(r'href="([^"]+)"', c) if re.search(r"pdf|download|research|report|analyst", h, re.I))
    print("أنماطُ الروابط:", hrefs.most_common(12))


asyncio.run(main())
