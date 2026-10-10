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
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
