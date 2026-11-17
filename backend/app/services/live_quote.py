"""السعرُ الحيُّ للرسم وحالةُ السوق (‏D761 · بأمر المالك 2026-11-17).

قال المالك: «في تبويب السوق الأمريكي داخل الرسم البياني اجعله مباشراً — بحدود المسموح، ولو متأخّراً مثل تريدينق فيو — أريد الأرقام
تتحرّك، أريد حيوية… ولازم أعرف إذا السوق مفتوح، مغلق، عطلة».

قِيس على الخادم (‏scripts/audit/live_sources_door.py · 2026-11-17 والسوقُ مفتوح):
  · ياهو ‏`/v7/finance/quote`: ‏NVDA ‏154.47 وزمنُه هو لحظةُ الطلب (‏Nasdaq Real Time Price) و‏`marketState` ‏REGULAR — **مباشر**،
    ويقبل رموزَ العقود (‏OCC) أيضاً. لكنّه محكومٌ بحصّة، فله عدّادٌ مستقلٌّ (‏`yahoo_live`) لا يستنزف حصّةَ التقييم.
  · مسحُ TradingView ‏`america`: ‏NVDA ‏154.45 · ‏`update_mode = delayed_streaming_900` (**مؤجّلٌ ربعَ ساعة**) · ‏`current_session`
    ‏market · وما قبل الافتتاح وبعده — في 0.03 ثانية وبلا حصّة. فهو الاحتياطُ، ويُوسَم «مؤجّل 15 دقيقة» ولا يُعرض كأنّه مباشر.
  · ‏`ksa`: ‏`current_session = out_of_session` بعد إغلاق «تداول» — يكشف العطلةَ التي لا يعرفها الجدول.
ويُخبَّأ الردُّ أربعَ ثوانٍ لكلّ رمز: كلُّ من يشاهد الرمزَ نفسَه يقرأ النداءَ نفسَه.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

from loguru import logger

from app.services.market_session import TV_STATE, YH_STATE, is_saudi, session_for

TTL = 4
TV_EXCH = ("NASDAQ", "NYSE", "AMEX", "CBOE", "NYSE ARCA")
TV_COLS = ["close", "change", "change_abs", "volume", "open", "high", "low", "update_mode", "current_session",
           "premarket_close", "premarket_change", "postmarket_close", "postmarket_change", "description"]


def _num(v):
    return float(v) if isinstance(v, (int, float)) else None


async def yahoo_quotes(symbols: list[str]) -> dict:
    """{رمز: صفُّ ياهو} من ‏`/v7/finance/quote` — بعدّاد ‏`yahoo_live` المستقلّ؛ و{} عند التعذّر أو نفاد الحصّة."""
    import httpx
    from app.services.market_data import market_service as M
    from app.services.usage_tracker import can_call, record
    if not symbols or not can_call("yahoo_live"):
        return {}
    record("yahoo_live")
    try:
        crumb = await M.primary._crumb()
    except Exception:                                             # noqa: BLE001
        crumb = None
    p = {"symbols": ",".join(symbols)}
    if crumb:
        p["crumb"] = crumb[0]
    H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        async with httpx.AsyncClient(timeout=6, headers=H, cookies=(crumb[1] if crumb else {}), follow_redirects=True) as c:
            for host in ("query1", "query2"):
                r = await c.get(f"https://{host}.finance.yahoo.com/v7/finance/quote", params=p)
                if r.status_code == 200:
                    rows = ((r.json().get("quoteResponse") or {}).get("result")) or []
                    return {str(q.get("symbol") or "").upper(): q for q in rows}
    except Exception as e:                                        # noqa: BLE001
        logger.debug("السعرُ الحيّ/ياهو: {}", type(e).__name__)
    return {}


def _tv_blocking(market: str, tickers: list[str], cols: list[str]) -> dict:
    from curl_cffi import requests as cr
    body = {"symbols": {"tickers": tickers, "query": {"types": []}}, "columns": cols}
    with cr.Session(impersonate="chrome") as s:
        r = s.post(f"https://scanner.tradingview.com/{market}/scan", data=json.dumps(body), timeout=8,
                   headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"})
    if r.status_code != 200:
        return {}
    return {row.get("s"): dict(zip(cols, row.get("d") or [])) for row in (json.loads(r.text or "{}").get("data") or [])}


async def tv_scan(market: str, tickers: list[str], cols: list[str] = TV_COLS) -> dict:
    try:
        return await asyncio.to_thread(_tv_blocking, market, tickers, cols)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("السعرُ الحيّ/TradingView: {}", type(e).__name__)
        return {}


def from_yahoo(q: dict) -> dict:
    st = YH_STATE.get(str(q.get("marketState") or ""))
    ext = None
    if st == "pre" and _num(q.get("preMarketPrice")):
        ext = {"kind": "pre", "price": _num(q.get("preMarketPrice")), "change": _num(q.get("preMarketChange")), "change_pct": _num(q.get("preMarketChangePercent"))}
    elif st in ("post", "closed") and _num(q.get("postMarketPrice")):
        ext = {"kind": "post", "price": _num(q.get("postMarketPrice")), "change": _num(q.get("postMarketChange")), "change_pct": _num(q.get("postMarketChangePercent"))}
    t = q.get("regularMarketTime")
    return {"price": _num(q.get("regularMarketPrice")), "change": _num(q.get("regularMarketChange")), "change_pct": _num(q.get("regularMarketChangePercent")),
            "prev_close": _num(q.get("regularMarketPreviousClose")), "open": _num(q.get("regularMarketOpen")), "high": _num(q.get("regularMarketDayHigh")),
            "low": _num(q.get("regularMarketDayLow")), "volume": _num(q.get("regularMarketVolume")),
            "time": datetime.fromtimestamp(t, tz=timezone.utc).isoformat(timespec="seconds") if isinstance(t, (int, float)) else None,
            "ext": ext, "name": q.get("shortName") or q.get("longName"), "currency": q.get("currency"),
            "earnings": datetime.fromtimestamp(q["earningsTimestamp"], tz=timezone.utc).isoformat(timespec="seconds")
            if isinstance(q.get("earningsTimestamp"), (int, float)) else None,
            "delayed": 0, "source": "ياهو", "_state": st}


def from_tv(row: dict) -> dict:
    st = TV_STATE.get(str(row.get("current_session") or ""))
    ext = None
    if st == "pre" and _num(row.get("premarket_close")):
        ext = {"kind": "pre", "price": _num(row.get("premarket_close")), "change": None, "change_pct": _num(row.get("premarket_change"))}
    elif st in ("post", "closed") and _num(row.get("postmarket_close")):
        ext = {"kind": "post", "price": _num(row.get("postmarket_close")), "change": None, "change_pct": _num(row.get("postmarket_change"))}
    mode = str(row.get("update_mode") or "")
    delayed = int(mode.rsplit("_", 1)[-1]) // 60 if mode.startswith("delayed") and mode.rsplit("_", 1)[-1].isdigit() else 0
    price, chg = _num(row.get("close")), _num(row.get("change_abs"))
    return {"price": price, "change": chg, "change_pct": _num(row.get("change")), "prev_close": (price - chg) if price is not None and chg is not None else None,
            "open": _num(row.get("open")), "high": _num(row.get("high")), "low": _num(row.get("low")), "volume": _num(row.get("volume")),
            "time": None, "ext": ext, "name": row.get("description"), "currency": None, "earnings": None,
            "delayed": delayed, "source": "TradingView", "_state": st}


async def live(symbol: str) -> dict | None:
    """السعرُ الحيُّ وحالةُ السوق لرمزٍ واحد — مخبّأٌ أربعَ ثوانٍ."""
    from app.services import cache
    sym = str(symbol or "").upper().strip()
    if not sym or len(sym) > 24:
        return None
    ck = f"live:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    out = None
    if is_saudi(sym):
        code = sym.replace(".SR", "").replace("^", "")
        rows = await tv_scan("ksa", [f"TADAWUL:{'TASI' if 'TASI' in code else code}"], ["close", "change", "update_mode", "current_session"])
        row = next(iter(rows.values()), None)
        st = TV_STATE.get(str((row or {}).get("current_session") or ""))
        out = {"symbol": sym, "price": None, "session": session_for(sym, st, "TradingView" if st else ""), "source": None}
    else:
        q = (await yahoo_quotes([sym])).get(sym)
        data = from_yahoo(q) if q and _num(q.get("regularMarketPrice")) else None
        if data is None and not sym.startswith("^") and not any(ch.isdigit() for ch in sym):
            rows = await tv_scan("america", [f"{x}:{sym.replace('-', '.')}" for x in TV_EXCH])
            row = max(rows.values(), key=lambda r: r.get("volume") or 0, default=None)
            data = from_tv(row) if row and _num(row.get("close")) else None
        st = (data or {}).pop("_state", None)
        out = {"symbol": sym, **(data or {"price": None}), "session": session_for(sym, st, (data or {}).get("source") or "")}
    out["at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cache.set(ck, out, TTL)
    return out
