#!/usr/bin/env python3
"""حارسُ D595: الماليةُ التي توقّفت ملفّاتُ XBRL لها تُقيَّم من إعلان نتائجها المنشور بدل الامتناع —
سنةٌ من الفترة حتى تاريخه مُسنوَنة، والحقوقُ كما أُعلنت، ولا خانةَ مختلقة.

    python3 scripts/audit/fin_announce_d595.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services.fair_value_models import announcement_year
ra = {"as_of": "2026-06-30", "months": 6,
      "quarter": {"revenue": 300e6, "net_income": 40e6, "equity": 900e6, "eps": 0.8},
      "ytd": {"revenue": 580e6, "net_income": 75e6, "eps": 1.5}}
y = announcement_year(ra)
check(y and abs(y["net_income"] - 150e6) < 1, "١ ستّةُ أشهرٍ تُسنوَن: الربحُ × 2", str(y and y["net_income"]))
check(y and y["equity"] == 900e6, "٢ والحقوقُ كما أُعلنت لا تُسنوَن")
check(y and abs(y["eps"] - 3.0) < 1e-9 and abs(y["revenue"] - 1160e6) < 1, "٣ وربحيةُ السهم والإيرادُ مُسنوَنان")
check(y and "total_debt" not in y and "operating_cash_flow" not in y, "٤ ولا خانةَ لم يحملها الإعلان — لا دَينَ ولا تدفّقَ مختلق")
check(announcement_year({**ra, "quarter": {"net_income": 1}, "ytd": {"net_income": 1}}) is None,
      "٥ وبلا حقوقٍ معلنة لا سنة — لا تقييمَ بلا ميزانية")
check(announcement_year(None) is None and announcement_year({"as_of": "2026-06-30"}) is None, "٦ وبلا إعلانٍ أو أشهرٍ لا شيء")
q1 = announcement_year({"as_of": "2026-03-31", "months": 3, "quarter": {"net_income": 10e6, "equity": 5e8}, "ytd": {}})
check(q1 and abs(q1["net_income"] - 40e6) < 1, "٧ والربعُ الأوّل: الفترةُ هي الربع × 4")
src = (ROOT / "backend/app/services/fair_value_models.py").read_text()
check("stale > STALE_STOP and archetype_of(sym) in FIN_TYPES" in src, "٨ وللمالياتِ وحدَها — غيرُها يحتاج دَيناً ونقداً لا يحملهما الإعلان")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
