#!/usr/bin/env python3
"""كاشفُ نصوص المفكرة (سؤالُ المالك 2026-10-10: «أُحبَط حين لا أرى تفاصيلَ لعنوان الخبر — تداول أم أرقام؟») — قارئٌ فقط.

لكلّ حدثٍ في مفكرة السوق (الأحدثِ أوّلاً) يُسأل البابُ نفسُه الذي تسأله النافذة (`/announcement-text` ثمّ
`/event-detail`) ويُطبع: مصدرُ الحدث · هل وصل نصّ · من أين (تداول كامل · أرقام كامل · أرقام ملخّصٌ مقفل · لا شيء)
· طولُه. ثمّ الحصيلةُ بالمصدر، وعيّنةٌ ممّا بلا نصّ ليُعرف صنفُه.
"""
import asyncio, collections, json, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None

N = 70


def data(r):
    return (json.loads(r.body) if getattr(r, "body", None) else r).get("data")


async def main():
    from app.services.content_engine import market_wide_events, clean_events, _cal_load_store
    from app.api.v1.endpoints.market import get_announcement_text, get_event_detail
    from app.data.market_universe import MARKET_UNIVERSE
    store = _cal_load_store() or {}
    print(f"═ المخزن: {len(store)} حدثاً · المصادر {collections.Counter(e.get('source') for e in store.values()).most_common()}")
    ev = clean_events(await market_wide_events())
    print(f"═ المفكرة المعروضة: {len(ev)} · المصادر {collections.Counter(e.get('source') for e in ev).most_common()}"
          f" · إعلانٌ/موعد {collections.Counter(e.get('date_kind') for e in ev).most_common()}")
    sem = asyncio.Semaphore(4)
    res = []

    async def one(e):
        async with sem:
            name = (MARKET_UNIVERSE.get(str(e.get("symbol") or "")) or {}).get("name_ar") or e.get("company_name") or ""
            got, src, n, locked = None, "—", 0, False
            try:
                if e.get("detail_id"):
                    t = (data(await get_event_detail(str(e["detail_id"]))) or {}).get("text")
                    if t:
                        got, src, n = "تفصيلُ أرقام", "أرقام/تفصيل", len(t)
                if not got and (e.get("symbol") or "argaam.com" in (e.get("url") or "")):
                    d = data(await get_announcement_text(symbol=e.get("symbol") or "", title=e.get("title") or "",
                                                          date=e.get("date") or "", u=e.get("url") or "", name=name)) or {}
                    if d.get("text"):
                        got, src, n = True, d.get("source"), len(d["text"])
                        locked = d.get("full") is False or bool(d.get("locked"))
            except Exception as ex:                                # noqa: BLE001
                src = f"✘ {type(ex).__name__}"
            res.append({**e, "_src": src, "_n": n, "_locked": locked, "_got": bool(got)})

    await asyncio.gather(*(one(e) for e in ev[:N]))
    by = collections.defaultdict(collections.Counter)
    for r in res:
        k = "بلا نصّ" if not r["_got"] else (f"{r['_src']} · ملخّصٌ مقفل" if r["_locked"] else f"{r['_src']} · كامل")
        by[r.get("source")][k] += 1
    print(f"\n═ أوّلُ {len(res)} حدثاً — مصدرُ الحدث ← ما يظهر في النافذة")
    for s, c in by.items():
        print(f"  {s}: {dict(c)}")
    lens = [r["_n"] for r in res if r["_got"]]
    print(f"  أطوالُ النصوص: أدنى {min(lens) if lens else 0} · وسيط {sorted(lens)[len(lens)//2] if lens else 0}")
    print("\n═ عيّنةٌ بلا نصّ أو بملخّصٍ مقفل:")
    for r in [r for r in res if not r["_got"] or r["_locked"]][:25]:
        print(f"  {r.get('date')} · {r.get('source')} · {r.get('type')} · {r.get('symbol')} · {(r.get('title') or '')[:70]} · {r['_src']} · {(r.get('url') or '')[-45:]}")
    print("\n═ عيّنةٌ بنصّ:")
    for r in [r for r in res if r["_got"] and not r["_locked"]][:8]:
        print(f"  {r.get('date')} · {r.get('source')} · {(r.get('title') or '')[:60]} ← {r['_src']} ({r['_n']} حرفاً)")


asyncio.run(main())
