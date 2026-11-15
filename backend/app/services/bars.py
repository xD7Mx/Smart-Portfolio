"""شموعُ الرسم البيانيّ: التنظيفُ والتجميع — دوالُّ خالصةٌ تُفحص بنفسها (‏D735 · بأمر المالك 2026-11-15).

قال المالك: «الشموعُ فيها ثغرة… كأنها ديكور ليست حقيقية سواء كانت أسبوع أو يوم… والمؤشّراتُ رسومُها فارغة… واجعل خيارَ
تخصيصٍ في الأطر — مثلاً 6 ساعات — مثل تريدنق فيو». وقِيس على الخادم (‏chart_bars_door) أربعُ ثغراتٍ في ما يصل الرسم:
  ١ شمعةٌ وهميّةٌ في العطلة: لقطةُ «تداول» أُعيد حفظُها يومَ السبت فأُلحقت شمعةً بتاريخه منسوخةً من الخميس.
  ٢ شمعةٌ مكرَّرةُ التاريخ: أسبوعيُّ ياهو يُلحق يومَ اليوم نقطةً فيقع أسبوعان بتاريخٍ واحد — والرسمُ يرفض التكرار فيُعرض
     فارغاً (‏S&P 500 وكلُّ رمزٍ غيرِ سعوديٍّ على الإطار الأسبوعيّ الافتراضيّ).
  ٣ شموعٌ مسطّحةٌ بلا حجمٍ في العطل الرسمية (‏11 من 502 يوماً للراجحي): خانةٌ يملؤها المزوّد لا جلسة.
  ٤ وآخرُ شمعةٍ في الإطار الساعيّ علامةُ الإغلاق: مسطّحةٌ بلا حجم — سعرٌ لا شمعة.
والإطارُ المخصَّص يُجمَّع من أقرب أساسٍ حقيقيّ: دقائقُ من دقائق، وساعاتٌ من الساعة مثبَّتةً بأوّل شمعةٍ في يومها (جلسةُ الرياض
10:00 ⇒ 4 ساعات = 10:00 و14:00 كتريدنق فيو)، وأيامٌ وأسابيعُ وشهورٌ من اليوميّ والشهريّ.
"""
from __future__ import annotations

import datetime as _dt
import re

_TF = re.compile(r"^(\d{1,3})(mo|wk|w|m|h|d)$")
_MAX = {"m": 240, "h": 24, "d": 30, "wk": 12, "mo": 12}
MAX_BARS = 3000


def parse_tf(tf) -> tuple[int, str] | None:
    """«6h» ← (6، "h") · «45m» · «3d» · «2wk» · «1mo». الدقائقُ المضاعِفةُ للستّين ساعاتٌ. وما خرج عن الحدّ لا يُقبل."""
    m = _TF.match(str(tf or "").strip().lower())
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2)
    u = "wk" if u == "w" else u
    if u == "m" and n >= 60 and n % 60 == 0:
        n, u = n // 60, "h"
    return (n, u) if 1 <= n <= _MAX[u] else None


def _ok(r) -> bool:
    try:
        return all(isinstance(r.get(k), (int, float)) and r[k] > 0 for k in ("open", "high", "low", "close"))
    except Exception:                                             # noqa: BLE001
        return False


def _fix(r: dict) -> dict:
    """القمّةُ لا تنزل عن طرفَي الجسم ولا القاعُ يعلوهما — خللُ تقريبٍ في المصدر يُصلَّح بأضيق ما يكفي."""
    hi, lo = max(r["high"], r["open"], r["close"]), min(r["low"], r["open"], r["close"])
    return r if hi == r["high"] and lo == r["low"] else {**r, "high": hi, "low": lo}


def _merge(a: dict, b: dict) -> dict:
    """شمعتان لفترةٍ واحدة ← واحدة: فتحُ الأولى وإغلاقُ الأخيرة وأقصى المدى؛ والحجمُ أكبرُهما (الثانيةُ جزءٌ من الأولى لا زيادةٌ عليها)."""
    return {**a, "high": max(a["high"], b["high"]), "low": min(a["low"], b["low"]), "close": b["close"],
            "volume": max(a.get("volume") or 0, b.get("volume") or 0)}


def _is_flat(r) -> bool:
    return r["open"] == r["high"] == r["low"] == r["close"]


def clean_daily(rows: list) -> list:
    """يوميٌّ نظيف: مرتَّبٌ بلا تكرارِ تاريخ، وبلا خاناتِ العطل (مسطّحةٌ بلا حجمٍ في سلسلةٍ لها حجم)."""
    out: list = []
    for r in sorted((x for x in rows or [] if _ok(x)), key=lambda x: str(x["date"])):
        r = _fix({**r, "date": str(r["date"])[:10]})
        if out and out[-1]["date"] == r["date"]:
            out[-1] = _merge(out[-1], r)
        else:
            out.append(r)
    has_vol = sum(1 for r in out if r.get("volume")) > len(out) / 2
    if has_vol:
        out = [r for r in out if not (_is_flat(r) and not r.get("volume"))]
    return out


def clean_intraday(rows: list) -> list:
    """دون اليوم: مرتَّبٌ بلا تكرار، وعلامةُ الإغلاق (آخرُ شمعةٍ مسطّحةٍ بلا حجم) تُدمج في شمعة يومها الأخيرة — سعرٌ لا شمعة."""
    out: list = []
    for r in sorted((x for x in rows or [] if _ok(x)), key=lambda x: str(x["date"])):
        r = _fix(r)
        if out and out[-1]["date"] == r["date"]:
            out[-1] = _merge(out[-1], r)
        else:
            out.append(r)
    has_vol = sum(1 for r in out if r.get("volume")) > len(out) / 2
    if has_vol and len(out) >= 2:
        last, prev = out[-1], out[-2]
        if _is_flat(last) and not last.get("volume") and str(last["date"])[:10] == str(prev["date"])[:10]:
            out[-2] = {**prev, "high": max(prev["high"], last["high"]), "low": min(prev["low"], last["low"]), "close": last["close"]}
            out.pop()
    return out


def _mins(stamp: str) -> int:
    return int(stamp[11:13]) * 60 + int(stamp[14:16])


def _agg(group: list, date: str) -> dict:
    return {"date": date, "open": group[0]["open"], "high": max(g["high"] for g in group), "low": min(g["low"] for g in group),
            "close": group[-1]["close"], "volume": sum((g.get("volume") or 0) for g in group)}


def bucket_intraday(rows: list, minutes: int) -> list:
    """شموعٌ دون اليوم ← إطارٌ أطول، مثبَّتاً بأوّل شمعةٍ في يومها: جلسةُ الرياض تبدأ 10:00 فالأربعُ ساعات 10:00 و14:00."""
    if minutes <= 0:
        return rows
    out: list = []
    day, anchor, key, group = None, 0, None, []
    for r in rows:
        d = str(r["date"])[:10]
        if d != day:
            day, anchor = d, _mins(str(r["date"]))
        k = (d, (_mins(str(r["date"])) - anchor) // minutes)
        if k != key and group:
            out.append(_agg(group, group[0]["date"]))
            group = []
        key = k
        group.append(r)
    if group:
        out.append(_agg(group, group[0]["date"]))
    return out


def bucket_n(rows: list, n: int) -> list:
    """كلُّ ‏n شمعةٍ متتاليةٍ شمعة (‏3 أيام · أسبوعان · 3 أشهر) — مثبَّتةً بآخر السلسلة فتكون الشمعةُ الجارية كاملةَ البداية."""
    if n <= 1 or not rows:
        return rows
    head = len(rows) % n
    chunks = ([rows[:head]] if head else []) + [rows[i:i + n] for i in range(head, len(rows), n)]
    return [_agg(c, c[0]["date"]) for c in chunks if c]


def weeks(rows: list, sunday_start: bool) -> list:
    """يوميٌّ ← أسبوعيّ بتقويم سوقه: الأحد–الخميس للسعوديّ، والإثنين–الجمعة لغيره — والشمعةُ مؤرَّخةٌ بأوّل أسبوعها."""
    out: list = []
    key, group = None, []
    for r in rows:
        d = _dt.date.fromisoformat(str(r["date"])[:10])
        k = d - _dt.timedelta(days=(d.weekday() + 1) % 7 if sunday_start else d.weekday())
        if k != key and group:
            out.append(_agg(group, key.isoformat()))
            group = []
        key = k
        group.append(r)
    if group:
        out.append(_agg(group, key.isoformat()))
    return out


def months(rows: list) -> list:
    """يوميٌّ ← شهريّ مؤرَّخاً بأوّل شهره."""
    out: list = []
    key, group = None, []
    for r in rows:
        k = str(r["date"])[:7]
        if k != key and group:
            out.append(_agg(group, f"{key}-01"))
            group = []
        key = k
        group.append(r)
    if group:
        out.append(_agg(group, f"{key}-01"))
    return out


def session_day(at: _dt.datetime, live: bool) -> _dt.date:
    """يومُ الجلسة التي تحملها لقطةُ «تداول»: الحيّةُ يومُها؛ والمحفوظةُ خارج الجلسة يومُ آخر جلسةٍ قبل زمن حفظها —
    الجمعةُ والسبتُ يعودان إلى الخميس، وما قبل افتتاح العاشرة يعود إلى يوم التداول السابق."""
    d = at.date()
    if not live and (at.hour * 60 + at.minute) < 10 * 60:
        d -= _dt.timedelta(days=1)
    while d.weekday() in (4, 5):                                  # الجمعة · السبت
        d -= _dt.timedelta(days=1)
    return d


def same_session(a: dict, b: dict, tol: float = 0.0015) -> bool:
    """أهما الجلسةُ نفسُها؟ — الأربعةُ متطابقةٌ في حدود التقريب."""
    try:
        return all(abs(float(a[k]) - float(b[k])) <= tol * max(abs(float(b[k])), 1e-9) for k in ("open", "high", "low", "close"))
    except Exception:                                             # noqa: BLE001
        return False


def live_daily(rows: list, snap: dict | None, at: _dt.datetime | None, live: bool) -> list:
    """الشمعةُ الجاريةُ لليوميّ من جلسة «تداول» الرسمية — تُحدَّث في يومها أو تُفتح ليومٍ جديدٍ **حقيقيّ**، ولا تُنسخ جلسةٌ
    مضت بتاريخ عطلة (عطبُ D735: شمعةُ السبت)."""
    if not rows or not snap or at is None:
        return rows
    c, h, l = snap.get("price"), snap.get("day_high"), snap.get("day_low")
    if not (isinstance(c, (int, float)) and c > 0 and isinstance(h, (int, float)) and isinstance(l, (int, float)) and h >= l > 0):
        return rows
    o = snap.get("day_open") if isinstance(snap.get("day_open"), (int, float)) and snap.get("day_open") > 0 else c
    cur = {"open": o, "high": max(h, o, c), "low": min(l, o, c), "close": c}
    key = session_day(at, live).isoformat()
    last = rows[-1]
    lk = str(last["date"])[:10]
    if lk == key:
        return rows[:-1] + [{**last, **cur, "volume": snap.get("volume") or last.get("volume") or 0}]
    if key > lk and not same_session(cur, last):
        return rows + [{"date": key, **cur, "volume": snap.get("volume") or 0}]
    return rows
