#!/usr/bin/env python3
"""كاشفُ صفحة بحوث الراجحي المالية بعد تغيّرها — قارئٌ فقط (ملاحظةُ المالك 2026-11-14: «موجودٌ في موقعهم بشكلٍ سليم،
ولكنك وضعتَ رابطاً عند الضغط عليه تخرج صورةُ أيقونة المشاركة»).

قِيس قبله (arc_links_door): الصفحةُ تعود 200 ولا ‏data-parentId فيها — فالقارئُ لا يبلغ قائمةَ البحوث أصلاً، وبنودُ
الراجحي في «التوقعات» من «أرقام» برابط صفحة الجهة العامّة. فهذا الكاشفُ يسمّي كيف تنشر الصفحةُ بحوثَها الآن:
  ١ بالجلب المنتحِل: سماتُ ‏data-*، والنماذج، وأسماءُ الخدمات في السكربتات، وروابطُ ‎.pdf‎ و‎/-/media/‎ بعيّنات.
  ٢ بالمتصفّح (حركةُ الشبكة): نداءاتُ XHR/fetch وأجسامُ المرشَّحين محدودةً — فيُسمّى البابُ بالقياس لا بالتخمين."""
import asyncio, json, os, re, sys, time
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None


def _short(s, n=160):
    s = re.sub(r"\s+", " ", str(s or ""))
    return s[:n]


async def main():
    from app.services import research_reports as R
    from app.services.tadawul_http import smart_fetch
    found = False
    for url in (R.ARC_PAGE, R.ARC + "/ar/research", R.ARC + "/en/research"):
        st, page = await smart_fetch(url, warm=R.ARC + "/ar", referer=R.ARC + "/ar", timeout=40)
        page = page or ""
        print(f"\n══ {url} → {st} · {len(page)} حرفاً")
        t = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
        print("العنوان:", _short(t.group(1) if t else "", 120))
        attrs = sorted(set(re.findall(r"\b(data-[a-zA-Z0-9_-]+)=", page)))
        print("سماتُ data-*:", ", ".join(attrs[:60]))
        for a in ("data-parentid", "data-lang", "data-pagesize", "data-api", "data-url", "data-endpoint", "data-source", "data-id"):
            for m in re.finditer(a + r"=[\"']([^\"']{1,160})[\"']", page, re.I):
                print(f"   {a} = {m.group(1)[:120]}")
        print("نماذج:", [(_short(m.group(1), 140)) for m in re.finditer(r"<form([^>]*)>", page, re.I)][:6])
        svc = sorted(set(re.findall(r"[\"'](/[A-Za-z0-9_/.-]*(?:api|Api|API|Listing|listing|Research|research|Search|search)[A-Za-z0-9_/.-]*)[\"']", page)))
        print("مساراتُ خدماتٍ في النصّ:", svc[:40])
        srcs = re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", page, re.I)
        print("سكربتات:", [s for s in srcs if "rajhi" in s or s.startswith("/")][:20])
        pdfs = re.findall(r"[\"'(]([^\"'()\s]+\.pdf(?:\?[^\"'()\s]*)?)", page, re.I)
        print(f"روابطُ ‎.pdf‎: {len(pdfs)}", [p[:150] for p in pdfs[:8]])
        found = found or len(pdfs) >= 3
        media = re.findall(r"[\"'(]([^\"'()\s]*/-/media/[^\"'()\s]+)", page, re.I)
        print(f"روابطُ ‎/-/media/‎: {len(media)}", [m[:150] for m in media[:10]])
        if st == 200 and len(page) > 1000:
            # أوّلُ موضعٍ يذكر «تقرير» أو تاريخاً قريباً — عيّنةٌ من شكل البند كما يُرسم
            m = re.search(r"(20\d\d[-/]\d\d[-/]\d\d|\d\d[-/]\d\d[-/]20\d\d)", page)
            if m:
                i = m.start()
                print("عيّنةُ ما حول أوّل تاريخ:", _short(re.sub(r"<[^>]+>", " ", page[max(0, i - 600):i + 400]), 700))
            # سكربتاتُ الصفحة نفسِها: أسماءُ دوالٍّ ونداءات
            for s in [s for s in srcs if s.startswith("/") and re.search(r"research|listing|custom|main|app", s, re.I)][:4]:
                st2, js = await smart_fetch(R.ARC + s, referer=url, timeout=30)
                calls = sorted(set(re.findall(r"[\"'`](/(?:sitecore|api|[a-z]{2}/api)[^\"'`\s]{3,120})[\"'`]", js or "")))
                print(f"   سكربت {s[:90]} → {st2} · {len(js or '')} · نداءات:", calls[:20])

    # ٢ حركةُ الشبكة في المتصفّح — وحدَه إن لم يكفِ الجلب (ذاكرةُ الخادم ضيّقة: لا يُفتح متصفّحٌ بلا حاجة)
    if found:
        print("\nالجلبُ وجد ملفّاتِ البحوث في نصّ الصفحة — لا حاجةَ إلى المتصفّح.")
        return
    try:
        from app.services.browser_fetch import sniff
        res = await sniff(R.ARC_PAGE, settle_ms=12000, hosts=("alrajhi-capital.sa",), max_bodies=6)
        xhr = [c for c in res.get("calls", []) if c.get("type") in ("xhr", "fetch")]
        print(f"\n══ المتصفّح: {len(res.get('calls', []))} نداءً · منها XHR/fetch {len(xhr)}")
        for c in xhr[:40]:
            print("  ", c.get("status"), c.get("method", ""), _short(c.get("url"), 220))
        for path, b in list((res.get("bodies") or {}).items())[:4]:
            print(f"\n   جسمُ {path[:160]}:\n   {_short(b, 2500)}")
        html = res.get("html") or ""
        if html:
            pdfs = re.findall(r"href=[\"']([^\"']+\.pdf[^\"']*)[\"']", html, re.I)
            hrefs = re.findall(r"href=[\"']([^\"']*(?:/-/media/|research|report)[^\"']*)[\"']", html, re.I)
            print(f"\n   في الصفحة المرسومة: ‎.pdf‎ {len(pdfs)} · روابطُ بحوث/وسائط {len(hrefs)}")
            for h in (pdfs or hrefs)[:12]:
                print("     ", h[:200])
    except Exception as e:                                        # noqa: BLE001
        print("المتصفّح:", type(e).__name__, str(e)[:200])


asyncio.run(main())
