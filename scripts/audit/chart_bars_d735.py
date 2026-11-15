#!/usr/bin/env python3
"""حارسُ D735 (المالك 2026-11-15): «الشموعُ فيها ثغرة — كأنها ديكور ليست حقيقية سواء كانت أسبوع أو يوم… والمؤشّراتُ رسومُها
فارغة لا تظهر لها شموع… واجعل خيارَ تخصيصٍ في الأطر، مثلاً 6 ساعات، مثل تريدنق فيو».

قِيس على الخادم (‏chart_bars_door · 2026-11-14): (١) شمعةٌ بتاريخ السبت 14-11 للراجحي منسوخةٌ من الخميس؛ (٢) أسبوعيُّ ‎^GSPC‎
فيه شمعتان بتاريخ 2026-11-08 — والرسمُ يرفض تكرارَ الزمن فيُعرض فارغاً؛ (٣) 11 شمعةً يوميةً مسطّحةً بلا حجمٍ في العطل؛
(٤) آخرُ شمعةِ الساعة مسطّحةٌ بلا حجم (علامةُ الإغلاق). والحارسُ يعيد الحالاتِ المقيسةَ على الدوالّ نفسِها.

    python3 scripts/audit/chart_bars_d735.py
"""
import datetime as dt, os, pathlib, sys, tempfile
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


try:
    from app.services import bars as B
except ModuleNotFoundError as e:
    check(False, "١ دوالُّ تنظيف الشموع وتجميعها موجودة", str(e))
    print("\nالنتيجة: عطب ✖"); sys.exit(1)

bar = lambda d, o, h, l, c, v=1000: {"date": d, "open": o, "high": h, "low": l, "close": c, "volume": v}

# ٢ التكرار: أسبوعيُّ ‎^GSPC‎ كما قِيس — شمعتان بتاريخٍ واحد
dup = [bar("2026-11-01", 7610.83, 7715.57, 7350.35, 7376.86, 31941600000), bar("2026-11-08", 7422.24, 7652.76, 7422.24, 7561.67, 24434940000),
       bar("2026-11-08", 7616.85, 7621.78, 7499.4, 7561.67, 2727332000)]
cd = B.clean_daily(dup)
check(len(cd) == 2 and len({r["date"] for r in cd}) == 2 and cd[-1]["open"] == 7422.24 and cd[-1]["high"] == 7652.76
      and cd[-1]["close"] == 7561.67 and cd[-1]["volume"] == 24434940000,
      "١ تاريخٌ مكرَّرٌ يُدمج شمعةً واحدة (فتحُ الأولى · أقصى المدى · حجمُ الأكبر) — فلا يرفض الرسمُ السلسلةَ ويُعرض فارغاً", str(cd[-1]))
# ٣ خاناتُ العطل
hol = [bar("2026-03-17", 60, 61, 59.5, 60.5), bar("2026-03-18", 60.5, 60.5, 60.5, 60.5, 0), bar("2026-03-19", 60.5, 60.5, 60.5, 60.5, 0),
       bar("2026-03-22", 60.6, 61.2, 60.1, 61.0), bar("2026-03-23", 61, 61, 61, 61, 5000)]
ch = B.clean_daily(hol)
check([r["date"] for r in ch] == ["2026-03-17", "2026-03-22", "2026-03-23"],
      "٢ شمعةٌ مسطّحةٌ بلا حجمٍ في سلسلةٍ لها حجمٌ خانةُ عطلةٍ تُحذف — والمسطّحةُ بحجمٍ جلسةٌ تبقى", str([r["date"] for r in ch]))
idx = [bar(f"2026-11-0{i}", 10000 + i, 10050 + i, 9980 + i, 10020 + i, 0) for i in range(1, 6)] + [bar("2026-11-06", 10030, 10030, 10030, 10030, 0)]
check(len(B.clean_daily(idx)) == 6, "٣ والمؤشّرُ (لا حجمَ له أصلاً) لا تُحذف منه شمعة")
# ٤ علامةُ الإغلاق في الساعة — كما قِيست للراجحي 2026-11-12
hrs = [bar("2026-11-12 13:00", 63.5, 63.8, 63.45, 63.8, 496309), bar("2026-11-12 14:00", 63.75, 64.0, 63.7, 63.85, 823795),
       bar("2026-11-12 15:00", 63.95, 63.95, 63.95, 63.95, 0)]
ci = B.clean_intraday(hrs)
check(len(ci) == 2 and ci[-1]["date"] == "2026-11-12 14:00" and ci[-1]["close"] == 63.95 and ci[-1]["high"] == 64.0 and ci[-1]["volume"] == 823795,
      "٤ علامةُ الإغلاق (آخرُ شمعةٍ مسطّحةٍ بلا حجم) تُدمج في شمعة يومها الأخيرة: إغلاقُها سعرُ الإغلاق — لا شمعةٌ ديكور", str(ci[-1]))
# ٤ب وإغلاقُ نيويورك منتصفُ ليل الرياض: العلامةُ «00:00» من اليوم التالي — كما قِيست لـS&P 500 على الخادم بعد النشر (‏2026-11-15)
us = [bar("2026-11-13 22:30", 7556.82, 7558.63, 7545.48, 7550.02, 229643000), bar("2026-11-13 23:30", 7550.02, 7568.33, 7544.35, 7560.87, 396182000),
      bar("2026-11-14 00:00", 7561.67, 7561.67, 7561.67, 7561.67, 0)]
cu = B.clean_intraday(us)
check(len(cu) == 2 and cu[-1]["date"] == "2026-11-13 23:30" and cu[-1]["close"] == 7561.67 and cu[-1]["volume"] == 396182000,
      "٤ب وعلامةُ إغلاق السوق الأمريكيّ (بعد منتصف ليل الرياض) تُدمج في آخر شمعةٍ من جلستها — لا شرطةٌ مسطّحةٌ آخرَ الرسم", str(cu[-1]))
far = us[:2] + [bar("2026-11-14 17:30", 7561.67, 7561.67, 7561.67, 7561.67, 0)]
check(len(B.clean_intraday(far)) == 3, "٤ج وشمعةٌ مسطّحةٌ بعد ساعاتٍ من الإغلاق ليست علامتَه — جلسةٌ أخرى لا تُدمج في الماضية")
# ٥ التجميع: جلسةُ الرياض 10:00–14:00
day = lambda d: [bar(f"{d} {h:02d}:00", 60 + h / 10, 60.5 + h / 10, 59.8 + h / 10, 60.2 + h / 10, 100) for h in (10, 11, 12, 13, 14)]
two = day("2026-11-11") + day("2026-11-12")
b4, b6, b2 = B.bucket_intraday(two, 240), B.bucket_intraday(two, 360), B.bucket_intraday(two, 120)
check([r["date"][11:] for r in b4] == ["10:00", "14:00"] * 2 and [r["date"][11:] for r in b2] == ["10:00", "12:00", "14:00"] * 2
      and len(b6) == 2 and b6[0]["open"] == two[0]["open"] and b6[0]["close"] == two[4]["close"] and b6[0]["volume"] == 500
      and b4[0]["high"] == max(r["high"] for r in two[:4]),
      "٥ الساعاتُ تُجمَّع مثبَّتةً بأوّل شمعةٍ في يومها: 4 ساعات = 10:00 و14:00 · ساعتان = 10 · 12 · 14 · و6 ساعات شمعةُ اليوم",
      f"{[r['date'][11:] for r in b4]} · {len(b6)}")
# ٦ الأسبوع بتقويم سوقه
d14 = [bar((dt.date(2026, 11, 1) + dt.timedelta(days=i)).isoformat(), 10 + i, 11 + i, 9 + i, 10.5 + i) for i in range(14)
       if (dt.date(2026, 11, 1) + dt.timedelta(days=i)).weekday() not in (4, 5)]
wk_sa = B.weeks(d14, True)
d_us = [bar((dt.date(2026, 11, 2) + dt.timedelta(days=i)).isoformat(), 10 + i, 11 + i, 9 + i, 10.5 + i) for i in range(12)
        if (dt.date(2026, 11, 2) + dt.timedelta(days=i)).weekday() < 5]
wk_us = B.weeks(d_us, False)
check([r["date"] for r in wk_sa] == ["2026-11-01", "2026-11-08"] and wk_sa[0]["open"] == 10 and wk_sa[0]["close"] == d14[4]["close"]
      and [r["date"] for r in wk_us] == ["2026-11-02", "2026-11-09"] and len({r["date"] for r in wk_us}) == len(wk_us),
      "٦ الأسبوعُ من اليوميّ بتقويم سوقه: الأحد–الخميس للسعوديّ والإثنين–الجمعة لغيره، مؤرَّخاً بأوّله — ولا أسبوعَ يتكرّر",
      f"{[r['date'] for r in wk_sa]} · {[r['date'] for r in wk_us]}")
b3 = B.bucket_n(d14[:7], 3)
check(len(b3) == 3 and b3[-1]["open"] == d14[4]["open"] and b3[-1]["close"] == d14[6]["close"] and b3[0]["date"] == d14[0]["date"],
      "٧ وكلُّ ثلاثة أيامٍ شمعة — مثبَّتةً بآخر السلسلة فالشمعةُ الجاريةُ كاملةُ البداية")
check(B.parse_tf("6h") == (6, "h") and B.parse_tf("45m") == (45, "m") and B.parse_tf("120m") == (2, "h") and B.parse_tf("3d") == (3, "d")
      and B.parse_tf("2w") == (2, "wk") and B.parse_tf("1mo") == (1, "mo") and B.parse_tf("1wk") == (1, "wk")
      and B.parse_tf("0h") is None and B.parse_tf("99h") is None and B.parse_tf("x") is None and B.parse_tf("5y") is None,
      "٨ الإطارُ المخصَّص يُقرأ (‏6h · 45m · 3d · 2w)، وما خرج عن الحدّ أو لا يُفهم يُرفض")
# ٩ الشمعةُ الجارية: الحالةُ المقيسة — لقطةٌ أُعيد حفظُها السبتَ بأرقام الخميس
RY = dt.timezone(dt.timedelta(hours=3))
thu = bar("2026-11-12", 64.35, 64.4, 63.45, 63.95, 4767283)
base = [bar("2026-11-11", 63.8, 64.35, 63.35, 64.35), thu]
snap = {"price": 63.95, "day_high": 64.4, "day_low": 63.45, "day_open": 64.35, "volume": 4767283}
sat = B.live_daily(base, snap, dt.datetime(2026, 11, 14, 23, 5, tzinfo=RY), False)
check(len(sat) == 2 and sat[-1]["date"] == "2026-11-12", "٩ لقطةٌ محفوظةٌ يومَ السبت بأرقام الخميس لا تفتح شمعةً بتاريخ العطلة (عطبُ القياس بعينه)",
      str([r["date"] for r in sat]))
pre = B.live_daily(base, snap, dt.datetime(2026, 11, 15, 8, 30, tzinfo=RY), False)
check(len(pre) == 2, "١٠ ولا قبل افتتاح الأحد: الجلسةُ نفسُها لا تُنسخ يوماً جديداً")
live = B.live_daily(base, {"price": 64.6, "day_high": 64.8, "day_low": 63.9, "day_open": 64.0, "volume": 900000},
                    dt.datetime(2026, 11, 15, 11, 20, tzinfo=RY), True)
check(len(live) == 3 and live[-1]["date"] == "2026-11-15" and live[-1]["close"] == 64.6 and live[-1]["open"] == 64.0,
      "١١ وجلسةٌ جديدةٌ حيّةٌ تفتح شمعتَها بيومها وأرقامها", str(live[-1]))
upd = B.live_daily(live, {"price": 65.1, "day_high": 65.2, "day_low": 63.9, "day_open": 64.0, "volume": 1500000},
                   dt.datetime(2026, 11, 15, 13, 0, tzinfo=RY), True)
check(len(upd) == 3 and upd[-1]["close"] == 65.1 and upd[-1]["high"] == 65.2, "١٢ ثمّ تتحرّك في مكانها مع التداول — لا شمعةٌ ثانية")
check(B.session_day(dt.datetime(2026, 11, 13, 12, 0, tzinfo=RY), False).isoformat() == "2026-11-12"
      and B.session_day(dt.datetime(2026, 11, 15, 9, 0, tzinfo=RY), False).isoformat() == "2026-11-12"
      and B.session_day(dt.datetime(2026, 11, 15, 16, 0, tzinfo=RY), False).isoformat() == "2026-11-15",
      "١٣ يومُ الجلسة: الجمعةُ والسبتُ وما قبل افتتاح الأحد ← الخميس؛ وبعد إغلاق الأحد ← الأحد")
md = (ROOT / "backend/app/services/market_data.py").read_text(encoding="utf-8")
ep = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check("B.clean_daily(" in md and "B.clean_intraday(" in md and "B.live_daily(" in md and "B.weeks(daily" in md
      and "parse_tf(tf)" in ep and "if tf in BAR_FRAMES" not in ep,
      "١٤ ومصدرُ الشموع يمرّ بالتنظيف، واليوميُّ أساسُ الأسبوع، والبابُ يقبل أيَّ إطارٍ صحيح")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
