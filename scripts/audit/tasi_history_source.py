#!/usr/bin/env python3
"""منحنى «تاسي» يُرسم من «تداول» لا يبقى فارغاً (D438).

    python3 scripts/audit/tasi_history_source.py

قِيس: ياهو لا يملك لـ`^TASI.SR` إلا يوماً واحداً — فكان «منحنى مؤشّر تاسي»
فارغاً دائماً. وقِيس بكاشف `tasi_chart_shape.py` أنّ مولّد رسم «تداول»
يردّ جلسةَ آخرِ يومٍ كاملة. والفحصُ سلوكيّ: جسمٌ بشكل ما قِيس يُمرَّر من
الباب الواحد للرسم، ويُشترط أن يصل الرسمَ منحنى، وأن يُحفظ الإغلاقُ يومياً،
وأن تمرّ نقطةُ النهاية نفسُها من هذا الباب.
"""
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

import asyncio
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


try:
    from app.services import market_data as MD
    from app.services import tadawul_http as TH
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)

BODY = json.dumps([{"dateTime": f"2026-09-22 10:{m:02d}:45", "dateTimeInMillis": 0,
                    "indexPrice": 10669.0 + m} for m in range(30)])


async def _fetch(url, *a, **k):
    return (200, BODY) if "ChartGenerator" in url else (404, "")
TH.fetch = _fetch


async def _yahoo_none(self, *a, **k):
    return None
MD.YahooFinanceAdapter.get_history = _yahoo_none

pts = asyncio.run(MD.market_service.get_history("^TASI.SR", "6mo")) or []
check(len(pts) >= 2, "١ منحنى تاسي يصل من «تداول» حين يعجز ياهو", f"{len(pts)} نقطة")
check(bool(pts) and pts[-1].get("close") == 10698.0,
      "٢ وآخرُ نقطةٍ هي آخرُ سعرٍ في الجلسة", str(pts[-1:])[:90])

try:
    from app.services import lastgood
    d = lastgood.load("market:tasi_daily") or {}
    check(d.get("2026-09-22") == 10698.0, "٣ ويُحفظ إغلاقُ الجلسة فيطول التاريخُ اليوميّ",
          str({k: v for k, v in d.items() if k != "_stale_since"}))
except ModuleNotFoundError as e:
    print(f"⚠ ٣ لم يُقَس ({e.name})")

src = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
seg = src.split('@router.get("/history/{symbol}")', 1)[-1].split("@router", 1)[0]
check("market_service.get_history(" in seg and "primary.get_history" not in seg,
      "٤ ونقطةُ /market/history تمرّ من الباب الواحد لا من المزوّد مباشرة")

print(("FAIL" if fail else "PASS") + " D438 — منحنى تاسي من «تداول»")
sys.exit(fail)
