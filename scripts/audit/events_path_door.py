#!/usr/bin/env python3
"""كاشفُ مسار الأحداث من نقطة الصفحة — قارئٌ فقط: ما يُرجعه كلُّ طورٍ لأوّل طلبٍ وثانيه («الغاز»)."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
import app.services.material_events as ME
import app.services.tadawul_disclosure as TD

_ef, _lf = ME.events_for, TD.list_for


async def ef(sym, *a, **k):
    hit = cache.get(f"events:v1:{sym}")
    r = await _ef(sym, *a, **k)
    print(f"   events_for({sym}) ← كاشٌ {'—' if hit is None else len(hit.get('events') or [])} · الناتج {len(r.get('events') or [])}")
    return r


async def lf(sym, *a, **k):
    hit = cache.get(f"tadawul:annlist:v3:{sym}")
    r = await _lf(sym, *a, **k)
    print(f"   list_for({sym}) ← كاشٌ {'—' if hit is None else len(hit)} · الناتج {len(r)}")
    return r
ME.events_for, TD.list_for = ef, lf


async def main():
    from app.api.v1.endpoints.market import get_material_events
    import json
    for i in range(2):
        print(f"الطلب {i + 1}: كاشُ العرض {'—' if cache.get('events:view:v2:2080') is None else 'موجود'} · لقطةٌ {bool(lastgood.load('events:view:2080'))}")
        r = await get_material_events("2080")
        d = (json.loads(r.body) if getattr(r, "body", None) else r).get("data") or {}
        print(f"   ← {len(d.get('events') or [])} حدثاً")


asyncio.run(main())
