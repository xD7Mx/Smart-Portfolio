#!/usr/bin/env python3
"""حارسُ D577: المضاعفاتُ التاريخية من سنوات الهيكل الحاليّ وحدَها — لا سنواتٍ قبل توزيع حصّةٍ أو تخفيض رأس مال،
ولا يُسقَط عددٌ بوحدة الآلاف (D503).

    python3 scripts/audit/hist_structure_d577.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services.fair_value_models import _same_company
# صافولا الحقيقية (كاشف morning_door)
sav = [{"as_of": "2021-12-31", "shares_outstanding": 943128571.0}, {"as_of": "2022-12-31", "shares_outstanding": 622219424.0},
       {"as_of": "2023-12-31", "shares_outstanding": 911168539.0}, {"as_of": "2024-12-31", "shares_outstanding": 945892713.0},
       {"as_of": "2025-12-31", "shares_outstanding": 300000000.0}]
k = _same_company(sav, 296681954.0)
check([p["as_of"] for p in k] == ["2025-12-31"], "١ صافولا: سنةُ الهيكل الحاليّ وحدَها", str([p["as_of"] for p in k]))
units = [{"as_of": "2023", "shares_outstanding": 300000.0}, {"as_of": "2024", "shares_outstanding": 300e6}, {"as_of": "2025", "shares_outstanding": None}]
check(len(_same_company(units, 300e6)) == 3, "٢ عددٌ بالآلاف وعددٌ غائب لا يُسقطان السنة")
src = (ROOT / "backend/app/services/fair_value_models.py").read_text()
check("for per in _same_company(annual[-5:], shares):" in src, "٣ المضاعفاتُ التاريخية تمرّ بمرشّح الهيكل")
sys.exit(fail)
