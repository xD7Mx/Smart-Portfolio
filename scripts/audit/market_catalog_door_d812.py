#!/usr/bin/env python3
"""كاشفُ D812 على الخادم — المؤشّراتُ والسلعُ التي صار البحثُ يجدها في كلّ شاشة: هل يرسمها الخادمُ فعلاً؟ (قراءةٌ لا تكتب شيئاً)

قال المالك (2026-11-24): «مربّعُ البحث سبيلُنا إلى الرسم المراد — تاسي وبرنت والذهب وغيرُها داخل كلّ إطار».
فالرمزُ الذي يظهر في البحث ولا يرسمه الخادمُ اختلاقٌ في الواجهة. لكلّ رمزٍ في دليل البحث (‏frontend/src/data/marketCatalog.ts —
والقائمةُ هنا نسختُه، يطابقها الحارسُ ‏troom_d810.mjs) شموعُه اليوميةُ من الباب نفسِه الذي يقرؤه الرسم: عددُها وتاريخُ آخرها وإغلاقُه
موجودٌ أم لا (لا يُطبع سعر)، وشموعُ الساعة كذلك.

    docker exec sp_backend python /app/scripts/audit/market_catalog_door_d812.py
"""
import os
import time

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()

import asyncio  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, "/app")

SYMBOLS = ["^TASI.SR", "^GSPC", "^IXIC", "^NDX", "^DJI", "^RUT", "^VIX", "BZ=F", "CL=F", "GC=F", "SI=F", "NG=F", "HG=F",
           "BTC-USD", "ETH-USD", "DX-Y.NYB", "^TNX"]


def _last(bars):
    if not bars:
        return "—", False
    b = bars[-1]
    t = b.get("date") or b.get("time") or ""
    return str(t)[:16], b.get("close") not in (None, 0)


async def main():
    from app.services.market_data import market_service
    ok_all = 0
    print("══ الشموعُ اليوميةُ وشموعُ الساعة لكلّ رمزٍ في دليل البحث")
    for s in SYMBOLS:
        t0 = time.monotonic()
        try:
            d = await asyncio.wait_for(market_service.get_bars(s, "1d"), 45)
        except Exception as e:                                   # noqa: BLE001
            d, err = [], type(e).__name__
        else:
            err = ""
        try:
            h = await asyncio.wait_for(market_service.get_bars(s, "1h"), 45)
        except Exception:                                        # noqa: BLE001
            h = []
        ld, cd = _last(d)
        lh, ch = _last(h)
        good = len(d) >= 50 and cd
        ok_all += good
        print(f"   {'✔' if good else '✖'} {s:10} · يوميّ {len(d):5} آخرُه {ld} إغلاق={'نعم' if cd else 'لا'} · ساعة {len(h):5} آخرُها {lh}"
              f" · {time.monotonic() - t0:.1f}ث{(' · ' + err) if err else ''}")
    print(f"══ يرسمها الخادم: {ok_all} من {len(SYMBOLS)}")


asyncio.run(main())
