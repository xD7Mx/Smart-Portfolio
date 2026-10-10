#!/usr/bin/env python3
"""قارئُ تقارير الجهات المرخّصة على الخادم (D662) — قارئٌ فقط: ما يخرج من كلّ جهةٍ بالشيفرة نفسِها قبل النشر.

    docker exec sp_backend python /app/scripts/audit/research_reader_door.py
"""
import asyncio, collections, html, json, re, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
import app.services.research_reports as RR


async def main():
    from app.services.tadawul_http import smart_fetch
    st, body = await smart_fetch(RR.AJC_PAGE, warm=RR.AJC + "/ar", referer=RR.AJC + "/ar", timeout=45)
    body = body or ""
    print(f"═ الجزيرة كابيتال: HTTP {st} · {len(body)}")
    for t in re.finditer(r"<table\b.*?</table>", body, re.S | re.I):
        tb = t.group(0)
        heads = [RR._txt(h) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", tb, re.S | re.I)]
        pre = RR._txt(body[max(0, t.start() - 700):t.start()])[-90:]
        print(f"   جدول · رؤوس {heads} · صفوف {len(re.findall(r'<tr', tb))} · قبله «{pre}»")
    a = RR.ajc_items(body)
    print(f"   بنود {len(a)} · أصناف {collections.Counter(x['kind'] for x in a).most_common()}")
    for x in sorted(a, key=lambda x: x["date"], reverse=True)[:12]:
        print(f"   {x['date']} · {x['kind']} · {x['title'][:70]} · {x.get('company')} · عادل {x.get('fair_value')} · {x['url'][-50:]}")
    comp = sorted([x for x in a if x["kind"] == "تقرير شركة"], key=lambda x: x["date"], reverse=True)[:10]
    print("   أحدثُ تقارير الشركات:")
    for x in comp:
        print(f"     {x['date']} · {x['title'][:80]} · رمز {x.get('company')} · عادل {x.get('fair_value')}")

    j = await RR._jadwa()
    print(f"\n═ جدوى: {len(j)} بنداً")
    for x in j[:8]:
        print(f"   {x['date']} · {x['kind']} · {x['title'][:80]} · {x['url'][-60:]}")

    from app.services.tadawul_http import smart_flow
    def plan():
        st, page = yield {"url": RR.ARC_PAGE, "timeout": 40}
        ps = RR.arc_params(page)
        print(f"\n═ الراجحي المالية: صفحة {st} · صِيَغ {ps}")
        for p in ps:
            st2, raw = yield {"url": RR.ARC_API, "params": p, "referer": RR.ARC_PAGE,
                              "headers": {"X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*"}}
            print(f"   النداء {p.get('category')!r}/{p.get('culture')}: {st2} · {len(raw or '')} · {(raw or '')[:700]}")
            try:
                first = (json.loads(raw or "null") or {}).get("Items", [None])[0]
                for pth, v in list(RR._leaves(first))[:40]:
                    print(f"      {'/'.join(x for x in pth if x not in ('__interceptors', 'Values'))[-60:]} = {v[:90]}")
            except Exception as e:                                 # noqa: BLE001
                print(f"      ✘ {e}")
            got = RR.arc_items(raw) if st2 == 200 else []
            if got:
                return got
        return []
    r = await smart_flow(plan, warm=RR.ARC + "/ar", timeout=40) or []
    print(f"   بنود {len(r)}")
    for x in r[:8]:
        print(f"   {x['date']} · {x['kind']} · {x['title'][:80]} · {x['url'][-60:]}")

    allr = await RR.collect()
    print(f"\n═ المجموعُ بعد الانتقاء: {len(allr)} · {collections.Counter(x['source'] for x in allr).most_common()} · {collections.Counter(x['kind'] for x in allr).most_common()}")
    from app.services.forecasts import build
    b = await build()
    print(f"═ تبويبُ التوقعات كما يُبنى: {len(b)} بنداً · أوّلُها {[(x['date'], x['source'], x['title'][:40]) for x in b[:5]]}")


asyncio.run(main())
