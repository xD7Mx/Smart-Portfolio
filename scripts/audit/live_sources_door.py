#!/usr/bin/env python3
"""كاشفٌ مؤقّت (‏D761): مصادرُ الحيويّة للسوق الأمريكيّ — مسحُ TradingView (‏america · ksa) بأعمدة الجلسة وما قبل/بعد السوق،
وحالةُ السوق من ياهو (‏marketState)، والبحثُ عن NIO وGRAB، وتقويمُ الأحداث الاقتصادية للأسبوع. قارئٌ فقط."""
import asyncio, json, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)


def tv(market, tickers, cols):
    from curl_cffi import requests as cr
    body = {"symbols": {"tickers": tickers, "query": {"types": []}}, "columns": cols}
    t0 = time.time()
    with cr.Session(impersonate="chrome") as s:
        r = s.post(f"https://scanner.tradingview.com/{market}/scan", data=json.dumps(body), timeout=12,
                   headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"})
    return r.status_code, (r.text or "")[:700], round(time.time() - t0, 2)


def get(url):
    from curl_cffi import requests as cr
    with cr.Session(impersonate="chrome") as s:
        r = s.get(url, timeout=15)
    return r.status_code, r.text or ""


async def main():
    base = ["close", "change", "change_abs", "volume", "update_mode", "description", "exchange", "type"]
    print("TV america أساس:", tv("america", ["NASDAQ:NVDA", "NYSE:NIO", "AMEX:SPY", "NASDAQ:GRAB"], base))
    for c in ["premarket_close", "premarket_change", "postmarket_close", "postmarket_change", "current_session", "market_status",
              "session", "is_market_open", "time", "lp_time", "high", "low", "open", "Volatility.D", "logoid", "earnings_release_next_date"]:
        st, txt, dt = tv("america", ["NASDAQ:NVDA"], ["close", c])
        print(f"  عمود {c}: {st} {txt[:160]} {dt}ث")
    print("TV ksa:", tv("ksa", ["TADAWUL:2222", "TADAWUL:TASI"], ["close", "change", "update_mode", "current_session"]))
    from app.services.options_chain import _get, search
    d = await _get("/v7/finance/quote", {"symbols": "NVDA,NIO,2222.SR,^GSPC,SPY"})
    for q in ((d or {}).get("quoteResponse") or {}).get("result") or []:
        print("ياهو", q.get("symbol"), q.get("marketState"), q.get("regularMarketPrice"), q.get("regularMarketChangePercent"),
              "قبل", q.get("preMarketPrice"), "بعد", q.get("postMarketPrice"), "زمن", q.get("regularMarketTime"),
              "أرباح", q.get("earningsTimestamp"), q.get("exchangeTimezoneName"), q.get("quoteSourceName"), q.get("exchangeDataDelayedBy"))
    for s in ("NIO", "GRAB", "nio", "Nvidia"):
        r = await search(s)
        print("بحث", s, [x["symbol"] for x in r][:8])
    for url in ("https://nfs.faireconomy.media/ff_calendar_thisweek.json",):
        try:
            st, txt = await asyncio.to_thread(get, url)
            print("تقويم", url, st, len(txt))
            items = json.loads(txt) if st == 200 else []
            print("  عدد", len(items), "مفاتيح", list(items[0].keys()) if items else None)
            for it in [x for x in items if x.get("impact") == "High"][:14]:
                print("  ", it.get("country"), it.get("date"), it.get("title"), "توقّع", it.get("forecast"), "سابق", it.get("previous"), "فعلي", it.get("actual"))
        except Exception as e:                                    # noqa: BLE001
            print("تقويم تعذّر", url, type(e).__name__, e)


asyncio.run(main())
