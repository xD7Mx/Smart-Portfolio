#!/usr/bin/env python3
"""كاشفُ مصادر شعارات الرموز غير السعودية (‏D743) — قارئٌ فقط: أيُّ مصدرٍ يسلّم شعاراً رسمياً لكلّ رمز؟
يجرّب بحثَ رموز تريدنق فيو (‏logoid ← ملفُّ SVG على خادم شعاراته)، ثمّ parqet، ثمّ FMP — ويطبع الحالةَ والنوعَ والحجم."""
import asyncio
import httpx

SYMS = {"QQQ": "QQQ", "AAPL": "AAPL", "NVDA": "NVDA", "SPY": "SPY", "TSLA": "TSLA", "MSFT": "MSFT", "^GSPC": "SPX", "^IXIC": "IXIC",
        "^DJI": "DJI", "BTC-USD": "BTCUSD", "GC=F": "GC1!", "BZ=F": "BRN1!", "TQQQ": "TQQQ", "META": "META"}
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
     "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"}


async def head(c, url):
    try:
        r = await c.get(url)
        return f"{r.status_code} {r.headers.get('content-type', '')[:20]} {len(r.content)}"
    except Exception as e:                                        # noqa: BLE001
        return f"✘ {type(e).__name__}"


async def main():
    async with httpx.AsyncClient(timeout=12, headers=H, follow_redirects=True) as c:
        for y, tv in SYMS.items():
            logoid = None
            try:
                r = await c.get("https://symbol-search.tradingview.com/symbol_search/v3/",
                                params={"text": tv, "hl": "0", "exchange": "", "lang": "en", "search_type": "", "domain": "production"})
                js = r.json() if r.status_code == 200 else {}
                items = js.get("symbols", js) if isinstance(js, dict) else js
                for it in (items or [])[:5]:
                    lid = it.get("logoid") or it.get("base-currency-logoid") or (it.get("logo") or {}).get("logoid")
                    if lid:
                        logoid = lid
                        print(f"  {y}: بحث {r.status_code} · أوّلُ تطابق {it.get('symbol')} {it.get('exchange')} {it.get('type')} · logoid={lid}")
                        break
                if not logoid:
                    print(f"  {y}: بحث {r.status_code} · بلا logoid · {str(items)[:160]}")
            except Exception as e:                                # noqa: BLE001
                print(f"  {y}: بحث ✘ {type(e).__name__}")
            if logoid:
                print("     tv  ", await head(c, f"https://s3-symbol-logo.tradingview.com/{logoid}.svg"))
            print("     parqet", await head(c, f"https://assets.parqet.com/logos/symbol/{y}?format=png&size=96"))
            print("     fmp   ", await head(c, f"https://financialmodelingprep.com/image-stock/{y}.png"))


asyncio.run(main())
