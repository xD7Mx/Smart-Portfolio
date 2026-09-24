#!/usr/bin/env python3
"""نصُّ الإفصاح: «تداول» أوّلاً و«أرقام» مكمِّلاً (D467).

    python3 scripts/audit/tadawul_first_disclosure.py

بأمر المالك. والفحصُ سلوكيّ على شكل الصفحة المقيس: قائمةُ إفصاحات الشركة
(`getAnnouncementListData`) وصفحةُ التفاصيل (`announcementBox`: ‏h3 ثمّ جداول
«بند | توضيح»)، ثمّ يُنادى البابُ الواحد `/market/announcement-text`.
"""
from __future__ import annotations
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
import asyncio, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services import tadawul_http as T, cache
    from app.api.v1.endpoints import market as MK
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)
try:
    from app.services import tadawul_disclosure as D
except ImportError:
    print("FAIL D467 — لا قارئَ لإفصاحات «تداول»"); sys.exit(1)
if not hasattr(MK, "get_announcement_text"):
    print("FAIL D467 — لا بابَ لنصّ الإعلان «تداول» أوّلاً"); sys.exit(1)

store = {}
cache.get = lambda k: store.get(k)
cache.set = lambda k, v, ttl=0: store.__setitem__(k, v)
LISTPAGE = '<base href="https://www.saudiexchange.sa/wps/portal/x/" /><script>url: \'p0/IZ7_A=CZ6_B=NJgetAnnouncementListData=/\'</script>'
ROWS = {"announcementList": [
    {"SYMBOL": "4001", "PR_DATE": "Aug 19, 2026", "announcementNumber": "97698",
     "announcementUrl": "/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements/issuer-announcements-details/?anId=97698&anCat=1&cs=4001&locale=en"},
    {"SYMBOL": "4001", "PR_DATE": "Sep 14, 2026", "announcementNumber": "98001",
     "announcementUrl": "/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements/issuer-announcements-details/?anId=98001&anCat=1&cs=4001&locale=en"}]}
DETAIL = {
    "97698": ('<div class="announcementBox width80"><div class="announcementBoxLft"><h3>تعلن شركة أسواق عبد الله العثيم عن استقالة الرئيس التنفيذي وتكليف العضو المنتدب بمهام الرئيس التنفيذي.</h3>'
              '<a id="companyProfLink" href="/x"><div>أسواق ع العثيم</div></a>'
              "<table class='stacktable'><thead><tr><th>بند</th><th>توضيح</th></tr></thead><tbody><tr><td>مقدمة</td><td>تعلن شركة أسواق عبد الله العثيم عن موافقة مجلس إدارتها على استقالة المكرم/ موفق عبد الله مباره.</p><p>ويتقدم مجلس الإدارة بالشكر.</td></tr>"
              "<table class='stacktable'><thead><tr><th>بند</th><th>توضيح</th></tr></thead><tbody><tr><td>اسباب الاستقالة</td><td>ظروف خاصة</td></tr></div><script>x</script>"),
    "98001": ('<div class="announcementBox"><h3>تعلن شركة أسواق عبد الله العثيم عن دعوة مساهميها لحضور اجتماع الجمعية العامة العادية</h3>'
              "<table class='stacktable'><tbody><tr><td>مقدمة</td><td>يسر مجلس الإدارة دعوة المساهمين لحضور الجمعية.</td></tr></div><script>"),
}
ARG = "https://www.argaam.com/ar/article/articledetail/id/1936139"
ARGPAGE = '<meta property="og:description" content="سجلت شركة العثيم أول خسائر فصلية" /><div>للإستمرار في قراءة التقرير</div>'
calls = []
async def fetch(url, **k):
    calls.append(url)
    if "issuer-announcements?" in url: return 200, LISTPAGE
    for i, h in DETAIL.items():
        if f"anId={i}" in url: return 200, h
    return 404, ""
async def smart_fetch(url, **k):
    calls.append(url)
    if "getAnnouncementListData" in url and (k.get("data") or {}).get("symbol") == "4001": return 200, json.dumps(ROWS)
    if url == ARG: return 200, ARGPAGE
    return 200, json.dumps({"announcementList": []})
T.fetch, T.smart_fetch = fetch, smart_fetch

def call(**p):
    r = asyncio.run(MK.get_announcement_text(**p))
    return (r if isinstance(r, dict) else json.loads(r.body)).get("data")

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

r = call(symbol="4001", title="استقالة الرئيس التنفيذي لـ أسواق العثيم.. وتكليف العضو المنتدب بمهامه", date="2026-08-19",
         u="https://www.argaam.com/ar/article/articledetail/id/1930467", name="أسواق ع العثيم") or {}
t = r.get("text", "")
check(r.get("source") == "تداول" and "موفق عبد الله مباره" in t and "ظروف خاصة" in t, "١ الإفصاحُ يُعرض بنصّ «تداول» الرسميّ أوّلاً", t[:70])
check("بند" not in t.split("\n")[0] and "أسواق ع العثيم" not in t and "<" not in t and "مقدمة | " in t,
      "٢ متنُ `announcementBox` وحده: بلا ترويسة الجدول ولا رابط الشركة ولا وسوم")
check(not any("argaam" in c for c in calls), "٣ ولا تُطلب «أرقام» حين يكفي «تداول»")
r2 = call(symbol="4001", title="أسواق العثيم: كيف سجلت الشركة أول خسائر فصلية لها في الربع الثاني 2026؟", date="2026-09-14",
          u=ARG, name="أسواق ع العثيم") or {}
check(r2.get("source") == "أرقام" and "الجمعية" not in r2.get("text", "") and r2.get("text") == "سجلت شركة العثيم أول خسائر فصلية",
      "٤ وتقريرُ «أرقام» في يوم إفصاحٍ آخر لا يُلبَس نصَّه — يُكمَّل من «أرقام»", r2.get("text", "")[:50])
check(D.similar("أسواق العثيم: كيف سجلت الشركة أول خسائر فصلية", "تعلن شركة أسواق عبد الله العثيم عن دعوة مساهميها لحضور اجتماع الجمعية", "أسواق ع العثيم") < 0.5,
      "٥ والتشابهُ لا يُحسب باسم الشركة المشترك")
check(D.similar("عمومية الغاز توافق على تفويض مجلس الإدارة بتوزيع أرباح مرحلية عن العام",
                "تعلن شركة الغاز والتصنيع الأهلية القابضة عن قرار مجلس الإدارة بتوزيع أرباح نقدية على المساهمين", "الغاز القابضة") < 0.5,
      "٦ و«مجلس الإدارة» العامّةُ لا تُلبِس موافقةَ العمومية نصَّ قرار التوزيع (قِيس على غازكو)")
print(f"{'FAIL' if fail else 'PASS'} D467 — «تداول» أوّلاً و«أرقام» مكمِّلاً")
sys.exit(fail)
