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
    d1 = data(await get_price_history("^TASI", tf="1d")) or []
    flat = sum(1 for b in d1 if min(b["open"], b["close"]) == b["low"] and max(b["open"], b["close"]) == b["high"])
    print(f"  يوميُّ تاسي: {len(d1)} شمعة · بلا ذيلٍ (أعلاها وأدناها طرفاها) {flat} — آخرُ ثلاث {d1[-3:]}")
    # كم يمتدّ فاصلُ الساعة في ياهو لتاسي؟ وهل لليوميّ أعلى وأدنى حقيقيّان؟
    import httpx
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as c:
        for rng, iv in (("6mo", "60m"), ("1y", "60m"), ("2y", "60m"), ("1y", "1d"), ("5y", "1wk"), ("10y", "1mo")):
            try:
                r = await c.get(f"https://query1.finance.yahoo.com/v8/finance/chart/%5ETASI.SR?range={rng}&interval={iv}")
                res = (r.json().get("chart", {}).get("result") or [None])[0] if r.status_code == 200 else None
                ts = (res or {}).get("timestamp") or []
                q = (((res or {}).get("indicators") or {}).get("quote") or [{}])[0]
                hi, lo, cl = q.get("high") or [], q.get("low") or [], q.get("close") or []
                wick = sum(1 for h, l, x in zip(hi, lo, cl) if None not in (h, l, x) and (h > x or l < x))
                from datetime import datetime, timezone, timedelta
                ds = [datetime.fromtimestamp(t, tz=timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M") for t in ts]
                print(f"  ياهو ^TASI.SR {rng}/{iv}: HTTP {r.status_code} · {len(ts)} · {ds[:1]} → {ds[-1:]} · بذيلٍ حقيقيّ {wick}")
            except Exception as e:                                 # noqa: BLE001
                print(f"  ياهو {rng}/{iv}: ✘ {type(e).__name__}")

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
