#!/usr/bin/env python3
"""حارسُ D580: نتائجُ الشركات من جدول إعلان «تداول» الموحَّد — بوحدتها الصحيحة، ولا تقديريةَ ولا جمعيات،
وتُقدِّم تاريخَ آخر قائمة فلا يمتنع القرارُ وقد نشرت الشركةُ نتائجَها.

    python3 scripts/audit/results_ann_d580.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import results_announcements as R
# متونُ «تداول» الحقيقية (كاشف results_ann_door)
sab = ("المبيعات/الايرادات | 24.81 | 30.23 | -17.929 | 26.15 | -5.124\n"
       "صافي الربح (الخسارة) العائد لمساهمي المصدر | -0.83 | -4.07 | -79.606 | 0.01 | -\n"
       "جميع الأرقام بالـ (مليار) ريال سعودي\n"
       "المبيعات/الايرادات | 50.96 | 59.49 | -14.338\n"
       "صافي الربح (الخسارة) العائد لمساهمي المصدر | -0.82 | -5.28 | -84.469\n"
       "إجمالي حقوق الملكية (بعد استبعاد الحصص غير المسيطرة) | 123.53 | 153.88 | -19.723\n"
       "ربحية (خسارة) السهم | -0.27 | -1.76\n"
       "يعود سبب الارتفاع (الانخفاض) في المبيعات/ الإيرادات خلال الربع الحالي | على الرغم")
p = R.parse(sab, "إعلان سابك عن النتائج المالية الأولية لفترة (6) الستة أشهر، المنتهية في 30/06/2026م")
check(bool(p) and p["as_of"] == "2026-06-30" and p["months"] == 6, "١ نهايةُ الفترة ومدّتُها من العنوان", str(p and p["as_of"]))
check(bool(p) and p["quarter"]["revenue"] == 24.81e9 and p["quarter"]["net_income"] == -0.83e9
      and p["ytd"]["equity"] == 123.53e9 and p["ytd"]["eps"] == -0.27, "٢ الربعُ والفترةُ بالمليار، والخسارةُ سالبة، وربحيةُ السهم بلا وحدة")
bupa = ("إيراد التأمين | 5,299,909 | 4,715,717 | 12.388 | 5,240,382 | 1.135\n"
        "صافي الربح (الخسارة) بعد الزكاة العائد للمساهمين | 306,779 | 286,253 | 7.17 | 387,296 | -20.789\n"
        "جميع الأرقام بالـ (الاف) ريال سعودي")
b = R.parse(bupa, "Bupa Arabia announces its Interim Consolidated Financial Results for the period ending on  2026-06-30 ( Six Months )")
check(bool(b) and b["quarter"]["revenue"] == 5299909e3 and b["quarter"]["net_income"] == 306779e3, "٣ التأمين: إيرادُ التأمين بالآلاف")
check(not R.is_results_title("X ANNOUNCES ITS ESTIMATED FINANCIAL RESULTS FOR THE PERIOD ENDED ON 30 JUNE 2026")
      and not R.is_results_title("X ANNOUNCES THE RESULTS OF THE 21st ORDINARY GENERAL ASSEMBLY MEETING")
      and R.is_results_title("X ANNOUNCES ITS ANNUAL CONSOLIDATED FINANCIAL RESULTS FOR THE YEAR ENDED 31 DECEMBER 2025 ("),
      "٤ لا تقديريةَ ولا جمعيات")
check(R.parse("لا جدولَ هنا | 5", "النتائج المالية") is None, "٥ بلا سطر وحدةٍ لا يُختلق شيء")

from app.services import lastgood
lastgood.save(R.STORE.format("2010"), {"at": "2026-10-03", "items": [{**p, "id": 1}]})
from app.services.four_scores import build_company_features
periods = [{"year": y, "as_of": f"{y}-12-31", "revenue": 1000.0, "net_income": 100.0, "total_assets": 5000.0,
            "total_equity": 2000.0, "operating_cash_flow": 120.0} for y in (2023, 2024, 2025)]
f, _i, _q = build_company_features(periods, info={}, sector="Materials", symbol="2010")
check(str(f.get("_asof"))[:10] == "2026-06-30", "٦ نتيجةُ يونيو المعلنة تُقدِّم تاريخَ آخر قائمة", str(f.get("_asof")))
check(R.due(["2010", "9999"], date(2026, 10, 3)) == ["9999"], "٧ من له نتيجةٌ حديثةٌ لا يُعاد، ومن لا سجلَّ له أوّلاً")
src = (ROOT / "backend/app/scheduler/scheduler.py").read_text()
check('id="results_announcements_evening"' in src, "٨ تُجدَّد كلَّ مساء")
sys.exit(fail)
