#!/usr/bin/env python3
"""تحقّقُ ما بعد النشر لـD661 وD662 — قارئٌ فقط.

١ شموعُ تاسي لكلّ إطار: العدد · المدى · ساعاتُ آخر الشموع (ساعةٌ حقيقية = «HH:00» لا يومٌ مجرّد).
٢ تبويبُ «التوقعات» كما تُرجعه نقطتُه: العددُ بجهاته وأصنافه، وأحدثُ تقارير الشركات بسعرها العادل.
"""
import asyncio, collections, json, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None


def data(r):
    return (json.loads(r.body) if getattr(r, "body", None) else r).get("data")


async def main():
    from app.api.v1.endpoints.market import get_price_history, get_forecasts
    print("═ ١ إطاراتُ الرسم")
    for sym in ("^TASI", "2222"):
        for tf in ("1h", "4h", "1d", "1wk", "1mo"):
            if sym == "2222" and tf not in ("1h", "4h"):
                continue
            d = data(await get_price_history(sym, tf=tf)) or []
            hrs = sorted({str(b["date"])[11:16] for b in d[-30:]}) if d and len(str(d[-1]["date"])) > 10 else []
            days = len({str(b["date"])[:10] for b in d})
            print(f"  {sym:>6} {tf:>3}: {len(d):>4} شمعة · {days} يوماً · {d[0]['date'] if d else '—'} ← {d[-1]['date'] if d else '—'}"
                  + (f" · ساعات {hrs}" if hrs else " · بلا ساعات"))
            if sym == "^TASI" and tf == "1h" and d:
                print(f"         آخرُ شمعة: {d[-1]}")
    from app.services import tasi_history as TH
    st = {k: v for k, v in (lastgood.load(TH._HOURS_KEY) or {}).items() if isinstance(v, list)}
    print(f"  جلساتٌ رسمية محفوظة: {sorted(st)[-5:]}")

    print("\n═ ٢ تبويبُ التوقعات")
    items = data(await get_forecasts()) or []
    print(f"  {len(items)} بنداً · الجهات {collections.Counter(x.get('source') for x in items).most_common()}")
    print(f"  الأصناف {collections.Counter(x.get('kind') for x in items).most_common()}")
    for x in items[:12]:
        print(f"  {x.get('date')} · {x.get('source')} · {x.get('kind')} · {x.get('title', '')[:60]}"
              + (f" · {x['company']}" if x.get("company") else "") + (f" · عادل {x['fair_value']}" if x.get("fair_value") else ""))
    fv = [x for x in items if x.get("fair_value")]
    print(f"  بسعرٍ عادلٍ من الجهة: {len(fv)} · منها {[(x['company'], x['fair_value'], x['date']) for x in fv[:8]]}")
    no_url = [x for x in items if not x.get("url")]
    print(f"  بلا رابط: {len(no_url)} · بلا تاريخ: {sum(1 for x in items if not x.get('date'))}")


asyncio.run(main())
