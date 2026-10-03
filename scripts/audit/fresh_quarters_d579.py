#!/usr/bin/env python3
"""حارسُ D579: قائمةٌ ربعيةٌ رسميةٌ منشورة تنفي القِدَم، والدفعةُ الليلية تُعيد قراءةَ من شاخت قراءتُه.

    python3 scripts/audit/fresh_quarters_d579.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date, timedelta
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import tadawul_xbrl as X
today = date.today()
store = {"1810": {"as_of": (today - timedelta(days=10)).isoformat(), "annual": [], "quarterly": [{"as_of": "2026-06-30"}]},
         "2010": {"as_of": (today - timedelta(days=90)).isoformat(), "annual": [], "quarterly": []},
         "2222": {"as_of": (today - timedelta(days=60)).isoformat(), "annual": [], "quarterly": []}}
X._get = lambda s: store.get(s)
check(X.stale_symbols(["1810", "2010", "2222", "9999"], 45) == ["2010", "2222"], "١ من شاخت قراءتُه يُعاد، والأقدمُ أوّلاً")

from app.services.four_scores import build_company_features
periods = [{"year": y, "as_of": f"{y}-12-31", "revenue": 1000.0 + y, "net_income": 100.0, "total_assets": 5000.0,
            "total_equity": 2000.0, "operating_cash_flow": 120.0} for y in (2023, 2024, 2025)]
feats, _i, _q = build_company_features(periods, info={}, sector="Materials", symbol="1810")
check(str(feats.get("_asof"))[:10] == "2026-06-30", "٢ ربعُ يونيو المنشور يُقدِّم تاريخَ آخر قائمة", str(feats.get("_asof")))
feats2, _i, _q = build_company_features(periods, info={}, sector="Materials", symbol="2010")
check(str(feats2.get("_asof"))[:10] == "2025-12-31", "٣ بلا ربعٍ أحدث يبقى تاريخُ السنويّ", str(feats2.get("_asof")))
src = (ROOT / "backend/app/scheduler/scheduler.py").read_text()
check("due = stale_symbols(universe, 45)" in src, "٤ الدفعةُ الليلية تضمّ الشائخ")
sys.exit(fail)
