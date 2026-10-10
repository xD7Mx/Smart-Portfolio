#!/usr/bin/env python3
"""حارسُ D662 (المالك 2026-10-10): «التوقعات في السوق — أريد تقاريرَ للجهات المعتمدة من بنوكٍ وغيرها لسوق تاسي،
لأنها حالياً خالية، ولا أريد شيئاً خالياً».

العطب: التبويبُ يُبنى من مصدرَين عامَّين في «أرقام» (عناوينُ الأخبار والتقاريرُ القطاعية) فعاد صفراً.
الجذر: لم تُقرأ الجهاتُ المرخّصةُ نفسُها، وكانت تنشر تقاريرها عامّةً — قِيس (research_sources_door · research_shape_door):
الجزيرة كابيتال جداولُ في HTML (‏1072 ملفّاً)، وجدوى بطاقاتٌ مؤرَّخة، والراجحي المالية نداءُ قائمةٍ في صفحتها.
"""
import os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


fc = (ROOT / "backend/app/services/forecasts.py").read_text(encoding="utf-8")
check("from app.services.research_reports import collect" in fc and "reports + news" in fc,
      "١ التبويبُ يُبنى من تقارير الجهات المرخّصة أوّلاً ثمّ أخبار «أرقام»")
check('lastgood.save(LAST_KEY' in fc and 'lastgood.load(LAST_KEY)' in fc,
      "٢ وتعذُّرٌ لحظيٌّ لا يُخليه: آخرُ ما وصل يُعرض بتاريخه")
try:
    import app.services.research_reports as R
except ModuleNotFoundError as e:
    check(False, "٣ قارئُ الجهات موجود", str(e))
    print("\nالنتيجة: عطب ✖")
    sys.exit(1)

ajc = '''<table><thead><tr> <th>سوق</th> <th>اسم البحث</th> <th>تاريخ التقرير </th> <th>ملف التقرير</th> </tr></thead>
<tr><td>السعودية</td><td>التقرير اليومي والنظرة الفنية</td><td>03-07-2024</td><td><a href="/media/a1/daily-07-03-2024-ar.pdf">تنزيل</a></td></tr>
<tr><td>السعودية</td><td>نتائج الربع الثاني - مذكرة سريعة</td><td>08-05-2026</td><td><a href="/media/a2/mobily-flash-note-q2-2026-ar.pdf">تنزيل</a></td></tr>
<tr><td>السعودية</td><td>بلا ملفّ</td><td>08-06-2026</td><td>—</td></tr>
<tr><td>السعودية</td><td></td><td>08-07-2026</td><td><a href="/media/a3/x.pdf">تنزيل</a></td></tr></table>'''
a = R.ajc_items(ajc)
check(len(a) == 2, "٣ الجزيرة كابيتال: كلُّ صفٍّ بعنوانه وتاريخه وملفّه — وما نقصه شيءٌ يُترك لا يُكمَّل", str(len(a)))
check(a and a[0]["date"] == "2024-03-07" and a[1]["date"] == "2026-08-05",
      "٤ والتاريخُ شهرٌ-يومٌ-سنة كما ينشره الجدول (03-07-2024 لملفّ daily-07-03-2024 = ‏7 مارس)", str([x["date"] for x in a]))
check(a and a[0]["kind"] == "تقرير يوميّ" and a[1]["kind"] == "تقرير شركة",
      "٥ والصنفُ من اسم الملفّ قبل العنوان: «اليوميّ والنظرةُ الفنية» يوميّ، ومذكّرةُ النتائج تقريرُ شركة", str([x["kind"] for x in a]))
check(all(x["url"].startswith("https://www.aljaziracapital.com.sa/media/") and x["source"] == "الجزيرة كابيتال" for x in a),
      "٦ ولكلّ بندٍ رابطُ ملفّه الأصليّ واسمُ جهته")

cov = '''<table><tr><th>رمز الشركة</th><th>اسم البحث</th><th>السعر العادل</th><th>تاريخ التقرير</th><th>ملف التقرير</th></tr>
<tr><td>4002</td><td>المواساة - نظرة على نتائج الربع الثاني 2026</td><td>92.50</td><td>08-04-2026</td><td><a href="/media/b1/mouwasat-flash-note-q2-2026-ar.pdf">تنزيل</a></td></tr>
<tr><td>4161</td><td>بن داود - تحديث</td><td>—</td><td>08-01-2026</td><td><a href="/media/b2/bindawood-update-ar.pdf">تنزيل</a></td></tr></table>
<table><tr><th>قطاع</th><th>اسم البحث</th><th>تاريخ التقرير</th><th>ملف التقرير</th></tr>
<tr><td>المصارف</td><td>تقرير المصارف الربعي</td><td>08-20-2026</td><td><a href="/media/b3/x.pdf">تنزيل</a></td></tr></table>'''
c = R.ajc_items(cov)
check([x["company"] for x in c[:2]] == ["4002", "4161"] and all(x["kind"] == "تقرير شركة" for x in c[:2]),
      "٦ب وجدولُ التغطية: الرمزُ من عمود «رمز الشركة» نفسِه لا من مطابقة الاسم", str([(x["company"], x["kind"]) for x in c]))
check(c and c[0].get("fair_value") == 92.5 and "fair_value" not in c[1],
      "٦ج والسعرُ العادلُ ما كتبته الجهةُ في صفّها — وما لم تكتبه لا يُملأ", str([x.get("fair_value") for x in c]))
check(len(c) == 3 and c[2]["kind"] == "تقرير قطاعيّ", "٦د وصنفُ الجدول من رأسه: «قطاع» قطاعيّ")

jd = '''<div class="report-item"><h2 class="title"><a href="/ar/node/1">الموجز البياني للاقتصاد السعودي - أكتوبر 2026</a></h2>
<span class="date"><time datetime="2026-10-06T12:00:00Z">2026-10-06</time></span><span class="date">كتيبات الرسوم البيانية الشهرية</span>
<div class="actions"><a href="/sites/default/files/2026-10/Chartbook.pdf">عرض</a></div></div>
<div class="report-item"><h2 class="title"><a>بلا تاريخ</a></h2><a href="/f/x.pdf">عرض</a></div>'''
j = R.jadwa_items(jd)
check(len(j) == 1 and j[0]["date"] == "2026-10-06" and j[0]["url"] == "https://www.jadwa.com/sites/default/files/2026-10/Chartbook.pdf"
      and j[0]["source"] == "جدوى للاستثمار", "٧ جدوى: بطاقةٌ بعنوانها وتاريخها وملفّها، وما بلا تاريخٍ يُترك", str(j))

check(R.arc_params("<p>لا معاملات</p>") == [], "٨ الراجحي المالية: لا نداءَ بمعاملاتٍ مخمَّنة — تُقرأ من الصفحة أو لا شيء")
arc = R.arc_items('{"Items":[{"Title":"تقرير السوق اليومي","Date":"2026-10-08T00:00:00",'
                  '"Url":"/-/media/Feature/AlRajhiCapital/ResearchListing/Daily-Reports/2026/OCT/DMR.pdf"},{"Title":"بلا رابط","Date":"2026-10-08"}]}')
check(len(arc) == 1 and arc[0]["url"].startswith("https://www.alrajhi-capital.sa/-/media/"), "٩ وردُّ القائمة: ما بلا رابطٍ يُترك", str(arc))

items = [{"kind": "تقرير يوميّ", "date": f"2026-10-0{i}", "url": f"u{i}", "title": "t"} for i in range(1, 8)]
items += [{"kind": "تقرير شركة", "date": "2026-10-05", "url": "c1", "title": "t"}, {"kind": "تقرير شركة", "date": "2026-10-05", "url": "c1", "title": "t"}]
sel = R.select(items)
check(sum(1 for x in sel if x["kind"] == "تقرير يوميّ") == 2 and [x["date"] for x in sel][:1] == ["2026-10-07"]
      and sum(1 for x in sel if x["url"] == "c1") == 1, "١٠ الأحدثُ أوّلاً، واليوميُّ لا يُغرق التبويب، والملفُّ لا يتكرّر")
check(R._company("التقرير الاستراتيجي للسوق") is None, "١١ والشركةُ لا تُنسب إلا بمطابقةٍ واحدة — العنوانُ العامُّ بلا رمز")

sc = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
check("async def job_forecasts" in sc and 'id="forecasts_hourly"' in sc, "١٢ ويُجمع مسبقاً كلَّ ساعة — لا ينتظر من يفتح التبويب")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
