#!/usr/bin/env python3
"""مقارنةُ D7M بتريدنق فيو (D465): شموعُ 4001 الأسبوعية كما يقرؤها التطبيق،
وهل تتوفّر شموعٌ لحظيةٌ (15د · ساعة) للأسهم السعودية لصفوف اللوحة. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/d7m_compare_4001.py
"""
import asyncio, json, sys
sys.path.insert(0, "/app")


async def main():
    try:
        from app.services.market_data import YahooFinanceProvider as Y  # noqa
    except Exception:
        Y = None
    from app.services import market_data as md
    y = md.market_service._yahoo()
    for sym, rg, iv in (("4001.SR", "5y", "1wk"), ("4001.SR", "2y", "1d"), ("4001.SR", "5d", "15m"),
                        ("4001.SR", "60d", "60m"), ("2080.SR", "5d", "15m"), ("^TASI.SR", "5d", "15m")):
        pts = await y._fetch_chart_points(sym, rg, iv)
        print(f"{sym} {rg} {iv}: {len(pts)} · آخر {str(pts[-1:])[:160]}")
        if sym == "4001.SR" and iv == "1wk":
            print("BARS " + json.dumps(pts, separators=(",", ":")))
    import httpx
    async with httpx.AsyncClient(timeout=12, headers={"User-Agent": "Mozilla/5.0"}) as c:
        for sym in ("4001.SR", "^TASI.SR"):
            r = await c.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=15m")
            res = (r.json().get("chart", {}).get("result") or [{}])[0]
            ts = res.get("timestamp") or []
            print(f"RAW {sym} 15m: http {r.status_code} · {len(ts)} شمعة · {ts[-1:] }")
    return 0

sys.exit(asyncio.run(main()))
