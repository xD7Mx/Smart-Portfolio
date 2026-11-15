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


async def verify():
    """إغلاقُ آخر جلسةٍ قبل اليوم من ياهو مقابل «الإغلاق السابق» الرسميّ في لقطة «تداول» — لكلّ شركات السوق الرئيسي."""
    from app.services import tadawul_market as TM
    from app.services.market_data import market_service as M
    from app.data.universe import is_main
    from app.services import research_paper as RP
    rows = {s: r for s, r in (TM.usable_rows()[0] or {}).items() if is_main(s)}
    tasi = RP._bars_ok(await M.get_bars("^TASI.SR", "1d"))
    last = tasi[-1]["date"][:10]
    prevd = tasi[-2]["date"][:10]
    ok = bad = miss = 0
    worst = []
    sem = asyncio.Semaphore(6)

    async def one(s, r):
        async with sem:
            b = RP._bars_ok(await M.get_bars(f"{s}.SR", "1d"))
        return s, r, {x["date"][:10]: x["close"] for x in b}
    for s, r, cl in await asyncio.gather(*(one(s, r) for s, r in rows.items())):
        pc = r.get("prev_close")
        y = cl.get(prevd)
        if not pc or not y:
            miss += 1
            continue
        d = abs(y / pc - 1) * 100
        if d <= 0.3:
            ok += 1
        else:
            bad += 1
            worst.append((s, round(y, 2), pc, round(d, 1)))
    print(f"إغلاقُ {prevd} (آخرُ جلسةٍ قبل {last}): مطابقٌ {ok} · مخالفٌ {bad} · غائب {miss}")
    print("  أكبرُ المخالفات:", sorted(worst, key=lambda w: -w[3])[:12])


asyncio.run(verify())
