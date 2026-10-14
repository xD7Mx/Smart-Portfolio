#!/usr/bin/env python3
"""فحصُ التسليم على الإنتاج (بلاغُ المالك 2026-10-14: «لم أجد التحديثات على التطبيق») — قارئٌ فقط.

يقرأ الواجهةَ التي يقدّمها الخادم فعلاً (‏sp_frontend · sp_nginx) — ملفّاتِ ‎JS‎ و‎CSS‎ كلَّها من الصفحة الأولى — ويبحث فيها عن
تعديلات اليوم بعلاماتها التي تبقى بعد التصغير، وعن غياب ما حُذف."""
import os, re, urllib.request

MARKS = (("الدرجُ يتبع الإصبع (D712)", "drawer-drag"), ("لا شبحَ للدرج حين يُغلق بالسحب (D712)", "data-noghost"),
         ("أسعارُ المحور بنمطٍ إطاريّ (D713)", "axis-tag"), ("شموعُ «تاسي» في تقرير المحفظة (D711)", "report-candles-tasi"),
         ("الصورةُ الشخصية دائرة (D710)", ".sheet).rounded-full"),
         ("تنبيهُ تعديل المركز بواقعةٍ واحدة (D709)", "تصحيحٌ للمركز وحده"), ("تحميلُ المستشار «يقرأ المحفظة…» (D709)", "يقرأ المحفظة"))
GONE = (("صندوقُ تبرير بطاقة المعاملة (D709)", "يُخصم الإجمالي من السيولة"), ("«فلا يتناقض معها» (D709)", "فلا يتناقض معها"),
        ("حاشيةُ الحاسبات (D709)", "لتقريب الصورة لا للضمان"), ("تلميحُ نبذة الشركة (D709)", "نصّك يتقدّم على المصدر"))


def get(u, t=10):
    return urllib.request.urlopen(u, timeout=t).read().decode("utf-8", "replace")


base = html = None
for u in (*filter(None, [os.environ.get("SP_FRONT_URL")]), "http://sp_frontend:3000/", "http://frontend:3000/", "http://sp_nginx/"):
    try:
        html, base = get(u, 8), u.rstrip("/")
        break
    except Exception:                                              # noqa: BLE001
        continue
if not base:
    print("✘ تعذّر الوصول إلى الواجهة من داخل الخادم")
    raise SystemExit(1)
todo = re.findall(r'/assets/[\w\-.]+\.(?:js|css)', html)
print("الصفحةُ الأولى تُحمّل:", " · ".join(todo[:6]))
seen, text = set(), ""
while todo and len(seen) < 160:
    a = todo.pop()
    if a in seen:
        continue
    seen.add(a)
    try:
        body = get(base + a)
    except Exception:                                              # noqa: BLE001
        continue
    text += body
    todo += ["/assets/" + x for x in re.findall(r'["\'/(]([\w\-.]+\.(?:js|css))["\')]', body) if not x.startswith("http")]
print(f"الواجهةُ من {base} · ملفّاتٌ قُرئت {len(seen)} · {len(text)//1024} ك.ب")
bad = 0
for label, needle in MARKS:
    ok = needle in text
    bad += not ok
    print(f"  {'✔' if ok else '✘ غائب'} {label}")
for label, needle in GONE:
    ok = needle not in text
    bad += not ok
    print(f"  {'✔ زال' if ok else '✘ ما زال'} {label}")
print("\nالنتيجة:", "الواجهةُ المنشورة تحمل تعديلاتِ اليوم ✔" if not bad else f"✖ {bad} علامةً لم تُطابق")
raise SystemExit(1 if bad else 0)
