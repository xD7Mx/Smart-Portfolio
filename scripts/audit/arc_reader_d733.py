#!/usr/bin/env python3
"""حارسُ D733 (المالك 2026-11-14): «أصلح قارئَ الراجحي — التقاريرُ موجودةٌ في موقعهم بشكلٍ سليم، ولكنك وضعتَ رابطاً عند
الضغط عليه تخرج صورةُ أيقونة المشاركة».

قِيس على الخادم (arc_site_door · arc_graph_door): الموقعُ صار Next.js على Sitecore JSS؛ لا ‏data-parentId ولا ‏ListingAPI،
فالقارئُ القديمُ لا يبلغ القائمة أصلاً. والقائمةُ نداءُ GraphQL ‏«SearchAndReports» (‏1,296 بنداً)، ولكلّ بندٍ حقلان بروابط وسائط:
‏«DownloadLink» ملفُّ التقرير، و«icon» صورةُ ‎arb-subscribe-report-download.png‎. وكان القارئُ يأخذ أوّلَ رابطٍ ‎/-/media/‎ في
شجرة البند — فالتقط الأيقونة. وآراءُ الراجحي في «أرقام» بلا ملفّ (عمودُ التحميل معطَّلٌ لها) فلا رابطَ لها هناك أصلاً.

    python3 scripts/audit/arc_reader_d733.py
"""
import json, os, pathlib, sys, tempfile
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


import app.services.research_reports as R                       # noqa: E402
if not hasattr(R, "arc_graph_items"):
    check(False, "١ قارئُ موقع الراجحي الجديد موجود", "لا arc_graph_items")
    print("\nالنتيجة: عطب ✖"); sys.exit(1)

# بندٌ كما ردّه الموقعُ فعلاً (arc_graph_door 2026-11-14) — والأيقونةُ قبل الملفّ في شجرته
ICON = "https://alrajhi-capital.sa:9443/-/media/Feature/AlRajhiCapital/Reports/arb-subscribe-report-download.png"
daily = {"id": "C5AE", "name": "DMZ 12 November 2026", "title": {"value": "التقرير اليومي لسوق الأسهم"},
         "image": {"src": "https://alrajhi-capital.sa:9443/-/media/Feature/AlRajhiCapital/ResearchListing/Daily-Reports/Daily-Report.png"},
         "icon": {"src": ICON},
         "Categories": {"targetItems": [{"id": "9554", "fields": [{"name": "Category", "value": "Daily Reports"}]}]},
         "Companies": {"targetItems": []}, "Sectors": {"targetItems": []}, "Date": {"value": "11/12/2026 00:00"},
         "DownloadPDFLink": {"jsonValue": {"value": {"href": "-/media/Feature/AlRajhiCapital/ResearchListing/Daily-Reports/2026/nov/DMR-Arabic---12-Nov-2026.pdf",
                                                     "linktype": "media"}}}}
noicon_only = {**daily, "DownloadPDFLink": {"jsonValue": {"value": {"href": ""}}}, "title": {"value": "بلا ملفّ"}}
comp = {**daily, "title": {"value": "نتائج الربع الثالث 2026"}, "Date": {"value": "11/3/2026 00:00"},
        "Categories": {"targetItems": [{"fields": [{"name": "Category", "value": "Company Reports"}]}]},
        "Companies": {"targetItems": [{"fields": [{"name": "Name", "value": "شركة المراعي"}]}]},
        "DownloadPDFLink": {"jsonValue": {"value": {"href": "/-/media/Feature/AlRajhiCapital/ResearchListing/Companies/Almarai-3Q26.pdf"}}}}
raw = json.dumps({"data": {"search": {"total": 1296, "pageInfo": {"endCursor": "MTY=", "hasNext": True}, "results": [daily, noicon_only, comp]}}})
items, info = R.arc_graph_items(raw)
check(len(items) == 2 and items[0]["url"] == "https://www.alrajhi-capital.sa/-/media/Feature/AlRajhiCapital/ResearchListing/Daily-Reports/2026/nov/DMR-Arabic---12-Nov-2026.pdf"
      and not any("arb-subscribe" in x["url"] or x["url"].lower().endswith((".png", ".jpg", ".svg")) for x in items),
      "١ الرابطُ حقلُ التحميل ملفَّ PDF — لا أيقونةُ «اشترك/حمّل» التي تسبقه في البند (عطبُ الملاحظة بعينه)", items[0]["url"][-60:] if items else "—")
check(all(x["title"] != "بلا ملفّ" for x in items), "٢ وبندٌ بلا ملفٍّ يُترك — لا يُستعاض عنه بصورة")
check(items and items[0]["date"] == "2026-11-12" and items[0]["kind"] == "تقرير يوميّ" and info.get("hasNext") and info.get("endCursor") == "MTY=",
      "٣ التاريخُ «11/12/2026» شهرٌ/يوم ⇒ 12 نوفمبر، و«Daily Reports» يوميّ، والصفحةُ التالية من مؤشّرها")
check(len(items) > 1 and items[1]["kind"] == "تقرير شركة" and "المراعي" in items[1]["title"] and items[1]["url"].endswith("Almarai-3Q26.pdf"),
      "٤ وتقريرُ الشركة باسمها من حقل «الشركات»", str(items[1:] and items[1]["title"]))
js = ('fetch("/sitecore/api/graph/edge?sc_apikey=00000000-1111-2222-3333-444444444444",{method:"POST",body:JSON.stringify({query:`query SearchAndReports '
      '{ search( where: { AND: [ { name: "_language", value:"ar" } { name: "_path", value: "{E771FC1D-B3C8-4BCD-B6E8-E57A753FC6B9}", operator: CONTAINS }, '
      '{name: "_templates", value: "{8B6A8870-0EA1-4C6E-9174-94A1FC91D1B0}",operator: EQ} ] }`})})')
d = R.arc_discover(["<html>لا شيء</html>", js])
check(d == {"key": "00000000-1111-2222-3333-444444444444", "root": "{E771FC1D-B3C8-4BCD-B6E8-E57A753FC6B9}",
            "template": "{8B6A8870-0EA1-4C6E-9174-94A1FC91D1B0}"} and R.arc_discover(["<p/>"]) == {},
      "٥ المفتاحُ العامّ والجذرُ والقالبُ يُقرأون من سكربت الصفحة — وبلا ذلك لا شيءَ مخمَّن", str(d))
# ٥ب الصيغتان كما قِيستا في الموقع فعلاً (arc_key_door): المفتاحُ في سكربت التطبيق احتياطاً لمتغيّر البيئة، والجذرُ مصدرُ المكوّن
d2 = R.arc_discover(['{"uid":"fe39","componentName":"ResearchAndReports","dataSource":"{E771FC1D-B3C8-4BCD-B6E8-E57A753FC6B9}","params":{}',
                     'let o={};o.sitecoreApiKey=n.env.SITECORE_API_KEY||"00000000-1111-2222-3333-444444444444",o.sitecoreApiHost=n.env.X'])
check(d2.get("key") == "00000000-1111-2222-3333-444444444444" and d2.get("root") == "{E771FC1D-B3C8-4BCD-B6E8-E57A753FC6B9}",
      "٥ب وبصيغتي الموقع المقيستين: ‏sitecoreApiKey=…SITECORE_API_KEY||\"…\"، و‏dataSource مكوّن «ResearchAndReports»", str(d2))
q = R.arc_query(d["root"], d["template"], 50, "MTY=")
check('after:"MTY="' in q and "DownloadLink" in q and "orderBy: { name: \"Date\", direction: DESC }" in q and "icon" not in q,
      "٦ والاستعلامُ استعلامُ الصفحة نفسُه بحقل التحميل — ولا يطلب الأيقونةَ أصلاً")
src = (ROOT / "backend/app/services/research_reports.py").read_text(encoding="utf-8")
check("B4E643CA" not in src and "sc_apikey" in src and "arc_items" not in src and "/-/media/|" not in src,
      "٧ ولا مفتاحَ محفوظاً في الشيفرة، والقارئُ القديمُ (أوّلُ رابطِ وسائط) محذوف")
# ٨ رأيُ الجهة بلا ملفٍّ يُربط بتقريرها عن الشركة نفسِها خلال أسبوع — الأقربُ تاريخاً
reps = [{"kind": "تقرير شركة", "company": "2280", "source": "الراجحي المالية", "date": "2026-11-03", "url": "https://x/a.pdf", "title": "أ"},
        {"kind": "تقرير شركة", "company": "2280", "source": "الراجحي المالية", "date": "2026-10-01", "url": "https://x/old.pdf", "title": "قديم"},
        {"kind": "تقرير شركة", "company": "2280", "source": "الجزيرة كابيتال", "date": "2026-11-04", "url": "https://x/ajc.pdf", "title": "ج"}]
ops = [{"source": "الراجحي المالية ", "company": "2280", "date": "2026-11-05", "url": None},
       {"source": "الراجحي المالية", "company": "2280", "date": "2026-10-20", "url": None},
       {"source": "الرياض المالية", "company": "2280", "date": "2026-11-04", "url": None}]
R.link_opinions(ops, reps)
check(ops[0]["url"] == "https://x/a.pdf" and ops[1]["url"] is None and ops[2]["url"] is None,
      "٨ رأيُ الراجحي (‏«أرقام» بلا ملفّ) يُربط بتقريرها عن الشركة نفسِها خلال أسبوع؛ وما أبعد، أو لجهةٍ أخرى، يبقى بلا رابط",
      str([o["url"] for o in ops]))
fc = (ROOT / "backend/app/services/forecasts.py").read_text(encoding="utf-8")
check("link_opinions(opinions, reports)" in fc, "٩ و«التوقعات» تربط الآراءَ بتقاريرها قبل العرض")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
