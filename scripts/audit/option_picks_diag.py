#!/usr/bin/env python3
"""كاشفٌ مؤقّت (‏D759): لماذا لا صفقة؟ — لكلّ رمزٍ ذي اتجاه: صفوفُ السلسلة وأسعارُ الطلب والعرض والاهتمامُ والتذبذب، وأفضلُ احتمالٍ وأرخصُ عقدٍ صالح."""
import asyncio, collections, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)


def relaxed(t):
    c, s50, s200, sl = t["close"], t["sma50"], t["sma200"], t["slope50"]
    if s50 > s200 * 1.01 and sl > 0.3 and c > s200:
        return "صاعد"
    if s50 < s200 * 0.99 and sl < -0.3 and c < s200:
        return "هابط"
    return "عرضي"


async def main():
    from app.services import option_picks as OP
    from app.services.options_chain import chain
    sc = await OP.scan()
    print("الحالي:", dict(collections.Counter(t["state"] for t in sc.values())), "· المرخى:", dict(collections.Counter(relaxed(t) for t in sc.values())))
    print("صاعد/هابط (مرخى):", {s: relaxed(t) for s, t in sc.items() if relaxed(t) != "عرضي"})
    shown = False
    for s, t in sorted(sc.items(), key=lambda kv: kv[1]["close"]):
        st = relaxed(t)
        if st == "عرضي":
            continue
        call = st == "صاعد"
        base = await chain(s)
        if not base:
            print(s, "لا سلسلة"); continue
        exps = [e for e in base.get("expirations") or [] if OP.MIN_DTE <= e["dte"] <= OP.MAX_DTE]
        line = [f"{s} {t['close']} {st} آجال {len(exps)}"]
        for e in (exps[:1] + exps[-1:]):
            ch = await chain(s, e["t"])
            rows = (ch or {}).get("calls" if call else "puts") or []
            if not shown and rows:
                print("  عيّنة:", rows[len(rows) // 2]); shown = True
            nz_ask = sum(1 for r in rows if (r.get("ask") or 0) > 0)
            nz_bid = sum(1 for r in rows if (r.get("bid") or 0) > 0)
            oi = sum(1 for r in rows if (r.get("oi") or 0) >= OP.MIN_OI)
            res = {}
            for b in (50, 100, 150, 300, 1000):
                k = OP.pick_contract(rows, float(ch["price"] or base["price"]), e["dte"], call, b)
                res[b] = f"{k['pop']:.0f}٪/${k['cost']:.0f}" if k else "-"
            line.append(f"[{e['dte']}ي صفوف {len(rows)} طلب {nz_ask} عرض {nz_bid} OI {oi} → " + " ".join(f"{b}:{v}" for b, v in res.items()) + "]")
        print("  ".join(line))


asyncio.run(main())
