#!/usr/bin/env python3
"""كاشفُ شموع الرسم البيانيّ (ملاحظةُ المالك 2026-11-15: «الشموعُ كأنها ديكور ليست حقيقية — أسبوعاً أو يوماً… والمؤشّراتُ
رسومُها فارغة لا تظهر لها شموع») — قارئٌ فقط: ما يصل الرسمَ فعلاً لكلّ رمزٍ وإطار، وحالُ حصّة المصدر."""
import asyncio, os, sys, time
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


def shape(rows):
    """علاماتُ الشمعة غير الحقيقية: بلا ذيل (قمّةٌ وقاعٌ = طرفا الجسم) · مسطّحة (الأربعةُ سواء) · فتحٌ = إغلاقُ السابقة · بلا حجم."""
    n = len(rows)
    if not n:
        return "—"
    flat = sum(1 for r in rows if r["open"] == r["high"] == r["low"] == r["close"])
    nowick = sum(1 for r in rows if r["high"] == max(r["open"], r["close"]) and r["low"] == min(r["open"], r["close"]))
    gapless = sum(1 for a, b in zip(rows, rows[1:]) if b["open"] == a["close"])
    novol = sum(1 for r in rows if not r.get("volume"))
    bad = sum(1 for r in rows if not (r["low"] <= min(r["open"], r["close"]) and r["high"] >= max(r["open"], r["close"])))
    return f"مسطّحة {flat} · بلا ذيل {nowick} · فتحٌ=إغلاقُ السابقة {gapless} · بلا حجم {novol} · مختلّة {bad}"


async def main():
    from app.services.market_data import market_service, BAR_FRAMES
    from app.services.usage_tracker import usage, can_call
    u = usage("yahoo")
    print("حصّةُ ياهو:", {k: u.get(k) for k in ("daily_used", "daily_limit", "minute_used", "minute_limit")}, "· يُسمح الآن:", can_call("yahoo"))
    syms = ["1120.SR", "2222.SR", "^TASI.SR", "^GSPC", "^IXIC", "^DJI", "BZ=F", "GC=F", "BTC-USD", "AAPL"]
    for s in syms:
        print(f"\n══ {s}")
        for tf in BAR_FRAMES:
            t0 = time.time()
            try:
                rows = await market_service.get_bars(s, tf) or []
            except Exception as e:                                # noqa: BLE001
                print(f"  {tf}: ✘ {type(e).__name__}: {e}")
                continue
            if not rows:
                print(f"  {tf}: 0 شمعة ({time.time() - t0:.1f}ث)")
                continue
            print(f"  {tf}: {len(rows)} شمعة · {rows[0]['date']} → {rows[-1]['date']} · {shape(rows)} ({time.time() - t0:.1f}ث)")
            if s in ("1120.SR", "^TASI.SR", "^GSPC") and tf in ("1d", "1wk", "1h"):
                for r in rows[-4:]:
                    print(f"      {r['date']}  O {r['open']}  H {r['high']}  L {r['low']}  C {r['close']}  V {r.get('volume')}")
    u = usage("yahoo")
    print("\nحصّةُ ياهو بعدها:", {k: u.get(k) for k in ("daily_used", "daily_limit")})


asyncio.run(main())
