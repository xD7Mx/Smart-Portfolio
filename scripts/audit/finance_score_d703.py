#!/usr/bin/env python3
"""حارسُ D703 · D720 — الدرجةُ الماليةُ جودةُ القوائم لا توقّعُ السهم.

‏D703 (2026-10-13): بُنيت الأوزانُ على «هل يتفوّق السهمُ بعد سنة» — فصار صافي ربح سنةٍ واحدة ‎35٪‎ وجودةُ الربح بلا وزن.
‏D720 (المالك 2026-10-14): «أرقامٌ ظالمة لا تنمّ عن صدق القوائم المالية». قِيس: الاتّصالات ‎46‎ بعائدٍ ‎18٪‎ وربحٍ مغطًّى بالنقد
لأنّ ربحَ سنةٍ نزل. فالحارسُ يُثبت العقدَ الجديد ويمنع العودة:
  · الأوزانُ: الربحيّةُ أثقلُها، ونموُّ الربح مركّبٌ عبر السنوات بوزنٍ معتدل، وجودةُ الربح بالنقد لها وزن.
  · سنةٌ هابطةٌ بعد نموٍّ لا تهدم الدرجة، والنموُّ المتّصلُ فوق الهابط المتّصل بفارقٍ يُقرأ.
  · الربحُ المغطّى بالنقد فوق الربح الورقيّ.
  · والخسارةُ لا «تنمو»، والخطوطُ الحمراءُ صفرٌ كما هي.

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
check(W.get("roe", 0) == max(W.values()) and 0 < W.get("ni_growth", 0) <= 0.2 and W.get("earnings_quality", 0) >= 0.1,
      "١ الأوزانُ لجودة القوائم: الربحيّةُ أثقلُها، ونموُّ الربح معتدلُ الوزن، وجودةُ الربح بالنقد لها وزن (‏D720)", str(W))


def series(nis, ocf_x=1.3, fcf=(150, 160, 170, 180), prev_override=None):
    out = []
    for i, ni in enumerate(nis):
        out.append({"revenue": 1000.0 * 1.06 ** i, "net_income": ni, "operating_cash_flow": ni * ocf_x if ni else 0,
                    "free_cash_flow": fcf[i % len(fcf)], "equity": 800.0, "debt_ratio": 0.35, "interest_coverage": 8, "capex": None})
    return out


up = SC._finance_score_from_periods(series([100, 110, 121, 133]))
dip = SC._finance_score_from_periods(series([100, 110, 121, 103]))
down = SC._finance_score_from_periods(series([133, 121, 110, 100]))
check(up is not None and dip is not None and down is not None and up > dip and up - dip <= 12 and up - down >= 10,
      "٢ سنةٌ هابطةٌ بعد نموٍّ لا تهدم الدرجة، والنموُّ المتّصلُ فوق الهابطِ المتّصل بفارقٍ يُقرأ",
      f"صاعد {up} · هبوطُ سنة {dip} · هابطٌ متّصل {down}")
cash = SC._finance_score_from_periods(series([100, 110, 121, 133]))
paper = SC._finance_score_from_periods(series([100, 110, 121, 133], ocf_x=0.3))
check(cash is not None and paper is not None and cash - paper >= 6,
      "٣ والربحُ المغطّى بالنقد فوق الربح الورقيّ (‏D720 — كان بلا وزن)", f"{cash} مقابل {paper}")

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
