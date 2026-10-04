#!/usr/bin/env python3
"""حارسُ D593: سعرُ الريت العادل لا يكون صافيَ الأصول وحدَه بثقةٍ «مرتفعة» — بل متوسّطَه مع قيمة التوزيع،
وبثقةٍ «متوسطة»؛ فلا يَعُدّ المستشارُ الآليّ خصمَ السوق الدائمَ عن الصافي هامشَ أمان.

    python3 scripts/audit/reit_fv_d593.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

src = (ROOT / "backend/app/services/fair_value_models.py").read_text()
ana = (ROOT / "backend/app/services/analysis.py").read_text()
from app.services.fair_value_models import reit_blend
# الرياض ريت كما قِيس: سعر 4.46 وصافي 9.41 — بتوزيعٍ 0.40 وعائدِ أقرانٍ 8٪ تكون قيمةُ التوزيع 5.00
fv, inc = reit_blend(9.41, 0.40, 8.0)
check(abs(inc - 5.0) < 1e-9, "١ قيمةُ التوزيع = توزيعُ السنة ÷ وسيطِ عائد الأقران", f"{inc}")
check(abs(fv - 7.205) < 1e-9, "٢ والسعرُ العادل متوسّطُ الصافي وقيمةِ التوزيع — لا الصافي وحدَه", f"{fv}")
fv2, inc2 = reit_blend(9.41, None, 8.0)
check(fv2 == 9.41 and inc2 is None, "٣ وبلا توزيعٍ معروف يبقى الصافي — لا يُختلق توزيع")
check('"confidence": "مرتفعة", "implausible": False' not in ana, "٤ ولا ثقةَ «مرتفعة» تُفرض على الريت")
check('"uncertainty": "منخفض"' not in src.split("async def _reit_nav_value")[1].split("async def for_symbol")[0],
      "٥ ولا «عدمُ يقينٍ منخفض» في نتيجة الريت")
check("len(ys) >= 5" in src and "s == sym" in src, "٦ وعائدُ الأقران وسيطُ خمسةٍ فأكثر بلا الصندوق نفسِه")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
