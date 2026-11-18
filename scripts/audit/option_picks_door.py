#!/usr/bin/env python3
"""كاشفُ مُنتقي عقود الخيارات ودفترِه على السوق الحيّ (‏D759 · ‏D762): يراجع بميزانية 150 ثمّ 100 كما يفعل زرُّ «راجع»، ويطبع التوصياتِ
بعقدها وفارقِها بالدولار وهدفها وعائدِها واحتمالاتها وحالِها في الدفتر، وإشاراتِ الخروج، والمستبعَدَ بسببه — ثمّ يراجع مرّةً ثانية
ليُثبت أنّ القائمةَ لا تتبدّل. يكتب في المخبأ ودفتر التوصيات وحدهما — لا يمسّ المحفظة."""
import asyncio, collections, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)


async def main():
    from app.services import option_picks as OP
    from app.services.live_quote import sessions
    print("السوق:", (await sessions())["us"]["label"])
    t0 = time.time()
    sc = await OP.scan()
    print("المسارات:", len(sc), dict(collections.Counter(t["state"] for t in sc.values())), f"{time.time() - t0:.0f}ث")
    for b in (150, 100):
        runs = []
        for k in range(2):
            t1 = time.time()
            res = await OP.run(b)
            runs.append([p["contract"] for p in res["picks"]])
            print(f"\n══ الميزانية {b}$ · مراجعة {k + 1} · {time.time() - t1:.0f}ث · الأخبار {res['news_ok']} · توصيات {len(res['picks'])} · آخر جلسة {res['closed']} ══")
        for p in res["picks"]:
            print(f"  {p['symbol']} {p['type']} تنفيذ {p['strike']} {p['expiry']} ({p['dte']}ي) · كلفة ${p['cost']} · فارق ${p['spread_usd']} ({p['spread_pct']}٪) {p.get('px_src')}"
                  f" · هدف {p['target']} ({p['target_label']}) · عائد {p['rr']}× · ربح {p['pop']}٪ · لمس {p['p_touch']}٪ · دلتا {p['delta']} · OI {p['oi']}"
                  f" · {'جديدة' if p['new'] else 'منذ ' + p['opened']} {p.get('pl_pct')}٪")
        for x in res["exits"]:
            print(f"  خروج {x['contract']} {x['status_ar']} {x.get('pl_pct')}٪ — {x['why']}")
        for s in res["skipped"][:12]:
            print(f"  لم يدخل {s['symbol']}: {s['why']}")
        print("  ثبات:", "القائمةُ نفسُها" if runs[0] == runs[1] else f"تبدّلت {runs[0]} ⇐ {runs[1]}")


asyncio.run(main())
