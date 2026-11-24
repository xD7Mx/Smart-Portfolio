#!/usr/bin/env python3
"""كاشفُ D825 على الخادم — أين يذهب زمنُ «التقرير اليومي»؟ (قراءةٌ لا تكتب شيئاً)

قال المالك (2026-11-24): «هناك تأخيرٌ في تحميل ملفّ التقرير اليوميّ». فيُقاس كلُّ ما يمرّ به فتحُه وحفظُه:

  ١ رأسُ التقرير (‏/research-desk): قراءةُ التقرير وأيامه.
  ٢ الورقةُ (‏/research-desk/paper): بناءُ HTML لكلّ جزء — مرّتين (هل من مخبّأ؟) — وحجمُه.
  ٣ الملفّ (‏/research-desk/pdf): الطباعةُ بالمتصفّح بلا واجهة — زمنُها وحجمُها، ومرّةً ثانية.

    docker exec sp_backend python /app/scripts/audit/report_speed_door_d825.py
"""
import os
import time

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()

import asyncio  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, "/app")


def ms(t0):
    return f"{(time.monotonic() - t0) * 1000:,.0f}ms"


async def main():
    from app.api.v1.endpoints import market as MK
    from app.services import research_paper as RP
    from app.services import saqr_report as SR
    from app.services import research_desk as RD
    import json
    size = lambda res: len(getattr(res, "body", b"") or json.dumps(res, ensure_ascii=False, default=str).encode())   # noqa: E731
    pf = next((str(k) for k in ("all", 1, 2, 3, 4, 5) if RD.report_dates(k)), None)
    print(f"══ ١ رأسُ التقرير (المحفظة: {pf} · أيامٌ {len(RD.report_dates(pf if pf == 'all' else int(pf))) if pf else 0})")
    for q in (pf, "all", "none"):
        t0 = time.monotonic()
        res = await MK.research_desk_view(None, q)
        print(f"   pf={q}: {ms(t0)} · {size(res):,}B")
    print("══ ٢ الورقة")
    key, r, mo = MK._report_for(pf, None)
    if not r:
        print("   لا تقرير")
        return
    print(f"   التقرير: {r.get('date')} · مفاتيحُه {len(r)}")
    for part in ("market", "portfolio", "all"):
        for i in (1, 2):
            t0 = time.monotonic()
            html = RP.render(r, part)
            print(f"   {part} #{i}: {ms(t0)} · {len(html):,} حرفاً")
    t0 = time.monotonic()
    res = await MK.research_desk_paper(None, "all", pf)
    print(f"   الطلبُ كاملاً (all): {ms(t0)} · {size(res):,}B")
    print("══ ٣ الملفّ")
    print(f"   المتصفّح: {SR.chrome_path()}")
    for i in (1, 2):
        t0 = time.monotonic()
        html = RP.render(r, "all")
        t1 = time.monotonic()
        data = await SR.to_pdf(html)
        print(f"   PDF #{i}: البناء {(t1 - t0) * 1000:,.0f}ms · الطباعة {ms(t1)} · {len(data or b''):,}B")
    try:
        import resource
        print(f"   ذاكرةُ الكاشف القصوى: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:,.0f}MB")
    except Exception:                                             # noqa: BLE001
        pass
    print("══ انتهى")


asyncio.run(main())
