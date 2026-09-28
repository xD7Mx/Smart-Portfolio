#!/usr/bin/env python3
"""امتلاءُ أعمدة فرز السوق كما يراها المالك (بعد الإنعاش) — نسبةٌ لكلّ عمود. قارئٌ فقط (D501).

    docker exec sp_backend python /app/scripts/audit/screener_fill.py
"""
import asyncio, sys
sys.path.insert(0, "/app")


async def main():
    from app.services.market_screener import get_cached_screener, refresh_derived
    rows = get_cached_screener() or []
    if not rows:
        print("═ لا لقطةَ فرزٍ محفوظة"); return
    rows = await refresh_derived([dict(r) for r in rows])
    n = len(rows)
    keys = sorted({k for r in rows for k in r.keys()})
    print(f"═ صفوفُ الفرز: {n}")
    for k in keys:
        c = sum(1 for r in rows if r.get(k) not in (None, "", [], {}))
        print(f"   {k:<28} {c:>4} / {n}  ({100*c/n:5.1f}٪)")
    src = {}
    for r in rows:
        for f in ("dividend_yield_source", "ratios_source"):
            v = r.get(f)
            if v:
                src[(f, v)] = src.get((f, v), 0) + 1
    print("\n═ المصادر:")
    for (f, v), c in sorted(src.items()):
        print(f"   {f}: {v} = {c}")

asyncio.run(main())
