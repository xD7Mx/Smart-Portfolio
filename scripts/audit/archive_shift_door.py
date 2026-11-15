#!/usr/bin/env python3
"""كاشفُ إزاحة التواريخ في إغلاقات الشركات (‏D749) — قارئٌ فقط.
عمقُ السوق المحسوبُ للخميس 12 نوفمبر خالف ما نشره التقريرُ المرجعيّ (99/161 مقابل 163/100). فيُقارَن تغيّرُ السوق المرجّح بالقيمة من إغلاقات
الشركات بتغيّر تاسي الفعليّ لكلّ جلسةٍ من العشر الأخيرة — في اليوم نفسِه وبإزاحة يومٍ قبله وبعده — ويُطبع إغلاقُ شركاتٍ كبرى حولها."""
import asyncio, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


async def main():
    from app.services.market_data import market_service as M
    from app.services import research_paper as RP
    tasi = RP._bars_ok(await M.get_bars("^TASI.SR", "1d"))[-12:]
    days = [b["date"][:10] for b in tasi]
    tp = {b["date"][:10]: RP._pct(b["close"], a["close"]) for a, b in zip(tasi, tasi[1:])}
    syms = ["2222", "1120", "1180", "2010", "7010", "1211", "1150", "2082", "1010", "5110"]
    raw = {}
    for s in syms:
        raw[s] = RP._bars_ok(await M.get_bars(f"{s}.SR", "1d"))[-12:]
    for s in syms[:3]:
        print(s, [(b["date"][:10], round(b["close"], 2)) for b in raw[s][-6:]])
    y = await M.primary.daily_base("1120.SR", "1mo")
    print("ياهو الخام 1120:", [(p.get("date"), p.get("close")) for p in (y or [])[-5:]])
    print("اليوم | تاسي | متوسّطُ العشر (اليوم) ")
    for d in days[1:]:
        ch = []
        for s in syms:
            cl = {b["date"][:10]: b["close"] for b in raw[s]}
            ks = sorted(k for k in cl if k < d)
            if d in cl and ks:
                ch.append(RP._pct(cl[d], cl[ks[-1]]))
        avg = sum(ch) / len(ch) if ch else None
        print(f"  {d} · تاسي {tp.get(d) and round(tp[d], 2)} · كبرى {avg and round(avg, 2)} ({len(ch)})")


asyncio.run(main())
