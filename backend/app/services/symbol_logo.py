"""شعاراتُ الرموز غير السعودية بهويّتها الرسمية (‏D743 · المالك 2026-11-15: «الرموزُ لا تظهر صورُها الحقيقية… QQQ يظهر بأيقونته،
وجميعُ شركات السوق الأمريكيّ تظهر بأيقونتها… لا مشوّهةً بدون أيقونات»).

كانت الواجهةُ تطلب شعارَ السهم الأمريكيّ بلاحقة السوق السعوديّ (‏QQQ.SR) فيفشل كلُّ مصدرٍ ويُرسم حرف. وقِيس على الخادم
(‏logo_sources_door): بحثُ رموز تريدنق فيو يسلّم لكلّ رمزٍ هويّةَ شعاره (‏logoid) وملفُّها على خادم شعاراته يعمل للأسهم والصناديق
(‏invesco لـQQQ) والمؤشّرات (‏s-and-p-500) والمعادن والنفط والعملات المشفّرة — 14 من 14. فالسلسلة: تريدنق فيو ← parqet ← FMP،
ويُحفظ ما نجح على القرص ثلاثين يوماً (والفشلُ يوماً) فلا يُطلب الشعارُ مرّتين.
"""
from __future__ import annotations

import json
import os
import re
import time

import httpx

_H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"}
_OK_TTL, _MISS_TTL = 30 * 86400, 86400
_ALIAS = {"^GSPC": "SPX", "^IXIC": "IXIC", "^DJI": "DJI", "^NDX": "NDX", "^RUT": "RUT", "^VIX": "VIX", "^FTSE": "UKX",
          "^GDAXI": "DAX", "^N225": "NI225", "BZ=F": "BRN1!", "^TASI.SR": "TASI"}


def tv_text(symbol: str) -> str:
    """رمزُ ياهو ← نصُّ بحث تريدنق فيو: المؤشّراتُ بأسمائها هناك، والعقودُ الآجلةُ بالمستمرّ «1!»، والمشفّرةُ والعملاتُ بلا فاصل."""
    s = str(symbol or "").upper().strip()
    if s in _ALIAS:
        return _ALIAS[s]
    if s.endswith("=F"):
        return s[:-2] + "1!"
    if s.endswith("=X"):
        return s[:-2]
    if re.match(r"^[A-Z0-9]+-(USD|USDT|EUR)$", s):
        return s.replace("-", "")
    return s.lstrip("^")


def _dir() -> str:
    d = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "logos")
    os.makedirs(d, exist_ok=True)
    return d


def _key(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", symbol.upper())[:40]


def _cached(symbol: str):
    base = os.path.join(_dir(), _key(symbol))
    try:
        meta = json.load(open(base + ".json", encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        return None
    if time.time() - meta.get("at", 0) > (_OK_TTL if meta.get("type") else _MISS_TTL):
        return None
    if not meta.get("type"):
        return ("miss", None)
    try:
        return (meta["type"], open(base + ".bin", "rb").read())
    except Exception:                                             # noqa: BLE001
        return None


def _store(symbol: str, ctype: str | None, data: bytes | None) -> None:
    base = os.path.join(_dir(), _key(symbol))
    try:
        if ctype and data:
            open(base + ".bin", "wb").write(data)
        json.dump({"type": ctype, "at": time.time()}, open(base + ".json", "w", encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        pass


async def _tv_logoid(c: httpx.AsyncClient, text: str, exchange: str = "") -> str | None:
    r = await c.get("https://symbol-search.tradingview.com/symbol_search/v3/",
                    params={"text": text, "hl": "0", "exchange": exchange, "lang": "en", "search_type": "", "domain": "production"})
    if r.status_code != 200:
        return None
    js = r.json()
    items = js.get("symbols", []) if isinstance(js, dict) else js or []
    plain = text.replace("1!", "")
    ranked = sorted(items[:10], key=lambda it: 0 if re.sub(r"<[^>]+>", "", str(it.get("symbol", ""))).upper() in (text, plain) else 1)
    for it in ranked:
        lid = it.get("logoid") or it.get("base-currency-logoid") or (it.get("logo") or {}).get("logoid")
        if lid:
            return lid
    return None


def _sa_logo_by_name(sym: str) -> str | None:
    """شعارُ الشركة السعودية من الدليل: برمزها، أو باسمها الرسميّ إن كان شعارُها في الدليل على رمزٍ آخر (نُقلت بين السوقين)."""
    try:
        from app.data.saudi_directory import SAUDI_DIRECTORY
    except Exception:                                             # noqa: BLE001
        return None
    row = SAUDI_DIRECTORY.get(sym) or {}
    if row.get("logo"):
        return row["logo"]
    nm = (row.get("name") or "").strip()
    if not nm:
        return None
    for s2, v in SAUDI_DIRECTORY.items():
        if s2 != sym and v.get("logo") and (v.get("name") or "").strip() == nm:
            return v["logo"]
    return None


async def fetch_logo(symbol: str) -> tuple[str, bytes] | None:
    """(النوع، البايتات) أو None — من الذاكرة أوّلاً."""
    s = str(symbol or "").upper().strip()
    # ‏D787: للسعوديّ مفتاحُ ذاكرةٍ جديد — قِيس على الخادم أنّ ما خُبّئ قبله لـ1325 و6022 و4328 صورةٌ واحدةٌ بحجمٍ واحد (826 بايتاً): شعارٌ عامٌّ
    # من بحثٍ بلا سوق، يبقى ثلاثين يوماً ويحجب شعارَ الاسم في الدليل
    ck = f"SA2_{s.split('.')[0]}" if re.match(r"^\d{4}(?:\.SR)?$", s) else symbol
    hit = _cached(ck)
    if hit:
        return None if hit[0] == "miss" else hit
    found = None
    # ‏D787: السهمُ السعوديّ (‏1325.SR) يُبحث في «تداول» برمزه؛ وإن لم يُعرف شعارُه فشعارُ الاسم نفسِه في الدليل (المنقولُ بين السوقين:
    # «حديد وطني» شعارُه في الدليل على رمزه القديم 9513 في «نمو» وصار 1325 في الرئيسية)
    sa = re.match(r"^(\d{4})(?:\.SR)?$", s)
    async with httpx.AsyncClient(timeout=10, headers=_H, follow_redirects=True) as c:
        if sa:
            for url in [u for u in (_sa_logo_by_name(sa.group(1)),) if u]:
                try:
                    r = await c.get(url)
                    if r.status_code == 200 and b"<svg" in r.content[:400]:
                        found = ("image/svg+xml", r.content)
                except Exception:                                 # noqa: BLE001
                    pass
        try:
            lid = None if found else await _tv_logoid(c, sa.group(1) if sa else tv_text(s), "TADAWUL" if sa else "")
            if lid and re.match(r"^[A-Za-z0-9/_.-]+$", lid):
                r = await c.get(f"https://s3-symbol-logo.tradingview.com/{lid}.svg")
                if r.status_code == 200 and b"<svg" in r.content[:400]:
                    found = ("image/svg+xml", r.content)
        except Exception:                                         # noqa: BLE001
            found = None
        for url in ([] if found else [f"https://assets.parqet.com/logos/symbol/{sa.group(1) + '.SR' if sa else s}?format=png&size=96",
                                       f"https://financialmodelingprep.com/image-stock/{s}.png"]):
            try:
                r = await c.get(url)
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/") and len(r.content) > 200:
                    found = (r.headers["content-type"].split(";")[0], r.content)
                    break
            except Exception:                                     # noqa: BLE001
                continue
    _store(ck, found[0] if found else None, found[1] if found else None)
    return found
