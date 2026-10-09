#!/usr/bin/env python3
"""كاشفُ الطلب البارد لإفصاحات «تداول» — قارئٌ فقط. يتتبّع أوّلَ طلبٍ في العمليّة خطوةً خطوة."""
import asyncio, json, sys, time
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
import app.services.tadawul_disclosure as TD
import app.services.tadawul_http as TH

_sf = TH.smart_fetch


async def traced(url, **kw):
    t = time.time()
    try:
        st, raw = await _sf(url, **kw)
    except Exception as e:                                         # noqa: BLE001
        print(f"   smart_fetch ✘ {type(e).__name__}: {str(e)[:120]}")
        raise
    n = None
    try:
        n = len((json.loads(raw) or {}).get("announcementList") or [])
    except Exception:                                              # noqa: BLE001
        pass
    print(f"   smart_fetch {kw.get('method', 'GET')} → {st} · {len(raw or '')} حرفاً · صفوف {n} · {time.time() - t:.1f}ث")
    return st, raw
TH.smart_fetch = traced


async def main():
    print("النقطةُ في الكاش:", cache.get("tadawul:annlist:ep"))
    ep = await TD._endpoint()
    print("النقطةُ المكتشفة:", ep)
    for i in range(3):
        rows = await TD.list_for("2080", 60)
        print(f"المحاولة {i + 1}: {len(rows)} إفصاحاً")
    from app.services.material_events import events_for
    print("المستخرِج:", len((await events_for("2080")).get("events") or []))


asyncio.run(main())
