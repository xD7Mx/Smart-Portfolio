#!/usr/bin/env python3
"""مسبارُ بنية ٣ — يقيس ما بعد التصحيح، ولا يكتب قارئاً قبل القياس.

    docker exec sp_backend python /app/scripts/audit/structure_probe.py own 1010
    docker exec sp_backend python /app/scripts/audit/structure_probe.py deals

## ما ثبت في القياس الثاني

· **«تداول» تحجب مسارَ الصفقات الخاصة عند الحافّة**: 200 وقشرةٌ بلا جدولٍ
  للجلب المنتحِل، و**403 Access Denied** من أكامايّ لمتصفّحٍ حقيقيّ. فلا
  حيلةَ في السكربت — المسارُ محجوب. و«أرقام» تنشرها بمسارين ظهرا بأسمائهما.

· **وأسماءُ تبويبات «أرقام» غيرُ ما افترضت**: «ملكية الأجانب» لا «الملكية
  الأجنبية»، و«الصفقات الخاصة» لا «صفقات كبار المساهمين»، و«توصيات
  المحللين» لا «تقديرات». فصار المعوَّلُ على المسار، والنصُّ سندٌ ثانٍ.

· **ولا `<table>` في صفحاتها** — الصفوفُ حاوياتٌ. فأُضيف قارئُ الحاويات،
  وهذا المسبارُ يقيس كم صفّاً يفهم **قبل** أن يُبنى عليه شيء.
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


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", TAG.sub(" ", DROP.sub(" ", html or ""))).strip()


async def grab(urls: list[str], settle: int = 9000) -> tuple[dict, list]:
    """يفتح الصفحاتِ بالمتصفّح ويلتقط نداءاتِ الشبكة معها."""
    from app.services.browser_fetch import _launch_kwargs
    from playwright.async_api import async_playwright

    calls: list[tuple[str, str]] = []
    out: dict[str, str] = {}
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(**_launch_kwargs())
    try:
        ctx = await browser.new_context(locale="ar-SA")
        page = await ctx.new_page()
        page.on("response", lambda r: calls.append((str(r.status), r.url))
                if any(k in r.url.lower() for k in
                       ("json", "ajax", "getdata", "partial", "deal", "holder"))
                else None)
        for u in urls:
            try:
                await page.goto(u, timeout=45_000, wait_until="domcontentloaded")
                await page.wait_for_timeout(settle)
                out[u] = await page.content()
            except Exception as e:                                # noqa: BLE001
                out[u] = ""
                print(f"   تعذّر {u[:70]}: {type(e).__name__}")
    finally:
        await browser.close()
        await pw.stop()
    return out, calls


def describe(html: str, label: str) -> None:
    from app.services import ownership as ow

    print(f"\n── {label}: {len(html)} حرفاً")
    tabs = re.findall(r"<table[^>]*>(.*?)</table>", html, re.S | re.I)
    print(f"   جداول: {len(tabs)}")

    rows = ow.parse(html)
    print(f"   صفوفٌ فهمها القارئُ الآن: {len(rows)}")
    for r in rows[:8]:
        print(f"     {r}")

    if not rows:
        # لِمَ لم يُفهَم شيء؟ تُطبع الكتلُ التي تحمل «٪» بأصنافها.
        pct_blocks = [m.group(0) for m in
                      re.finditer(r"<(div|li|tr)\b[^>]*>(?:(?!<\1\b).)*?%.*?</\1>",
                                  DROP.sub(" ", html), re.S | re.I)][:6]
        print(f"   كتلٌ تحمل علامةَ النسبة: {len(pct_blocks)}")
        for b in pct_blocks:
            cls = re.search(r'class="([^"]{0,70})"', b)
            print(f"     class={cls.group(1) if cls else '—'} · {visible(b)[:110]}")
        if not pct_blocks:
            body = DROP.sub(" ", html)
            common = [(c, n) for c, n in
                      Counter(re.findall(r'class="([^"]{3,60})"', body)).most_common(12)
                      if n >= 4]
            print("   لا علامةَ نسبةٍ أصلاً. أكثرُ الأصناف:")
            for c, n in common:
                print(f"     {n:>4} × {c}")
            print("   النصُّ المرئيّ (آخرُ 400 حرفٍ من أوّل 4000):")
            print("     " + visible(body)[3600:4000])


async def own(sym: str) -> None:
    from app.services import ownership as ow
    from app.services.argaam_calendar import BASE, _company_id, _company_url

    cid = await _company_id(sym)
    print(f"معرِّفُ الشركة: {cid}")
    if not cid:
        return
    pages, _ = await grab([_company_url(cid)])
    home = next(iter(pages.values()), "")
    links = ow.tab_links(home, BASE, company_id=cid)
    print(f"\nالتُقط الآن: {sorted(links)}")
    for k, v in links.items():
        print(f"   {k}: {v[:120]}")
    if not links:
        return
    got, calls = await grab(list(links.values()))
    for k, u in links.items():
        describe(got.get(u, ""), k)
    if calls:
        print("\n   نداءاتُ الشبكة أثناء الرسم:")
        for st, u in list(dict.fromkeys(calls))[:12]:
            print(f"     {st} · {u[:130]}")


async def deals() -> None:
    from app.services.special_deals import ARGAAM_MARKET
    urls = [ARGAAM_MARKET,
            "https://www.argaam.com/ar/shareholder/major-shareholders/"
            "company-deals/marketid/3/companyid/47/بنك-الرياض"]
    got, calls = await grab(urls)
    for u in urls:
        describe(got.get(u, ""), u.split("/ar/")[-1][:60])
        html = got.get(u, "")
        # الصفقةُ رقمٌ لا نسبة: تُطبع كتلٌ تحمل أرقاماً كبيرةً بأصنافها.
        blocks = [m.group(0) for m in
                  re.finditer(r"<(div|li|tr)\b[^>]*>(?:(?!<\1\b).)*?"
                              r"\d{1,3}(?:,\d{3}){2,}.*?</\1>",
                              DROP.sub(" ", html), re.S | re.I)][:6]
        print(f"   كتلٌ تحمل أرقامَ كمّياتٍ كبيرة: {len(blocks)}")
        for b in blocks:
            cls = re.search(r'class="([^"]{0,70})"', b)
            print(f"     class={cls.group(1) if cls else '—'} · {visible(b)[:130]}")
    if calls:
        print("\n   نداءاتُ الشبكة:")
        for st, u in list(dict.fromkeys(calls))[:12]:
            print(f"     {st} · {u[:130]}")


a = sys.argv[1:] or ["own", "1010"]
asyncio.run(deals() if a[0] == "deals" else own(a[1] if len(a) > 1 else "1010"))
