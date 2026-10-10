#!/usr/bin/env python3
"""تتبّعُ مصادر آراء بيوت الخبرة في «أرقام» (D664) — قارئٌ فقط.

قِيس: صفحةُ «آراء الشركة» (analystrecomendationopinionbycompany) بلا جدولٍ في HTML، وصفحةُ الوسيط
(brokeropinions/3/{معرّف}) جدولٌ عامّ. فيُكتشف هنا معرّفُ كلّ وسيط: من مراقب الآراء (قائمة الوسطاء) ومن صفحات
الشركات (روابط ?brokerID=)، ثمّ يُقرأ جدولُ كلّ وسيطٍ ويُطبع اسمُه وعددُ صفوفه ومداها."""
import asyncio, collections, html, re, sys, time
sys.path.insert(0, "/app")
A = "https://www.argaam.com"


async def main():
    from app.services.tadawul_http import smart_fetch, smart_flow
    from app.services.argaam_ids import build, snapshot
    import app.services.analyst_opinions as AO
    await build()
    ids = (snapshot() or {}).get("ids") or {}
    found: dict[str, str] = {}
    for u in ("/ar/monitors/analyst-opinion", "/ar/monitors/analyst-estimates"):
        st, b = await smart_fetch(A + u, warm=A + "/ar", referer=A + "/ar", timeout=30)
        b = html.unescape(b or "")
        for bid, name in re.findall(r'brokerID=(\d+)[^>]*>\s*([^<]{2,60})<', b):
            found.setdefault(bid, " ".join(name.split()))
        for bid in re.findall(r"brokerID=(\d+)", b):
            found.setdefault(bid, "")
        opts = re.findall(r'<option[^>]*value="(\d{3,6})"[^>]*>([^<]{2,60})</option>', b)
        nb = len(set(re.findall(r"brokerID=(\d+)", b)))
        print(f"{u} → {st} · معرّفات {nb} · خيارات {len(opts)} — {opts[:40]}")
        for v, n in opts:
            found.setdefault(v, n.strip())
    st, b = await smart_fetch(A + "/ar/analystestimates/analystrecomendationsestimate/3/843/4", warm=A + "/ar", referer=A + "/ar", timeout=30)
    b = html.unescape(b or "")
    ths = [" ".join(re.sub(r"<[^>]+>", " ", h).split()) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", b, re.S)][:14]
    print(f"analystrecomendationsestimate/3/843/4 → {st} · {len(b)} · رؤوس {ths} · صفوف آراء {len(AO.rows_of(b))}")
    # من صفحات عيّنةٍ من الشركات
    sample = [ids[s] for s in ("2222", "1120", "4190", "2010", "7010", "1180", "2280", "1211", "4002", "4260", "2050", "1150") if ids.get(s)]

    def plan():
        for cid in sample:
            st, body = yield {"url": A + f"/ar/company/companyoverview/marketid/3/companyid/{cid}", "referer": A + "/ar"}
            for bid in re.findall(r"brokerID=(\d+)", body or ""):
                found.setdefault(bid, "")
        return None
    await smart_flow(plan, warm=A + "/ar", timeout=30)
    print(f"\nمعرّفاتُ الوسطاء المكتشفة: {len(found)}")
    got = {}

    def plan2():
        for bid in sorted(found, key=int):
            st, body = yield {"url": A + f"/ar/analystestimates/brokeropinions/3/{bid}", "referer": A + "/ar"}
            rs = AO.rows_of(body) if st == 200 else []
            cids = re.findall(r"analystrecomendationopinionbycompany/3/(\d+)", body or "")
            got[bid] = (st, rs, len(cids))
        return None
    t0 = time.time()
    await smart_flow(plan2, warm=A + "/ar", timeout=30)
    print(f"جدولُ كلّ وسيط ({time.time() - t0:.0f}ث):")
    tot = 0
    for bid, (st, rs, nc) in got.items():
        houses = collections.Counter(r["house"] for r in rs)
        ds = sorted(r["date"] for r in rs)
        yr = sum(1 for d in ds if d >= "2025-10-10")
        tot += yr
        print(f"  {bid}: {st} · {len(rs)} صفّاً · في سنة {yr} · {ds[:1]}→{ds[-1:]} · {list(houses)[:2]} · روابطُ شركات {nc}")
    print(f"المجموع في سنة: {tot}")


asyncio.run(main())
