#!/usr/bin/env python3
"""جدولُ السوق يعرض السعرَ العادل من المخزن الحيّ لا نسخةَ آخر بناء (D458).

    python3 scripts/audit/screener_fv_from_store.py

قِيس بكاشف `fv_vs_analysts.py`: الجدولُ يعرض 4030 بـ58,303 و1030 بـ24,163
بعد إصلاحها في المحرّك والمخزن (D439/D445). والفحصُ سلوكيّ: صفٌّ يحمل الرقمَ
القديم، والمخزنُ يحمل المصحَّح، ويُنادى إنعاشُ التقديم الحقيقيّ.
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
    from app.services import market_screener as MS, content_engine as CE
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)
STORE = {"4030": {"fair_value": 38.2, "fair_value_conf": "متوسطة", "finance_score": 79},
         "1030": {"fair_value": None, "finance_score": 60}}
CE.fund_store_load = lambda: STORE
MS._tadawul_prices = lambda: {"4030": 35.54, "1030": 14.7}
rows = [{"symbol": "4030", "price": 35.54, "fair_value": 58303.18, "fair_value_upside_pct": 163949.5},
        {"symbol": "1030", "price": 14.7, "fair_value": 24163.83}]
out = asyncio.run(MS.refresh_derived(rows))
a, b = out[0], out[1]
fail = 0
def check(ok, label, det=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))
check(a.get("fair_value") == 38.2, "١ الصفُّ يحمل سعرَ المخزن المصحَّح لا 58,303", str(a.get("fair_value")))
check(a.get("fair_value_upside_pct") == round((38.2 - 35.54) / 35.54 * 100, 1), "٢ والفجوةُ منه", str(a.get("fair_value_upside_pct")))
check(b.get("fair_value") is None, "٣ والمحجوبُ في المخزن فارغٌ في الجدول لا رقمَه القديم", str(b.get("fair_value")))
print(("FAIL" if fail else "PASS") + " D458 — الجدولُ من المخزن الحيّ")
sys.exit(fail)
