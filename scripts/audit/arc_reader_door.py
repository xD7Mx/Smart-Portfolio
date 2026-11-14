#!/usr/bin/env python3
"""كاشفُ قارئ الراجحي المالية الجديد على الخادم (‏D733) — قارئٌ فقط: يشغّل القارئَ نفسَه ويطبع ما يقرؤه، ومن أين قرأ
المفتاحَ والاستعلام، وما يُربط من آراء «أرقام» بتقاريرها. لا يكتب في المخزَّن."""
import asyncio, os, re, sys, time
from collections import Counter
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None


async def main():
    from app.services import research_reports as R
    from app.services.tadawul_http import smart_fetch
    st, page = await smart_fetch(R.ARC_PAGE, warm=R.ARC + "/ar", timeout=40)
    d = R.arc_discover([page])
    print("الصفحة:", st, "· من HTML:", {k: (v[:8] + "…") for k, v in d.items()})
    t0 = time.time()
    items = await R._arc()
    print(f"القارئ: {len(items)} بنداً في {time.time() - t0:.1f}ث · الأصناف: {Counter(x['kind'] for x in items).most_common()}")
    print("أحدثُ تاريخ:", max((x["date"] for x in items), default="—"), "· أقدمُه:", min((x["date"] for x in items), default="—"))
    bad = [x for x in items if not re.search(r"\.pdf$", x["url"].split("?")[0], re.I)]
    print("روابطُ ليست PDF:", len(bad), [b["url"][-70:] for b in bad[:3]])
    for x in [i for i in items if i["kind"] != "تقرير يوميّ"][:12]:
        print(f"   {x['date']} · {x['kind']} · رمز {x.get('company')} · {x['title'][:60]} · {x['url'][-70:]}")
    for x in [i for i in items if i["kind"] == "تقرير يوميّ"][:3]:
        print(f"   {x['date']} · يوميّ · {x['url'][-70:]}")
    sel = R.select(items)
    print("بعد الانتقاء (سنة · خمسةُ يوميّات):", len(sel))
    from app.services.analyst_opinions import as_forecasts
    ops = R.select(as_forecasts())
    rj = [o for o in ops if "الراجحي" in str(o.get("source"))]
    R.link_opinions(ops, sel)
    linked = [o for o in rj if o.get("url")]
    print(f"آراءُ الراجحي في «أرقام»: {len(rj)} · رُبط منها بتقريرٍ في موقعها: {len(linked)}")
    for o in linked[:8]:
        print(f"   {o['date']} · {o['title'][:50]} → {o['url'][-70:]} ({o.get('report_title', '')[:40]})")


asyncio.run(main())
