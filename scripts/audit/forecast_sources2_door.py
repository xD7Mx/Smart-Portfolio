#!/usr/bin/env python3
"""كاشفُ مصادر التوقعات — الجولة الثانية (المالك: «أريد جلبَ جميع التوقعات الممكنة من الجهات المعتبرة») — قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/forecast_sources2_door.py

١ «أرقام»: آراءُ بيوت الخبرة (توصيةٌ وسعرٌ مستهدف لكلّ جهة) — أمفتوحةٌ للزائر أم للمشتركين؟ وكم صفّاً؟
٢ «مباشر»: أخبارُ التوصيات.
٣ الراجحي المالية: كلُّ صفحات القائمة وأصنافُها (لا اليوميُّ وحدَه).
٤ الرياض المالية: ما تطلبه صفحةُ أبحاثها فعلاً (المتصفّح) — فالجلبُ يعود قشرة.
٥ كامكو إنفست: أبحاثُ الخليج والسعودية.
"""
import asyncio, collections, html, json, re, sys
sys.path.insert(0, "/app")

LOCK = re.compile(r"subscription-page|اشترك الآن|للإستمرار في قراءة|للاستمرار في قراءة|يرجى تسجيل الدخول|Subscribe|login-required", re.I)


def vis(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s or "", flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def rows(page):
    from app.services.argaam_calendar import _rows_of
    try:
        return _rows_of(page)
    except Exception:                                              # noqa: BLE001
        return []


async def show(name, url, warm=None, n=6):
    from app.services.tadawul_http import smart_fetch
    try:
        st, body = await smart_fetch(url, warm=warm, referer=warm, timeout=35)
    except Exception as e:                                         # noqa: BLE001
        print(f"  ✘ {name}: {type(e).__name__}"); return ""
    body = body or ""
    rs = rows(body)
    locks = sorted(set(m.group(0) for m in LOCK.finditer(body)))[:5]
    print(f"\n── {name}\n   {url}\n   HTTP {st} · {len(body)} حرفاً · صفوف {len(rs)} · أقفال {locks}")
    for r in rs[:n]:
        print("   ص:", " | ".join(" ".join(c.split())[:28] for c in r[:9]))
    if not rs:
        print("   نص:", vis(body)[:500])
    return body


async def main():
    A = "https://www.argaam.com"
    print("═ ١ «أرقام» — آراءُ بيوت الخبرة")
    b = await show("صفحةُ وسيطٍ (2604)", A + "/ar/analystestimates/brokeropinions/3/2604", A + "/ar")
    links = sorted(set(re.findall(r'href="(/ar/analystestimates/brokeropinions/3/\d+[^"]*)"', b)))[:60]
    print(f"   روابطُ وسطاء آخرين في الصفحة: {len(links)} — {links[:12]}")
    await show("آراءُ الرياض المالية", A + "/ar/tadawul/tasi/riyad-capital/researchers-opinions", A + "/ar")
    await show("تقديراتُ المحللين لشركة (بدجت)", A + "/ar/bf/budget-saudi/analyst-estimates", A + "/ar")
    await show("مراقبُ آراء المحللين", A + "/ar/monitors/analyst-opinion", A + "/ar")
    await show("دراسةُ الأسعار المستهدفة الربعية", A + "/ar/reports/quarterly-target-prices/54888", A + "/ar", n=4)

    print("\n═ ٢ «مباشر» — التوصيات")
    mb = await show("مباشر — نبض التوصيات", "https://www.mubasher.info/news/sa/pulse/recommendations", "https://www.mubasher.info/")
    heads = re.findall(r'<a[^>]+href="(/news/[^"]+)"[^>]*>\s*([^<]{20,160})</a>', mb)[:10]
    for h, t in heads:
        print(f"   خبر: {' '.join(t.split())[:100]} ← {h[-60:]}")

    print("\n═ ٣ الراجحي المالية — كلُّ الصفحات")
    import app.services.research_reports as RR
    from app.services.tadawul_http import smart_flow

    def plan():
        st, page = yield {"url": RR.ARC_PAGE, "timeout": 40}
        ps = RR.arc_params(page)
        cats = re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]{2,60})</option>', page or "")
        print(f"   خياراتُ المرشِّحات في الصفحة: {len(cats)} — {cats[:30]}")
        if not ps:
            return None
        allc = collections.Counter()
        tot = 0
        for pg in range(1, 9):
            p = {**ps[0], "pageNo": pg, "pageSize": 30}
            st2, raw = yield {"url": RR.ARC_API, "params": p, "referer": RR.ARC_PAGE,
                              "headers": {"X-Requested-With": "XMLHttpRequest"}}
            try:
                items = (json.loads(raw or "null") or {}).get("Items") or []
            except Exception:                                      # noqa: BLE001
                items = []
            got = RR.arc_items(raw)
            tot += len(got)
            for it in items:
                lv = list(RR._leaves(it))
                cat = next((v for pth, v in lv if "Categories" in pth and pth[-1] == "Name"), "?")
                allc[cat] += 1
            print(f"   صفحة {pg}: HTTP {st2} · بنود {len(items)} · مقروءة {len(got)} · أوّلُها {[(g['date'], g['title'][:30]) for g in got[:2]]}")
            if not items:
                break
        print(f"   الأصناف: {allc.most_common()}")
        if items:
            for pth, v in list(RR._leaves(items[0]))[:30]:
                print(f"      {'/'.join(x for x in pth if x not in ('__interceptors', 'Values'))[-50:]} = {v[:70]}")
        return tot
    print("   المجموع:", await smart_flow(plan, warm=RR.ARC + "/ar", timeout=40))

    print("\n═ ٤ الرياض المالية — نداءاتُ صفحة الأبحاث في المتصفّح")
    try:
        from app.services.browser_fetch import sniff
        res = await sniff("https://www.riyadcapital.com/ar/research-reports", settle_ms=9000,
                          want=r"(?i)json|research|report|document|/o/|api")
        xs = [c for c in res.get("calls", []) if c.get("type") in ("xhr", "fetch") or re.search(r"(?i)research|\.pdf|documents", c.get("url", ""))]
        for c in xs[:25]:
            print(f"   {c.get('status')} {c.get('type')} {c.get('url')[:150]}")
        for k, v in list((res.get("bodies") or {}).items())[:4]:
            print(f"   جسم {k[-80:]}: {str(v)[:400]}")
        h = res.get("html") or ""
        pdfs = sorted(set(re.findall(r'href="([^"]+(?:\.pdf|/documents/[^"]+))"', h)))
        print(f"   روابطُ ملفّات في الصفحة المرسومة: {len(pdfs)} — {pdfs[:10]}")
        print("   نص:", vis(h)[:600])
    except Exception as e:                                         # noqa: BLE001
        print(f"   ✘ المتصفّح: {type(e).__name__}: {str(e)[:160]}")

    print("\n═ ٥ كامكو إنفست")
    await show("كامكو — الأبحاث", "https://www.kamcoinvest.com/research", "https://www.kamcoinvest.com/")


asyncio.run(main())
