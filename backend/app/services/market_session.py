"""حالةُ السوق كتريدنق فيو (‏D761 · بأمر المالك 2026-11-17).

قال المالك: «علامةٌ بجانب اسم الشركة — رمزٌ للسوق مثل تريدينق فيو بالضبط: مفتوح، قبل الماركت، بعد الماركت… مغلق، عطلة —
والسوقُ الأمريكيّ لازم يكون مدعوماً».

الحالةُ من جدول البورصة نفسِه (‏NYSE/Nasdaq بتوقيت نيويورك · «تداول» بتوقيت الرياض) وعطلِها المعلنة، ثمّ يُقدَّم عليها ما يقوله
المصدرُ الحيّ إن قاله (‏TradingView ‏`current_session` · ياهو ‏`marketState`) — فإغلاقٌ طارئٌ لا يعرفه الجدولُ يظهر كما هو.
وعطلُ «تداول» الثابتةُ وحدَها تُسمّى (يومُ التأسيس واليومُ الوطنيّ)؛ وعطلتا العيدين يُعلنهما السوقُ كلَّ عام فلا تُخترع تواريخُهما —
يُكتشف الإغلاقُ من المصدر الحيّ ويُقال «عطلة» بلا اسم.
"""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo

NY, RY = ZoneInfo("America/New_York"), ZoneInfo("Asia/Riyadh")

# عطلُ بورصة نيويورك المعلنة (‏NYSE Holidays) — والإغلاقُ المبكّر الساعةَ الواحدة
US_HOLIDAYS = {
    "2026-01-01": "رأس السنة", "2026-01-19": "يوم مارتن لوثر كينغ", "2026-02-16": "يوم الرؤساء", "2026-04-03": "الجمعة العظيمة",
    "2026-05-25": "يوم الذكرى", "2026-06-19": "يوم جونتينث", "2026-07-03": "يوم الاستقلال", "2026-09-07": "عيد العمّال",
    "2026-11-26": "عيد الشكر", "2026-12-25": "عيد الميلاد",
    "2027-01-01": "رأس السنة", "2027-01-18": "يوم مارتن لوثر كينغ", "2027-02-15": "يوم الرؤساء", "2027-03-26": "الجمعة العظيمة",
    "2027-05-31": "يوم الذكرى", "2027-06-18": "يوم جونتينث", "2027-07-05": "يوم الاستقلال", "2027-09-06": "عيد العمّال",
    "2027-11-25": "عيد الشكر", "2027-12-24": "عيد الميلاد",
}
US_EARLY = {"2026-11-27", "2026-12-24", "2027-11-26"}
SA_FIXED = {"02-22": "يوم التأسيس", "09-23": "اليوم الوطني"}

LABEL = {"pre": "قبل الافتتاح", "open": "السوق مفتوح", "post": "بعد الإغلاق", "closed": "السوق مغلق", "holiday": "عطلة",
         "auction": "مزاد الإغلاق", "preopen": "مزاد الافتتاح"}


def is_saudi(symbol: str) -> bool:
    s = str(symbol or "").upper()
    return s.endswith(".SR") or s.isdigit() or "TASI" in s


def _dur(sec: float) -> str:
    """مدّةٌ بكلامٍ عربيّ: «45 د» · «3 س 20 د» · «يوم و5 س» · «يومين» · «3 أيام»."""
    m = max(1, int(round(sec / 60)))
    if m < 60:
        return f"{m} د"
    h, mm = divmod(m, 60)
    if h < 24:
        return f"{h} س {mm} د" if mm else f"{h} س"
    d, hh = divmod(h, 24)
    days = "يوم" if d == 1 else "يومين" if d == 2 else f"{d} أيام" if d <= 10 else f"{d} يوماً"
    return f"{days} و{hh} س" if hh else days


def _us_day(d: date) -> tuple[str, dtime, dtime, dtime, dtime] | None:
    """(النوع، بدءُ ما قبل الافتتاح، الافتتاح، الإغلاق، نهايةُ ما بعده) ليومٍ أمريكيّ — أو None للعطلة ونهاية الأسبوع."""
    if d.weekday() >= 5 or d.isoformat() in US_HOLIDAYS:
        return None
    early = d.isoformat() in US_EARLY
    return ("early" if early else "full", dtime(4), dtime(9, 30), dtime(13) if early else dtime(16), dtime(17) if early else dtime(20))


def _sa_day(d: date) -> tuple[dtime, dtime, dtime, dtime] | None:
    """(مزادُ الافتتاح، الافتتاح، الإغلاق، نهايةُ مزاد الإغلاق والتداول على سعر الإغلاق) — الأحدُ إلى الخميس."""
    if d.weekday() in (4, 5) or d.strftime("%m-%d") in SA_FIXED:      # الجمعة والسبت
        return None
    return dtime(9, 30), dtime(10), dtime(15), dtime(15, 20)


def us_session(now: datetime | None = None) -> dict:
    now = (now or datetime.now(timezone.utc)).astimezone(NY)
    d, t = now.date(), now.time()
    day = _us_day(d)
    if day:
        _, pre, op, cl, post = day
        at = lambda tt: datetime.combine(d, tt, NY)                 # noqa: E731
        if pre <= t < op:
            return _mk("us", "pre", at(op), f"يفتح بعد {_dur((at(op) - now).total_seconds())}")
        if op <= t < cl:
            return _mk("us", "open", at(cl), f"يغلق بعد {_dur((at(cl) - now).total_seconds())}" + (" (إغلاقٌ مبكّر)" if day[0] == "early" else ""))
        if cl <= t < post:
            return _mk("us", "post", at(post), f"ينتهي بعد {_dur((at(post) - now).total_seconds())}")
    nxt, opn = _next_us_open(now)
    hol = US_HOLIDAYS.get(d.isoformat())
    if hol:
        return {**_mk("us", "holiday", nxt, f"يفتح بعد {_dur((opn - now).total_seconds())}"), "holiday": hol}
    return _mk("us", "closed", nxt, f"يفتح بعد {_dur((opn - now).total_seconds())}")


def _next_us_open(now: datetime) -> tuple[datetime, datetime]:
    """(بدءُ ما قبل الافتتاح التالي، الافتتاحُ الرسميُّ التالي)."""
    d = now.date()
    for i in range(0, 10):
        dd = d + timedelta(days=i)
        day = _us_day(dd)
        if not day:
            continue
        o = datetime.combine(dd, day[1], NY)
        if o > now:
            return o, datetime.combine(dd, day[2], NY)
    return now + timedelta(days=1), now + timedelta(days=1)


def sa_session(now: datetime | None = None) -> dict:
    now = (now or datetime.now(timezone.utc)).astimezone(RY)
    d, t = now.date(), now.time()
    day = _sa_day(d)
    if day:
        po, op, cl, end = day
        at = lambda tt: datetime.combine(d, tt, RY)                 # noqa: E731
        if po <= t < op:
            return _mk("sa", "preopen", at(op), f"يفتح بعد {_dur((at(op) - now).total_seconds())}")
        if op <= t < cl:
            return _mk("sa", "open", at(cl), f"يغلق بعد {_dur((at(cl) - now).total_seconds())}")
        if cl <= t < end:
            return _mk("sa", "auction", at(end), f"ينتهي بعد {_dur((at(end) - now).total_seconds())}")
    nxt, opn = _next_sa_open(now)
    hol = SA_FIXED.get(d.strftime("%m-%d")) if d.weekday() not in (4, 5) else None
    if hol:
        return {**_mk("sa", "holiday", nxt, f"يفتح بعد {_dur((opn - now).total_seconds())}"), "holiday": hol}
    return _mk("sa", "closed", nxt, f"يفتح بعد {_dur((opn - now).total_seconds())}")


def _next_sa_open(now: datetime) -> tuple[datetime, datetime]:
    """(مزادُ الافتتاح التالي، الافتتاحُ التالي)."""
    d = now.date()
    for i in range(0, 10):
        dd = d + timedelta(days=i)
        day = _sa_day(dd)
        if not day:
            continue
        o = datetime.combine(dd, day[0], RY)
        if o > now:
            return o, datetime.combine(dd, day[1], RY)
    return now + timedelta(days=1), now + timedelta(days=1)


def _mk(market: str, state: str, nxt: datetime | None, detail: str) -> dict:
    return {"market": market, "state": state, "label": LABEL[state], "detail": detail,
            "next": nxt.astimezone(timezone.utc).isoformat(timespec="seconds") if nxt else None, "source": "schedule"}


# ── المصدرُ الحيّ يُقدَّم على الجدول ──
TV_STATE = {"market": "open", "pre_market": "pre", "post_market": "post", "out_of_session": "closed"}
YH_STATE = {"REGULAR": "open", "PRE": "pre", "POST": "post", "PREPRE": "closed", "POSTPOST": "closed", "CLOSED": "closed"}


def reconcile(sched: dict, live_state: str | None, source: str) -> dict:
    """الجدولُ يقول شيئاً والمصدرُ الحيُّ يقول غيرَه: يُصدَّق المصدر — إلا أن يكون الجدولُ «عطلةً» مسمّاةً والمصدرُ «مغلقاً» فتبقى باسمها.
    وإغلاقٌ في ساعات التداول يومَ عمل = عطلةٌ غيرُ مسمّاة (عيدٌ يعلنه السوق)."""
    if not live_state or live_state == sched["state"]:
        return sched
    if sched["state"] == "holiday" and live_state == "closed":
        return sched
    if sched["state"] in ("auction", "preopen") and live_state in ("open", "closed", "pre"):
        return sched                     # مزادا «تداول» لا يميّزهما المصدرُ — الجدولُ أدقّ
    out = {**sched, "state": live_state, "label": LABEL[live_state], "source": source}
    if live_state == "closed" and sched["state"] in ("open", "pre", "post"):
        hol = sched["state"] == "open"
        out.update(state="holiday" if hol else "closed", label=LABEL["holiday" if hol else "closed"],
                   detail="السوقُ مغلقٌ اليوم" if hol else sched["detail"], next=None if hol else sched["next"])
    return out


def session_for(symbol: str, live_state: str | None = None, source: str = "") -> dict:
    sched = sa_session() if is_saudi(symbol) else us_session()
    return reconcile(sched, live_state, source)
