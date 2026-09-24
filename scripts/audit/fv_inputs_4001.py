#!/usr/bin/env python3
"""مدخلاتُ المحرّك المتعدّد النماذج (D468) — ما في XBRL ولقطة تداول لـ4001 ونظائره. قارئٌ فقط."""
import asyncio, sys, collections
sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_market as TM
    from app.services.tadawul_xbrl import for_symbol as X
    from app.services.statement_merge import archetype_of
    rows = TM.usable_rows()[0] or {}
    if not rows:
        await TM.refresh(); rows = TM.usable_rows()[0] or {}
    r = rows.get("4001") or rows.get("4001.SR") or {}
    print("مفاتيحُ لقطة تداول:", sorted(r.keys()))
    print("4001:", {k: r.get(k) for k in ("price", "sector", "sector_en", "sector_ar", "industry", "market_cap", "shares")})
    for kind in ("annual", "quarterly", "quarter"):
        try:
            a = X("4001", kind) or []
        except Exception as e:
            a = []; print(kind, "خطأ", e)
        print(f"\nXBRL {kind}: {len(a)} فترة")
        if a:
            print("  المفاتيح:", sorted(a[-1].keys()))
            for p in a[-3:]:
                print("  ", {k: v for k, v in p.items() if isinstance(v, (int, float, str)) and k not in ("source",)})
    print("\nالنمط:", archetype_of("4001"))
    sec = collections.defaultdict(list)
    for s, rr in rows.items():
        sec[(rr or {}).get("sector_en") or (rr or {}).get("sector")].append(str(s).replace(".SR", ""))
    k = (r.get("sector_en") or r.get("sector"))
    print("نظائرُ القطاع الرسميّ:", k, sorted(sec.get(k, [])))
    print("عددُ القطاعات:", len(sec), {str(a)[:40]: len(b) for a, b in list(sec.items())[:30]})


asyncio.run(main())
