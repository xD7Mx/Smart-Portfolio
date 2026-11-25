"""فريقُ صقر — لجنةُ خبراءٍ تحكم على كلّ عقدٍ قبل أن يراه المالك (‏D776 بأمر المالك 2026-11-20).

قال المالك: «نحوّل صقر إلى فريق… مسؤولٌ عن اختيار العقود ورفع نسبة النجاح — مثلاً لو اخترتُ نسبةَ نجاحٍ لا تقلّ عن 90٪… ذكيٌّ جداً وبسيطٌ
في الوقت نفسه، لا يعقّد ولا يتفلسف… عقدٌ ناضجٌ لا يتآكل مع الزمن قريباً… يقرؤون الخبرَ الذي يخصّ كلَّ شركةٍ بذاتها».

ستّةُ أعضاء، لكلٍّ سطرٌ واحدٌ بحكمه (يوافق · يتحفّظ · يرفض) — ورفضُ واحدٍ يُسقط العقد:
  ١ الأساس — متانةُ الشركة المالية (درجةُ الفرز الأساسيّ).
  ٢ الفنّ — المسارُ وزخمُه مع اتجاه العقد.
  ٣ الأخبار — خبرُ الشركة نفسِها في الأيام العشرة الأخيرة (يقرؤه النموذج).
  ٤ اليونانيات — الدلتا، والتآكلُ الأسبوعيّ من ثمن العقد، والتذبذبُ الضمنيّ.
  ٥ المخاطر — الفارق، والاهتمامُ المفتوح، وموعدُ الأرباح، وبُعدُ التعادل.
  ٦ الاحتمال — نسبةُ النجاح: احتمالُ أن يبلغ العقدُ +30٪ (جنيُ المالك) قبل وقفه (−40٪ افتراضاً) وقبل موعد الخروج.

ونسبةُ النجاح تقديرٌ من التذبذب الضمنيّ نفسِه (السوقُ يسعّر هذا التذبذب) بشبكةٍ ذات حاجزين — لا وعد. والوعدُ الوحيدُ الصادق هو السجلّ:
كلُّ عقدٍ يختاره الفريقُ يُتابَع بسعره الحيّ حتى ينجح (+30٪) أو يُوقَف أو يحين خروجُه، فتُقاس النسبةُ الفعلية لا المقدَّرة.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

from app.services import option_picks as OP

TP = 0.30                 # المالك: «عقودٌ تطلع 30٪ أقلَّ شيء» — والنجاحُ بلوغُها
STOP = 0.40               # وقفُ العقد الافتراضيّ عند صقر (‏opt_stop)
EXIT_DTE = OP.EXIT_DTE    # الخروجُ قبل ستين يوماً من الانتهاء — فالنجاحُ يُقاس قبله
MIN_H = 30                # أقصرُ أفقٍ يُقاس عليه (يوماً)
WIN_LEVELS = (50, 60, 70, 80, 90)
DEFAULT_MIN_WIN = 0       # الكلّ مرتّباً بنسبة النجاح — والمالكُ يرفع الحدَّ الأدنى متى شاء
STEPS = 160
_MEMO: dict[tuple, dict] = {}


def _level(S: float, K: float, T: float, iv: float, call: bool, value: float) -> float | None:
    """سعرُ السهم الذي تبلغ عنده قيمةُ العقد `value` (تنصيف — القيمةُ رتيبةٌ في السعر)."""
    if T <= 0 or iv <= 0 or value <= 0:
        return None
    lo, hi = S * 0.05, S * 8
    f = lambda x: OP.bs_price(x, K, T, iv, call) - value   # noqa: E731
    if call:
        if f(hi) < 0 or f(lo) > 0:
            return None
    elif f(lo) < 0 or f(hi) > 0:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        v = f(mid)
        if (v < 0) == call:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def first_hit(up: float, dn: float, T: float, iv: float, r: float = OP.RATE, steps: int = STEPS) -> float:
    """احتمالُ أن يبلغ اللوغاريتمُ حاجزَ النجاح ‎`up` (>0) قبل حاجز الفشل ‎`dn` (<0) وقبل الأجل ‎`T` — مشيٌ عشوائيٌّ ثنائيٌّ بانحرافٍ محايدٍ للمخاطرة."""
    if T <= 0 or iv <= 0 or up <= 0 or dn >= 0:
        return 0.0
    # الخطوةُ تتّسع لستّ درجاتٍ على الأقلّ دون أقرب الحاجزين — وإلا ابتلع التقريبُ الحاجزَ القريب (قيس: 0.83 بدل 0.90)
    steps = int(min(2500, max(steps, math.ceil((iv * math.sqrt(T) * 6 / min(up, -dn)) ** 2))))
    dt = T / steps
    dx = iv * math.sqrt(dt)
    mu = r - iv * iv / 2
    pu = min(1.0, max(0.0, 0.5 * (1 + mu * math.sqrt(dt) / iv)))
    hi, lo = max(1, round(up / dx)), min(-1, round(dn / dx))
    n = hi - lo + 1
    p = [0.0] * n
    p[-lo] = 1.0
    won = 0.0
    for _ in range(steps):
        q = [0.0] * n
        for i in range(1, n - 1):
            m = p[i]
            if m:
                q[i + 1] += m * pu
                q[i - 1] += m * (1 - pu)
        won += q[-1]
        q[-1] = q[0] = 0.0
        p = q
    return won


def odds(k: dict, S: float | None, stop: float = STOP) -> dict | None:
    """نسبةُ النجاح للعقد: بلوغُ +30٪ قبل الوقف وقبل الخروج — وسعرا السهم اللذان يبلغ عندهما العقدُ كلّاً منهما."""
    if not S or not k.get("iv") or not k.get("ask") or not k.get("dte"):
        return None
    key = (k.get("contract"), k["ask"], k["dte"], k["iv"], round(S, 2), stop)
    if key in _MEMO:
        return _MEMO[key]
    call = k["type"] == "call"
    iv, K, T = k["iv"] / 100, k["strike"], k["dte"] / 365
    h = max(k["dte"] - EXIT_DTE, MIN_H) / 365
    t_rem = max(T - h, 1 / 365)
    s_up = _level(S, K, t_rem, iv, call, k["ask"] * (1 + TP))       # عند الخروج أقلُّ قيمةٍ زمنية ⇐ أبعدُ حركةٍ لازمة (تحفّظ)
    s_dn = _level(S, K, T, iv, call, k["ask"] * (1 - stop))         # والوقفُ الآن بكامل قيمته الزمنية ⇐ أقربُ هبوطٍ يوقفه (تحفّظ)
    if not s_up or not s_dn:
        return None
    up, dn = (math.log(s_up / S), math.log(s_dn / S)) if call else (math.log(S / s_up), math.log(S / s_dn))
    p = first_hit(up, dn, h, iv) if up > 0 and dn < 0 else (1.0 if up <= 0 else 0.0)
    theta = OP.bs_price(S, K, T, iv, call) - OP.bs_price(S, K, max(T - 7 / 365, 1 / 365), iv, call)
    out = {"p30": round(p * 100, 1), "s_up": round(s_up, 2), "s_dn": round(s_dn, 2), "up_pct": round(abs(s_up / S - 1) * 100, 1),
           "dn_pct": round(abs(s_dn / S - 1) * 100, 1), "decay_wk": round(max(theta, 0) / k["ask"] * 100, 2), "days": round(h * 365)}
    _MEMO[key] = out
    if len(_MEMO) > 20000:
        _MEMO.clear()
    return out


STOCK_DAYS = 90           # ‏D832: أفقُ السهم السعوديّ — ثلاثةُ أشهر (أفقُ مساره ‎ret3m)


def odds_stock(ask: float, stop: float, target: float, vol: float | None, days: int = STOCK_DAYS) -> float | None:
    """‏D832 — نسبةُ النجاح للسهم بالنموذج نفسِه الذي يُقاس به العقد: احتمالُ أن يبلغ السعرُ هدفَه قبل وقفه وقبل الأفق — من تذبذبه المحقَّق
    (لا خيارات للسوق السعوديّ يُقرأ منها تذبذبٌ ضمنيّ). تقديرٌ لا وعد؛ وبلا تذبذبٍ أو بحاجزين مقلوبين ⇒ None."""
    if not ask or not vol or not target or not stop or not (stop < ask < target):
        return None
    return round(first_hit(math.log(target / ask), math.log(stop / ask), days / 365, vol) * 100, 1)


def _m(role: str, v: str, say: str) -> dict:
    return {"role": role, "v": v, "say": say}


def judge(k: dict, e: dict, stop: float = STOP, today: date | None = None) -> dict:
    """حكمُ الفريق على عقدٍ واحد: ستّةُ أعضاءٍ بسطرٍ لكلّ — ‏{"members", "veto", "warns", "p30", "odds", "verdict"}."""
    call = k["type"] == "call"
    tr = e.get("trend") or {}
    od = odds(k, e.get("price") or k.get("price"), stop)
    mem = []
    # ١ الأساس
    f = e.get("fund")
    if f is None:
        mem.append(_m("الأساس", "warn", "درجةُ المتانة غيرُ متوفّرة"))
    elif call:
        mem.append(_m("الأساس", "ok" if f >= 80 else "warn", f"{'متانةٌ ماليةٌ ممتازة' if f >= 80 else 'متانةٌ مقبولة'} ({f:.0f}/100)"))
    else:
        mem.append(_m("الأساس", "warn" if f >= 85 else "ok", f"شركةٌ متينة ({f:.0f}/100) — الهبوطُ قد لا يدوم" if f >= 85 else f"متانتُها {f:.0f}/100 لا تمنع الهبوط"))
    # ٢ الفنّ
    st, r3 = tr.get("state"), tr.get("ret3m")
    want = "صاعد" if call else "هابط"
    if st != want:
        mem.append(_m("الفنّ", "veto", f"المسارُ {st or 'غيرُ معروف'} لا {want}"))
    elif r3 is not None and ((call and r3 >= 5) or (not call and r3 <= -5)):
        mem.append(_m("الفنّ", "ok", f"مسارٌ {want} وزخمُه معه ({r3:+.0f}٪ في ثلاثة أشهر)"))
    else:
        mem.append(_m("الفنّ", "warn", f"مسارٌ {want} وزخمُه فاتر ({(r3 or 0):+.0f}٪ في ثلاثة أشهر)"))
    # ٣ الأخبار — خبرُ الشركة نفسِها
    n = e.get("news") or {}
    imp = str(n.get("impact") or "")
    if imp in ("إيجابي", "سلبي"):
        good = (imp == "إيجابي") == call
        mem.append(_m("الأخبار", "ok" if good else "veto", f"{'يدعمها' if good else 'يعاكسها'}: {n.get('event') or imp}"))
    else:
        mem.append(_m("الأخبار", "ok", "لا خبرَ مؤثّراً للشركة في عشرة أيام"))
    # ٤ اليونانيات
    d = abs(k.get("delta") or 0)
    dw = od["decay_wk"] if od else None
    g_v = "ok"
    bits = [f"دلتا {d:.2f}"]
    if d < 0.45:
        g_v = "warn"
    if dw is not None:
        bits.append(f"يتآكل {dw:.1f}٪ أسبوعياً")
        if dw > 4:
            g_v = "veto"
        elif dw > 2:
            g_v = "warn" if g_v == "ok" else g_v
    if (k.get("iv") or 0) > 80:
        bits.append(f"تذبذبٌ مرتفع {k['iv']:.0f}٪")
        g_v = "warn" if g_v == "ok" else g_v
    mem.append(_m("اليونانيات", g_v, " · ".join(bits)))
    # ٥ المخاطر
    risks, r_v = [], "ok"
    sp, oi = k.get("spread_pct") or 0, k.get("oi") or 0
    if sp > 7:
        risks.append(f"فارقٌ {sp:.1f}٪")
        r_v = "warn"
    if oi < 300:
        risks.append(f"اهتمامٌ مفتوح {oi:,}")
        r_v = "warn"
    if (k.get("need_pct") or 0) > 15:
        risks.append(f"التعادلُ بعيد ({k['need_pct']:.0f}٪)")
        r_v = "warn"
    earn = e.get("earn")
    if earn:
        try:
            ed = (date.fromisoformat(earn) - (today or datetime.now(timezone.utc).date())).days
        except ValueError:
            ed = None
        if ed is not None and 0 <= ed <= 14:
            risks.append(f"إعلانُ الأرباح بعد {ed} يوماً")
            r_v = "warn"
    mem.append(_m("المخاطر", r_v, " · ".join(risks) if risks else f"فارقٌ {sp:.1f}٪ · اهتمامٌ {oi:,} — سيولةٌ تكفي للدخول والخروج"))
    # ٦ الاحتمال — نسبةُ النجاح
    if not od:
        mem.append(_m("الاحتمال", "warn", "نسبةُ النجاح غيرُ متوفّرة لهذا العقد"))
        p = None
    else:
        p = od["p30"]
        say = f"نسبةُ النجاح {p:.0f}٪: يبلغ +{TP * 100:.0f}٪ إن تحرّك السهمُ {od['up_pct']:.1f}٪ قبل أن يهبط {od['dn_pct']:.1f}٪ (الوقف) — خلال {od['days']} يوماً"
        # قيس (‏D776): بهدف +30٪ ووقف −40٪ يسعّر السوقُ أكثرَ العقود الطويلة بين 30٪ و55٪ — فالرفضُ لما دون 30٪ والتحفّظُ لما دون 55٪
        mem.append(_m("الاحتمال", "ok" if p >= 55 else "warn" if p >= 30 else "veto", say))
    veto = any(m["v"] == "veto" for m in mem)
    warns = sum(1 for m in mem if m["v"] == "warn")
    verdict = "يرفض" if veto else "يوافق" if warns == 0 else "يوافق بتحفّظ"
    return {"members": mem, "veto": veto, "warns": warns, "p30": p, "odds": od, "verdict": verdict}


# ══ سجلُّ الفريق — النسبةُ الفعلية لا المقدَّرة ══
MAX_TRACK = 40           # أقصى ما يُتابَع مفتوحاً (كلٌّ نداءٌ للسلسلة في كلّ متابعة)
PICK_PER_BUILD = 8       # أعلى ما يختاره الفريقُ في كلّ بناء
MARK_MIN = 60            # يُتابَع السجلُّ كلَّ ساعةٍ في الجلسة


def _track_path() -> str:
    import os
    d = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "saqr")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "team_track.json")


def track_load() -> dict:
    import json
    try:
        with open(_track_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"open": [], "closed": [], "marked": None}


def track_save(t: dict) -> None:
    import json
    import os
    tmp = _track_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(t, fh, ensure_ascii=False)
    os.replace(tmp, _track_path())


def track_add(items: list[dict], now: datetime) -> int:
    """يُسجَّل ما اختاره الفريقُ (الأعلى نسبةَ نجاحٍ — ‎≥ 45٪ بلا رفضٍ وتحفّظان فأقلّ) بسعر عرضه الحيّ — سهمٌ واحدٌ لا يُكرَّر وهو مفتوح."""
    t = track_load()
    have = {r["symbol"] for r in t["open"]}
    added = 0
    for it in items:
        if len(t["open"]) >= MAX_TRACK or added >= PICK_PER_BUILD:
            break
        tm = it.get("team") or {}
        if it["symbol"] in have or tm.get("veto") or tm.get("warns", 9) > 2 or (tm.get("p30") or 0) < 45 or it.get("px_src") != "ask":
            continue
        exp = date.fromisoformat(it["expiry"])
        t["open"].append({"contract": it["contract"], "symbol": it["symbol"], "type": it["type"], "strike": it["strike"], "expiry": it["expiry"],
                          "entry": it["ask"], "p30": it["team"]["p30"], "at": now.isoformat(timespec="seconds"),
                          "exit_by": (exp - timedelta(days=EXIT_DTE)).isoformat(), "best": it["ask"], "last": it["ask"]})
        have.add(it["symbol"])
        added += 1
    if added:
        track_save(t)
    return added


async def track_mark(now: datetime, quote) -> dict:
    """متابعةُ السجلّ بالطلب الحيّ: نجح (+30٪) · أُوقف (−40٪) · حان الخروج — والنسبةُ الفعلية من المغلقة."""
    t = track_load()
    keep = []
    for r in t["open"]:
        q = None
        try:
            q = await quote(r["contract"])
        except Exception:                                         # noqa: BLE001
            q = None
        bid = (q or {}).get("bid") if (q or {}).get("live") else None
        if bid:
            r["last"] = bid
            r["best"] = max(r.get("best") or 0, bid)
        res = None
        if bid and bid >= r["entry"] * (1 + TP):
            res = "win"
        elif bid and bid <= r["entry"] * (1 - STOP):
            res = "stop"
        elif now.date().isoformat() >= r["exit_by"]:
            res = "time"
        if res:
            t["closed"].insert(0, {**r, "result": res, "closed": now.isoformat(timespec="seconds"),
                                   "pl_pct": round(((r.get("last") or r["entry"]) / r["entry"] - 1) * 100, 1)})
        else:
            keep.append(r)
    t["open"], t["closed"], t["marked"] = keep, t["closed"][:300], now.isoformat(timespec="seconds")
    track_save(t)
    return t


def track_stats(t: dict | None = None) -> dict:
    t = t or track_load()
    c = t.get("closed") or []
    wins = sum(1 for r in c if r["result"] == "win")
    return {"open": len(t.get("open") or []), "closed": len(c), "wins": wins, "rate": round(wins / len(c) * 100, 1) if c else None,
            "marked": t.get("marked"), "since": min((r["at"] for r in (t.get("open") or []) + c), default=None)}
