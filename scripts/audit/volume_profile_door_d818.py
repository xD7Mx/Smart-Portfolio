#!/usr/bin/env python3
"""كاشفُ D818 على الخادم — الفوليوم بروفايل على رموزٍ حقيقية (قراءةٌ لا تكتب شيئاً).

  ١ البروفايل لكلّ نافذة: عددُ الشموع ومداها، ونقطةُ التحكّم ومنطقةُ القيمة، والعُقدُ الكثيفة والفراغات، والسيولةُ وزمنُ الحساب.
  ٢ القراءةُ عند السعر الحاليّ وشاهدُ «الحجم» للشراء.
  ٣ أثرُه على عقود الأمريكيّ: كم عقداً تُسقطه جدرانُ الحجم وكم هدفاً صار عقدةَ حجم (من دفتر العقود الفعليّ لثلاثة رموز).

    docker exec sp_backend python /app/scripts/audit/volume_profile_door_d818.py
"""
import os
import time

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()

import asyncio  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, "/app")

US = [("SPY", 3), ("NVDA", 30), ("AAPL", 200)]
SA = ["2222", "1120", "7010"]


def line(vp):
    if not vp:
        return "لا بروفايل (شموعٌ قليلة أو تعذّر الجلب)"
    hv = ", ".join(f"{h['p']:.2f}({h['w']:.2f})" for h in vp["hvn"][:5])
    lv = ", ".join(f"{p:.2f}" for p in vp["lvn"][:4])
    return (f"{vp['n']} شمعة {vp['from']}→{vp['to']} · مدى {vp['lo']:.2f}–{vp['hi']:.2f} · تحكّم {vp['poc']:.2f} · قيمة {vp['val']:.2f}–{vp['vah']:.2f}"
            f" · كثيف [{hv}] · فراغ [{lv}] · {'ضعيفُ السيولة' if vp['thin'] else 'سيولةٌ كافية'} · {vp.get('tf')}")


async def main():
    from app.services import volume_profile as VP
    from app.services.market_data import market_service as M
    print("══ ١ و٢ البروفايل والقراءة")
    for sym, dte in US:
        t0 = time.monotonic()
        vp = await VP.for_symbol(sym, dte, False)
        ms = (time.monotonic() - t0) * 1000
        p = await M.get_prices([sym])
        S = (p.get(sym) or {}).get("price")
        rd = VP.read(vp, S, "long")
        m = VP.member(rd, "long")
        print(f"   {sym} (أجل {dte} يوماً · {VP.window(dte)[2]}): {line(vp)} · {ms:.0f}ms")
        print(f"      السعر {S} · {rd and rd['zone']} · التالي {rd and rd['next']} · جدار {rd and rd['wall']} · قاعدة {rd and rd['support']} · فراغٌ أمامه {rd and rd['gap_ahead']}")
        print(f"      الحجم: {m['v']} — {m['say']}")
    for sym in SA:
        t0 = time.monotonic()
        vp = await VP.for_symbol(sym, None, True)
        ms = (time.monotonic() - t0) * 1000
        p = await M.get_prices([sym])
        S = (p.get(sym) or p.get(f"{sym}.SR") or {}).get("price")
        rd = VP.read(vp, S, "long")
        m = VP.member(rd, "long")
        print(f"   {sym}: {line(vp)} · {ms:.0f}ms")
        print(f"      السعر {S} · {rd and rd['zone']} · التالي {rd and rd['next']} · قاعدة {rd and rd['support']}")
        print(f"      الحجم: {m['v']} — {m['say']}")

    print("══ ٣ أثرُه على عقود الأمريكيّ")
    from app.services import option_picks as OP
    for sym in ("NVDA", "AAPL", "AMD"):
        try:
            bars = await M.get_bars(sym, "1d")
            tr = OP.trend_of(bars or [])
            if not tr:
                print(f"   {sym}: لا مسار")
                continue
            call = tr["state"] != "هابط"
            diag: dict = {}
            t0 = time.monotonic()
            _, ks = await OP.valid_contracts(sym, call, tr, diag)
            vp_t = [k for k in ks if "الفوليوم" in (k.get("target_label") or "")]
            print(f"   {sym} ({'شراء' if call else 'بيع'}): عقودٌ صالحة {len(ks)} · هدفُها عقدةُ حجم {len(vp_t)} · أبعدُ مرحلة "
                  f"{OP.STAGES[diag['stage']] if diag.get('stage', -1) >= 0 else '—'} · {time.monotonic() - t0:.1f}ث")
            for k in ks[:3]:
                v = k.get("vp") or {}
                print(f"      {k['contract']} تنفيذ {k['strike']} هدف {k['target']} ({k['target_label']}) · {v.get('zone')} · درجة {k['score']}")
        except Exception as e:                                   # noqa: BLE001
            print(f"   {sym}: تعذّر {type(e).__name__}: {str(e)[:120]}")


asyncio.run(main())
