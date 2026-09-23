#!/usr/bin/env python3
"""عددُ أسهمٍ بالآلاف لا يصنع «سعراً عادلاً» ألفَ ضعف (D439).

    python3 scripts/audit/fv_shares_unit.py

رآه المالك على البحري 4030: «السعر العادل 58,303.18 · ‎+163,949٪» على سعر
‎35.54. وقِيس بكاشف `fv_paths_4030.py`: مسارٌ واحدٌ ناجٍ هو «نموٌّ دائم
(دفترية وتوزيع)»، ودفتريتُه للسهم ‎11,660 = حقوق ‎11.35 مليار ÷ ‎973,182
سهماً — عددٌ بالآلاف في أحدث ربع. فالفحصُ سلوكيّ: تُمرَّر قوائمُ بهذا
الشكل إلى المحرّك، ويُشترط ألّا يخرج مسارٌ ولا قيمةٌ فوق عشرة أضعاف السعر.
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
    from app.services import fair_value as F
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)

fail = 0
def check(ok, label, detail=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))

P = [
 {"year": 2023, "revenue": 8.78e9, "net_income": 1.79e9, "operating_cash_flow": 3.56e9,
  "capex": 1.64e9, "equity": 9.0e9, "total_debt": 8.36e9, "shares_outstanding": 738281.0,
  "eps": 2.19, "dividends_paid": 0.9e9},
 {"year": 2024, "revenue": 9.48e9, "net_income": 2.39e9, "operating_cash_flow": 3.41e9,
  "capex": 5.47e9, "equity": 10.2e9, "total_debt": 9.72e9, "shares_outstanding": 1015234468.0,
  "eps": 2.35, "dividends_paid": 1.0e9},
 {"year": 2025, "revenue": 10.35e9, "net_income": 2.56e9, "operating_cash_flow": 3.21e9,
  "capex": 4.24e9, "equity": 11.35e9, "total_debt": 12.2e9, "shares_outstanding": 973182129.0,
  "eps": 2.63, "dividends_paid": 1.1e9},
]
LQ = {"as_of": "2026-06-30", "equity": 11.35e9, "shares_outstanding": 973182.0}
price = 35.54
out = F.compute({"trailingEps": 2.63, "returnOnEquity": 0.1676, "dividendRate": 1.1},
                price, sector_avg_pe=12.0, periods=P, latest_quarter=LQ,
                archetype="industrial", symbol="4030.SR", asof="2026-06-30")
vals = [m.get("value") for m in out.get("methods") or [] if m.get("value")]
v = out.get("value")
check(all(x <= price * 10 for x in vals), "١ لا مسارَ يخرج عشرةَ أضعاف السعر من عددٍ بالآلاف",
      str([round(x, 2) for x in vals]))
check(v is None or v <= price * 10, "٢ ولا «سعرٌ عادل» معروضٌ بهذا الشذوذ", str(v))
print(("FAIL" if fail else "PASS") + " D439 — وحدةُ عدد الأسهم")
sys.exit(fail)
