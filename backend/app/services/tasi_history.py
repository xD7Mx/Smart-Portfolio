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


def remember_close(session: list) -> list:
    """يُضاف إغلاقُ الجلسة إلى السجلّ اليوميّ ويُردّ السجلُّ مرتّباً."""
    from app.services import lastgood
    daily = dict(lastgood.load(_DAILY_KEY) or {})
    daily.pop("_stale_since", None)
    if session:
        last = session[-1]
        daily[last["date"][:10]] = last["close"]
        lastgood.save(_DAILY_KEY, daily)
    return [{"date": d, "time": 0, "open": c, "high": c, "low": c,
             "close": c, "volume": 0} for d, c in sorted(daily.items())]


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
    pts = daily[-keep:] if len(daily) >= 2 else session
    if len(pts) < 2:
        return None
    cache.set(ck, pts, _TTL)
    return pts
