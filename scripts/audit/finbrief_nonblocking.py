#!/usr/bin/env python3
"""خلاصةُ القوائم لا تنتظر النموذج (D447).

    python3 scripts/audit/finbrief_nonblocking.py

قِيس: القوائمُ في صفحة السهم تستغرق نحو خمس ثوانٍ في أوّل فتح، ونداءُ
النموذج في `financial_brief.brief` ينتظره الطلبُ كلُّه. والفحصُ سلوكيّ:
نموذجٌ مصطنعٌ يستغرق ثلاث ثوانٍ، ويُشترط أن تعود الخلاصةُ في أقلّ من
نصف ثانية، وأن يُكتب سطرُ النموذج في الخلفية للفتح التالي.
"""
from __future__ import annotations
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import asyncio, pathlib, sys, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services import financial_brief as B
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)

async def _slow(*a, **k):
    await asyncio.sleep(3)
    return "سطرُ النموذج."
B.ai_line = _slow
P = [{"year": 2023 + i, "revenue": 1e9 * (1 + i / 10), "net_income": 1e8 * (1 + i / 10),
      "operating_cash_flow": 1.2e8, "equity": 1e9, "total_debt": 2e8} for i in range(3)]

async def main():
    t = time.perf_counter()
    b1 = await B.brief(P, kind="annual", symbol="9999")
    dt = time.perf_counter() - t
    await asyncio.sleep(3.3)
    b2 = await B.brief(P, kind="annual", symbol="9999")
    return dt, b1, b2
dt, b1, b2 = asyncio.run(main())
fail = 0
def check(ok, label, det=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))
check(dt < 0.5, "١ الخلاصةُ تعود فوراً ولا تنتظر النموذج", f"{dt:.2f} ثانية")
check(bool(b1.get("line")), "٢ ولا تعود فارغة — القاعديُّ حاضر", str(b1.get("line"))[:60])
check(b2.get("by") == "جيمناي", "٣ وسطرُ النموذج يُكتب في الخلفية للفتح التالي", str(b2.get("by")))
print(("FAIL" if fail else "PASS") + " D447 — القوائمُ لا تنتظر النموذج")
sys.exit(fail)
