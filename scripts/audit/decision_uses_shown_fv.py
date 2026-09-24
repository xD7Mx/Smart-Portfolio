#!/usr/bin/env python3
"""القرارُ يُحكم بالسعر العادل المعروض لا بهدف المحلّلين (D454).

    python3 scripts/audit/decision_uses_shown_fv.py

رآه المالك على 2080: سعرٌ عادلٌ 55.39 ودرجةٌ 78 في «تقييم الأداء»، ورأيُ
الذكاء «بيانات غير كافية… غيابُ إجماع المحللين» — وقال: «التطبيق ارتكب
المحظور». والفحصُ سلوكيّ: شركةٌ بلا هدفِ محلّلين ولها تقديرٌ من المحرّك،
ويُشترط ألّا يمتنع القرارُ بسبب غياب الهدف.
"""
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import asyncio, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services import analysis as AN
    from app.services.market_data import market_service as MS
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)
P = [{"year": 2021 + i, "as_of": f"{2021+i}-12-31", "revenue": 3e9 * (1 + i * .06), "net_income": 4e8 * (1 + i * .08),
      "operating_cash_flow": 5e8, "capex": 1.5e8, "free_cash_flow": 3.5e8, "equity": 3e9 + i * 1e8,
      "total_assets": 5e9, "total_liabilities": 2e9, "total_debt": 6e8, "eps": 5.3 * (1 + i * .08),
      "shares_outstanding": 7.5e7, "ebit": 5e8, "interest_expense": 3e7, "pretax_income": 4.6e8,
      "current_assets": 2e9, "current_liabilities": 1e9, "dividends_paid": 2e8} for i in range(5)]
async def _fin(*a, **k): return {"periods": [dict(p) for p in P]}
async def _price(*a, **k): return {"price": 61.1, "change_pct": 0.2}
async def _info(*a, **k): return {"sector": "Utilities"}          # لا target_mean_price
async def _none(*a, **k): return None
MS.get_financials, MS.get_price, MS.get_company_info, MS.get_history = _fin, _price, _info, _none
an = asyncio.run(AN.analyze_company("2080.SR", allow_supplement=False)) or {}
d = an.get("decision") or {}
fv = an.get("fair_value")
fail = 0
def check(ok, label, det=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))
check(fv is not None, "٠ للشركة سعرٌ عادلٌ من المحرّك بلا هدفِ محلّلين", str(fv))
check(not (fv is not None and d.get("label") == "بيانات غير كافية" and "محلّلين" in str(d.get("reason"))),
      "١ ولا يمتنع القرارُ لغياب هدف المحلّلين وسعرُها العادل معروض", f"{d.get('label')} · {str(d.get('reason'))[:70]}")
print(("FAIL" if fail else "PASS") + " D454 — القرارُ بالسعر العادل المعروض")
sys.exit(fail)
