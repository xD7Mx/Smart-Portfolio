#!/usr/bin/env python3
"""حارسُ D664 (المالك 2026-10-10): «أحببتُ ما صنعتَه في التوقعات، ولكن أريد جلبَ جميع التوقعات الممكنة من الجهات المعتبرة».

العطب: التبويبُ ستّون بنداً بسقفٍ لكلّ صنف (30 تقريرَ شركة · 10 قطاعات · …)، وآراءُ بيوت الخبرة — التوصيةُ والسعرُ المستهدف
لكلّ جهة — غائبة. وقِيس أنّ «أرقام» تنشرها عامّةً لكلّ جهة (18 جهةً بـ856 رأياً في سنة)، وأنّ تقاريرَ الجزيرة كابيتال
في سنةٍ أكثرُ من مئةٍ وخمسين.
الجذر: سقوفٌ وضعتُها لقائمةٍ بلا فرز، ومصدرُ الآراء لم يُبحث عنه.
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


try:
    import app.services.analyst_opinions as AO
except ModuleNotFoundError as e:
    check(False, "١ قارئُ آراء بيوت الخبرة موجود", str(e))
    print("\nالنتيجة: عطب ✖")
    sys.exit(1)
import app.services.research_reports as RR

page = '''<table id="tableForExcel"><tr><th>التاريخ</th><th>شركة الأبحاث</th><th>الشركة</th><th>قطاع أرقام</th><th>التوصية السابقة</th>
<th>التوصية</th><th>السعر وقت التوصية</th><th>السعر المستهدف</th><th>التغير</th><th>تحميل</th></tr>
<tr><td><nobr>2026/09/10</nobr></td><td><a href="https://www.argaam.com/ar/analystestimates/brokeropinions/3/2604">الراجحي المالية </a></td>
<td><a href="https://www.argaam.com/ar/analystestimates/analystrecomendationopinionbycompany/3/95">جرير</a></td><td>المكتبات</td>
<td>محايد</td><td>تخفيض مراكز</td><td> 16.45 </td><td> 15.00 </td><td>(8.81 %)</td><td><i class="ico pdf disabled"></i></td></tr>
<tr><td>2026/08/12</td><td><span>الرياض المالية</span></td><td><a href="/ar/analystestimates/analystrecomendationopinionbycompany/3/843">بدجت</a></td><td>النقل</td>
<td>شراء</td><td>شراء</td><td>28.70</td><td>42.00</td><td>46.34 %</td>
<td><a href="https://argaamplus.s3.amazonaws.com/6fd5fda3.pdf" target="_blank"><i class="ico pdf"></i></a></td></tr>
<tr><td>2026/08/01</td><td></td><td>بلا جهة</td><td></td><td></td><td>شراء</td><td>1</td><td>2</td><td></td><td></td></tr></table>'''
rs = AO.rows_of(page)
check(len(rs) == 2, "١ جدولُ الجهة: كلُّ صفٍّ بجهته وتاريخه وتوصيته — وما نقصه ذلك يُترك", str(len(rs)))
check(rs and rs[0]["rating"] == "تخفيض مراكز" and rs[0]["prev"] == "محايد" and rs[0]["target"] == 15.0 and rs[0]["price"] == 16.45,
      "٢ الأعمدةُ برؤوسها: «التوصية» غيرُ «التوصية السابقة»، والسعرُ المستهدف والسعرُ وقتها كما كُتبا", str(rs[:1]))
check([r["cid"] for r in rs] == ["95", "843"], "٣ والشركةُ من معرّفها في رابط الصفّ — لا من مطابقة اسمها")
check(rs[1]["pdf"] == "https://argaamplus.s3.amazonaws.com/6fd5fda3.pdf" and rs[0]["pdf"] is None,
      "٤ وملفُّ تقرير الجهة حين يُنشر، ولا يُختلق رابطٌ لما لم يُنشر")
for r in rs:
    r["page"] = "https://www.argaam.com/ar/analystestimates/brokeropinions/3/2604"
fc = AO.as_forecasts({"4190": rs[:1], "4260": rs[1:]})
check(fc[0]["source"] == "الراجحي المالية" and fc[0]["via"] == "أرقام" and fc[0]["kind"] == "توصية وسعرٌ مستهدف"
      and "(كانت محايد)" in fc[0]["title"] and fc[0]["url"].endswith("/2604"),
      "٥ البندُ باسم الجهة و«أرقام» ناقلٌ يُذكر، وتغيُّرُ التوصية يُقال", str(fc[0]))
check(len({x["id"] for x in fc}) == 2, "٦ ولكلّ رأيٍ هويّتُه — لا يُسقط رأيٌ لأنّ رابطَه صفحةُ الجهة نفسُها")

items = [{"id": f"o{i}", "kind": "توصية وسعرٌ مستهدف", "date": f"2026-0{1 + i % 9}-15", "source": "س"} for i in range(80)]
items += [{"url": f"d{i}", "kind": "تقرير يوميّ", "date": f"2026-10-0{1 + i}", "source": "الجزيرة كابيتال"} for i in range(8)]
items += [{"url": "old", "kind": "تقرير شركة", "date": "2024-01-01", "source": "س"}]
sel = RR.select(items, today="2026-10-10")
check(sum(1 for x in sel if x["kind"] == "توصية وسعرٌ مستهدف") == 80, "٧ لا سقفَ لكلّ صنف: كلُّ ما في السنة يُعرض")
check(sum(1 for x in sel if x["kind"] == "تقرير يوميّ") == RR.DAILY_KEEP and not any(x.get("url") == "old" for x in sel),
      "٨ واليوميُّ آخرُ خمسةٍ لكلّ جهة، وما جاوز السنةَ يُترك")

fcs = (ROOT / "backend/app/services/forecasts.py").read_text(encoding="utf-8")
check("from app.services.analyst_opinions import as_forecasts" in fcs and "reports + opinions + news" in fcs,
      "٩ التبويبُ يجمع تقاريرَ الجهات وآراءَ بيوت الخبرة وأخبارَ «أرقام»")
sc = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
check("async def job_analyst_opinions" in sc and 'id="analyst_opinions_night"' in sc and 'id="analyst_opinions_boot"' in sc,
      "١٠ ويُجمع ليلاً، وبعد الإقلاع إن لم يُجمع بعد — لا في طلب مستخدم")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check("from app.services.analyst_opinions import for_symbol as _ops" in mk, "١١ وتبويبُ «توصيات المحللين» في صفحة الشركة من الجدول نفسِه")
ui = (ROOT / "frontend/src/components/market/EventsList.tsx").read_text(encoding="utf-8")
check("FC_GROUPS" in ui and "كل الجهات" in ui and "عرض المزيد" in ui and "السعر المستهدف" in ui,
      "١٢ والواجهةُ تفرز بالنوع والجهة وتعرض أربعين فأربعين — مئاتُ البنود لا تُمرَّر بلا نهاية")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
