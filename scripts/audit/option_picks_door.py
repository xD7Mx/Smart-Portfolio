#!/usr/bin/env python3
"""كاشفُ مُنتقي عقود الخيارات على السوق الحيّ (‏D759): يشغّل المحرّكَ بميزانية 100 دولار كما يفعل زرُّ «ابحث»، ويطبع المساراتِ وقراءةَ
الأخبار والصفقاتِ بمقاييسها والمستبعَدَ بسببه. يكتب في المخبأ وحده (نتيجةُ البحث نصفَ ساعة) — لا يمسّ المحفظة."""
import asyncio, collections, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)


async def main():
    from app.services import option_picks as OP
    t0 = time.time()
    sc = await OP.scan()
    print("المسارات:", len(sc), dict(collections.Counter(t["state"] for t in sc.values())), f"{time.time() - t0:.0f}ث")
    for b in (150, 100, 50):
        t1 = time.time()
        res = await OP.run(b)
        print(f"\n══ الميزانية {b}$ · {time.time() - t1:.0f}ث · الأخبار مقروءة {res['news_ok']} · صفقات {len(res['picks'])} ══")
        for p in res["picks"]:
            print(f"  {p['symbol']} {p['type']} {p['strike']} {p['expiry']} ({p['dte']}ي) · ${p['cost']} · ربح {p['pop']}٪ · دلتا {p['delta']} · "
                  f"IV {p['iv']}٪ · OI {p['oi']} · فارق {p['spread_pct']} · سعر {p.get('px_src')} · مسار {p['trend']['state']} · خبر {(p.get('news') or {}).get('impact')}"
                  f"/{(p.get('news') or {}).get('strength')} {((p.get('news') or {}).get('event') or '')[:70]}")
        for s in res["skipped"][:15]:
            print(f"  مستبعَد {s['symbol']}: {s['why']}")


asyncio.run(main())
