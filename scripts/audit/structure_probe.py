#!/usr/bin/env python3
"""مسبارُ بنية: يطبع **شكلَ** الصفحة لا تفسيري لها (D273 · D270).

    docker exec sp_backend python /app/scripts/audit/structure_probe.py deals
    docker exec sp_backend python /app/scripts/audit/structure_probe.py own 1010

القياسُ السابقُ ردّ افتراضين معاً: صفحةُ الصفقات الخاصة لا تحمل نداءَ
بوّابةٍ أصلاً (‏556 ألفَ حرفٍ وصفرُ نداءات) — فالأرجحُ أنّ الجدولَ مرسومٌ
في الصفحة نفسِها؛ وتبويباتُ «أرقام» تُفتح بالمتصفّح وتعطي صفرَ صفوفٍ —
فالأرجحُ أنّ صفوفَها ليست `<table>`. وكلاهما **ترجيح**، والترجيحُ لا
يُبنى عليه. فهذا المسبارُ يطبع ما في الصفحة: كم جدولاً، وكم صفّاً، وما
عناوينُه، وأيُّ حاوياتٍ تحمل الصفوفَ إن لم تكن جداول.
"""
from __future__ import annotations

import asyncio
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

TAG = re.compile(r"<[^>]+>")


def text(s: str) -> str:
    return re.sub(r"\s+", " ", TAG.sub(" ", s or "")).strip()


def describe(html: str, label: str) -> None:
    print(f"\n── {label}: {len(html)} حرفاً")
    tabs = re.findall(r"<table[^>]*>(.*?)</table>", html, re.S | re.I)
    print(f"   جداول: {len(tabs)}")
    for i, tb in enumerate(tabs[:6]):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S | re.I)
        head = text(rows[0])[:110] if rows else "—"
        print(f"     [{i}] صفوف={len(rows)} · أوّلُ صفّ: {head}")
        if len(rows) > 1:
            print(f"          صفٌّ تالٍ: {text(rows[1])[:110]}")
    if not tabs:
        # لا جداول: تُطبع الحاوياتُ المتكرّرةُ بصنفها — لعلّ الصفوفَ divات.
        classes = re.findall(r'class="([^"]{3,60})"', html)
        from collections import Counter
        common = [(c, n) for c, n in Counter(classes).most_common(14) if n >= 3]
        print("   لا جدول. أكثرُ الأصناف تكراراً:")
        for c, n in common:
            print(f"     {n:>4} × {c}")
    # كلماتٌ دالّة: وجودُها يقول إنّ المحتوى وصل ولو بشكلٍ آخر
    for kw in ("الصفقات الخاصة", "كبار المساهمين", "الملكية الأجنبية",
               "تقديرات المحللين", "نسبة التملك", "الكمية", "القيمة"):
        if kw in html:
            i = html.index(kw)
            print(f"   «{kw}» موجودةٌ — سياقُها: {text(html[i:i+220])[:150]}")


async def deals() -> None:
    from app.services.special_deals import PAGE
    from app.services.tadawul_http import fetch
    status, body = await fetch(PAGE)
    print(f"HTTP {status}")
    if status != 200 or not body:
        return
    describe(body, "صفحةُ الصفقات الخاصة")
    # أيُّ نداءاتٍ فيها أصلاً؟ (‏NJ لم يوجد — فتُطبع أنماطٌ أخرى)
    for pat, name in ((r'(?:href|src|action)="([^"]*/wps/[^"]{10,120})"', "روابطُ البوّابة"),
                      (r'url\s*:\s*[\x27"]([^\x27"]{10,140})', "نداءاتُ جافاسكربت"),
                      (r'data-url="([^"]{10,140})"', "data-url")):
        hits = sorted(set(re.findall(pat, body)))[:10]
        if hits:
            print(f"\n   {name}:")
            for h in hits:
                print("     " + h[:130])


async def own(sym: str) -> None:
    from app.services import ownership as ow
    from app.services.argaam_calendar import BASE, _company_id, _company_url
    from app.services.browser_fetch import render
    cid = await _company_id(sym)
    print(f"معرِّفُ الشركة: {cid}")
    if not cid:
        return
    home = next(iter((await render([_company_url(cid)])).values()), "")
    links = ow.tab_links(home, BASE)
    print("الروابطُ المكتشَفة:")
    for k, v in links.items():
        print(f"   {k}: {v}")
    if not links:
        describe(home, "صفحةُ الشركة")
        return
    pages = await render(list(links.values()), settle_ms=6000)
    for k, u in links.items():
        describe(pages.get(u, ""), k)


a = sys.argv[1:] or ["deals"]
asyncio.run(deals() if a[0] == "deals" else own(a[1] if len(a) > 1 else "1010"))
