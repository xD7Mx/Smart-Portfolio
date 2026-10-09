#!/usr/bin/env python3
"""فحصُ التسليم على الإنتاج (سؤالُ المالك 2026-10-09: «هل حذفتَ الأحداث؟ وتعديلاتي لم أجدها») — قارئٌ فقط.

١ نقطةُ الأحداث الجوهرية كما تناديها الصفحة لشركاتٍ لها أحداث: كم حدثاً يصل، وهل جُمع المكرَّر.
٢ الواجهةُ التي يقدّمها الخادم فعلاً (‏sp_frontend): هل في ملفّاتها تعديلاتُ اليوم بنصوصها."""
import asyncio, json, re, sys, urllib.request
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None

SYMS = ["2080", "2222", "1120", "2010", "7010", "4013"]


async def events():
    from app.api.v1.endpoints.market import get_material_events
    for s in SYMS:
        try:
            r = await get_material_events(s)
            body = getattr(r, "body", None)
            d = ((json.loads(body) if body else r).get("data")) or {}
            ev = d.get("events") or []
            print(f"  {s}: {len(ev)} حدثاً — " + " · ".join(f"{e.get('date')} {e.get('kind_ar')} ×{e.get('filings', 1)}" for e in ev[:6]))
        except Exception as e:                                     # noqa: BLE001
            print(f"  {s}: ✘ {type(e).__name__}: {str(e)[:120]}")


def frontend():
    base = None
    for u in ("http://sp_frontend:3000/", "http://frontend:3000/", "http://sp_nginx/"):
        try:
            html = urllib.request.urlopen(u, timeout=8).read().decode("utf-8", "replace")
            base = u
            break
        except Exception:                                          # noqa: BLE001
            continue
    if not base:
        print("  ✘ تعذّر الوصول إلى الواجهة من داخل الخادم")
        return
    seen, todo, text = set(), re.findall(r'/assets/[^"\']+\.js', html), ""
    while todo and len(seen) < 80:
        a = todo.pop()
        if a in seen:
            continue
        seen.add(a)
        try:
            js = urllib.request.urlopen(base.rstrip("/") + a, timeout=10).read().decode("utf-8", "replace")
        except Exception:                                          # noqa: BLE001
            continue
        text += js
        todo += [("/assets/" + x) for x in re.findall(r'assets/([\w\-.]+\.js)', js)] + re.findall(r'"\./([\w\-.]+\.js)"', js) and \
            [("/assets/" + x) for x in re.findall(r'"\./([\w\-.]+\.js)"', js)] or []
    print(f"  الواجهةُ من {base} · ملفّاتٌ قُرئت {len(seen)}")
    for label, needle in (("إطارُ «4 ساعات» في الرسم", "4 ساعات"), ("حفظُ الإطار المختار", "sp_chart_tf"),
                          ("«أُعلن أوّلاً» في الأحداث", "أُعلن أوّلاً"), ("«السعر العادل اليوم» في تقرير الشركة", "السعر العادل اليوم"),
                          ("«ثقة التقدير» في تقرير الشركة", "ثقة التقدير"), ("اسمُ التبويب القديم «D7M أسبوعي»", "D7M أسبوعي")):
        print(f"    {'✔' if needle in text else '✘'} {label}" if "القديم" not in label
              else f"    {'✘ ما زال' if needle in text else '✔ زال'} {label}")


print("١ الأحداثُ الجوهرية من نقطة الصفحة:")
asyncio.run(events())
print("٢ الواجهةُ المنشورة:")
frontend()
