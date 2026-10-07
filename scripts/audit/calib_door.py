#!/usr/bin/env python3
"""معايرةُ النماذج بأهداف المحلّلين — لكلّ نموذجٍ ونمطٍ: وسيطُ (قيمةُ النموذج ÷ الهدف) وتشتّتُه. قارئٌ فقط.
والسعرُ للمقارنة: وسيطُ (الهدف ÷ السعر) يقول كم يرى المحلّلون من صعود."""
import asyncio, collections, json, statistics, sys
sys.path.insert(0, "/app")


async def main():
    from app.services import fair_value_models as F
    from app.services.market_screener import get_cached_screener
    rows = [r for r in (get_cached_screener() or []) if isinstance(r.get("analyst_target"), (int, float))
            and r["analyst_target"] > 0 and isinstance(r.get("price"), (int, float)) and r["price"] > 0]
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    fin = collections.defaultdict(list)
    tp = collections.defaultdict(list)
    dump = []
    for r in rows:
        s = str(r["symbol"]).replace(".SR", "")
        try:
            i = await F.gather(s)
            v = F.value(i) if i else None
        except Exception:                                          # noqa: BLE001
            continue
        if not v or not v.get("value"):
            continue
        at, px = r["analyst_target"], r["price"]
        a = i.archetype
        tp[a].append(at / px)
        fin[a].append(v["value"] / at)
        rec = {"s": s, "a": a, "px": px, "at": at, "v": v["value"], "m": {}}
        for m in v.get("models") or []:
            by[a][m["key"]].append(m["value"] / at)
            by["*"][m["key"]].append(m["value"] / at)
            rec["m"][m["key"]] = round(m["value"], 2)
        dump.append(rec)
    md = lambda xs: statistics.median(xs) if xs else None          # noqa: E731
    print(f"أوراقٌ لها هدف وقيمة: {len(dump)}")
    for a in sorted(fin, key=lambda k: -len(fin[k])):
        print(f"\n═ {a} n={len(fin[a])} · هدفُهم÷السعر {md(tp[a]):.2f} · قيمتُنا÷هدفهم {md(fin[a]):.2f}")
        for k, xs in sorted(by[a].items(), key=lambda kv: -len(kv[1])):
            if len(xs) >= 3:
                dev = md([abs(x - 1) for x in xs])
                print(f"   {k:16} n={len(xs):>3} · وسيط {md(xs):.2f} · انحراف {dev:.0%}")
    print("\n═ الكلّ")
    for k, xs in sorted(by["*"].items(), key=lambda kv: -len(kv[1])):
        print(f"   {k:16} n={len(xs):>3} · وسيط {md(xs):.2f} · انحراف {md([abs(x - 1) for x in xs]):.0%}")
    print("@@DUMP@@" + json.dumps(dump, ensure_ascii=False))

asyncio.run(main())
