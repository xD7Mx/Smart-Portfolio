#!/usr/bin/env python3
"""كاشفُ قائمة صقر (‏D771) على الخادم: يبني القائمةَ بأوامر المالك الحقيقية ويطبع خلاصتَها — كم عقداً، وأعلاها بإيجابياته وسلبياته، وما استُبعد ولماذا،
والزمن. القائمةُ ناتجُ صقر نفسِه (ملفُّ قائمته) لا رقمٌ من أرقام المالك.

    docker exec sp_backend python /app/scripts/audit/saqr_list_door.py
"""
import asyncio
import sys
import time

sys.path.insert(0, "/app")


async def main():
    from app.services import saqr_list as SL
    from app.services import saqr_trader as SQ
    st = SQ.load("us")
    c = SQ.cfg(st)
    print("الأوامر:", {k: c.get(k) for k in ("per_trade", "sides", "auto", "mode")}, "· المراكز:", [p["symbol"] for p in st["positions"]],
          "· النقد:", st["cash"])
    t0 = time.time()
    r = await SL.build(c, {p["symbol"] for p in st["positions"]})
    print(f"══ {r.get('label')} · {len(r.get('items') or [])} عقداً من {r.get('scanned')} ورقة (المجال {r.get('universe')}) · بميزانية {r.get('budget')} · "
          f"{time.time() - t0:.0f}ث · آخرُ جلسة={r.get('snap')}")
    print("استُبعد:", r.get("excluded"), "· أرخصُ صالحٍ فوق الميزانية:", r.get("cheapest"))
    for i in (r.get("items") or [])[:15]:
        print(f"  {i['grade']} {i['symbol']:<6} {i['type']:<4} {i['strike']:>7g} {i['expiry']} ({i['dte']}ي) كلفة {i['cost']:>6.0f} · هدف {i['gain_target']:+d}٪ "
              f"· احتمال {i['pop']:.0f}٪ · 30٪ عند {i['tp30']['price']} ({i['tp30']['pct']}٪) · +{len(i['pros'])}/−{len(i['cons'])}")
    if r.get("items"):
        i = r["items"][0]
        print("  إيجابياتُ الأوّل:", i["pros"])
        print("  سلبياتُه:", i["cons"])
    calls = sum(1 for i in r.get("items") or [] if i["type"] == "call")
    print("شراء:", calls, "· بيع:", len(r.get("items") or []) - calls)

asyncio.run(main())
