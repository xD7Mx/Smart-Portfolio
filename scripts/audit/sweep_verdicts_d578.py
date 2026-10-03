#!/usr/bin/env python3
"""حارسُ D578: مسحةُ السوق اليومية تكتب حكمَها للفرز — فلا تبقى شركةٌ بلا قرار لأنّ صفحتَها لم تُفتح.

    python3 scripts/audit/sweep_verdicts_d578.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import lastgood
from app.services.market_valuation_sweep import record_verdicts
T = date(2026, 10, 3)
lastgood.save("governance:deep", {
    "1120": {"decision": {"label": "شراء"}, "at": "2026-10-01", "quality": 80},        # حكمُ صفحةٍ حديث
    "2222": {"decision": {"label": "انتظار"}, "at": "2026-09-20", "red_lines": 0},     # أقدمُ من أسبوع
    "4001": {"decision": {"label": "شراء"}, "at": "2026-09-20"}})                       # والمسحةُ تمتنع
v = lambda lab, ev=True: {"_verdict": {"decision": {"label": lab}, "evaluable": ev, "quality": 60, "fair_value": 10.0}}
n = record_verdicts({"1120": v("تجنب"), "2222": v("شراء"), "4001": v("بيانات غير كافية", False),
                     "1010": v("انتظار"), "9999": {"_verdict": {"decision": None}}}, T)
s = lastgood.load("governance:deep")
check(s["1010"]["decision"]["label"] == "انتظار" and s["1010"]["source"] == "sweep", "١ شركةٌ بلا حكمٍ تأخذ حكمَ المسحة")
check(s["1120"]["decision"]["label"] == "شراء", "٢ حكمُ صفحةٍ حديث لا يُستبدل")
check(s["2222"]["decision"]["label"] == "شراء" and s["2222"]["red_lines"] == 0, "٣ حكمٌ أقدمُ من أسبوع يُجدَّد وتبقى حقولُه")
check(s["4001"]["decision"]["label"] == "شراء", "٤ امتناعُ المسحة لا يمحو حكماً عميقاً حديثاً")
check("9999" not in s and n == 2, "٥ لا حكمَ لا يُكتب", str(n))
src = (ROOT / "backend/app/services/market_valuation_sweep.py").read_text()
check('if kk != "_verdict"' in src and "rep_verdicts = record_verdicts(done)" in src, "٦ المسحةُ تكتب الأحكام ولا تُلوّث مخزن الأساسيات")
sys.exit(fail)
