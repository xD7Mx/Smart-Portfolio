#!/usr/bin/env python3
"""أوزانُ الترجيح من مواصفة النمط لا وزنٌ واحدٌ للجميع (D455).

    python3 scripts/audit/sector_weights_applied.py

سأل المالك: «هل يُعقل أن يكون السعرُ العادل لأرامكو 16 والمحللون 30؟».
وقِيس بكاشف `fv_paths.py`: المساراتُ 18.56 خصماً · 12.97 دخلاً متبقّياً ·
39.22 مضاعفاً — والمضاعفُ مستبعَدٌ «شاهداً أضعف»، والترجيحُ وزنٌ واحدٌ لتسعة
أنماط (خصم 0.45). ومواصفةُ السلعيّ: مضاعفٌ 0.45 · خصمٌ 0.30 · متبقٍّ 0.25.
والفحصُ سلوكيّ بأرقام أرامكو كما قِيست.
"""
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services import fair_value as F
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)
P = [{"year": y, "revenue": r, "net_income": ni, "operating_cash_flow": o, "capex": -c, "total_debt": d,
      "shares_outstanding": sh, "eps": e, "equity": 1.45e12, "dividends_paid": -3.1e11}
     for y, r, ni, o, c, d, sh, e in ((2023, 1.653e12, 4.548e11, 5.378e11, 1.583e11, 2.9e11, 2.4193e11, 1.87),
                                      (2024, 1.637e12, 3.984e11, 5.089e11, 1.889e11, 3.19e11, 2.4189e11, 1.63),
                                      (2025, 1.559e12, 3.502e11, 5.108e11, 1.904e11, 3.636e11, 2.4188e11, 1.44))]
o = F.compute({"eps": 1.45, "beta": 0.006}, 25.64, sector_avg_pe=27.05, periods=P,
              archetype="commodity", symbol="2222.SR")
w = o.get("weighting") or {}
fail = 0
def check(ok, label, det=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))
check(w.get("مضاعف القطاع") == "45%", "١ السلعيُّ يُرجَّح بمواصفته: المضاعفُ 45٪", str(w))
check(not o.get("excluded"), "٢ ولا يُستبعَد مضاعفُ القطاع وهو العدسةُ الأولى في نمطه", str(o.get("excluded"))[:60])
check(o.get("value") and o["value"] > 20, "٣ فلا يخرج تقديرُ أرامكو 16 ومساراتُه 18.6/13/39", str(o.get("value")))
# ‏D457: نمطٌ بلا خصمٍ في مواصفته (المطوّرُ العقاريّ) لا يسقط بـKeyError
try:
    o2 = F.compute({"eps": 1.45, "beta": 0.9}, 25.64, sector_avg_pe=18.0, periods=P,
                   archetype="re_developer", symbol="4020.SR")
    check(True, "٤ ونمطٌ بلا خصمٍ في مواصفته يُقيَّم ولا يسقط", str(o2.get("value")))
except Exception as e:                                            # noqa: BLE001
    check(False, "٤ ونمطٌ بلا خصمٍ في مواصفته يُقيَّم ولا يسقط", f"{type(e).__name__}: {e}")
print(("FAIL" if fail else "PASS") + " D455 — أوزانُ القطاع من مواصفته")
sys.exit(fail)
