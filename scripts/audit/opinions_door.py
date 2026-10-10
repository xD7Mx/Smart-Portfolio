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
    from app.services.argaam_ids import build, snapshot
    from app.services.tadawul_http import smart_flow
    await build()
    ids = (snapshot() or {}).get("ids") or {}
    pairs = [(s, str(ids[s])) for s in SAMPLE if ids.get(s)]
    got: dict = {}
    t0 = time.time()
    await smart_flow(AO._plan(pairs, got), warm=AO.A + "/ar", timeout=30)
    dt = time.time() - t0
    print(f"═ آراءُ بيوت الخبرة: {len(got)}/{len(pairs)} شركةً · {sum(len(v) for v in got.values())} رأياً · {dt:.1f}ث ({dt / max(1, len(pairs)):.1f}ث للصفحة)")
    for s, rs in got.items():
        houses = collections.Counter(r["house"] for r in rs)
        yr = [r for r in rs if r["date"] >= "2025-10-10"]
        print(f"  {s}: {len(rs)} رأياً · في سنة {len(yr)} · بملفّ {sum(1 for r in rs if r['pdf'])} · جهات {len(houses)} — {list(houses)[:8]}")
    for s, rs in list(got.items())[:2]:
        for r in rs[:3]:
            print(f"     {r}")
    fc = AO.as_forecasts(got)
    from app.services.research_reports import select
    sel = select(fc)
    print(f"  بنودُ التوقعات منها (سنة): {len(sel)} — أوّلُها {[(x['date'], x['source'], x['title'][:40], x['target']) for x in sel[:4]]}")

    import app.services.research_reports as RR
    r = await RR._arc()
    print(f"\n═ الراجحي المالية بكلّ الفئات: {len(r)} · أصناف {collections.Counter(x['kind'] for x in r).most_common()}")
    for x in [x for x in r if x["kind"] != "تقرير يوميّ"][:10]:
        print(f"   {x['date']} · {x['kind']} · {x['title'][:70]} · {x.get('company')}")
    allr = await RR.collect()
    print(f"\n═ تقاريرُ الجهات بعد الانتقاء (سنة): {len(allr)} · {collections.Counter(x['source'] for x in allr).most_common()}")
    print(f"   الأصناف {collections.Counter(x['kind'] for x in allr).most_common()}")
    print(f"\n═ تقديرُ الجمع الكامل: {len(ids)} معرّفاً ÷ 4 جلسات × {dt / max(1, len(pairs)):.1f}ث ≈ {len(ids) / 4 * dt / max(1, len(pairs)) / 60:.1f} دقيقة")


asyncio.run(main())
