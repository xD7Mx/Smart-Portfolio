#!/usr/bin/env python3
"""التدقيقُ لا يشتقّ رقماً للسهم من عددٍ بالآلاف (D445).

    python3 scripts/audit/audit_shares_unit.py

قِيس في إحصاء السوق: سبعُ أوراقٍ «سعرُها العادل» 250–1400 ضعفَ سعرها
(1050: ‏17,717 على 21.18). وسببُها بكاشف `fv_paths_absurd.py`: عددُ الأسهم
في الإفصاح بالآلاف في كلّ سنة، فيشتقّ التدقيقُ ربحيةَ سهمٍ 2,159 بدل 2.00
ويعتمدها. والفحصُ سلوكيّ على أرقام 1050 كما قِيست.
"""
from __future__ import annotations
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services.data_quality import audit
    from app.services import fair_value as F
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)
fail = 0
def check(ok, label, det=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

# كما قِيست لـ1050: عددٌ بالآلاف ووسمُ الدمج (‏1096×).
P = [{"year": y, "net_income": ni, "equity": 5.07e10, "eps": e,
      "shares_outstanding": sh, "shares_mismatch": 1096.0}
     for y, ni, e, sh in ((2023, 4.22e9, 1.61, 2487249.0), (2024, 4.54e9, 1.72, 2483025.0),
                          (2025, 5.35e9, 1.97, 2479514.0))]
q = audit({"eps": 2.00, "book_value": 17.56, "roe": 11.4}, P)
v = q["values"]
check(v.get("eps") == 2.00, "١ ربحيةُ السهم تبقى 2.00 ولا تصير 2,159", str(v.get("eps")))
check(v.get("book_value") == 17.56, "٢ والدفتريةُ 17.56 لا 20,431", str(v.get("book_value")))

# وبلا وسمٍ من الدمج: فارقُ مئةِ ضعفٍ خطأُ وحدةٍ لا تصحيح.
P2 = [{**p, "shares_mismatch": None} for p in P]
v2 = audit({"eps": 2.00, "book_value": 17.56}, P2)["values"]
check(v2.get("eps") == 2.00, "٣ وبلا وسم: فارقُ ألفِ ضعفٍ لا يستبدل الملخَّص", str(v2.get("eps")))

out = F.compute(v, 21.18, sector_avg_pe=11.0, periods=P, archetype="bank", symbol="1050.SR")
val = out.get("value")
check(val is None or val <= 21.18 * 10, "٤ ولا «سعرٌ عادل» ألفَ ضعف من المسار نفسِه", str(val))
print(("FAIL" if fail else "PASS") + " D445 — التدقيقُ ووحدةُ الأسهم")
sys.exit(fail)
