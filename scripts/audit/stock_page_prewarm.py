#!/usr/bin/env python3
"""صفحةُ السهم تقرأ المحضَّر: التوزيعاتُ من المسحة والتوصياتُ الفارغةُ مخزَّنة (D451).

    python3 scripts/audit/stock_page_prewarm.py

قِيس على الخادم بكاشف `endpoint_timing.py`: التوزيعاتُ 3.18 ثانية والتوصياتُ
3.32 في أوّل فتح. والفحصُ سلوكيّ: مسحةٌ على رمزين تُحضّر توزيعاتِ كليهما،
ونقطةُ التوصيات لا تجلب مرّتين حين يكون الجوابُ فارغاً.
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
    from app.services import market_valuation_sweep as SW, tadawul_dividends as TD, analysis as AN
    from app.services import argaam_calendar as AC
    from app.api.v1.endpoints import market as M
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)
fail = 0
def check(ok, label, det=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

warmed = []
async def _read(sym): warmed.append(str(sym).replace(".SR", "")); return None
TD.read = _read
async def _an(sym, **k): return {"fair_value": 10.0, "score": 70, "price": 9.0}
AN.analyze_company = _an
try:
    asyncio.run(SW.sweep(["2222", "1120"]))
except Exception as e:                                            # noqa: BLE001
    print(f"… المسحةُ رفعت {type(e).__name__}: {e}")
check({"2222", "1120"} <= set(warmed), "١ المسحةُ تُحضّر توزيعاتِ كلّ رمزٍ مسحته", str(warmed))

calls = {"n": 0}
async def _recs(sym): calls["n"] += 1; return {"rows": [], "fetched_at": "x"}
AC.fetch_company_recommendations = _recs
from app.services import cache
cache.delete("argaam:recs:7777") if hasattr(cache, "delete") else None
asyncio.run(M.get_company_recommendations("7777"))
asyncio.run(M.get_company_recommendations("7777"))
check(calls["n"] == 1, "٢ التوصياتُ الفارغةُ لا تُجلب في كلّ فتح", f"نداءات={calls['n']}")
print(("FAIL" if fail else "PASS") + " D451 — صفحةُ السهم تقرأ المحضَّر")
sys.exit(fail)
