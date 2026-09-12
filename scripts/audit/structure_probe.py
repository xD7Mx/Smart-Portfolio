#!/usr/bin/env python3
"""مسبارُ بنية — الإصدارُ الثاني، مبنيٌّ على ما رُدّ لا على ترجيحي (D273 · D270).

    docker exec sp_backend python /app/scripts/audit/structure_probe.py deals
    docker exec sp_backend python /app/scripts/audit/structure_probe.py own 1010

## ما قاله القياسُ الأوّل، وما غيّره

**الصفقاتُ الخاصة**: صفرُ جداولَ في 556 ألفَ حرف — فالصفحةُ **قشرةٌ**
والجدولُ يُرسَم بعدها. والنداءاتُ الظاهرةُ كلُّها خدماتُ الترويسة
(‏TickerServlet · ThemeTASIUtilityServlet) لا جدولَ الصفقات. وقد ثبت أن
**المتصفّح يعمل على الخادم** — فتُفتح الصفحةُ به ويُقاس ما رُسم، وتُلتقط
مع ذلك نداءاتُ الشبكة التي أطلقتها الصفحةُ نفسُها: إن وُجد نداءٌ نظيفٌ
استُغني عن المتصفّح لاحقاً، وإلّا بقي هو الوسيلة.

**هيكلُ الملكية**: رابطٌ واحدٌ من أربعةٍ اكتُشف، والصفحةُ بلا جداول،
وفيها `locked-menu` و`lock-menu-icon` تسعاً وأربعين مرّة — وهذه إشارةُ
**محتوًى مقفلٍ خلف اشتراك**، لا إشارةُ قارئٍ ضعيف. والفرقُ حاسم: قارئٌ
يُصلَح، واشتراكٌ يُقال للمالك ولا يُلتفّ عليه. فيُطبع النصُّ المرئيُّ
بعد نزع السكربتات، وتُطبع كلُّ الروابط المرشَّحة بأسمائها الحقيقية.
"""
from __future__ import annotations

import asyncio
import re
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

TAG = re.compile(r"<[^>]+>")
DROP = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)
LOCK_WORDS = ("locked", "lock-menu", "اشترك", "الاشتراك", "تسجيل الدخول",
              "للمشتركين", "باقة", "premium", "subscribe")


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", TAG.sub(" ", DROP.sub(" ", html or ""))).strip()


def describe(html: str, label: str) -> None:
    print(f"\n── {label}: {len(html)} حرفاً")
    tabs = re.findall(r"<table[^>]*>(.*?)</table>", html, re.S | re.I)
    print(f"   جداول: {len(tabs)}")
    for i, tb in enumerate(tabs[:6]):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S | re.I)
        print(f"     [{i}] صفوف={len(rows)} · {visible(rows[0])[:100] if rows else '—'}")
        if len(rows) > 1:
            print(f"          {visible(rows[1])[:100]}")
    if not tabs:
        body = DROP.sub(" ", html)
        common = [(c, n) for c, n in
                  Counter(re.findall(r'class="([^"]{3,60})"', body)).most_common(18)
                  if n >= 3]
        print("   لا جدول. أكثرُ الأصناف تكراراً (بعد نزع السكربتات):")
        for c, n in common:
            print(f"     {n:>4} × {c}")

    # ══ المقفلُ يُقال مقفلاً ══
    hits = [w for w in LOCK_WORDS if w.lower() in html.lower()]
    if hits:
        print(f"   ⚠ إشاراتُ إقفال: {', '.join(hits)}")
        for w in hits[:3]:
            i = html.lower().index(w.lower())
            print(f"     سياقُ «{w}»: {visible(html[max(0,i-160):i+200])[:170]}")

    txt = visible(html)
    print(f"   النصُّ المرئيّ ({len(txt)} حرفاً):")
    print("     " + (txt[:700] if txt else "— لا نصّ"))


async def deals() -> None:
    from app.services.special_deals import PAGE
    from app.services.browser_fetch import BrowserUnavailable, _launch_kwargs

    # ١ · بالمتصفّح، مع التقاط نداءات الشبكة التي تُطلقها الصفحةُ نفسُها.
    try:
        from playwright.async_api import async_playwright
    except Exception as e:                                        # noqa: BLE001
        raise BrowserUnavailable(str(e)) from e

    calls: list[tuple[str, str]] = []
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(**_launch_kwargs())
    try:
        ctx = await browser.new_context(locale="ar-SA")
        page = await ctx.new_page()

        def on_resp(r):
            u = r.url
            if any(k in u.lower() for k in ("json", "servlet", "deal", "=nj")):
                calls.append((str(r.status), u))

        page.on("response", on_resp)
        await page.goto(PAGE, timeout=45_000, wait_until="domcontentloaded")
        await page.wait_for_timeout(9_000)
        html = await page.content()
    finally:
        await browser.close()
        await pw.stop()

    describe(html, "صفحةُ الصفقات الخاصة (بعد رسم المتصفّح)")
    print("\n   نداءاتُ الشبكة التي أطلقتها الصفحة:")
    seen = set()
    for st, u in calls:
        if u in seen:
            continue
        seen.add(u)
        print(f"     {st} · {u[:150]}")
    if not calls:
        print("     — لا نداءَ مطابقاً")


async def own(sym: str) -> None:
    from app.services import ownership as ow
    from app.services.argaam_calendar import BASE, _company_id, _company_url
    from app.services.browser_fetch import render

    cid = await _company_id(sym)
    print(f"معرِّفُ الشركة: {cid}")
    if not cid:
        return
    home = next(iter((await render([_company_url(cid)])).values()), "")

    # ══ الروابطُ الحقيقيةُ تُطبع كلُّها ══
    # ثلاثةٌ من أربعةٍ لم تُكتشَف، فلعلّ أسماءها غيرُ ما افترضتُ. فتُطبع كلُّ
    # رابطٍ يحمل معنى الملكية بنصِّه كما هو — ومنه تُبنى المطابقة.
    print("\nكلُّ الروابط ذات الصلة كما وردت:")
    KEYS = ("shareholder", "ownership", "foreign", "estimate", "insider",
            "major", "holders", "forecast", "target")
    seen = set()
    for href, label in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                                  home, re.S | re.I):
        if not any(k in href.lower() for k in KEYS):
            continue
        if href in seen:
            continue
        seen.add(href)
        print(f"   «{visible(label)[:40]}» → {href[:120]}")

    links = ow.tab_links(home, BASE)
    print(f"\nما التقطه القارئُ الحالي: {sorted(links)}")
    if not links:
        describe(home, "صفحةُ الشركة")
        return
    pages = await render(list(links.values()), settle_ms=8000)
    for k, u in links.items():
        describe(pages.get(u, ""), k)


a = sys.argv[1:] or ["deals"]
asyncio.run(deals() if a[0] == "deals" else own(a[1] if len(a) > 1 else "1010"))
