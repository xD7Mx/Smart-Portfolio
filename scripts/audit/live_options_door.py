#!/usr/bin/env python3
"""كاشفُ D761 على السوق الحيّ: السعرُ الحيُّ وحالةُ السوق (سهمٌ أمريكيّ · سعوديّ · عقد)، والسلسلةُ باليونانيات ورأسِها، والأحداثُ الاقتصادية
بقراءة أثرها، والتحليلُ الذكيّ (‏NVDA بميزانية 150 · ‏^SPX بميزانية 150 · حكمُ عقدٍ بعينه). يكتب في المخبأ وحده — لا يمسّ المحفظة."""
import asyncio, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)


async def main():
    from app.services.live_quote import live
    from app.services.options_chain import chain
    from app.services.option_advisor import enrich_rows, stats, analyze
    from app.services.econ_calendar import week
    for s in ("NVDA", "2222.SR", "^GSPC"):
        t0 = time.time()
        q = await live(s)
        print("حيّ", s, q.get("price"), q.get("change_pct"), q.get("source"), "تأجيل", q.get("delayed"), "·", q["session"]["state"], q["session"]["label"],
              q["session"]["detail"], q["session"].get("holiday"), q["session"].get("source"), f"{time.time() - t0:.2f}ث")
    c = await chain("NIO")
    cur = next(e for e in c["expirations"] if e["t"] == c["expiry"])
    import copy
    c = copy.deepcopy(c)
    enrich_rows(c["calls"], float(c["price"]), cur["dte"], True)
    enrich_rows(c["puts"], float(c["price"]), cur["dte"], False)
    print("سلسلة NIO", c["price"], cur["date"], cur["dte"], "يوماً · رأس", stats(c, float(c["price"]), cur["dte"]))
    for r in [x for x in c["calls"] if x.get("g")][:3]:
        print("  ", r["contract"], r["bid"], r["ask"], r["last"], r["g"])
    a = await chain("NIO", c["expirations"][-1]["t"])
    k = next((r["contract"] for r in a["puts"] if r.get("oi")), None)
    if k:
        q = await live(k)
        print("حيّ عقد", k, q.get("price"), q.get("source"), q["session"]["state"])
    t0 = time.time()
    w = await week()
    print(f"\nأحداث ({time.time() - t0:.1f}ث) قراءة {w['read_ok']} عدد {len(w['events'])}")
    for e in w["events"][:8]:
        print("  ", e["day"], e["riyadh"][-5:], e["title"], "·", e.get("ar"), "· ميل", e.get("lean"), "·", (e.get("above") or "")[:90])
    for args in ({"symbol": "NVDA", "budget": 150}, {"symbol": "^SPX", "budget": 150}, {"symbol": "SPY", "budget": 300}):
        t0 = time.time()
        r = await analyze(**args)
        print(f"\nتحليل {args} ({time.time() - t0:.1f}ث) مسار {(r.get('trend') or {}).get('state')} ميل {r.get('lean')} HV {r.get('hv')} أرباح {r.get('earnings')} فحص {r.get('scanned')}")
        print("  خلاصة:", (r.get("summary") or "")[:300])
        print("  ملاءمة:", (r.get("fit") or {}).get("text"), "·", ((r.get("fit") or {}).get("alt") or {}).get("text"))
        for b in r.get("best") or []:
            print("  الأنسب", b["contract"], b["cost"], b["dte"], b["verdict_ar"], {x: b["g"][x] for x in ("delta", "theta", "iv", "pop")}, "| مع:", b["pros"][:1], "| حذر:", b["cons"][:2])
        for b in r.get("refused") or []:
            print("  أمتنع", b["contract"], b["cost"], b["cons"][:1])
    if k:
        r = await analyze("NIO", contract=k, budget=100)
        cc = r.get("contract") or {}
        print("\nحكم عقد", k, cc.get("verdict_ar"), cc.get("cost"), "| مع:", cc.get("pros"), "| ضد:", cc.get("cons"), r.get("error"))


asyncio.run(main())
