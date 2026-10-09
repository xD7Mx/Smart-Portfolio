#!/usr/bin/env python3
"""حارسُ D658: «المسارُ الواحد» في بوّابة القرار يُعدّ من نماذج المحرّك الذي أنتج الرقمَ المعروض — لا من الاحتياطيّ.

العطب (قِيس على 2.1): القرارُ يقول «التقديرُ من مسارٍ واحد بلا شاهدٍ ثانٍ» وتفاصيلُ النماذج بجانبه تعرض عشرة، لأنّ العدَّ من
المحرّك الاحتياطيّ ومساراتُه تتبع توافرَ بيانات المزوّد لحظةَ الحساب — فتأرجح قرارُ سلوشنز (7202) بين «شراء» و«انتظار»."""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0
def check(ok, label):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}")
src = (ROOT / "backend/app/services/analysis.py").read_text(encoding="utf-8")
i_new = src.find('_fv.update({"confidence": confidence_of(_new), "model_value": _new.get("model_value")})')
i_sp = src.find('_fv["single_path"] = len(_new.get("models") or []) < 2')
i_gate = src.find("single_path=bool(_fv.get(\"single_path\"))")
check(0 < i_new < i_sp, "١ حين يُنتج محرّكُ النماذج الرقمَ تُعدّ مساراتُه هو")
check(0 < i_sp < i_gate, "٢ وقبل بوّابة القرار — فالقرارُ يُحكم بشهود الرقم المعروض")
pg = (ROOT / "scripts/audit/parity_gate.py").read_text(encoding="utf-8")
check('"d_single_contra"' in pg and "single_screen" in pg, "٣ والتناقضُ يُقاس في الصفحة والفرز معاً (بوابةُ رقم اليوم)")
fz = (ROOT / "scripts/audit/engine_freeze_d635.py").read_text(encoding="utf-8")
check('"d_single_contra": (-1, 0)' in fz, "٤ وحارسُ التجميد يمنع عودتَه")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
