#!/usr/bin/env python3
"""حارسُ D605–D606: العائدُ المركّبُ واحدٌ بين المستشار والمؤشرات؛ والهدفُ في موعدٍ يحدّده المالك؛ وأيقونةُ الحقيبة.

    python3 scripts/audit/autopilot_goal_d606.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

ap = (ROOT / "backend/app/services/autopilot.py").read_text()
pe = (ROOT / "backend/app/api/v1/endpoints/portfolio.py").read_text()
check("unified_cagr_pct(db)" in ap and "unified_cagr_pct(db, net)" in pe and "compute_cagr_pct(db)" not in ap,
      "١ المستشارُ والمؤشراتُ المالية يقرآن العائدَ المركّب من دالّةٍ واحدة")
from app.services.autopilot import years_in, goal_plan
check(years_in("اريد الوصول للهدف خلال اربع سنوات") == 4 and years_in("في 5 سنين") == 5 and years_in("بعد سنتين") == 2
      and years_in("متى أصل؟") is None, "٢ الموعدُ يُفهم من كلام المالك (أربع · 5 · سنتين) ولا يُختلق")
p = goal_plan(400_000, 1_000_000, 4, 9.0)
check(abs(p["العائد_المطلوب_بلا_ضخ٪"] - 25.7) < 0.05, "٣ العائدُ المطلوبُ بلا ضخّ: (1,000,000 ÷ 400,000)^(1/4) − 1 = 25.7٪")
check(p["ما_تبلغه_بعائدك_الحالي"] == 564_633 and 7_500 < p["الضخ_الشهري_المطلوب"] < 7_800,
      "٤ وبعائده الحاليّ 9٪ يبلغ 564,633 — والضخُّ الشهريّ يسدّ الفجوة", str(p["الضخ_الشهري_المطلوب"]))
check("بالعائد وحده" in p["الحكم"], "٥ و25٪ سنوياً يُقال عنها «غير واقعيّ بالعائد وحده» — لا وعد")
check(goal_plan(1_100_000, 1_000_000, 4, 9.0)["الضخ_الشهري_المطلوب"] == 0, "٦ ومن بلغ هدفه لا يُطالَب بضخّ")
card = (ROOT / "frontend/src/components/governance/AutopilotCard.tsx").read_text()
check("Briefcase" in card and "Plane" not in card, "٧ أيقونةُ المستشار حقيبةُ أعمال لا طائرة")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
