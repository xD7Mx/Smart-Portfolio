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
# ‏D461: التاريخُ اليوميُّ الكامل (2007 → أمس · 4,921 نقطة مقيسة) — نوعُ رسمٍ
# اكتُشف في `indicesGraph.js` بصفحة المؤشّرات، ويربطه «تداول» نفسُه بأزرار المُدد.
URL_DAILY = ("https://www.saudiexchange.sa/tadawul.eportal.charts.v2/ChartGenerator"
             "?methodType=parsingMethod&chart-type=SQL_T_IC_ALL_COM&chart-parameter=tasi"
             "&format=json")
SYMBOLS = {"^TASI.SR", "^TASI", "TASI"}
_KEEP = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 260, "2y": 520, "5y": 1300}
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


def daily_candles(rows: list) -> list:
    """إغلاقاتٌ يومية ← شموعٌ من إغلاق الأمس إلى إغلاق اليوم.

    المصدرُ ينشر الإغلاقَ وحدَه لكلّ يوم؛ فالشمعةُ تفتح عند إغلاق اليوم السابق
    وتُغلق عند إغلاق يومها، وأعلاها وأدناها طرفاها — رسمُ سلسلةِ إغلاقٍ شموعاً.
    """
    out, prev = [], None
    for r in rows if isinstance(rows, list) else []:
        p, dt = r.get("indexPrice"), str(r.get("dateTime") or "")[:10]
        if not isinstance(p, (int, float)) or p <= 0 or len(dt) < 10:
            continue
        o = prev if prev is not None else p
        out.append({"date": dt, "time": 0, "open": o, "high": max(o, p),
                    "low": min(o, p), "close": p, "volume": 0})
        prev = p
    return out


def weekly(rows: list) -> list:
    """شموعٌ يومية ← أسبوعية (فتحُ أوّل يوم · أعلى · أدنى · إغلاقُ آخر يوم).

    ‏D462: ياهو يسلّم السنتين والخمسَ **أسبوعياً** (فاصل 1wk)، وكان تاسي يُسلَّم
    يومياً — فبدت شموعُه في المدّة نفسِها ألفاً وثلاثمئة خيطٍ متراصّ بجانب
    مئتين وستين شمعةً للأسواق العالمية. فالإطارُ واحدٌ للسوقين.
    """
    import datetime as _dt
    out: list = []
    for r in rows:
        d = _dt.date.fromisoformat(r["date"][:10])
        wk = (d - _dt.timedelta(days=(d.weekday() + 1) % 7)).isoformat()   # الأحد
        if out and out[-1]["_wk"] == wk:
            b = out[-1]
            b["high"], b["low"] = max(b["high"], r["high"]), min(b["low"], r["low"])
            b["close"], b["date"] = r["close"], r["date"][:10]
            b["volume"] = (b.get("volume") or 0) + (r.get("volume") or 0)
        else:
            out.append({**r, "date": r["date"][:10], "_wk": wk})
    for b in out:
        b.pop("_wk", None)
    return out


_WEEKLY = {"2y": 104, "5y": 260}


async def history(range_: str = "3mo") -> Optional[list]:
    """تاريخُ تاسي لمدّة الرسم: يوميٌّ رسميٌّ كامل + جلسةُ اليوم شمعةً أخيرة (D461)."""
    from app.services import cache, lastgood
    ck = f"hist:tadawul:tasi:v3:{range_}"
    hit = cache.get(ck)
    if hit is not None:
        return hit
    from app.services.tadawul_http import fetch
    daily = cache.get("hist:tadawul:tasi:daily")
    if daily is None:
        try:
            st, body = await fetch(URL_DAILY)
            daily = daily_candles(json.loads(body)) if st == 200 and body else []
        except Exception as e:                                    # noqa: BLE001
            logger.warning(f"tasi daily: {type(e).__name__}: {e}")
            daily = []
        if daily:
            cache.set("hist:tadawul:tasi:daily", daily, 6 * 3600)
            lastgood.save("market:tasi_daily_full", {"rows": daily[-1400:]})
        else:
            daily = ((lastgood.load("market:tasi_daily_full") or {}).get("rows")) or []
    try:
        st, body = await fetch(URL)
        session = parse_session(body) if st == 200 else []
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"tasi history: {type(e).__name__}: {e}")
        session = []
    remember_close(session)
    pts = list(daily)
    if session:
        day = session[0]["date"][:10]
        cl = [p["close"] for p in session]
        o = pts[-1]["close"] if pts and pts[-1]["date"] < day else cl[0]
        today = {"date": day, "time": 0, "open": o, "high": max(cl + [o]),
                 "low": min(cl + [o]), "close": cl[-1], "volume": 0}
        pts = [p for p in pts if p["date"] < day] + [today]
    if len(pts) < 2:
        c = candles(session)
        return c if len(c) >= 2 else None
    if range_ in _WEEKLY:
        pts = weekly(pts)[-_WEEKLY[range_]:]
    else:
        pts = pts[-_KEEP.get(range_, 132):]
    cache.set(ck, pts, _TTL)
    return pts
