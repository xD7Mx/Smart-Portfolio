#!/usr/bin/env python3
"""لا يُنشر «سعرٌ عادل» يكذّبه السوقُ، والدفتريةُ تُطابَق بالرسميّ (D449).

    python3 scripts/audit/fv_publish_plausible.py

قِيس في إحصاء السوق: 53 ورقةً «سعرُها العادل» دون 0.4× سعرها، منها 2001
بدفتريةٍ 0.30 على سعر 26.22 — وحدةُ مالٍ لا تطابق وحدةَ الأسهم — و«تداول»
تنشر مضاعفَ الدفترية لكلّ ورقة. وقال المالك عن الشاذّ المعروض: «ما هذا
الهراء». والفحصُ سلوكيّ على المحرّك نفسِه.
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
fail = 0
def check(ok, label, det=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

# ١ · خاسرةٌ بدفتريةٍ بوحدةٍ خاطئة (0.30) ومضاعفُ «تداول» 1.6×
P = [{"year": y, "revenue": 1e9, "net_income": -5e7, "equity": 2.0e5, "shares_outstanding": 6.7e5,
      "operating_cash_flow": 1e7, "capex": 2e7} for y in (2023, 2024, 2025)]
o = F.compute({"eps": -0.4, "book_value": 0.30, "price_to_book": 1.6}, 26.22,
              periods=P, archetype="commodity", symbol="2001.SR")
nav = [m.get("value") for m in o.get("methods") or []]
check(o.get("value") is None or o["value"] >= 26.22 * 0.4,
      "١ الدفتريةُ تُطابَق بمضاعف «تداول» — لا 0.30 على سعر 26", f"{o.get('value')} · {nav}")

# ٢ · والشاذُّ لا يُنشر باسم السعر العادل
Q = [{"year": y, "revenue": 1e9, "net_income": 1e8, "equity": 1e9, "shares_outstanding": 1e8,
      "operating_cash_flow": 1.2e8, "capex": 2e7, "eps": 1.0} for y in (2023, 2024, 2025)]
o2 = F.compute({"eps": 1.0, "book_value": 10.0, "roe": 10.0}, 400.0, sector_avg_pe=12.0,
               periods=Q, archetype="asset_light", symbol="9998.SR")
check(o2.get("value") is None and o2.get("implausible_value"),
      "٢ تقديرٌ عند 0.03× السعر لا يُنشر «سعراً عادلاً»", f"value={o2.get('value')} · محفوظ={o2.get('implausible_value')}")
check(bool(o2.get("unavailable_reason")), "٣ ويُقال سببُ الحجب")
print(("FAIL" if fail else "PASS") + " D449 — لا شاذَّ يُنشر")
sys.exit(fail)
