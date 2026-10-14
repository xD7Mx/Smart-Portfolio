"""كاشفُ D713 (قراءةٌ فقط): أحقيقيّةٌ شموعُ الرسم كتريدنق فيو؟ — بلاغُ المالك: «الشموعُ يومٌ وأسبوعٌ وشهر لكنّها ليست حقيقية مثل
تريدنق فيو». فيطبع لكلّ رمزٍ وإطار (يوم · أسبوع · شهر · ساعة): عددَ الشموع وأوّلَها وآخرَها، ونسبةَ ما له ذيلٌ حقيقيّ (أعلى فوق جسمه أو
أدنى تحته)، ونسبةَ ما يفتح عند إغلاق ما قبله بالضبط (علامةُ شمعةٍ مبنيّةٍ من الإغلاق)، ونسبةَ الجسم الصفريّ؛ ثمّ يقارن آخرَ شمعةٍ
يومية بجلسة اليوم الرسمية من لقطة «تداول» (افتتاحٌ · أعلى · أدنى · إغلاق)، وأيّامَ الأسبوع في الأسبوعية.

    docker exec sp_backend python /app/scripts/audit/bars_real_door.py
"""
import asyncio
import os
import sys
import time

os.environ["TZ"] = "Asia/Riyadh"
if hasattr(time, "tzset"):
    time.tzset()
sys.path.insert(0, "/app")


def stats(rows):
    n = len(rows)
    if n < 2:
        return f"{n} شمعة"
    wick = sum(1 for r in rows if r["high"] > max(r["open"], r["close"]) + 1e-9 or r["low"] < min(r["open"], r["close"]) - 1e-9)
    gap0 = sum(1 for a, b in zip(rows, rows[1:]) if abs(b["open"] - a["close"]) < 1e-9)
    flat = sum(1 for r in rows if abs(r["open"] - r["close"]) < 1e-9)
    return (f"{n} شمعة · {str(rows[0]['date'])[:16]} ← {str(rows[-1]['date'])[:16]} · بذيلٍ {wick * 100 // n}٪ · "
            f"تفتح عند إغلاق سابقتها {gap0 * 100 // (n - 1)}٪ · جسمٌ صفريّ {flat * 100 // n}٪")


async def main():
    import datetime as dt
    from app.services.market_data import market_service
    from app.services import tadawul_market as TM
    from app.services import lastgood
    rows, live, at = TM.usable_rows()
    if not rows:
        rec = lastgood.load(TM.STORE_KEY) or {}
        rows = rec.get("rows") if isinstance(rec.get("rows"), dict) else {}
    for sym in ("2222.SR", "1120.SR", "^TASI.SR"):
        print(f"\n══ {sym}")
        for tf in ("1d", "1wk", "1mo", "1h"):
            try:
                b = await market_service.get_bars(sym, tf) or []
            except Exception as e:                                 # noqa: BLE001
                print(f"   [{tf}] تعذّر {type(e).__name__}: {e}")
                continue
            print(f"   [{tf}] {stats(b)}")
            if tf == "1d" and b:
                print(f"      آخرُ ثلاث: {[(r['date'], r['open'], r['high'], r['low'], r['close']) for r in b[-3:]]}")
                r0 = rows.get(sym.replace(".SR", "")) if sym != "^TASI.SR" else None
                if r0:
                    print(f"      جلسةُ «تداول» الرسمية: افتتاح {r0.get('day_open')} · أعلى {r0.get('day_high')} · أدنى {r0.get('day_low')} · "
                          f"إغلاق {r0.get('price')} · إغلاقٌ سابق {r0.get('prev_close')}")
            if tf == "1wk" and b:
                wd = sorted({dt.date.fromisoformat(str(r["date"])[:10]).strftime("%a") for r in b[-30:]})
                print(f"      أيّامُ تاريخ الشمعة الأسبوعية (آخر 30): {wd} · آخرُ ثلاث: "
                      f"{[(str(r['date'])[:10], r['open'], r['high'], r['low'], r['close']) for r in b[-3:]]}")
            if tf == "1mo" and b:
                print(f"      آخرُ ثلاث: {[(str(r['date'])[:10], r['open'], r['high'], r['low'], r['close']) for r in b[-3:]]}")
            await asyncio.sleep(0.5)


asyncio.run(main())
