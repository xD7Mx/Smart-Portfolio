#!/usr/bin/env python3
"""حارسُ D655 (سؤالُ المالك 2026-10-09): السعرُ العادل وهدفُه في تقرير الشركة هما رقمُ صفحة السهم والفرز نفسُه.

العطب المقيس على الإنتاج (report_parity_door · run 37956078485): 12 تقريراً من 272 تعرض «السعرَ المستهدف خلال 12 شهراً»
لشركاتٍ حجب المحرّكُ رقمَها (8 نماذجُها متباينةٌ بعيدة · 4 قوائمُها أقدمُ من 15 شهراً)؛ والباقيةُ تطابق الصفحةَ يومَ الجمعة
وحده — لأنّ التقريرَ بنى الهدفَ من حساب النماذج الخام لا من رقم اليوم."""
import os, pathlib, sys, tempfile
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

from app.services.fair_value_view import target_from   # noqa: E402
m = {"value": 52.0, "target_12m": 57.2}
check(target_from(50.0, m) == 55.0, "١ الهدفُ يُبنى من السعر العادل المعروض بنسبة النماذج", str(target_from(50.0, m)))
check(target_from(None, m) is None, "٢ ورقمٌ محجوبٌ لا هدفَ له — لا يُشتقّ من حسابٍ امتنع المحرّكُ عن نشره")
check(target_from(50.0, {"live_value": 52.0, "value": 50.0, "target_12m": 57.2}) == 55.0,
      "٣ وبعد تراكب رقم اليوم تُقرأ قيمةُ النماذج الحيّة لا المعروضة")
qr = (ROOT / "backend/app/services/quarter_report.py").read_text(encoding="utf-8")
b = qr[qr.index("async def build"):]
check('target = fvm.get("target_12m")' not in b and "target = target_from(fair, fvm)" in b,
      "٤ تقريرُ الشركة لا يأخذ الهدفَ من حساب النماذج الخام")
check('fair = an.get("fair_value")' in b and "await analyze_company(" in b,
      "٥ والسعرُ العادل في التقرير من المُنتِج الواحد (صفحةُ السهم: رقمُ اليوم بقواعد الحجب والوسم)")
check('"fair_value": fair, "fair_value_conf"' in b and '"fair_value_note": fv_note' in b,
      "٦ والترويسةُ تحمل الرقمَ وثقتَه وسببَ حجبه أو وسمه")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check("t = target_from(ov, res)" in mk, "٧ وصفحةُ السهم تبني هدفَها بالصيغة نفسِها")
doc = (ROOT / "frontend/src/components/reports/CompanyReportDocument.tsx").read_text(encoding="utf-8")
check('"السعر العادل اليوم"' in doc and '"ثقة التقدير"' in doc and "k.sub &&" in doc,
      "٨ وورقةُ التقرير تعرض السعرَ العادل اليوم وثقتَه وسببَه")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
