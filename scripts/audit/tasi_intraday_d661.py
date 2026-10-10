#!/usr/bin/env python3
"""حارسُ D661 (المالك 2026-10-10): «إطاراتُ الرسم البياني — الساعةُ والبقيّة ليست حقيقية، أنت فقط غيّرتَ الأسماء».

العطب: قِيس بـ`bars_door.py` أنّ ساعةَ الأسهم وأربعَ ساعاتها حقيقيةٌ (326 شمعة 10:00–15:00)، أمّا «تاسي» فساعتُه 22 شمعةً
يوميةً وأربعُ ساعاته 66 يوميةً: `get_bars` حوّل الإطارَ إلى مدّةٍ (`"1h": "1mo"`) ونادى التاريخَ اليوميّ.
الجذر: افتُرض أنّ لا مصدرَ لتاسي دون اليوم، ولم يُقَس. وقِيس (`tasi_intraday_door.py`): ياهو يسلّم `^TASI.SR` بفاصل
ساعةٍ حقيقيّ، ومولّدُ «تداول» جلسةٌ واحدةٌ دقيقةً دقيقة تُحفظ ساعاتُها فيطول الرسميُّ."""
import asyncio, os, pathlib, re, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


md = (ROOT / "backend/app/services/market_data.py").read_text(encoding="utf-8")
seg = md[md.index("class MarketDataService"):]
seg = seg[seg.index("async def get_bars"):]
seg = seg[:seg.index("async def get_history")]
check(not re.search(r'"1h"\s*:\s*"\d', seg) and not re.search(r'"4h"\s*:\s*"\d', seg),
      "١ ساعةُ تاسي وأربعُ ساعاته لا تُحوَّلان إلى مدّةٍ يومية")
check('if tf in ("1h", "4h"):' in seg and "return await self._tasi_intraday(tf)" in seg,
      "٢ وتمرّان بمصدرٍ دون اليوم")
check('self._yahoo().get_bars("^TASI.SR", tf)' in seg and "_th.capture()" in seg and "_th.overlay(" in seg,
      "٣ مصدرُها: ساعاتُ ياهو لـ^TASI.SR والجلساتُ الرسمية المحفوظة من «تداول» فوقها")

from app.services import tasi_history as TH   # noqa: E402
from app.services.market_data import four_hour   # noqa: E402
sess = []
for hh, mm, p in ((9, 59, 100.0), (10, 0, 101.0), (10, 30, 103.0), (10, 59, 99.0), (11, 5, 100.0),
                  (14, 59, 104.0), (15, 0, 105.0), (15, 10, 106.0), (16, 0, 106.5)):
    sess.append({"date": f"2026-10-08T{hh:02d}:{mm:02d}", "close": p, "open": p, "high": p, "low": p})
h = TH.session_hours(sess)
check([b["date"] for b in h] == ["2026-10-08 10:00", "2026-10-08 11:00", "2026-10-08 14:00", "2026-10-08 15:00"],
      "٤ الجلسةُ دقيقةً دقيقة ← شموعُ ساعةٍ بتوقيت الرياض «YYYY-MM-DD HH:00»", str([b["date"] for b in h]))
check(h[0]["open"] == 100.0 and h[0]["high"] == 103.0 and h[0]["low"] == 99.0 and h[0]["close"] == 99.0,
      "٥ والشمعةُ من أسعار دقائقها: فتحٌ · أعلى · أدنى · إغلاق", str(h[0]))
check(h[-1]["close"] == 106.5, "٦ ومزادُ الإغلاق وما بعده في شمعة 15:00 — إغلاقُها إغلاقُ الجلسة")
f4 = four_hour(h)
check([b["date"][11:] for b in f4] == ["10:00", "14:00"], "٧ والأربعُ ساعات منها على جلسة الرياض: 10:00 و14:00")

store = TH.remember_hours(sess)
check(list(store) == ["2026-10-08"] and len(store["2026-10-08"]) == 4, "٨ وتُحفظ ساعاتُ الجلسة تحت يومها فيطول السجلّ")
yahoo = [{"date": f"2026-10-0{d} {x:02d}:00", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 0}
         for d in (7, 8) for x in range(10, 16)]
ov = TH.overlay(yahoo, store)
check(len(ov) == 10 and [r["date"] for r in ov if r["date"].startswith("2026-10-08")] == [b["date"] for b in h]
      and all(r["close"] == 1 for r in ov if r["date"].startswith("2026-10-07")),
      "٩ اليومُ المحفوظ من «تداول» يُؤخذ منها كاملاً وما قبله من ياهو — بلا تكرار", str(len(ov)))
check(all(len(r["date"]) == 16 for r in ov), "١٠ وكلُّ شمعةٍ بساعتها — لا يومَ مجرّداً تحت اسم الساعة")

# ‏D663: «والبقيّة» — اليومُ والأسبوعُ والشهر: شمعةُ إغلاقٍ إلى إغلاقٍ بلا ذيلٍ ليست شمعةَ يوم
check("return await self._tasi_daily(tf)" in seg and "_th.real_daily(" in md and '"1y")) or []' not in seg,
      "١٢ يومُ تاسي وأسبوعُه وشهرُه يمرّون بالشموع الحقيقية لا بسلسلة الإغلاق وحدَها")
closes = [{"date": "2026-10-07", "open": 100, "high": 101, "low": 100, "close": 101, "volume": 0},
          {"date": "2026-10-08", "open": 101, "high": 102, "low": 101, "close": 102, "volume": 0}]
hrs = [{"date": "2026-10-08 10:00", "open": 101.2, "high": 103, "low": 100.5, "close": 102.5},
       {"date": "2026-10-08 15:00", "open": 102.5, "high": 102.6, "low": 101.8, "close": 101.9}]
rd = TH.real_daily(closes, hrs)
check(rd[-1]["open"] == 101.2 and rd[-1]["high"] == 103 and rd[-1]["low"] == 100.5 and rd[-1]["close"] == 102,
      "١٣ اليومُ الذي له ساعاتٌ: فتحُ أوّلها · أعلاها · أدناها — وإغلاقُه الرسميُّ يحكم", str(rd[-1]))
check(rd[0] == closes[0], "١٤ وما قبل مدى الساعات يبقى سلسلةَ الإغلاق الرسمية كما هي — لا يُخترع له ذيل")

sc = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
check("job_tasi_session" in sc and 'id="tasi_session_close"' in sc and "capture()" in sc,
      "١١ وتُحفظ الجلسةُ بعد الإغلاق مجدولةً — وإن لم يفتح أحدٌ الرسم")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
