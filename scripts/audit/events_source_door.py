#!/usr/bin/env python3
"""كاشفُ مصدر الأحداث — قارئٌ فقط: ما في الكاش للعرض وللمستخرِج، وما تُرجعه قائمةُ إفصاحات «تداول» الآن."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
from app.services.tadawul_disclosure import list_for

SYMS = ["2080", "1120", "4013", "2222"]


async def main():
    for s in SYMS:
        v = cache.get(f"events:view:v2:{s}")
        x = cache.get(f"events:v1:{s}")
        print(f"{s}: كاشُ العرض {'—' if v is None else len(v.get('events') or [])} · كاشُ المستخرِج "
              f"{'—' if x is None else len(x.get('events') or [])} (عمره {cache.age(f'events:v1:{s}')})")
        try:
            lst = await list_for(s, 60)
            print(f"   قائمةُ «تداول» الآن: {len(lst)} إفصاحاً · " + " · ".join(f"{a.get('date')}" for a in lst[:5]))
            from app.services.material_events import kind_of, events_for
            for a in lst[:12]:
                print(f"     {a.get('date')} · نوعُه {kind_of(a.get('title') or '')} · {str(a.get('title'))[:110]}")
            ev = await events_for(s)
            print(f"   المستخرِجُ الآن: {len(ev.get('events') or [])} حدثاً")
        except Exception as e:                                     # noqa: BLE001
            print(f"   قائمةُ «تداول»: ✘ {type(e).__name__}: {str(e)[:100]}")


asyncio.run(main())
