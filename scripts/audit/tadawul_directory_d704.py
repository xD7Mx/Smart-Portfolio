#!/usr/bin/env python3
"""حارسُ D704 — «تداول» مصدرُ اسم الشركة وقطاعها وعضويةِ السوق الرئيسية (بأمر المالك 2026-10-14).

قال المالك: «اجعل تداول هو مصدرك ومصدر التطبيق… المهمّ أن اسمَ الشركة وقطاعَها يظهر من تداول حتى يكون التطبيقُ مواكباً
للشركات الجديدة والمنقولة والموقوفة… لتعرف شركاتِ السوق الرئيسيّ وليس نمو». وكان السوقُ يُحسم ببادئة الرمز (9 = نمو)، والكونُ من
ملفّاتٍ ثابتة لا يدخلها اكتتابٌ جديد، والدليلُ يرجع إلى «أرقام» إن تعذّرت «تداول». فالحارسُ يمنع العودة — سلوكاً:
  · الدليلُ من صفحتَي «السوق الرئيسية» و«نمو» باللغتين، والعربيُّ من «تداول» بلغتها لا تعريباً.
  · العضويةُ بالصفحة لا بالبادئة: المنقولُ إلى الرئيسية رئيسيّ، والبادئةُ احتياطٌ لما لا يعرفه الدليل.
  · الجديدُ في الرئيسية يدخل الكونَ باسمه وقطاعه الرسميَّين، و«نمو» لا يُضاف إليها جديد.
  · الغائبُ يُوسَم بتاريخه ولا يُحذف، والعائدُ يُرفع وسمُه، والقائمةُ القصيرةُ تُرفض ولا تكتب شيئاً.
  · ولا «أرقام» في الدليل، والمزامنةُ ليليّةٌ وعند كلّ نشر.

    python3 scripts/audit/tadawul_directory_d704.py
"""
import asyncio, importlib, os, sys, tempfile
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


from app.services import tadawul_sync as TS, tadawul_market as TM, lastgood
from app.data import universe as U

if not hasattr(TS, "sync_directory"):
    check(False, "٠ مزامنةُ دليل «تداول» موجودة")
    print("\nالنتيجة: عطب ✖")
    sys.exit(1)

# صفحاتٌ مصطنعة بشكل خدمة «تداول» (companySymbol · companyName · sectorName): 210 رئيسيّةً — منها المنقولةُ 9990 من «نمو»
# والجديدةُ 4999 — و«نمو» فيها 9510 والمنقولةُ إليها 2998
MAIN = [f"{1000 + k}" for k in range(208)] + ["9990", "4999"]
NOMU = ["9510", "2998"]
SEC_AR, SEC_EN = "المواد الأساسية", "Materials"


def rows_for(syms, loc):
    return [{"companySymbol": s, "companyName": (f"شركة اختبار {s}" if loc == "ar" else f"Test Co {s}"),
             "sectorName": (("السلع طويلة الاجل" if s == "1001" else SEC_AR) if loc == "ar" else SEC_EN)} for s in syms]


state = {"main": MAIN}


async def fake_rows(page=None, locale="en"):
    return (rows_for(state["main"], locale), None) if page == TM.PAGE else (rows_for(NOMU, locale), None)

TM.fetch_rows = fake_rows
r = asyncio.run(TS.sync_directory())
d = TS.directory()
check(r.get("ok") and len(d.get("main") or {}) == 210 and set(d.get("nomu") or {}) == set(NOMU)
      and d["main"]["4999"].get("name") == "اختبار 4999" and d["main"]["4999"].get("sector") == SEC_AR
      and d["main"]["4999"].get("name_en") == "Test Co 4999" and d["main"]["4999"].get("sector_en") == SEC_EN,
      "١ الدليلُ من صفحتَي «تداول» باللغتين — الاسمُ والقطاعُ العربيّان من «تداول» بلغتها لا تعريباً", str(r)[:120])

U._DM_AT = 0.0
check(U.market_of("9990") == U.MAIN and U.market_of("2998") == U.NOMU and U.market_of("1000") == U.MAIN
      and U.market_of("9555") == U.NOMU and U.market_of("3555") == U.MAIN,
      "٢ العضويةُ بالصفحة لا بالبادئة: المنقولُ إلى الرئيسية رئيسيّ والمنقولُ إلى «نمو» منها — والبادئةُ لما لا يعرفه الدليل")

from app.data import market_universe as MUmod
MUmod = importlib.reload(MUmod)
MU = MUmod.MARKET_UNIVERSE
check("4999" in MU and MU["4999"].get("name_ar") == "اختبار 4999" and MU["4999"].get("sector") == SEC_AR
      and "4999" in U.main_market(MU) and "2998" not in U.main_market(MU),
      "٣ الجديدُ في الرئيسية يدخل الكونَ باسمه وقطاعه الرسميَّين — ويُحسب في السوق الرئيسية", str(MU.get("4999")))
check("2998" not in MU or MU["2998"].get("market_td") == "nomu",
      "٤ و«نمو» لا يُضاف إليها جديد (المالكُ يريد تاسي)")
from app.data import saudi_directory as SDmod, company_sectors as CSmod
SDmod = importlib.reload(SDmod)
CSmod = importlib.reload(CSmod)
check(TS.directory()["main"]["1001"].get("sector") == "السلع طويلة الأجل" and CSmod.SYMBOL_TO_SECTOR_AR.get("1001") == "السلع طويلة الأجل"
      and CSmod.SYMBOL_TO_SECTOR_AR.get("4999") == SEC_AR and SDmod.SYMBOL_TO_NAME.get("4999") == "اختبار 4999",
      "٤ب والقطاعُ من «تداول» بإملاء التطبيق الواحد («الاجل» ← «الأجل») — في المصدر الذي تقرؤه الشاشاتُ والمحرّكاتُ كلُّها",
      f"{CSmod.SYMBOL_TO_SECTOR_AR.get('1001')} · {CSmod.SYMBOL_TO_SECTOR_AR.get('4999')}")

state["main"] = [s for s in MAIN if s != "1005"]
asyncio.run(TS.sync_directory())
g1 = (TS.directory().get("gone") or {})
state["main"] = MAIN
asyncio.run(TS.sync_directory())
g2 = (TS.directory().get("gone") or {})
check("1005" in g1 and "1005" not in g2, "٥ الغائبُ عن الرئيسية يُوسَم بتاريخ غيابه ولا يُحذف — والعائدُ يُرفع وسمُه", f"{g1} ← {g2}")

before = TS.directory()
state["main"] = MAIN[:50]
r = asyncio.run(TS.sync_directory())
check(not r.get("ok") and TS.directory() == before, "٦ والقائمةُ القصيرةُ جلبٌ فشل — تُرفض ولا تكتب شيئاً", str(r)[:100])
state["main"] = MAIN


async def _boom():
    raise AssertionError("أرقام نوديت")

TS._argaam_listed = _boom
TS.directory = lambda: {**before, "at": TS._now()}
got, why = asyncio.run(TS.fetch_listed())
check(len(got) >= 200 and why is None, "٧ قائمةُ المدرَجين من دليل «تداول» — ولا «أرقام» في الدليل", str(why))

src = open(os.path.join(ROOT, "backend/app/services/tadawul_sync.py"), encoding="utf-8").read()
fl = src[src.index("async def fetch_listed"):src.index("def plan(")]
sch = open(os.path.join(ROOT, "backend/app/scheduler/scheduler.py"), encoding="utf-8").read()
check("_argaam_listed()" not in fl and "await sync_directory()" in src[src.index("async def sync_official"):]
      and "from app.services.tadawul_sync import sync_directory" in sch,
      "٨ والمزامنةُ ليليّةٌ وعند كلّ نشر (‏sync_official في complete.sh)، ولا رجوعَ إلى «أرقام»")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
