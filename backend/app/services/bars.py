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


def _gap_min(a: str, b: str) -> float | None:
    """الدقائقُ بين شمعتين دون اليوم («‏YYYY-MM-DD HH:MM») — وما لا يُقرأ لا يُحكم به."""
    try:
        f = "%Y-%m-%d %H:%M"
        return (_dt.datetime.strptime(str(b)[:16], f) - _dt.datetime.strptime(str(a)[:16], f)).total_seconds() / 60
    except Exception:                                             # noqa: BLE001
        return None


def clean_intraday(rows: list) -> list:
    """دون اليوم: مرتَّبٌ بلا تكرار، وكلُّ شمعةٍ مسطّحةٍ بلا حجمٍ في سلسلةٍ لها حجمٌ ساعةٌ بلا صفقة — لا شمعة (تريدنق فيو لا يرسم
    ساعةً لم يُتداول فيها). فإن كانت آخرَ جلستها (لا شمعةَ بعدها في ثلاث ساعات) فهي علامةُ الإغلاق: سعرُها إغلاقُ الشمعة التي قبلها.
    والجلسةُ تُعرف بالقُرب لا بتاريخ التقويم — إغلاقُ نيويورك منتصفُ ليل الرياض (‏D738)، وقِيست مسطّحاتٌ وسطَ ساعات تاسي
    والنفط والذهب بعد نشر D735 (‏D739)."""
    out: list = []
    for r in sorted((x for x in rows or [] if _ok(x)), key=lambda x: str(x["date"])):
        r = _fix(r)
        if out and out[-1]["date"] == r["date"]:
            out[-1] = _merge(out[-1], r)
        else:
            out.append(r)
    if not (sum(1 for r in out if r.get("volume")) > len(out) / 2):
        return out
    kept: list = []
    for i, r in enumerate(out):
        if not (_is_flat(r) and not r.get("volume")):
            kept.append(r)
            continue
        nxt = out[i + 1] if i + 1 < len(out) else None
        g_prev = _gap_min(kept[-1]["date"], r["date"]) if kept else None
        g_next = _gap_min(r["date"], nxt["date"]) if nxt else None
        if kept and g_prev is not None and 0 < g_prev <= 180 and (g_next is None or g_next > 180):
            p = kept[-1]
            kept[-1] = {**p, "high": max(p["high"], r["close"]), "low": min(p["low"], r["close"]), "close": r["close"]}
    return kept


def _mins(stamp: str) -> int:
    return int(stamp[11:13]) * 60 + int(stamp[14:16])


def _agg(group: list, date: str) -> dict:
    out = {"date": date, "open": group[0]["open"], "high": max(g["high"] for g in group), "low": min(g["low"] for g in group),
           "close": group[-1]["close"], "volume": sum((g.get("volume") or 0) for g in group)}
    if any(g.get("basis") for g in group):                        # ‏D739: شمعةٌ فيها يومٌ من الإغلاقات وحدها تُوسَم كذلك
        out["basis"] = "close"
    return out


def _utc_min(stamp: str) -> int | None:
    """دقائقُ التوقيت العالميّ منذ 1970 لختمٍ بساعة الرياض (‏UTC+3 ثابتٌ بلا توقيتٍ صيفيّ)."""
    try:
        t = _dt.datetime.strptime(str(stamp)[:16], "%Y-%m-%d %H:%M")
        return int((t - _dt.datetime(1970, 1, 1)).total_seconds() // 60) - 180
    except Exception:                                             # noqa: BLE001
        return None


def session_mode(symbol: str) -> str:
    """كيف تُثبَّت الإطاراتُ المجمَّعة دون اليوم — كتريدنق فيو:
    «day» الأسهمُ والمؤشّرات: من افتتاح جلستها كلَّ يوم (الرياض 10:00 · نيويورك 9:30).
    «gap» العقودُ الآجلة والعملات (تداولٌ شبهُ متّصل بفاصلٍ يوميّ): من أوّل شمعةٍ بعد الفاصل — افتتاحُ جلستها.
    «utc» العملاتُ المشفّرة (بلا فاصل): من منتصف ليل التوقيت العالميّ — 00:00 و04:00 و08:00…"""
    s = str(symbol or "").upper()
    if re.search(r"-(USD|USDT|EUR|BTC|ETH)$", s):
        return "utc"
    if s.endswith("=F") or s.endswith("=X"):
        return "gap"
    return "day"


def bucket_intraday(rows: list, minutes: int, mode: str = "day", base: int = 60) -> list:
    """شموعٌ دون اليوم ← إطارٌ أطول، مثبَّتاً بافتتاح الجلسة (‏session_mode): الأسهمُ من أوّل شمعةٍ في يومها (جلسةُ الرياض
    10:00 ⇒ أربعُ ساعات = 10:00 و14:00)، والآجلةُ من أوّل شمعةٍ بعد فاصلها اليوميّ، والمشفّرةُ من منتصف ليل التوقيت العالميّ."""
    if minutes <= 0:
        return rows
    out: list = []
    sess, anchor, key, group, prev_u = None, 0, None, [], None
    for r in rows:
        st = str(r["date"])
        u = _utc_min(st)
        if mode == "utc" and u is not None:
            k = ("u", u // minutes)
        else:
            if mode == "gap" and u is not None:
                new = prev_u is None or u - prev_u > base
            else:
                new = st[:10] != sess
            if new:
                sess, anchor = st[:10], (u if mode == "gap" and u is not None else _mins(st))
            k = (sess, anchor, ((u if mode == "gap" and u is not None else _mins(st)) - anchor) // minutes)
        prev_u = u
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


def finalize(rows: list) -> list:
    """البابُ الأخير قبل الرسم (‏D739) — كلُّ مسارٍ يمرّ منه، فلا تصل الرسمَ شمعةٌ مختلّة (قمّةٌ دون جسمها: قِيست في شهريّ الذهب)
    ولا مكرَّرةٌ ولا غيرُ مرتَّبة ولا خانةُ عطلةٍ أو ساعةٌ بلا صفقة، أيّاً كان مصدرُها أو تجميعُها."""
    rows = [r for r in rows or [] if _ok(r)]
    if not rows:
        return []
    intraday = any(len(str(r["date"])) > 10 for r in rows)
    return (clean_intraday(rows) if intraday else clean_daily(rows))[-MAX_BARS:]


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
