"""كاشفٌ (قراءةٌ فقط): هل يسجّل ياهو منحَ الأسهم السعودية تجزئةً؟ وأين الهبوطُ الشهريُّ
الحادّ الذي لا يفسّره تاسي — في أسهمٍ معروفةٍ بالمنح.

    docker exec sp_backend python /app/scripts/audit/bonus_door.py
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")
AST = timezone(timedelta(hours=3))


async def main():
    import httpx
    from app.services import lastgood
    from app.services.stars_backtest import DATA_KEY
    tasi = (lastgood.load(DATA_KEY) or {}).get("tasi") or {}
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(timeout=15, headers=h) as c:
        for s in ("1120", "2222", "1010", "2010", "4200", "1180"):
            r = await c.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.SR?range=max&interval=1mo&events=div,split")
            res = (r.json().get("chart", {}).get("result") or [None])[0] or {}
            spl = [(datetime.fromtimestamp(v["date"], tz=AST).date().isoformat(), v.get("splitRatio"))
                   for v in ((res.get("events") or {}).get("splits") or {}).values()]
            ts = res.get("timestamp") or []
            cl = ((res.get("indicators", {}).get("quote") or [{}])[0]).get("close") or []
            ad = ((res.get("indicators", {}).get("adjclose") or [{}])[0]).get("adjclose") or []
            m = [(datetime.fromtimestamp(t, tz=AST).date().isoformat()[:7], c_, a_) for t, c_, a_ in zip(ts, cl, ad) if c_]
            drops = []
            for (y0, c0, _), (y1, c1, _) in zip(m, m[1:]):
                t0, t1 = tasi.get(y0), tasi.get(y1)
                if c0 and c1 / c0 < 0.8:
                    drops.append([y1, round(c1 / c0, 3), round(t1 / t0, 3) if t0 and t1 else None])
            print("@@BONUS@@" + json.dumps({"s": s, "splits": spl, "drops": drops,
                                             "first": m[:1], "last": m[-1:]}, ensure_ascii=False))


asyncio.run(main())
