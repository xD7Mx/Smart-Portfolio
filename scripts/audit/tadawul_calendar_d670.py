#!/usr/bin/env python3
"""حارسُ D670: أحداثُ «تداول» الرسمية تظهر في المفكرة بعناوينها العربية.

الحالُ قبل الإصلاح (قِيس على الإنتاج): بنّاءُ مفكرة «تداول» يقرأ خدمةَ أخبار السوق — أخبارٌ للهيئة و«إيداع» بلا رمز
وبالإنجليزية — فيُسقطها المرشِّحُ العربيّ (D506) كلَّها: 19 في المخزن · 0 في المفكرة. وخدمةُ إفصاحات الشركات للسوق كلّه
تُعطي 60 من 60 بعنوانٍ عربيٍّ رسميّ ورمز، 38 منها لا حدثَ لها في المفكرة. فالحارسُ يمنع العودةَ إلى المصدر الإنجليزيّ،
ويمنع الترجمةَ بدلَ النصّ الرسميّ، ويتحقّق أن الحدثَ الرسميَّ يبلغ المفكرةَ مرّةً واحدة.

    python3 scripts/audit/tadawul_calendar_d670.py
"""
import asyncio, inspect, json, os, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import content_engine as C          # noqa: E402
from app.services import tadawul_disclosure as D      # noqa: E402
from app.services import tadawul_http as H            # noqa: E402

src = inspect.getsource(C.build_market_calendar_tadawul)
code = src.split('"""', 2)[-1]
check("market_list" in code and "fetch_tadawul_announcements" not in code,
      "١ بنّاءُ المفكرة يقرأ إفصاحاتِ الشركات (market_list) لا خدمةَ أخبار السوق الإنجليزية")
check(not any(w in code.lower() for w in ("translat", "ترجم")) and "ترجم" not in inspect.getsource(D.market_list).split('"""', 2)[-1],
      "٢ ولا ترجمةَ آلية: النصُّ العربيُّ الرسميّ وحده")

# ٣ · قارئُ السوق: العربيُّ برمزه ورابطه يُقبل، والإنجليزيُّ وما بلا رمزٍ أو رابطٍ يُسقط
ROWS = [
    {"SYMBOL": "4192", "TITLE": "السيف غاليري", "PR_DATE": "Oct 08, 2026", "announcementNumber": 1,
     "SHORT_DESC": "إعلان شركة متاجر السيف للتنمية والاستثمار عن قرار مجلس الإدارة بتوزيع أرباح نقدية",
     "announcementUrl": "/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements/x?locale=en"},
    {"SYMBOL": "6012", "TITLE": "ريدان", "PR_DATE": "Oct 08, 2026", "announcementNumber": 2,
     "SHORT_DESC": "اعلان شركة ريدان الغذائية عن استقالة عضو لجنة المراجعة",
     "announcementUrl": "/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements/y?locale=ar"},
    {"SYMBOL": "2280", "TITLE": "Almarai", "PR_DATE": "Oct 08, 2026", "announcementNumber": 3,
     "SHORT_DESC": "Almarai announces its Capital Markets Day presentation",
     "announcementUrl": "/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements/z?locale=en"},
    {"SYMBOL": "", "TITLE": "", "PR_DATE": "Oct 08, 2026", "announcementNumber": 4,
     "SHORT_DESC": "إعلانٌ بلا رمز", "announcementUrl": "/wps/x"},
]


async def _ep():
    return "https://www.saudiexchange.sa/svc"


async def _sf(*a, **k):
    return 200, json.dumps({"announcementList": ROWS})

_o = (D._endpoint, H.smart_fetch)
D._endpoint, H.smart_fetch = _ep, _sf
try:
    got = asyncio.run(D.market_list())
finally:
    D._endpoint, H.smart_fetch = _o
check([g["symbol"] for g in got] == ["4192", "6012"],
      "٣ قارئُ السوق يقبل العربيَّ برمزه ويُسقط الإنجليزيَّ وما بلا رمز", str([g.get("symbol") for g in got]))
check(all(g["url"].startswith("https://www.saudiexchange.sa/") and "locale=ar" in g["url"]
          and g["date"] == "2026-10-08" and g.get("date_kind") == "announced" for g in got),
      "٤ ورابطُه مطلقٌ بنسخته العربية، وتاريخُه تاريخُ إعلان", str([(g.get("url"), g.get("date")) for g in got][:1]))

# ٥ · من البنّاء إلى المفكرة: الحدثُ الرسميُّ يظهر، وبقايا الأخبار الإنجليزية تُزال، والحدثُ نفسُه من «أرقام» لا يتكرّر
store = {
    "old-en": {"id": "old-en", "type": "OTHER", "title": "CMA Announces the Approval of Public Offering",
               "symbol": None, "date": "2026-10-05", "date_kind": "announced", "source": "تداول"},
    "arg-1": {"id": "arg-1", "type": C._cal_type(got[0]["title"]), "title": got[0]["title"], "symbol": "4192",
              "date": "2026-10-08", "date_kind": "announced", "source": "أرقام"},
}


async def _ml(size: int = 150):
    return got

_saved = {}
_o2 = (D.market_list, C._cal_load_store, C._universe_pairs, C._cal_prune_and_save)
D.market_list = _ml
C._cal_load_store = lambda: store
C._universe_pairs = lambda: [("4192", "السيف غاليري"), ("6012", "ريدان")]
C._cal_prune_and_save = lambda s: _saved.update(s) or None
try:
    added = asyncio.run(C.build_market_calendar_tadawul())
    _after = dict(_saved)
    C._cal_load_store = lambda: _after
    shown = C.clean_events(asyncio.run(C.market_wide_events()))
finally:
    D.market_list, C._cal_load_store, C._universe_pairs, C._cal_prune_and_save = _o2
td = [e for e in shown if e.get("source") == "تداول"]
check(len(td) == 2 and all(e.get("date_kind") == "announced" for e in td),
      "٥ إفصاحاتُ «تداول» تبلغ المفكرةَ المعروضةَ بعناوينها العربية", f"{len(td)} من 2 · أُضيف {added}")
check("old-en" not in _after, "٦ وبقايا أخبار السوق الإنجليزية تُزال من المخزن فلا تُزاحم المعروضَ على حدّه")
s4192 = [e for e in shown if e.get("symbol") == "4192"]
check(len(s4192) == 1 and s4192[0].get("source") == "تداول",
      "٧ والحدثُ نفسُه من «أرقام» و«تداول» يُعرض مرّةً بنسخة «تداول»", str([e.get("source") for e in s4192]))
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
