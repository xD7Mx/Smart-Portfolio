#!/usr/bin/env python3
"""حارسُ D575: قرارُ الشركة واحدٌ في الفرز وصفحتِها — الفرزُ يقرأ آخرَ حكمٍ من المخزن العميق،
والامتناعُ يُكتب فيه أيضاً فلا يبقى «شراء» قديم.

    python3 scripts/audit/decision_sync_d575.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import lastgood
from app.services import market_screener as M
lastgood.save("governance:deep", {"2050": {"decision": {"label": "شراء"}}, "4340": {"decision": "بيانات غير كافية"}})
rows = [{"symbol": "2050", "decision": "انتظار"}, {"symbol": "4340.SR", "decision": "شراء"}, {"symbol": "1120", "decision": "شراء"}]
out = M.with_live_decisions(rows)
check(out[0]["decision"] == "شراء", "١ قرارُ الصفحة يغلب لقطةَ المسح", str(out[0]))
check(out[1]["decision"] == "بيانات غير كافية", "٢ الامتناعُ يصل الفرز (رمزٌ بلاحقة .SR)", str(out[1]))
check(out[2]["decision"] == "شراء" and rows[0]["decision"] == "انتظار", "٣ شركةٌ بلا حكمٍ عميق تبقى، والمدخلُ لا يُعدَّل")
lastgood.save("market:screener", rows)
got = M.get_cached_screener() or []
check(any(r["symbol"] == "2050" and r["decision"] == "شراء" for r in got), "٤ get_cached_screener يمرّ بالمزامنة")
src = (ROOT / "backend/app/services/analysis.py").read_text()
check("D575" in src and 'store[k] = {**store[k], "decision"' in src, "٥ الامتناعُ يُكتب في المخزن العميق")
sys.exit(fail)
