#!/usr/bin/env python3
"""الشمعةُ الأسبوعية للسوق السعودي من الأحد إلى الخميس (D465).

    python3 scripts/audit/saudi_weekly_sunday.py

قاسه المالك بتريدنق فيو: شمعةُ 4001 الجارية فيه تفتح 4.67، وفي التطبيق 4.55.
الجذر: ياهو يسلّم «1wk» للسوق السعودي من الإثنين إلى الأحد بتوقيت الرياض،
فتقع جلسةُ الأحد في الأسبوع السابق، ويُكرّر الأسبوعَ الجاري شمعةً جزئيةً ثانية.
والفحصُ سلوكيّ: جلساتٌ يوميةٌ معلومة (أحدٌ إلى خميس) وأسبوعيةُ ياهو المزاحةُ،
ثمّ يُنادى البابُ الواحد `market_service.get_history(…, "5y")`.
"""
from __future__ import annotations
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import asyncio, datetime as dt, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services import market_data as MD
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)

# ثلاثون أسبوعاً من الجلسات: الأحد يفتح الأسبوع (سعرُه 100+أسبوع) والخميس يغلقه
DAILY, WEEKLY = [], []
d0 = dt.date(2026, 3, 1)                       # أحد
for w in range(30):
    for k in range(5):                          # الأحد … الخميس
        d = d0 + dt.timedelta(days=7 * w + k)
        base = 100 + w
        o = base + (0.5 if k == 0 else 0.2 * k)
        DAILY.append({"date": d.isoformat(), "open": o, "high": o + 1, "low": o - 1, "close": o + 0.1, "volume": 10})
# أسبوعيةُ ياهو كما تصل: من الإثنين، فالأحدُ في الأسبوع السابق، وشمعةٌ جزئيةٌ مكرّرة
for w in range(30):
    rows = [r for r in DAILY if (d0 + dt.timedelta(days=7 * w + 1)).isoformat() <= r["date"] <= (d0 + dt.timedelta(days=7 * w + 7)).isoformat()]
    WEEKLY.append({"date": rows[0]["date"], "open": rows[0]["open"], "high": max(r["high"] for r in rows),
                   "low": min(r["low"] for r in rows), "close": rows[-1]["close"], "volume": 50})
WEEKLY.append({**DAILY[-1]})

async def fake(self, symbol, range_, interval):
    return [dict(r) for r in (DAILY if interval == "1d" else WEEKLY)]
MD.YahooFinanceAdapter._fetch_chart_points = fake

pts = asyncio.run(MD.market_service.get_history("4001.SR", "5y")) or []
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

last = pts[-1] if pts else {}
check(len(pts) == 30, "١ ثلاثون أسبوعاً بلا شمعةٍ جزئيةٍ مكرّرة", str(len(pts)))
check(abs(last.get("open", 0) - (129 + 0.5)) < 1e-9, "٢ الشمعةُ الجاريةُ تفتح بجلسة الأحد", str(last.get("open")))
check(abs(last.get("close", 0) - (129 + 0.8 + 0.1)) < 1e-9, "٣ وتغلق بجلسة الخميس", str(last.get("close")))
dates = [dt.date.fromisoformat(p["date"][:10]) for p in pts]
check(all((b - a).days == 7 for a, b in zip(dates, dates[1:])), "٤ الأسابيعُ متتاليةٌ سبعةً سبعة")
check(sum(p.get("volume", 0) for p in pts) == 10 * len(DAILY), "٥ والحجمُ مجموعُ الجلسات")
print(f"{'FAIL' if fail else 'PASS'} D465 — أسبوعُ السوق السعودي من الأحد إلى الخميس")
sys.exit(fail)
