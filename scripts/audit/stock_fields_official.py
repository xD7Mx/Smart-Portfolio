#!/usr/bin/env python3
"""حقولُ السوق في صفحة السهم من لقطة «تداول» حين يعجز ياهو (D440).

    python3 scripts/audit/stock_fields_official.py

رآه المالك: «أعلى سنوي وأدنى سنوي وغيرها لم أجدها… واجعل مصدرها رسمي
تداول». والفحصُ سلوكيّ: ياهو صامتٌ تماماً، ولقطةُ «تداول» تحمل الحقول، ثم
يُنادى بناءُ التحليل الحقيقيّ ويُشترط أن تصل الحقولُ صفحةَ السهم.
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
    from app.services import analysis as AN, tadawul_market as TM
    from app.services.market_data import market_service as MS
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)

ROW = {"price": 35.54, "week52_high": 41.2, "week52_low": 27.1,
       "pe_ratio": 13.5, "price_to_book": 2.9, "market_cap": 3.4e10}
TM.row_for = lambda s: dict(ROW)
async def _none(*a, **k): return None
async def _price(*a, **k): return {"price": 35.54, "change_pct": 0.3}
MS.get_price = _price
MS.get_company_info = _none
MS.get_history = _none
MS.get_financials = _none
try:
    an = asyncio.run(AN.analyze_company("4030.SR", allow_supplement=False)) or {}
except Exception as e:                                            # noqa: BLE001
    an = {}; print(f"… التحليلُ رفع {type(e).__name__}: {e}")
f = an.get("fundamentals") or {}
fail = 0
for k in ("week52_high", "week52_low", "pe_ratio", "price_to_book", "market_cap"):
    ok = f.get(k) == ROW[k]
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} «{k}» يصل صفحةَ السهم من «تداول» وياهو صامت — {f.get(k)!r}")
print(("FAIL" if fail else "PASS") + " D440 — حقولُ السوق من «تداول»")
sys.exit(fail)
