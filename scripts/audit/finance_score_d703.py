#!/usr/bin/env python3
"""حارسُ D703 — الدرجةُ الماليةُ مبنيّةٌ على النتيجة لا على الانطباع (بأمر المالك 2026-10-13).

قال المالك: «أريد كلَّ الأرقام التي تظهر في التطبيق محلَّ ثقة — سواءٌ درجةٌ ماليةٌ أو سعرٌ عادل». قِيست مكوّناتُ الدرجة
داخل كلّ قطاعٍ بما كان منشوراً منذ 2023 (2,976 مشاهدة): كانت الدرجةُ القديمةُ −0.03 في النصف الأوّل داخل القطاع (−0.12 في
السوق كلّه) — أي أنّ الأعلى درجةً تخلّف عن أقرانه. وأثبتُ مكوّنٍ نموُّ صافي الربح ولم يكن فيها، وجودةُ الربح وهامشُ التدفّق
الحرّ ينقلبان بين النظامين. فالحارسُ يمنع العودة:
  · الأوزانُ كما قِيست، ونموُّ صافي الربح أثقلُها، وجودةُ الربح والتدفّقُ الحرّ بلا وزنٍ في الترتيب (والخطُّ الأحمر باقٍ لهما).
  · الربحُ الصاعد فوق الهابط بفارقٍ يُقرأ، والخسارةُ لا «تنمو» بانكماشها.
  · الخطوطُ الحمراءُ صفرٌ كما هي، والاختبارُ التاريخيّ يقيس الدالّةَ نفسَها التي تعرضها البطاقة.
  · والعدد يُميَّز بالعربية: «6 حالات» لا «6 حالة».

    python3 scripts/audit/finance_score_d703.py
"""
import os, sys, tempfile
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


from app.services import scores as SC

W = getattr(SC, "FINANCE_WEIGHTS", {})
check(W == {"revenue_growth": 0.15, "roe": 0.20, "ni_growth": 0.35, "debt": 0.15, "coverage": 0.15,
            "earnings_quality": 0.0, "fcf_margin": 0.0},
      "١ أوزانُ الدرجة كما قِيست بالنتيجة — نموُّ صافي الربح أثقلُها، وجودةُ الربح والتدفّقُ الحرّ بلا وزن", str(W))


def series(nis, ocf_x=1.3, fcf=(150, 160, 170), prev_override=None):
    out = []
    for i, ni in enumerate(nis):
        out.append({"revenue": 1000.0 * 1.06 ** i, "net_income": ni, "operating_cash_flow": ni * ocf_x if ni else 0,
                    "free_cash_flow": fcf[i], "equity": 800.0, "debt_ratio": 0.35, "interest_coverage": 8, "capex": None})
    return out


up = SC._finance_score_from_periods(series([100, 110, 121]))
down = SC._finance_score_from_periods(series([100, 110, 99]))
check(up is not None and down is not None and up - down >= 15,
      "٢ الربحُ الصاعدُ فوق الهابط بفارقٍ يُقرأ (ونموُّه أثبتُ ما سبق التفوّق)", f"{up} مقابل {down}")

base = SC._finance_score_from_periods(series([100, 110, 121]))
noisy = SC._finance_score_from_periods(series([100, 110, 121], ocf_x=0.3, fcf=(-50, 400, -20)))
check(base == noisy, "٣ وجودةُ الربح وهامشُ التدفّق الحرّ لا يحرّكان الترتيب — انقلبا بين النظامين فلا يُبنى عليهما",
      f"{base} و{noisy}")

shrink = SC._finance_score_from_periods(series([-50, -200, -140]))
deeper = SC._finance_score_from_periods(series([-50, -100, -140]))
check(shrink is not None and shrink == deeper,
      "٤ والخسارةُ لا «تنمو»: انكماشُها من −200 إلى −140 لا يُقرأ نموّاً ‎+30٪", f"{shrink} و{deeper}")

score, lines, _w = SC.governed_finance_score(series([-30, -40, -20]))
check(score == 0 and any(l.get("id") == "loss_streak" for l in lines),
      "٥ والخطُّ الأحمرُ صفرٌ كما هو — خسارةُ ثلاث سنوات تُستبعد", f"{score} · {[l.get('id') for l in lines]}")
score, lines, _w = SC.governed_finance_score(series([100, 110, 121], fcf=(-10, -20, -30)))
check(any(w.get("id") == "no_fcf" for w in _w),
      "٦ والتدفّقُ الحرّ السالبُ ثلاثاً تحذيرٌ باقٍ بجانب الدرجة — لا وزنَ له في الترتيب ولا يُخفى",
      f"{score} · {[w.get('id') for w in _w]}")

bt = open(os.path.join(ROOT, "scripts/audit/fv_backtest_d699.py"), encoding="utf-8").read()
check("governed_finance_score(per, sym)" in bt and 'out[f"o_fs_ic{h}"]' in bt,
      "٧ والاختبارُ التاريخيّ يقيس الدالّةَ نفسَها التي تعرضها البطاقة، وارتباطُها يُحرس في التجميد")

from app.services import fair_value_models as F
cases = getattr(F, "_cases", None)
check(cases is not None and (cases(6), cases(18), cases(76), cases(105), cases(1000), cases(1234))
      == ("حالات", "حالةً", "حالةً", "حالات", "حالة", "حالةً"),
      "٨ والعددُ يُميَّز بالعربية: «6 حالات» و«76 حالةً» — لا «6 حالة»")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
