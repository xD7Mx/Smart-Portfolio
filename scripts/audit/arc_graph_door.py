#!/usr/bin/env python3
"""كاشفُ نداء قائمة البحوث في موقع الراجحي المالية الجديد — قارئٌ فقط.

قِيس (arc_site_door): الصفحةُ صارت Next.js على Sitecore JSS، ولا ‏data-parentId فيها؛ وفي الصفحة المرسومة ملفّاتُ
‎/-/media/Feature/AlRajhiCapital/ResearchListing/…pdf‎ — والنداءُ الوحيدُ بالبيانات ‎POST /sitecore/api/graph/edge‎.
فهذا يسجّل جسمَ ذلك النداء (الاستعلامُ ومتغيّراتُه) وردَّه، ويقرأ من أين يأتي مفتاحُ الواجهة العامّ في الصفحة —
فيُبنى القارئُ بالقياس لا بالتخمين."""
import asyncio, json, os, re, sys, time
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


async def main():
    from playwright.async_api import async_playwright
    from app.services.browser_fetch import _launch_kwargs
    from app.services import research_reports as R
    pw = await async_playwright().start()
    b = await pw.chromium.launch(**_launch_kwargs())
    try:
        ctx = await b.new_context(locale="ar-SA", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page = await ctx.new_page()
        reqs, resps = [], []

        def on_req(r):
            if "graph/edge" in r.url or "/api/" in r.url and r.method == "POST":
                reqs.append((r.url, r.method, r.post_data or ""))

        async def on_resp(r):
            if "graph/edge" in r.url:
                try:
                    resps.append((r.url, r.status, await r.text()))
                except Exception as e:                            # noqa: BLE001
                    resps.append((r.url, r.status, f"<{type(e).__name__}>"))

        page.on("request", on_req)
        page.on("response", lambda r: asyncio.ensure_future(on_resp(r)))
        await page.goto(R.ARC_PAGE, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(12000)
        html = await page.content()
        print("نداءاتُ graph/edge:", len(reqs))
        key_src = re.findall(r"sc_apikey=([0-9A-Fa-f-]{36})", " ".join(u for u, _, _ in reqs))
        print("في النداء مفتاحٌ عامّ:", bool(key_src))       # لا يُطبع منه شيء (‏D385)
        for i, (u, m, body) in enumerate(reqs[:6]):
            print(f"\n── الطلب {i}: {m} {u.split('?')[0][:140]}")
            try:
                j = json.loads(body)
                q = j.get("query", "") if isinstance(j, dict) else ""
                print("   الاستعلام:", re.sub(r"\s+", " ", q)[:2500])
                print("   المتغيّرات:", json.dumps(j.get("variables"), ensure_ascii=False)[:800] if isinstance(j, dict) else "")
                print("   اسمُ العملية:", j.get("operationName") if isinstance(j, dict) else "")
            except Exception:                                     # noqa: BLE001
                print("   الجسم:", body[:800])
        for i, (u, st, txt) in enumerate(resps[:6]):
            print(f"\n── الردّ {i}: {st} · {len(txt)} حرفاً")
            print("  ", re.sub(r"\s+", " ", txt)[:3500])
        # من أين يُقرأ المفتاحُ في الصفحة نفسِها (لا يُحفظ في الشيفرة)
        st = await page.evaluate("() => document.getElementById('__NEXT_DATA__')?.textContent?.length || 0")
        print("\n__NEXT_DATA__:", st, "· المفتاحُ في HTML:", bool(re.search(r"[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}", html)))
        # بندُ قائمةٍ مرسوم: النصُّ حول أوّل ملفّ
        m = re.search(r"ResearchListing/[^\"']+\.pdf", html)
        if m:
            i = m.start()
            print("\nحول أوّل ملفّ في الصفحة المرسومة:", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", html[max(0, i - 1500):i + 300]))[:1500])
        # تبويباتُ/فئاتُ القائمة كما تُرسم
        cats = await page.evaluate("() => [...document.querySelectorAll('button, [role=tab], select option')].map(e => e.textContent.trim()).filter(t => t && t.length < 40).slice(0, 60)")
        print("\nأزرارٌ وخيارات:", cats)
    finally:
        await b.close()
        await pw.stop()


asyncio.run(main())
