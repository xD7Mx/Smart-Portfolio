"""سعرُ برنت مباشراً — طبقاتٌ مقيسةٌ مرتَّبة، والغيابُ يُقال (D435).

    from app.services.commodity_quote import brent_quote
    q = await brent_quote()   # {"price","change","change_pct","source","delayed",...}

## لماذا

قال المالك: «حالةُ السوق لنفط برنت تعمل في حين أنّ الرقم لا يظهر… أشعر
أنّنا لم نذهب للمدى الذي نستطيع الوصولَ إليه لإيجاد مصدرٍ مباشرٍ لسعر برنت».

وكان برنت من ياهو وحدَه (‏`BZ=F`) عبر `get_price` — وياهو محكومٌ بحصّتنا
الداخلية (‏`can_call("yahoo")`) التي تستنفدها مسحاتُ التقييم، فتخلو البطاقة.
وقِيس بكاشف `scripts/audit/brent_sources.py` على الخادم:

  · «TradingView» ‏`FX:UKOIL` — **مباشر** (`streaming`) · 103.44
  · ‏`ICEEUR:BRN1!` — مؤجَّلٌ عشر دقائق (`delayed_streaming_600`) · 103.08
  · ياهو ‏`BZ=F` — 98.4: متأخّرٌ عن السوق نحو 5٪.

## الترتيب

  ١· المباشرُ (‏`FX:UKOIL`)
  ٢· المؤجَّلُ (‏`ICEEUR:BRN1!`) موسوماً `delayed = True`
  ٣· ياهو
  ٤· آخرُ رقمٍ محفوظٍ **بزمنه** (‏`stale_since`) — لا فراغ ولا اختلاق
  ٥· وإلا `None` صريح

والجلبُ بانتحال بصمة المتصفّح في خيطٍ منفصل (‏`docs/FETCH_METHOD.md`)،
ومحفوظٌ ثلاثين ثانية: أقصرُ من أيّ تحديثٍ يُرى، فلا يُضرَب المصدرُ مع كلّ
طلب.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from loguru import logger

CACHE_KEY = "market:brent:live"
STORE_KEY = "market:brent"
TTL = 30
LIVE, DELAYED = "FX:UKOIL", "ICEEUR:BRN1!"
_COLS = ["close", "change", "change_abs", "update_mode"]


def _blocking_scan(tickers: list[str]) -> dict:
    from curl_cffi import requests as cr
    body = {"symbols": {"tickers": tickers, "query": {"types": []}},
            "columns": _COLS}
    with cr.Session(impersonate="chrome") as s:
        r = s.post("https://scanner.tradingview.com/cfd/scan",
                   data=json.dumps(body), timeout=10,
                   headers={"Content-Type": "application/json",
                            "Origin": "https://www.tradingview.com",
                            "Referer": "https://www.tradingview.com/"})
    if r.status_code != 200:
        return {}
    out = {}
    for row in (json.loads(r.text or "{}").get("data") or []):
        out[row.get("s")] = dict(zip(_COLS, row.get("d") or []))
    return out


async def _tv_scan(tickers: list[str]) -> dict:
    """{رمز: {close, change, change_abs, update_mode}} — أو {} عند التعذّر."""
    try:
        return await asyncio.to_thread(_blocking_scan, tickers)
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"برنت/TradingView تعذّر: {type(e).__name__}: {e}")
        return {}


async def _yahoo_brent() -> dict | None:
    try:
        from app.services.market_data import market_service
        return await market_service.get_price("BZ=F")
    except Exception:                                             # noqa: BLE001
        return None


def _num(v):
    return float(v) if isinstance(v, (int, float)) else None


def _from_tv(sym: str, row: dict) -> dict | None:
    px = _num(row.get("close"))
    if not px or px <= 0:
        return None
    mode = str(row.get("update_mode") or "")
    return {
        "symbol": "BRENT",
        "price": round(px, 2),
        "change": _num(row.get("change_abs")),
        "change_pct": round(_num(row.get("change")) or 0.0, 2),
        "currency": "USD",
        "source": f"TradingView ({sym})",
        "update_mode": mode,
        "delayed": mode != "streaming",
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


async def brent_quote() -> dict | None:
    from app.services import cache, lastgood
    hit = cache.get(CACHE_KEY)
    if isinstance(hit, dict):
        return hit

    q = None
    rows = await _tv_scan([LIVE, DELAYED])
    for sym in (LIVE, DELAYED):
        if sym in (rows or {}):
            q = _from_tv(sym, rows[sym])
            if q:
                break
    if q is None:
        y = await _yahoo_brent()
        if isinstance(y, dict) and _num(y.get("price")):
            q = {**y, "symbol": "BRENT", "source": "ياهو (BZ=F)",
                 "delayed": True}

    if q is not None:
        cache.set(CACHE_KEY, q, TTL)
        try:
            lastgood.save(STORE_KEY, q)
        except Exception:                                         # noqa: BLE001
            pass
        return q

    last = lastgood.load(STORE_KEY, max_age_seconds=7 * 24 * 3600)
    if isinstance(last, dict) and _num(last.get("price")):
        return {**last, "stale_since": last.get("_stale_since")}
    return None
