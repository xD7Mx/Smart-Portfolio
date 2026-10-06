#!/usr/bin/env python3
"""حارسُ D609: سنواتُ الوصول إلى الهدف في مؤشرات المحفظة ومحفظة النجوم، والمستشارُ يخطّط للهدف في موعد المالك.

    python3 scripts/audit/goal_metrics_d609.py
"""
import pathlib, re, sys, math
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

g = (ROOT / "frontend/src/utils/goal.ts").read_text()
check("Math.log(target / current) / Math.log(1 + cagrPct / 100)" in g and "cagrPct <= 0) return null" in g,
      "١ سنواتُ الهدف = ln(الهدف ÷ الحاليّ) ÷ ln(1 + العائد) — ولا موعدَ بعائدٍ سالبٍ أو مجهول")
check(abs(math.log(1e6 / 4e5) / math.log(1.09) - 10.63) < 0.01, "٢ مثالٌ مقيس: 400 ألف بعائد 9٪ تبلغ المليون في 10.6 سنة")
pp = (ROOT / "frontend/src/pages/PortfolioPage.tsx").read_text()
check("yearsToGoal(goals.million.current, goals.million.target, m.cagr_pct)" in pp, "٣ مؤشراتُ المحفظة: الوصولُ إلى الهدف بالعائد المركّب نفسِه")
sp = (ROOT / "frontend/src/pages/StarsPage.tsx").read_text()
check("yearsToGoal(g.current, g.target, data.cagr)" in sp and "pm?.cagr_pct" in sp,
      "٤ مختبرُ الأبحاث: الوصولُ إلى الهدف بعائد السلّة مقابل عائد المحفظة (D612)")
ai = (ROOT / "backend/app/api/v1/endpoints/ai.py").read_text()
seg = ai.split('@router.get("/portfolio-autopilot/plan")')[1].split("@router")[0]
check("goal_plan(" in seg and "unified_cagr_pct" in seg and '"اشترِ الآن"' in seg, "٥ خطةُ المستشار بالعائد الموحّد، والضخُّ إلى ما اكتملت قناعتُه وحده")
ac = (ROOT / "frontend/src/components/governance/AutopilotCard.tsx").read_text()
check("<GoalPlan />" in ac and "autopilotPlan(years)" in ac, "٦ بطاقةُ المستشار: الهدفُ في موعدك (سنتان … عشر)")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
