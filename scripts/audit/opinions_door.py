#!/usr/bin/env python3
"""قارئُ آراء بيوت الخبرة وتقارير الجهات على الخادم قبل النشر (D664) — قارئٌ فقط (لا يُحفظ شيء).

    docker exec sp_backend python /app/scripts/audit/opinions_door.py
"""
import asyncio, collections, sys, time
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
SAMPLE = ("2222", "1120", "4003", "2010", "7010", "1180", "2280", "4190", "1211", "4002", "7202", "4161")


async def main():
    import app.services.analyst_opinions as AO
    t0 = time.time()
    got = await AO.refresh()
    rows = [r for v in got.values() for r in v]
    yr = [r for r in rows if r["date"] >= "2025-10-10"]
    print(f"═ آراءُ بيوت الخبرة: {len(got)} شركةً · {len(rows)} رأياً (في سنة {len(yr)}) · بملفّ {sum(1 for r in rows if r['pdf'])} · {time.time() - t0:.0f}ث")
    for h, n in collections.Counter(r["house"] for r in yr).most_common():
        print(f"   {h}: {n}")
    for s in SAMPLE[:4]:
        for r in AO.for_symbol(s)[:3] if s in got else []:
            pass
        rs = sorted(got.get(s, []), key=lambda r: r["date"], reverse=True)[:3]
        print(f"   {s}: " + " | ".join(f"{r['date']} {r['house']} {r['rating']} {r['target']}" for r in rs))
    from app.services.research_reports import select
    sel = select(AO.as_forecasts(got))
    print(f"   بنودُ التوقعات منها (سنة): {len(sel)}")
    import app.services.research_reports as RR
    allr = await RR.collect()
    print(f"\n═ تقاريرُ الجهات (سنة): {len(allr)} · {collections.Counter(x['source'] for x in allr).most_common()}")
    print(f"   الأصناف {collections.Counter(x['kind'] for x in allr).most_common()}")


asyncio.run(main())
