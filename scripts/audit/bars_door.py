#!/usr/bin/env python3
"""كاشفُ إطارات الرسم على الإنتاج (المالك: «الساعةُ والبقيّة ليست حقيقية») — قارئٌ فقط: ما تُرجعه نقطةُ الرسم لكلّ إطار."""
import asyncio, json, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None


async def main():
    from app.api.v1.endpoints.market import get_price_history
    for sym in ("2222", "1120", "^TASI"):
        print(sym)
        for tf in ("1h", "4h", "1d", "1wk", "1mo"):
            try:
                r = await get_price_history(sym, tf=tf)
                d = (json.loads(r.body) if getattr(r, "body", None) else r).get("data") or []
                gaps = sorted({str(b["date"])[11:16] for b in d[-30:]}) if d and len(str(d[-1]["date"])) > 10 else []
                print(f"  {tf:>3}: {len(d):>4} شمعة · {d[0]['date'] if d else '—'} ← {d[-1]['date'] if d else '—'}"
                      + (f" · ساعاتُ آخرِ الشموع {gaps[:8]}" if gaps else ""))
            except Exception as e:                                 # noqa: BLE001
                print(f"  {tf:>3}: ✘ {type(e).__name__}: {str(e)[:120]}")


asyncio.run(main())
