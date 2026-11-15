"""البحثُ في السوق الأمريكي كلِّه وسلسلةُ عقود الخيارات (‏D747 · بأمر المالك 2026-11-15).

«قائمةُ البحث تشمل جميعَ أسهم السوق الأمريكي… وأضف الخيارات — أختار عقدي من هنا، بعد أسبوعٍ أو بعد يومين — تريدنق فيو يدعمه
فندعمه». قِيس على الخادم (‏scripts/audit/report_data_door.py): بحثُ ياهو يعطي الرموزَ بأسمائها وبورصاتها وأنواعها، وسلسلةُ SPY
اثنان وثلاثون أجلاً أقربُها الغد، ولكلّ عقدٍ رمزُه (‏OCC) وسعرُه وعرضُه وطلبُه وكمّيتُه وعقودُه المفتوحة وتذبذبُه الضمنيّ، ورسمُه
اليوميّ من باب الشموع نفسِه. وأسعارُ العقود متأخّرةٌ عند المزوّد (ربعَ ساعة) — فيُقال ذلك ولا يُخفى.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone

from loguru import logger

OPTION_RX = re.compile(r"^([A-Z]{1,6})(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")
SYMBOL_RX = re.compile(r"^[\^A-Z][A-Z0-9.\-=^]{0,14}$")
US_EXCH = {"NMS", "NYQ", "NGM", "NCM", "ASE", "PCX", "BTS", "NAS", "NYS", "ARCA", "BATS", "CBOE", "WCB", "DJI", "SNP", "NIM", "CXI"}
TYPES = {"EQUITY": "سهم", "ETF": "صندوق متداول", "INDEX": "مؤشّر", "MUTUALFUND": "صندوق", "FUTURE": "عقد آجل",
         "CRYPTOCURRENCY": "عملة مشفّرة", "CURRENCY": "عملة"}
EXCH_AR = {"NMS": "ناسداك", "NGM": "ناسداك", "NCM": "ناسداك", "NAS": "ناسداك", "NYQ": "نيويورك", "NYS": "نيويورك", "ASE": "نيويورك أمريكان",
           "PCX": "نيويورك آركا", "ARCA": "نيويورك آركا", "BTS": "باتس", "BATS": "باتس", "CBOE": "شيكاغو", "WCB": "شيكاغو", "SNP": "إس آند بي",
           "DJI": "داو جونز", "NIM": "ناسداك", "CXI": "شيكاغو"}


def parse_option(sym: str) -> dict | None:
    """رمزُ العقد (‏OCC): الأصلُ ثمّ الأجلُ (سنة شهر يوم) ثمّ النوعُ ثمّ سعرُ التنفيذ × 1000."""
    m = OPTION_RX.match(str(sym or "").upper())
    if not m:
        return None
    root, yy, mm, dd, cp, k = m.groups()
    try:
        exp = datetime(2000 + int(yy), int(mm), int(dd)).date().isoformat()
    except ValueError:
        return None
    return {"root": root, "expiry": exp, "type": "call" if cp == "C" else "put", "strike": int(k) / 1000}


async def _get(path: str, params: dict | None = None, timeout: float = 14) -> dict | None:
    import httpx
    from app.services.market_data import market_service as M
    from app.services.usage_tracker import can_call, record
    if not can_call("yahoo"):
        return None
    record("yahoo")
    crumb = None
    try:
        crumb = await M.primary._crumb()
    except Exception:                                             # noqa: BLE001
        crumb = None
    p = dict(params or {})
    if crumb:
        p["crumb"] = crumb[0]
    H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(timeout=timeout, headers=H, cookies=(crumb[1] if crumb else {}), follow_redirects=True) as c:
        for host in ("query2", "query1"):
            try:
                r = await c.get(f"https://{host}.finance.yahoo.com{path}", params=p)
                if r.status_code == 200:
                    return r.json()
            except Exception:                                     # noqa: BLE001
                continue
    return None


def shape_search(quotes: list[dict]) -> list[dict]:
    """نتائجُ البحث: الأمريكيُّ أوّلاً، ثمّ غيرُه — بالرمز والاسم والبورصة والنوع، ولا عقودَ خياراتٍ هنا (لها سلسلتُها)."""
    out = []
    for q in quotes or []:
        sym, typ = str(q.get("symbol") or "").upper(), str(q.get("quoteType") or "")
        if not sym or typ not in TYPES or not SYMBOL_RX.match(sym):
            continue
        ex = str(q.get("exchange") or "")
        us = ex in US_EXCH
        out.append({"symbol": sym, "name": q.get("longname") or q.get("shortname") or sym, "type": TYPES[typ],
                    "exchange": EXCH_AR.get(ex, q.get("exchDisp") or ex), "us": us,
                    "options": us and typ in ("EQUITY", "ETF")})
    out.sort(key=lambda x: (not x["us"],))
    return out[:12]


async def search(q: str) -> list[dict]:
    from app.services import cache
    q = re.sub(r"\s+", " ", str(q or "")).strip()[:32]
    if not q:
        return []
    ck = f"ysearch:{q.lower()}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    d = await _get("/v1/finance/search", {"q": q, "quotesCount": 16, "newsCount": 0, "listsCount": 0, "enableFuzzyQuery": "false"})
    if d is None:
        return []
    out = shape_search(d.get("quotes") or [])
    cache.set(ck, out, 3600)
    return out


def _row(o: dict) -> dict:
    f = lambda k: (float(o[k]) if isinstance(o.get(k), (int, float)) else None)   # noqa: E731
    return {"contract": o.get("contractSymbol"), "strike": f("strike"), "last": f("lastPrice"), "bid": f("bid"), "ask": f("ask"),
            "change": f("change"), "pct": f("percentChange"), "volume": int(o["volume"]) if isinstance(o.get("volume"), (int, float)) else None,
            "oi": int(o["openInterest"]) if isinstance(o.get("openInterest"), (int, float)) else None,
            "iv": round(float(o["impliedVolatility"]) * 100, 1) if isinstance(o.get("impliedVolatility"), (int, float)) else None,
            "itm": bool(o.get("inTheMoney")),
            "last_trade": datetime.fromtimestamp(o["lastTradeDate"], tz=timezone.utc).isoformat() if isinstance(o.get("lastTradeDate"), (int, float)) else None}


def shape_chain(res: dict, now: float | None = None) -> dict:
    """السلسلةُ لأجلٍ واحد: الآجالُ كلُّها بأيامها الباقية، وعقودُ الشراء والبيع مرتّبةً بسعر التنفيذ."""
    now = now or time.time()
    q = res.get("quote") or {}
    exps = []
    for t in res.get("expirationDates") or []:
        if not isinstance(t, (int, float)):
            continue
        d = datetime.fromtimestamp(t, tz=timezone.utc).date()
        exps.append({"t": int(t), "date": d.isoformat(), "dte": max(0, (d - datetime.fromtimestamp(now, tz=timezone.utc).date()).days)})
    op = (res.get("options") or [{}])[0]
    calls = sorted((_row(o) for o in op.get("calls") or [] if o.get("contractSymbol")), key=lambda r: r["strike"] or 0)
    puts = sorted((_row(o) for o in op.get("puts") or [] if o.get("contractSymbol")), key=lambda r: r["strike"] or 0)
    t0 = op.get("expirationDate")
    return {"symbol": res.get("underlyingSymbol") or q.get("symbol"), "name": q.get("longName") or q.get("shortName"),
            "price": q.get("regularMarketPrice"), "change_pct": q.get("regularMarketChangePercent"), "currency": q.get("currency") or "USD",
            "expirations": exps, "expiry": int(t0) if isinstance(t0, (int, float)) else (exps[0]["t"] if exps else None),
            "calls": calls, "puts": puts, "delayed": True}


async def chain(symbol: str, date_t: int | None = None) -> dict | None:
    from app.services import cache
    sym = str(symbol or "").upper().strip()
    if not SYMBOL_RX.match(sym) or sym.endswith(".SR") or sym.isdigit():
        return None
    ck = f"ochain:{sym}:{date_t or 0}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    d = await _get(f"/v7/finance/options/{sym}", {"date": int(date_t)} if date_t else None)
    res = ((d or {}).get("optionChain") or {}).get("result") or []
    if not res:
        logger.info("الخيارات: لا سلسلةَ لـ{}", sym)
        return None
    out = shape_chain(res[0])
    cache.set(ck, out, 60)
    return out
