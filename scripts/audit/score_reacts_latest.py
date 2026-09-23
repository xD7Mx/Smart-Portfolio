#!/usr/bin/env python3
"""درجةُ الجودة تتفاعل مع آخر النتائج لا مع آخر سنويٍّ وحده (D450).

    python3 scripts/audit/score_reacts_latest.py

قال المالك: «أريد الدرجةَ ذكيةً وتتفاعل حسب آخر النتائج». وقِيس أنّ الدرجةَ
تُبنى من السلسلة السنوية وحدَها — فربعٌ خاسرٌ لا يمسّها حتى السنويّ التالي،
مع أنّ آخرَ اثني عشرَ شهراً محسوبةٌ مُتحقَّقاً منها (`_ttm_from`).

والفحصُ سلوكيّ: شركةٌ سنواتُها رابحة، وآخرُ اثني عشرَ شهراً خسارةٌ وتدفّقٌ
سالب، ويُنادى بناءُ الدرجة الحقيقيّ مرّتين — ويُشترط أن تهبط الدرجة.
"""
from __future__ import annotations
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

P = [{"year": y, "as_of": f"{y}-12-31", "revenue": 2e9 * (1 + i * .08), "net_income": 3e8 * (1 + i * .1),
      "operating_cash_flow": 3.6e8, "capex": 8e7, "free_cash_flow": 2.8e8, "equity": 2.5e9,
      "total_assets": 4e9, "total_liabilities": 1.5e9, "total_debt": 5e8, "eps": 1.5,
      "shares_outstanding": 2e8, "ebit": 3.8e8, "interest_expense": 2e7, "pretax_income": 3.3e8,
      "current_assets": 1.5e9, "current_liabilities": 8e8, "dividends_paid": 1e8}
     for i, y in enumerate((2022, 2023, 2024, 2025))]
TTM = {"as_of": "2026-06-30", "revenue": 1.6e9, "net_income": -2.5e8, "operating_cash_flow": -1.5e8,
       "capex": 9e7, "free_cash_flow": -2.4e8, "pretax_income": -2.4e8, "ebit": -2.1e8,
       "equity": 2.2e9, "total_debt": 1.4e9}
mode = {"ttm": None}
async def _fin(*a, **k): return {"periods": [dict(p) for p in P], "ttm": mode["ttm"]}
MS.get_financials = _fin

async def run():
    r = await AN._financial_from_statements("4444.SR", sector="المواد الأساسية", info={}, allow_supplement=False)
    return (r or {}).get("score")
s0 = asyncio.run(run())
mode["ttm"] = TTM
s1 = asyncio.run(run())
fail = 0
def check(ok, label, det=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))
check(isinstance(s0, (int, float)) and isinstance(s1, (int, float)) and s1 < s0 - 3,
      "١ خسارةُ آخر اثني عشرَ شهراً تُهبط درجةَ الجودة", f"بلا آخر النتائج {s0} · معها {s1}")
p2 = AN.with_ttm([dict(p) for p in P], {"unverified": True})
check(len(p2) == len(P) and not p2[-1].get("ttm"), "٢ والاثنا عشرَ غيرُ المُتحقَّق منها لا تدخل")
print(("FAIL" if fail else "PASS") + " D450 — الدرجةُ تتفاعل مع آخر النتائج")
sys.exit(fail)
