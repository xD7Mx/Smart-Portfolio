#!/usr/bin/env python3
"""تتبّعُ ما ردّته صفحاتُ آراء الشركة وقائمةُ الراجحي بفئاتها (D664) — قارئٌ فقط."""
import asyncio, html, json, re, sys
sys.path.insert(0, "/app")
A = "https://www.argaam.com"


async def main():
    from app.services.tadawul_http import smart_fetch, smart_flow
    from app.services.argaam_ids import build, snapshot
    await build()
    ids = (snapshot() or {}).get("ids") or {}
    for sym in ("4260", "4190", "2222"):
        cid = ids.get(sym)
        print(f"═ {sym} · معرّفُ أرقام {cid}")
        for u in (f"/ar/analystestimates/analystrecomendationopinionbycompany/3/{cid}",
                  f"/ar/company/companyoverview/marketid/3/companyid/{cid}"):
            st, b = await smart_fetch(A + u, warm=A + "/ar", referer=A + "/ar", timeout=30)
            b = html.unescape(b or "")
            ths = [re.sub(r"<[^>]+>|\s+", " ", h).strip() for h in re.findall(r"<th\b[^>]*>(.*?)</th>", b, re.S)][:12]
            bf = sorted(set(re.findall(r'href="(/ar/bf/[^"/]+/[^"]*)"', b)))[:8]
            title = re.search(r"<title>(.*?)</title>", b, re.S)
            print(f"  {u} → {st} · {len(b)} · عنوان «{(title.group(1).strip() if title else '')[:80]}» · رؤوس {ths}")
            print(f"     روابطُ bf: {bf}")
            ana = sorted(set(re.findall(r'href="([^"]*analyst[^"]*)"', b, re.I)))[:8]
            print(f"     روابطُ المحللين: {ana}")
    import app.services.research_reports as RR

    def plan():
        st, page = yield {"url": RR.ARC_PAGE, "timeout": 40}
        ps = RR.arc_params(page)
        di = re.findall(r'<input[^>]*id="[^"]*input-date[^"]*"[^>]*>', page or "")
        print(f"\n═ الراجحي: حقلُ التاريخ {di[:2]}")
        for cat, date, size in (("بحوث الأسهم", "0", 30), ("بحوث الأسهم", "0", 300), ("بحوث الأسهم", "2026", 30),
                                ("بحوث الاقتصاد", "0", 300)):
            p = {**ps[0], "category": cat, "date": date, "pageSize": size, "pageNo": 1}
            st2, raw = yield {"url": RR.ARC_API, "params": p, "referer": RR.ARC_PAGE, "headers": {"X-Requested-With": "XMLHttpRequest"}}
            got = RR.arc_items(raw) if st2 == 200 else []
            ds = sorted(x["date"] for x in got)
            try:
                d = json.loads(raw or "null") or {}
                meta = {k: v for k, v in d.items() if k != "Items"} if isinstance(d, dict) else {}
            except Exception:                                      # noqa: BLE001
                meta = {}
            print(f"  {cat} · تاريخ {date} · حجم {size}: HTTP {st2} · {len(got)} · من {ds[:1]} إلى {ds[-1:]} · {str(meta)[:200]}")
        return None
    await smart_flow(plan, warm=RR.ARC + "/ar", timeout=40)


asyncio.run(main())
