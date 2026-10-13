#!/usr/bin/env python3
"""اختبارُ حارس التجميد D635 بمساراته الخمسة — في مجلّدٍ مؤقّت، لا يمسّ خطَّ الأساس الحقيقيّ."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import engine_freeze_d635 as F   # noqa: E402

fail = 0
def check(ok, label):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}")

tmp = pathlib.Path(tempfile.mkdtemp())
F.BASE, F.REPORTS = tmp / "base.json", tmp / "reports"
import contextlib, io
def run():
    with contextlib.redirect_stdout(io.StringIO()):
        return F.main()
m0 = {"coverage": 0.91, "unnamed_missing": 0, "stale": 0, "precapital": 0, "far_share": 0.044, "median_dev": 0.16,
      "conf_share": 0.67, "sector_dev": {"البنوك": 0.05, "التأمين": 0.18}, "flagged": ["التأمين"],
      "verdict": {"١ التغطية": True, "٤ المرجع": True}}
check(run() == 0, "١ قبل التجميد يمرّ")
fp = F.fingerprint()
F.BASE.write_text(json.dumps({"version": "1.0", "fingerprint": fp, "metrics": m0}))
check(run() == 0, "٢ المحرّكاتُ كما جُمّدت تمرّ")
F.BASE.write_text(json.dumps({"version": "1.0", "fingerprint": "older", "metrics": m0}))
check(run() == 1, "٣ تعديلٌ بلا تقرير بوابةٍ يسقط")
F.REPORTS.mkdir()
def report(m):
    (F.REPORTS / f"{fp}.json").write_text(json.dumps({"metrics": m}))
report({**m0, "sector_dev": {"البنوك": 0.09, "التأمين": 0.18}})
check(run() == 1, "٤ تراجعُ قطاعٍ مُعايَر يسقط وإن ثبت الباقي")
report(dict(m0))
check(run() == 1, "٥ تعديلٌ لا يتفوّق في شيءٍ يسقط — تعديلٌ بلا فائدةٍ مقيسة")
report({**m0, "median_dev": 0.14})
check(run() == 0, "٦ تفوّقٌ بلا تراجعٍ يمرّ")
report({**m0, "median_dev": 0.14, "sector_dev": {"البنوك": 0.05, "التأمين": 0.30}})
check(run() == 0, "٧ القطاعُ الموسوم (لم يُعايَر) لا يُحسب تراجعاً")
report({**m0, "median_dev": 0.14, "verdict": {"١ التغطية": False, "٤ المرجع": True}})
check(run() == 1, "٨ بندٌ اجتاز ثمّ سقط يسقط")
# ‏D676: تراجعٌ قَبِلَه المالكُ بنصّه — في مقياسه وحده وفوق أرضيّته
def report_acc(m, acc):
    (F.REPORTS / f"{fp}.json").write_text(json.dumps({"metrics": m, "owner_accepted": acc}))
_acc = {"coverage": {"floor": 0.88, "decision": "تُحجب بسببٍ مسمّى"}}
report_acc({**m0, "median_dev": 0.14, "coverage": 0.893}, _acc)
check(run() == 0, "٩ تراجعُ التغطية فوق أرضيّةٍ قَبِلها المالكُ بنصّه يمرّ")
report_acc({**m0, "coverage": 0.893}, _acc)
check(run() == 1, "٩ب والتراجعُ المقبول لا يُعدّ تحسّناً — يلزم تفوّقٌ في مقياسٍ آخر")
report_acc({**m0, "median_dev": 0.14, "coverage": 0.87}, _acc)
check(run() == 1, "١٠ وتحت الأرضيّة يسقط")
report_acc({**m0, "median_dev": 0.14, "coverage": 0.893}, {"coverage": {"floor": 0.88}})
check(run() == 1, "١١ وبلا نصّ القرار يسقط — لا قبولَ بلا قرارٍ مكتوب")
report_acc({**m0, "median_dev": 0.14, "coverage": 0.91, "far_share": 0.08}, _acc)
check(run() == 1, "١٢ والقبولُ في مقياسه وحده — تراجعُ غيره يبقى تراجعاً")
# ‏D681: ملحقُ الأساس — مقياسٌ جديدٌ قِيس على شيفرة المجمَّد نفسِها يُقارَن به، ولا يغيّر مقياساً في الأساس
F.BASE.write_text(json.dumps({"version": "1.0", "fingerprint": "older", "metrics": m0}))
(F.REPORTS / "older.addendum.json").write_text(json.dumps({"fingerprint": "older", "metrics": {"d_abstain_overwrite": 3}}))
report({**m0, "d_abstain_overwrite": 0})
check(run() == 0, "١٣ مقياسٌ جديدٌ في ملحق الأساس (3) يُحسب تحسّناً حين يبلغ المرشَّحُ 0")
report({**m0, "d_abstain_overwrite": 4})
check(run() == 1, "١٤ وتراجعُه عن الملحق تراجع")
(F.REPORTS / "older.addendum.json").write_text(json.dumps({"fingerprint": "other", "metrics": {"d_abstain_overwrite": 3}}))
report({**m0, "d_abstain_overwrite": 0})
check(run() == 1, "١٥ وملحقٌ ببصمةٍ أخرى لا يُقرأ")
(F.REPORTS / "older.addendum.json").write_text(json.dumps({"fingerprint": "older", "metrics": {"median_dev": 0.30}}))
report({**m0, "median_dev": 0.20})
check(run() == 1, "١٦ والملحقُ لا يغيّر مقياساً في الأساس — يضيف ولا يستبدل")
# ‏D692: شاهدُ الأساس في يوم التقرير نفسِه — السوقُ تحرّك فساءت مقاييسُ الأساس نفسِه
(F.REPORTS / "older.addendum.json").unlink()
def report_on(m, day):
    (F.REPORTS / f"{fp}.json").write_text(json.dumps({"metrics": m, "measured_at": day}))
drift = {**m0, "median_dev": 0.19, "d_abstain_overwrite": 3}
(F.REPORTS / "older.control.json").write_text(json.dumps({"fingerprint": "older", "measured_at": "2026-10-13", "metrics": drift}))
report_on({**drift, "d_abstain_overwrite": 0}, "2026-10-13")
check(run() == 0, "١٧ شاهدُ الأساس في يوم التقرير نفسِه هو المرجع — حركةُ السوق لا تُحسب على المرشَّح")
report_on({**drift, "d_abstain_overwrite": 0}, "2026-10-14")
check(run() == 1, "١٨ وشاهدٌ من يومٍ آخر لا يُقرأ — يعود المرجعُ إلى أرقام التجميد")
(F.REPORTS / "older.control.json").write_text(json.dumps({"fingerprint": "other", "measured_at": "2026-10-13", "metrics": drift}))
report_on({**drift, "d_abstain_overwrite": 0}, "2026-10-13")
check(run() == 1, "١٩ ولا شاهدَ ببصمةٍ غيرِ بصمة الأساس")
(F.REPORTS / "older.control.json").write_text(json.dumps({"fingerprint": "older", "measured_at": "2026-10-13", "metrics": drift}))
report_on({**drift, "median_dev": 0.21, "d_abstain_overwrite": 0}, "2026-10-13")
check(run() == 1, "٢٠ والمرشَّحُ يُحاسَب على تراجعه عن الشاهد — لا رخصةَ تراجع")
report_on(drift, "2026-10-13")
check(run() == 1, "٢١ ومطابقةُ الشاهد وحدها ليست تفوّقاً — تعديلٌ بلا فائدةٍ مقيسة")
dv = {**drift, "verdict": {"١ التغطية": True, "٤ المرجع": False}}
(F.REPORTS / "older.control.json").write_text(json.dumps({"fingerprint": "older", "measured_at": "2026-10-13", "metrics": dv}))
report_on({**dv, "d_abstain_overwrite": 0}, "2026-10-13")
check(run() == 0, "٢٢ وبندٌ يسقط اليومَ في الأساس نفسِه لا يُحسب على المرشَّح «اجتاز ثمّ سقط»")
report_on({**dv, "d_abstain_overwrite": 0, "verdict": {"١ التغطية": False, "٤ المرجع": False}}, "2026-10-13")
check(run() == 1, "٢٣ وما اجتازه الأساسُ اليومَ يُلزم المرشَّح")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
