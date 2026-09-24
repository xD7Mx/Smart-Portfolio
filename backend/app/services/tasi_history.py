"""تاريخُ «تاسي» من مولّد رسم «تداول» الرسميّ (D438).

ياهو لا يملك لـ`^TASI.SR` إلا يوماً واحداً في كلّ نطاق — قيدٌ دائم، فكان
منحنى المؤشّر فارغاً أبداً. وقِيس بكاشف `tasi_chart_shape.py`: مولّدُ رسم
الصفحة الرئيسية في «تداول» يردّ جلسةَ آخرِ يوم تداولٍ كاملةً دقيقةً دقيقة
(‏311 نقطة: `dateTime` و`indexPrice`).

فتُسلَّم منه نقاطٌ بشكل نقاط ياهو نفسِه. ويُحفظ إغلاقُ كلّ جلسةٍ في
`lastgood` فيتكوّن تاريخٌ يوميٌّ حقيقيّ يطول مع الأيام؛ فإذا بلغ يومين
سُلِّم اليوميُّ، وقبل ذلك تُسلَّم الجلسةُ الأخيرة.
"""
from __future__ import annotations

import json
from typing import Optional

from loguru import logger

URL = ("https://www.saudiexchange.sa/tadawul.eportal.charts.v2/ChartGenerator"
       "?methodType=parsingMethod&chart-type=SQL_MI_MSPV&chart-parameter=tasi"
       "&format=json&pageName=MarketStatusHomeGraph")
SYMBOLS = {"^TASI.SR", "^TASI", "TASI"}
_DAILY_KEY = "market:tasi_daily"
_TTL = 5 * 60


def parse_session(body: str) -> list:
    """جسمُ المولّد ← نقاطٌ بشكل الرسم (date/time/open/high/low/close)."""
    try:
        rows = json.loads(body)
    except Exception:                                             # noqa: BLE001
        return []
    out = []
    for r in rows if isinstance(rows, list) else []:
        p, dt = r.get("indexPrice"), str(r.get("dateTime") or "")
        if not isinstance(p, (int, float)) or p <= 0 or len(dt) < 16:
            continue
        out.append({"date": dt[:16], "time": 0, "open": p, "high": p,
                    "low": p, "close": p, "volume": 0})
    return out


def candles(session: list, minutes: int = 5) -> list:
    """نقاطُ الدقيقة ← شموعُ خمسِ دقائق حقيقية (فتحٌ · أعلى · أدنى · إغلاق).

    ‏D460: كان كلُّ نقطةٍ شمعةً فتحُها وأعلاها وأدناها وإغلاقُها واحد — فتُرسم
    خطوطاً مسطّحةً لا تُرى. والشمعةُ من أسعار دقائقها.
    """
    out: list = []
    for p in session:
        d = p["date"]
        hh, mm = int(d[11:13]), int(d[14:16])
        key = f"{d[:11]}{hh:02d}:{mm - mm % minutes:02d}"
        c = p["close"]
        if out and out[-1]["date"] == key:
            b = out[-1]
            b["high"], b["low"], b["close"] = max(b["high"], c), min(b["low"], c), c
        else:
            out.append({"date": key, "time": 0, "open": c, "high": c, "low": c,
                        "close": c, "volume": 0})
    return out


def remember_close(session: list) -> list:
    """يُحفظ يومُ الجلسة شمعةً كاملة (فتحُها وأعلاها وأدناها وإغلاقُها)."""
    from app.services import lastgood
    daily = dict(lastgood.load(_DAILY_KEY) or {})
    daily.pop("_stale_since", None)
    if session:
        cl = [p["close"] for p in session]
        daily[session[-1]["date"][:10]] = {"open": cl[0], "high": max(cl),
                                           "low": min(cl), "close": cl[-1]}
        lastgood.save(_DAILY_KEY, daily)
    out = []
    for d, v in sorted(daily.items()):
        if isinstance(v, dict):
            out.append({"date": d, "time": 0, **{k: v[k] for k in ("open", "high", "low", "close")},
                        "volume": 0})
        elif isinstance(v, (int, float)):
            out.append({"date": d, "time": 0, "open": v, "high": v, "low": v,
                        "close": v, "volume": 0})
    return out


MIN_DAILY = 20    # دون عشرين يوماً محفوظاً تُعرض الجلسةُ كاملةً شموعاً لا نقطتان


async def history(range_: str = "3mo") -> Optional[list]:
    from app.services import cache
    ck = f"hist:tadawul:tasi:{range_}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    try:
        from app.services.tadawul_http import fetch
        st, body = await fetch(URL)
        session = parse_session(body) if st == 200 else []
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"tasi history: {type(e).__name__}: {e}")
        session = []
    daily = remember_close(session)
    keep = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 260}.get(range_, 132)
    pts = daily[-keep:] if (len(daily) >= MIN_DAILY or not session) else candles(session)
    if len(pts) < 2:
        return None
    cache.set(ck, pts, _TTL)
    return pts
