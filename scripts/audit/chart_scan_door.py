#!/usr/bin/env python3
"""كاشفُ مسح الرسم (‏D784) على الخادم — قراءةٌ لا تكتب شيئاً:
  ١ مستوياتُ «المختصر» الستّة لتاسي من شموعه الحقيقية بحساب الرسم نفسِه (‏chart_tech) — تُقارن بأرقام المالك
     (11486 · 11293 · 10558 · 10330 · 9367 · 9175) على اليوميّ والأسبوعيّ.
  ٢ أيُّ حقول مُصفّي TradingView الفنية تعود للسوقين (اليوميّ و«|1W» الأسبوعيّ و‏MFI/CMF) — قبل البناء عليها.

    docker exec sp_backend python /app/scripts/audit/chart_scan_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")

COLS = ["close", "change", "Value.Traded", "average_volume_10d_calc", "relative_volume_10d_calc", "SMA50", "SMA200", "EMA20", "EMA50",
        "RSI", "RSI[1]", "Stoch.RSI.K", "Stoch.RSI.D", "ADX", "ADX+DI", "ADX-DI", "MoneyFlow", "ChaikinMoneyFlow", "Perf.1M", "Perf.3M",
        "price_52_week_high", "price_52_week_low", "RSI|1W", "Stoch.RSI.K|1W", "Stoch.RSI.D|1W", "ADX|1W", "ADX+DI|1W", "ADX-DI|1W", "EMA50|1W",
        "SMA200|1W", "close|1W", "Recommend.All", "Recommend.All|1W"]


def tv(market: str, tickers: list[str]) -> dict:
    from curl_cffi import requests as cr
    body = {"symbols": {"tickers": tickers, "query": {"types": []}}, "columns": COLS}
    with cr.Session(impersonate="chrome") as s:
        r = s.post(f"https://scanner.tradingview.com/{market}/scan", data=json.dumps(body), timeout=20,
                   headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"})
    print(f"  {market}: HTTP {r.status_code}")
    return {row.get("s"): dict(zip(COLS, row.get("d") or [])) for row in (json.loads(r.text or "{}").get("data") or [])}


async def main():
    from app.services import chart_tech as T
    from app.services.market_data import market_service as M
    print("══ ١ تاسي — المختصرُ الستّة:")
    for tf in ("1d", "1wk"):
        bars = T.clean(await M.get_bars("^TASI.SR", tf))
        f = T.auto_fib(bars, 3, 7)
        if not f:
            print(f"  [{tf}] لا زجزاجَ ({len(bars)} شمعة)")
            continue
        six = sorted((round(f["lines"][lv], 1) for lv in T.SIX), reverse=True)
        print(f"  [{tf}] {len(bars)} شمعة · آخرُها {bars[-1]['date']} {bars[-1]['close']:.1f} · الضلع {f['start']['price']:.1f} ⇐ {f['end']['price']:.1f}")
        print(f"        الستّة: {six}")
        r = T.read(bars, saudi=True, longs_only=True)
        if r:
            print(f"        القراءة: {r.get('setup')} · {r.get('where')} · جودة {r.get('quality')} · {r.get('horizon')} · {r.get('reasons')}")
    print("══ ٢ حقولُ المُصفّي:")
    for market, tick in (("america", ["NASDAQ:NVDA", "NASDAQ:AAPL"]), ("ksa", ["TADAWUL:2222", "TADAWUL:1120"])):
        try:
            rows = await asyncio.to_thread(tv, market, tick)
        except Exception as e:                                    # noqa: BLE001
            print(f"  {market}: تعذّر {type(e).__name__}")
            continue
        for s, row in rows.items():
            miss = [k for k in COLS if row.get(k) is None]
            print(f"  {s}: غائبة {miss or 'لا شيء'}")
            print(f"     RSI {row.get('RSI')} · K {row.get('Stoch.RSI.K')} · K|1W {row.get('Stoch.RSI.K|1W')} · ADX {row.get('ADX')} · MFI {row.get('MoneyFlow')} "
                  f"· CMF {row.get('ChaikinMoneyFlow')} · RVOL {row.get('relative_volume_10d_calc')}")
    # ٣ حجمُ السوق السعوديّ كلِّه من المُصفّي (نداءٌ واحد)
    try:
        from curl_cffi import requests as cr

        def all_ksa():
            body = {"filter": [{"left": "type", "operation": "in_range", "right": ["stock"]}], "columns": ["name", "close", "Stoch.RSI.K", "RSI|1W"],
                    "range": [0, 1000]}
            with cr.Session(impersonate="chrome") as s:
                r = s.post("https://scanner.tradingview.com/ksa/scan", data=json.dumps(body), timeout=20,
                           headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"})
            d = json.loads(r.text or "{}")
            return d.get("totalCount"), len(d.get("data") or [])
        tot, got = await asyncio.to_thread(all_ksa)
        print(f"══ ٣ السوقُ السعوديّ كلُّه من المُصفّي: {got} من {tot}")
    except Exception as e:                                        # noqa: BLE001
        print("══ ٣ تعذّر:", type(e).__name__)

asyncio.run(main())
