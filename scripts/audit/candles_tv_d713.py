#!/usr/bin/env python3
"""حارسُ D713 — شموعُ الرسم كتريدنق فيو (بلاغُ المالك: «الشموعُ يومٌ وأسبوعٌ وشهر لكنّها ليست حقيقية مثل تريدنق فيو»).

قِيس على الخادم (‏bars_real_door · run 38595783271): اليوميُّ حقيقيٌّ ويطابق جلسةَ «تداول» (أرامكو: افتتاح 25.70 · أعلى 25.72 · أدنى
25.38 · إغلاق 25.38)، لكنّ الشهريَّ من ياهو مؤرَّخٌ بتاريخ UTC لمنتصف ليل الرياض — فيقع الشهرُ في آخر يومٍ من سابقه، ويُلحق ياهو
يومَ اليوم نقطةً مستقلّة فينقسم الشهرُ الجاري شمعتين (الراجحي: «2026-09-30» لأكتوبر حتى الأمس ثمّ «2026-10-14» يومُ اليوم)؛
والأسبوعيُّ مؤرَّخٌ بآخر أيّامه؛ والشمعةُ الجاريةُ تتجمّد بذاكرة يوم. فالحارسُ يمنع العودة سلوكاً:

    python3 scripts/audit/candles_tv_d713.py
"""
import os, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from datetime import datetime, timezone, timedelta

fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import market_data as M

need = [n for n in ("riyadh_months", "week_start", "live_tail") if not hasattr(M, n)]
if need:
    check(False, "٠ أدواتُ شموع تريدنق فيو موجودة", ", ".join(need))
    print("\nالنتيجة: عطب ✖")
    sys.exit(1)

R = timezone(timedelta(hours=3))
ts = lambda *a: int(datetime(*a, tzinfo=R).timestamp())           # noqa: E731
# نقاطُ ياهو الشهرية للراجحي كما قِيست: الشهرُ عند منتصف ليل الرياض، ويومُ اليوم نقطةٌ مستقلّة
pts = [{"date": "2026-08-31", "time": ts(2026, 9, 1), "open": 67.5, "high": 68.05, "low": 63.15, "close": 63.3},
       {"date": "2026-09-30", "time": ts(2026, 10, 1), "open": 63.35, "high": 64.7, "low": 61.8, "close": 62.1},
       {"date": "2026-10-14", "time": ts(2026, 10, 14, 15), "open": 62.1, "high": 62.1, "low": 60.85, "close": 60.85}]
m = M.riyadh_months(pts)
check([r["date"] for r in m] == ["2026-09-01", "2026-10-01"] and m[-1]["open"] == 63.35 and m[-1]["low"] == 60.85
      and m[-1]["close"] == 60.85 and m[-1]["high"] == 64.7,
      "١ الشهرُ شمعةٌ واحدةٌ بتقويم الرياض مؤرَّخةٌ بأوّل يومه — لا في آخر يوم الشهر السابق، ولا ينقسم الجاري شمعتين",
      str([(r["date"], r["open"], r["high"], r["low"], r["close"]) for r in m]))
w = M.week_start([{"date": "2026-10-08", "open": 1, "high": 2, "low": 0.5, "close": 1.5},
                  {"date": "2026-10-14", "open": 1, "high": 2, "low": 0.5, "close": 1.5}])
check([r["date"] for r in w] == ["2026-10-04", "2026-10-11"], "٢ والأسبوعُ مؤرَّخٌ بأوّل أسبوع التداول (الأحد) كتريدنق فيو",
      str([r["date"] for r in w]))
snap = {"price": 25.38, "day_high": 25.72, "day_low": 25.38, "day_open": 25.7, "volume": 10}
d1 = M.live_tail([{"date": "2026-10-13", "open": 25.76, "high": 25.86, "low": 25.66, "close": 25.78}], snap, "2026-10-14", "1d")
d2 = M.live_tail([{"date": "2026-10-14", "open": 25.0, "high": 25.1, "low": 24.9, "close": 25.0}], snap, "2026-10-14", "1d")
check(len(d1) == 2 and d1[-1] == {"date": "2026-10-14", "open": 25.7, "high": 25.72, "low": 25.38, "close": 25.38, "volume": 10}
      and d2[-1]["open"] == 25.7 and d2[-1]["close"] == 25.38 and d2[-1]["high"] == 25.72,
      "٣ والشمعةُ اليوميةُ الجاريةُ هي جلسةُ «تداول» الرسمية — تُفتح إن غابت وتُكتب إن تقادمت", str(d1[-1]))
wk = M.live_tail([{"date": "2026-10-11", "open": 25.62, "high": 25.7, "low": 25.5, "close": 25.6}], snap, "2026-10-14", "1wk")
mo = M.live_tail([{"date": "2026-10-01", "open": 25.2, "high": 26.04, "low": 25.12, "close": 25.78}], snap, "2026-10-14", "1mo")
check(wk[-1]["high"] == 25.72 and wk[-1]["low"] == 25.38 and wk[-1]["close"] == 25.38 and wk[-1]["open"] == 25.62
      and mo[-1]["high"] == 26.04 and mo[-1]["low"] == 25.12 and mo[-1]["close"] == 25.38 and len(mo) == 1,
      "٤ والأسبوعُ والشهرُ الجاريان يمتدّان بأعلى الجلسة وأدناها ويُغلقان بسعرها — ولا يُمسّ افتتاحُهما", f"{wk[-1]} · {mo[-1]}")
src = open(os.path.join(ROOT, "backend/app/services/market_data.py"), encoding="utf-8").read()
check("riyadh_months(await self._fetch_chart_points(symbol, \"10y\", \"1mo\"))" in src
      and "week_start(await self.get_history(symbol, \"5y\")" in src and "rows = live_tail(rows, snap, day, tf)" in src
      and "return week_start(rows) if tf == \"1wk\" else rows" in src,
      "٥ وبابُ الرسم يستعملها: شهرُ الأسهم بتقويم الرياض، وأسبوعُ الأسهم وتاسي بأوّله، والجاريةُ من جلسة «تداول»")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
