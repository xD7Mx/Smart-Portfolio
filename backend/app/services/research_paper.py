"""ورقةُ التقرير اليوميّ — على هيئة «التقرير اليوميّ والنظرة الفنية» لبيوت الأبحاث (‏D746 · بأمر المالك 2026-11-15).

«أبغى شيئاً طبقَ الأصل من الجزيرة كابيتال… عندهم تقسيماتٌ للمؤشّر وللقطاعات وللإحصاءات وللمعدّل… عمقُ السوق ونظرتُنا: شراء،
جني أرباح… ولا تذكر المصادر». قِيست البنيةُ من التقرير المنشور نفسِه (‏scripts/audit/ajc_layout_door.py) فصارت أربعَ صفحات:
  ١ التقرير اليوميّ — مؤشّرُ السوق ومؤشّراتُه المالية وحركتُه في الجلسة، والقطاعات، ومعدّلُ القيم والإحصاءاتُ المجمّعة، والأكبرُ وزناً؛
    وفي العمود الآخر الأخبارُ المحلية وتحليلُ السوق والأكثرُ ارتفاعاً وانخفاضاً.
  ٢ الأسواق — الإقليمية والعالمية والسلع والعملات والفائدة، وإجراءاتُ الشركات، والأخبارُ العالمية.
  ٣ النظرةُ الفنية اليومية — التعليقُ والتوقّعات، والدعمُ والمقاومة، والرسمُ اليوميّ، وملاحظاتٌ فنية، وبياناتُ السوق، ونظرتُنا، وعمقُ السوق.
  ٤ محفظتُنا — نظرتُنا لكلّ مركز، وأفضلُ اختياراتنا لليوم بنطاق الشراء والمستهدف ووقف الخسارة، وما يُتابَع.

الأرقامُ كلُّها محسوبةٌ هنا من مصادر التطبيق (لقطةُ «تداول» وخدمةُ مؤشّرها، وإفصاحُ XBRL، وتاريخُ الأسعار)، والنصُّ الحرُّ وحده من
قسم الأبحاث مقيّداً بمصادره — والمصادرُ لا تُعرض. وما لا مصدرَ له لا يُكتب: الصفُّ الغائبُ يُترك، والخليةُ الغائبةُ «—».
"""
from __future__ import annotations

import asyncio
import html as _html
import json
import math
import re
from datetime import date, datetime, timedelta

from loguru import logger

WEEKDAYS = ("الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد")
MONTHS = ("يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر")

GLOBAL = (("^DJI", "داو جونز (أمريكا)"), ("^IXIC", "ناسداك (أمريكا)"), ("^GSPC", "إس آند بي 500 (أمريكا)"),
          ("^FTSE", "فوتسي 100 (بريطانيا)"), ("^GDAXI", "داكس (ألمانيا)"), ("^FCHI", "كاك 40 (فرنسا)"),
          ("^N225", "نيكاي 225 (اليابان)"), ("^HSI", "هانغ سنغ (هونغ كونغ)"), ("000001.SS", "شنغهاي المركّب (الصين)"),
          ("^KS11", "كوسبي (كوريا الجنوبية)"), ("^AXJO", "إيه إس إكس 200 (أستراليا)"), ("^BSESN", "سينسكس (الهند)"),
          ("^BVSP", "بوفيسبا (البرازيل)"), ("EEM", "صندوق الأسواق الناشئة"), ("URTH", "صندوق الأسواق العالمية"))
COMMOD = (("BZ=F", "خام برنت (برميل)"), ("CL=F", "خام غرب تكساس (برميل)"), ("NG=F", "الغاز الطبيعي (مليون وحدة حرارية)"),
          ("GC=F", "الذهب (أونصة)"), ("SI=F", "الفضة (أونصة)"), ("HG=F", "النحاس (رطل)"), ("ALI=F", "الألومنيوم (طن)"),
          ("TIO=F", "خام الحديد (طن)"), ("HRC=F", "الحديد المدرفل (طن)"), ("SB=F", "السكر (سنت/رطل)"))
FX = (("DX-Y.NYB", "مؤشر الدولار"), ("EURUSD=X", "اليورو"), ("GBPUSD=X", "الجنيه الإسترليني"), ("JPY=X", "الين الياباني"),
      ("CHF=X", "الفرنك السويسري"), ("CAD=X", "الدولار الكندي"), ("AUDUSD=X", "الدولار الأسترالي"), ("CNY=X", "اليوان الصيني"),
      ("INR=X", "الروبية الهندية"), ("BTC-USD", "بيتكوين"), ("ETH-USD", "إيثيريوم"), ("XRP-USD", "ريبل"))
RATES = (("^IRX", "الخزانة الأمريكية 3 أشهر"), ("^FVX", "الخزانة الأمريكية 5 سنوات"), ("^TNX", "الخزانة الأمريكية 10 سنوات"))

# نظرتُنا — من الأشدّ هبوطاً إلى الأشدّ صعوداً، كما في دائرة «نظرتنا»
VIEWS = ("اتجاه هابط", "نظرة حذرة", "جني الأرباح", "محايد", "احتفاظ", "شراء حذر", "شراء")
BUY_DECISIONS = {"شراء", "شراء قوي"}


# ── أدواتٌ صغيرة ────────────────────────────────────────────────────────────
def day_label(d: date | str) -> str:
    d = date.fromisoformat(str(d)[:10]) if not isinstance(d, date) else d
    return f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


def short_day(d: str) -> str:
    try:
        x = date.fromisoformat(str(d)[:10])
        return f"{x.day} {MONTHS[x.month - 1]}"
    except ValueError:
        return str(d)


def _f(x) -> float | None:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x) if math.isfinite(x) else None
    try:
        v = float(str(x).replace(",", "").strip())
        return v if math.isfinite(v) else None
    except ValueError:
        return None


def _pct(a, b) -> float | None:
    a, b = _f(a), _f(b)
    return (a / b - 1) * 100 if a is not None and b not in (None, 0) else None


def _sma(xs: list[float], n: int) -> float | None:
    return sum(xs[-n:]) / n if len(xs) >= n else None


def _ema(xs: list[float], n: int) -> list[float]:
    if len(xs) < n:
        return []
    k, out = 2 / (n + 1), [sum(xs[:n]) / n]
    for x in xs[n:]:
        out.append(x * k + out[-1] * (1 - k))
    return out


def _rsi(xs: list[float], n: int = 14) -> float | None:
    if len(xs) <= n:
        return None
    g = [max(0.0, xs[i] - xs[i - 1]) for i in range(1, len(xs))]
    l = [max(0.0, xs[i - 1] - xs[i]) for i in range(1, len(xs))]
    ag, al = sum(g[:n]) / n, sum(l[:n]) / n
    for i in range(n, len(g)):
        ag, al = (ag * (n - 1) + g[i]) / n, (al * (n - 1) + l[i]) / n
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)


def _atr(bars: list[dict], n: int = 14) -> float | None:
    if len(bars) <= n:
        return None
    trs = [max(b["high"] - b["low"], abs(b["high"] - a["close"]), abs(b["low"] - a["close"])) for a, b in zip(bars, bars[1:])]
    v = sum(trs[:n]) / n
    for t in trs[n:]:
        v = (v * (n - 1) + t) / n
    return v


def pivots(h: float, l: float, c: float) -> dict:
    """المحورُ الكلاسيكيّ من جلسةٍ واحدة: المحورُ ثمّ ثلاثُ مقاوماتٍ وثلاثةُ دعوم."""
    p = (h + l + c) / 3
    return {"s3": l - 2 * (h - p), "s2": p - (h - l), "s1": 2 * p - h, "p": p, "r1": 2 * p - l, "r2": p + (h - l), "r3": h + 2 * (p - l)}


def _bars_ok(bars) -> list[dict]:
    out = []
    for b in bars or []:
        o, h, l, c = (_f(b.get(k)) for k in ("open", "high", "low", "close"))
        if None in (o, h, l, c) or c <= 0:
            continue
        out.append({"date": str(b.get("date") or "")[:16], "open": o, "high": max(h, o, c), "low": min(l, o, c), "close": c,
                    "volume": _f(b.get("volume")) or 0.0})
    return out


def technicals(bars: list[dict]) -> dict | None:
    """قراءةُ المؤشّر أو السهم من شموعه اليومية — كلُّ رقمٍ بمعادلته المعروفة، لا تقدير."""
    bars = _bars_ok(bars)
    if len(bars) < 30:
        return None
    cl = [b["close"] for b in bars]
    last, prev = bars[-1], bars[-2]
    e12, e26 = _ema(cl, 12), _ema(cl, 26)
    macd = [a - b for a, b in zip(e12[-len(e26):], e26)] if e26 else []
    sig = _ema(macd, 9) if len(macd) >= 9 else []
    hist = macd[-1] - sig[-1] if sig else None
    hist_prev = (macd[-2] - sig[-2]) if len(sig) >= 2 else None
    rng = last["high"] - last["low"]
    body = abs(last["close"] - last["open"])
    d0 = date.fromisoformat(last["date"][:10])

    def base(before: str):
        xs = [b["close"] for b in bars if b["date"][:10] < before]
        return xs[-1] if xs else None
    q0 = date(d0.year, 3 * ((d0.month - 1) // 3) + 1, 1)
    yr = bars[-250:]
    t = {"date": last["date"][:10], "close": last["close"], "open": last["open"], "high": last["high"], "low": last["low"],
         "prev": prev["close"], "chg": last["close"] - prev["close"], "chg_pct": _pct(last["close"], prev["close"]),
         "sma10": _sma(cl, 10), "sma20": _sma(cl, 20), "sma50": _sma(cl, 50), "sma100": _sma(cl, 100), "sma200": _sma(cl, 200),
         "rsi": _rsi(cl), "macd": macd[-1] if macd else None, "macd_sig": sig[-1] if sig else None, "macd_hist": hist,
         "macd_cross": (None if hist is None or hist_prev is None else "up" if hist > 0 >= hist_prev else "down" if hist < 0 <= hist_prev else None),
         "atr": _atr(bars), "hi52": max(b["high"] for b in yr), "lo52": min(b["low"] for b in yr),
         "mtd": _pct(last["close"], base(d0.replace(day=1).isoformat())),
         "qtd": _pct(last["close"], base(q0.isoformat())),
         "ytd": _pct(last["close"], base(date(d0.year, 1, 1).isoformat())),
         "candle": ("doji" if rng > 0 and body < 0.1 * rng else "green" if last["close"] >= last["open"] else "red"),
         "close_at": ("low" if rng > 0 and (last["close"] - last["low"]) < 0.15 * rng else
                      "high" if rng > 0 and (last["high"] - last["close"]) < 0.15 * rng else "mid"),
         "piv": pivots(last["high"], last["low"], last["close"])}
    t["view"] = view_of(t)
    return t


def view_of(t: dict) -> str:
    """نظرتُنا قريبةُ المدى من خمس إشاراتٍ معلنة: فوق متوسّط 50 · فوق 200 · متوسّط 10 فوق 50 · الماكد موجب · القوةُ النسبية بين 50 و70."""
    c, rsi = t.get("close"), t.get("rsi")
    s = sum(1 for ok in (
        t.get("sma50") is not None and c > t["sma50"],
        t.get("sma200") is not None and c > t["sma200"],
        t.get("sma10") is not None and t.get("sma50") is not None and t["sma10"] > t["sma50"],
        (t.get("macd_hist") or 0) > 0,
        rsi is not None and 50 <= rsi < 70) if ok)
    if rsi is not None and rsi >= 70:
        return "جني الأرباح"
    if s >= 4:
        return "شراء"
    if s == 3:
        return "شراء حذر" if (t.get("chg") or 0) >= 0 else "احتفاظ"
    if s == 2:
        return "محايد"
    if s == 1:
        return "نظرة حذرة"
    return "اتجاه هابط"


# ── مؤشّرُ الأبحاث (‏D753 · بأمر المالك 2026-11-16) ─────────────────────────────────────────────────────────────
# «الرسمُ مثلُ الذي في تقرير الجزيرة كابيتال — تريدنق فيو بخمسة مؤشّرات، ثلاثةٌ أعلى واثنان أسفل… وضعه في الرسم عندي مؤشّراً مستقلّاً
# باسم مؤشّر الأبحاث، مطابقاً». قرأه القارئُ البصريّ من رسم التقرير نفسِه (‏ajc_chart_door): متوسّطُ 20 (‏#ef9a9a) ومتوسّطُ 50 (‏#a5d6a7)
# وفيبوناتشي من قاع السنة إلى أوّل قمّة ارتداد (0 · 1 · 1.272 · 1.618 · 2 بالأزرق ‏#2962ff) فوق؛ والكمّيةُ وRSI 14 (أزرق، 30 و70) تحت؛
# وخطوطُ اتجاهٍ تصل القمم، وأسهمُ شراءٍ وبيع. والدعمُ والمقاومةُ في جدوله تلاقي مستوياتٍ: فيبوناتشي والمتوسّطان والقممُ والقيعانُ السابقة
# والأرقامُ النفسية (10,000 · 10,060 = فيبوناتشي 1 · 10,250 = 127.2٪ المحور · 10,490 = 161.8٪). والشيفرةُ نفسُها في الرسم التفاعليّ
# (‏frontend/src/lib/researchIndicator.ts) — والحارسُ يطابق بينهما.
RI_FIB = (0.0, 1.0, 1.272, 1.618, 2.0)
RI_COLORS = {"sma20": "#ef9a9a", "sma50": "#a5d6a7", "fib": "#2962ff", "rsi": "#2962ff", "rsi_band": "#f0f3fa", "trend": "#131722",
             "buy": "#089981", "sell": "#f23645"}


def _pivots(vals: list[float], k: int = 3, high: bool = True) -> list[int]:
    out = []
    for j in range(k, len(vals) - k):
        w = vals[j - k:j + k + 1]
        if vals[j] == (max(w) if high else min(w)) and w.count(vals[j]) == 1:
            out.append(j)
    return out


def _rsi_series(cl: list[float], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(cl)
    if len(cl) <= n:
        return out
    g = [max(0.0, cl[i] - cl[i - 1]) for i in range(1, len(cl))]
    l = [max(0.0, cl[i - 1] - cl[i]) for i in range(1, len(cl))]
    ag, al = sum(g[:n]) / n, sum(l[:n]) / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n, len(g)):
        ag, al = (ag * (n - 1) + g[i]) / n, (al * (n - 1) + l[i]) / n
        out[i + 1] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def fib_anchor(H: list[float], L: list[float], C: list[float], w0: int) -> dict | None:
    """مرساةُ فيبوناتشي كما يرسمها المحلّل: من أدنى قاعٍ في السنة (0) إلى أوّل قمّة ارتدادٍ ذات شأن (1) — صعودٌ 5٪ فأكثر يتبعه تراجعٌ
    38.2٪ منه فأكثر — والامتداداتُ 1.272 و1.618 و2 أهدافٌ فوقها. وإن تجاوز السعرُ امتدادَ 2 فقد استُنفدت الموجة: تُعاد المرساةُ على ما بعدها."""
    n, start, fib = len(C), w0, None
    ph = _pivots(H)
    for _ in range(4):
        if start >= n - 5:
            break
        i0 = min(range(start, n), key=lambda i: L[i])
        p0 = L[i0]
        pick = None
        for j in (j for j in ph if j > i0):
            nxt = next((m for m in range(j + 1, n) if H[m] > H[j]), n)
            low = min(L[j + 1:nxt]) if nxt > j + 1 else H[j]
            if (H[j] - p0) / p0 >= 0.05 and (H[j] - low) / (H[j] - p0) >= 0.382:
                pick = j
                break
        if pick is None:
            break
        p1 = H[pick]
        fib = {"i0": i0, "i1": pick, "p0": p0, "p1": p1, "levels": [{"k": k, "p": p0 + k * (p1 - p0)} for k in RI_FIB]}
        if C[-1] <= p0 + 2 * (p1 - p0):
            break
        start = pick + 1
    if fib is None:
        # لا موجةَ بتراجعٍ صريح (اتجاهٌ متّصل): من قاع السنة إلى أعلى قمّةٍ بعده إن بلغ الصعودُ 3٪
        i0 = min(range(w0, n), key=lambda i: L[i])
        if i0 < n - 5:
            i1 = max(range(i0 + 1, n), key=lambda i: H[i])
            if (H[i1] - L[i0]) / L[i0] >= 0.03:
                fib = {"i0": i0, "i1": i1, "p0": L[i0], "p1": H[i1], "levels": [{"k": k, "p": L[i0] + k * (H[i1] - L[i0])} for k in RI_FIB]}
    return fib


def psych_step(c: float) -> float:
    """خطوةُ الأرقام النفسية: أقربُ رقمٍ «مستدير» (1 · 2 · 2.5 · 5 · 10 × عشرة) إلى 4٪ من السعر — 10,214 ← 500، و63 ← 2.5."""
    raw = c * 0.04
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    return min((m * mag for m in (1, 2, 2.5, 5, 10)), key=lambda x: abs(x - raw))


def research_ind(bars: list[dict]) -> dict | None:
    """مؤشّرُ الأبحاث من شموعٍ يومية ({o,h,l,c,v}): المتوسّطان، وRSI، وفيبوناتشي، وخطّا الاتجاه، والإشارات، والدعومُ والمقاوماتُ بالتلاقي."""
    n = len(bars)
    if n < 30:
        return None
    H, L, C = [b["h"] for b in bars], [b["l"] for b in bars], [b["c"] for b in bars]
    sma = lambda k: [sum(C[i - k + 1:i + 1]) / k if i >= k - 1 else None for i in range(n)]   # noqa: E731
    s20, s50 = sma(20), sma(50)
    rsi = _rsi_series(C)
    w0 = max(0, n - 250)
    fib = fib_anchor(H, L, C, w0)
    pH, pL = _pivots(H), _pivots(L, high=False)
    trend = {"res": None, "sup": None}
    hs = [j for j in pH if j >= w0]
    for a, b in zip(hs[::-1][1:], hs[::-1]):
        if H[a] > H[b]:
            slope = (H[b] - H[a]) / (b - a)
            trend["res"] = {"x1": a, "y1": H[a], "x2": n - 1, "y2": H[a] + slope * (n - 1 - a)}
            break
    ls = [j for j in pL if j >= w0]
    for a, b in zip(ls[::-1][1:], ls[::-1]):
        if L[a] < L[b]:
            slope = (L[b] - L[a]) / (b - a)
            trend["sup"] = {"x1": a, "y1": L[a], "x2": n - 1, "y2": L[a] + slope * (n - 1 - a)}
            break
    for k2 in ("res", "sup"):
        t = trend[k2]
        if t and not (0.85 * C[-1] <= t["y2"] <= 1.15 * C[-1]):
            trend[k2] = None
    sig = []
    for i in range(1, n):
        a, b = rsi[i - 1], rsi[i]
        if a is not None and b is not None:
            if a < 30 <= b:
                sig.append({"i": i, "side": "buy"})
            elif a > 70 >= b:
                sig.append({"i": i, "side": "sell"})
    return {"sma20": s20, "sma50": s50, "rsi": rsi, "fib": fib, "trend": trend, "signals": sig,
            "levels": research_levels(bars, s20[-1], s50[-1], fib, pH, pL)}


def research_levels(bars: list[dict], s20, s50, fib: dict | None, pH: list[int], pL: list[int]) -> dict:
    """الدعومُ الثلاثة والمحورُ والمقاوماتُ الثلاث بالتلاقي — كجدول «المقاومة والدعم» في التقرير المرجعيّ: فيبوناتشي والمتوسّطان والقممُ
    والقيعانُ السابقة (مئةٌ وعشرون جلسة) والأرقامُ النفسية، ولكلّ مستوًى اسمُه. والمحورُ مستوى فيبوناتشي على 1.5٪ من الإغلاق (الكسرُ الأخير)
    وإلا المحورُ الكلاسيكيّ؛ وما نقص من الطرفين يُكمَل بالكلاسيكيّ."""
    c, h, l = bars[-1]["c"], bars[-1]["h"], bars[-1]["l"]
    n = len(bars)
    cands: list[tuple[float, str]] = []
    if fib:
        cands += [(x["p"], f"فيبوناتشي {x['k'] * 100:g}٪" if x["k"] not in (0.0, 1.0) else ("قاع الموجة" if x["k"] == 0 else "قمة الموجة"))
                  for x in fib["levels"]]
    if s20:
        cands.append((s20, "متوسط 20"))
    if s50:
        cands.append((s50, "متوسط 50"))
    cands += [(bars[j]["h"], "قمة سابقة") for j in pH if j >= n - 120]
    cands += [(bars[j]["l"], "قاع سابق") for j in pL if j >= n - 120]
    step = psych_step(c)
    base = math.floor(c / step) * step
    real = list(cands)
    # الرقمُ النفسيُّ يُترك إن قاربه (0.6٪) مستوًى حقيقيّ — فالفيبوناتشي والمتوسّطُ والقمّةُ أَولى منه
    cands += [(v, "مستوى نفسي") for v in [base - k * step for k in range(0, 4)] + [base + k * step for k in range(1, 5)]
              if v > 0 and not any(abs(v - r[0]) / c < 0.006 for r in real)]
    cl = pivots(h, l, c)
    piv = None
    if fib:
        near = [x for x in fib["levels"] if abs(x["p"] - c) / c <= 0.015 and x["k"] not in (0.0,)]
        if near:
            x = min(near, key=lambda x: abs(x["p"] - c))
            piv = (x["p"], f"فيبوناتشي {x['k'] * 100:g}٪" if x["k"] != 1.0 else "قمة الموجة")
    if piv is None:
        piv = (cl["p"], "المحور الكلاسيكي")
    gap = 0.004 * c

    def side(vals, below):
        vals = sorted(vals, key=lambda v: -v[0] if below else v[0])
        out: list[tuple[float, str]] = []
        for v, nm in vals:
            if abs(v - piv[0]) < gap or any(abs(v - o[0]) < gap for o in out):
                continue
            out.append((v, nm))
            if len(out) == 3:
                break
        return out
    sup = side([x for x in cands if x[0] < min(c, piv[0]) - gap / 2], True)
    res = side([x for x in cands if x[0] > max(c, piv[0]) + gap / 2], False)
    for k in ("s1", "s2", "s3"):
        if len(sup) < 3 and cl[k] < min([s[0] for s in sup] + [piv[0], c]) - gap:
            sup.append((cl[k], "المحور الكلاسيكي"))
    for k in ("r1", "r2", "r3"):
        if len(res) < 3 and cl[k] > max([r[0] for r in res] + [piv[0], c]) + gap:
            res.append((cl[k], "المحور الكلاسيكي"))
    out = {"p": piv[0], "p_name": piv[1]}
    for i, (v, nm) in enumerate(sup[:3]):
        out[f"s{i + 1}"], out[f"s{i + 1}_name"] = v, nm
    for i, (v, nm) in enumerate(res[:3]):
        out[f"r{i + 1}"], out[f"r{i + 1}_name"] = v, nm
    return out


# ── جمعُ جلسة اليوم ────────────────────────────────────────────────────────
async def _index_raw() -> dict:
    from app.services import tadawul_market as TM
    from app.services.tadawul_http import fetch
    home = "https://www.saudiexchange.sa/wps/portal/saudiexchange/home"
    for url in (TM.INDEX_URL, TM.INDEX_URL_ALT):
        try:
            st, body = await fetch(url, referer=home)
            if st == 200 and body:
                d = json.loads(body)
                if isinstance(d, dict) and d.get("tasiValue") is not None:
                    return d
        except Exception:                                         # noqa: BLE001
            continue
    return {}


def daily_volume(hourly: list[dict]) -> dict:
    """كمّيةُ تاسي اليومية من شموعه الساعية — يوميُّه الرسميّ إغلاقٌ بلا كمّية (‏D663)، ولوحةُ الكمّية في رسم الأبحاث تحتاجها."""
    out: dict[str, float] = {}
    for b in hourly or []:
        d, v = str(b.get("date") or "")[:10], _f(b.get("volume")) or 0
        if d and v > 0:
            out[d] = out.get(d, 0.0) + v
    return out


def _summary(bean: dict | None) -> dict:
    s = ((bean or {}).get("tasiTodaysSummaryBean") or {}) if isinstance(bean, dict) else {}
    return {"close": _f(s.get("indexPrice")), "chg": _f(s.get("netChange")), "pct": _f(s.get("percentChange")),
            "high": _f(s.get("highPrice")), "low": _f(s.get("lowPrice")), "open": _f(s.get("openPrice")), "prev": _f(s.get("previouseIndexPrice"))}


def _fundamentals(sym: str) -> dict:
    """الأسهمُ القائمة وصافي الربح والحقوق من آخر سنةٍ مفصَحٍ عنها (XBRL) — ولا سنةٌ موسومةٌ بخطأ وحدة."""
    try:
        from app.services.tadawul_xbrl import for_symbol
        rows = for_symbol(sym, "annual") or []
    except Exception:                                             # noqa: BLE001
        return {}
    if not rows:
        return {}
    p = rows[-1]
    if p.get("shares_unit_gap") or p.get("shares_mismatch"):
        return {}
    ni, eps = _f(p.get("net_income")), _f(p.get("eps"))
    sh, ok = verified_shares(_f(p.get("shares_outstanding")), ni, eps)
    return {"shares": sh, "verified": ok, "ni": ni, "eq": _f(p.get("equity"))}


def verified_shares(sh: float | None, ni: float | None, eps: float | None) -> tuple[float | None, bool]:
    """الأسهمُ القائمةُ مُتحقَّقاً منها بالأسهم الضمنية (صافي الربح ÷ ربحية السهم) — قِيس (‏paper_caps_door): اثنتان وخمسون شركةً وحدةُ أسهمها
    في الإفصاح خاطئة (×1000 · ×10 · ÷1000)، فظهرت «الطبية التخصصية» ثانيةَ السوق وزناً. فإن قاربت الضمنيةَ (بين ثلثَيها ومرّةٍ ونصف — فرقُ
    المتوسّط المرجّح والإصدار) بقيت، وإن بعُدت بقوّةٍ من قوى العشرة صُحّحت وحدتُها، وإلا فالضمنيةُ إن كانت ربحيةُ السهم كبيرةً بما يكفي لدقّتها،
    وإلا لا أسهم. وبلا ربحيةٍ تبقى غيرَ متحقَّقٍ منها فتُختبر بمضاعف الدفترية لاحقاً."""
    if not sh or sh <= 0:
        sh = None
    imp = ni / eps if ni and eps and abs(eps) >= 0.05 else None
    if imp is None or imp <= 0:
        return sh, False
    if sh:
        r = sh / imp
        if 0.66 <= r <= 1.5:
            return sh, True
        k = round(math.log10(r))
        if k and 0.8 <= r / 10 ** k <= 1.25:
            return sh / 10 ** k, True
    return (imp, True) if abs(eps) >= 0.5 else (None, False)


def market_tables(rows: dict, names: dict, sectors: dict, fund: dict, dy: dict) -> dict:
    """القطاعاتُ والأكثرُ ارتفاعاً وانخفاضاً وقيمةً والأكبرُ وزناً والمؤشّراتُ المالية — من صفوف السوق الرئيسي وحدها."""
    sec: dict[str, dict] = {}
    caps, tot = [], {"cap": 0.0, "ni": 0.0, "eq": 0.0, "dyw": 0.0, "dyc": 0.0, "n": 0, "with": 0}
    plain = []
    for sym, r in rows.items():
        px, prev = _f(r.get("price")), _f(r.get("prev_close"))
        if not px:
            continue
        chg = _f(r.get("change_pct"))
        if chg is None and prev:
            chg = _pct(px, prev)
        plain.append({"symbol": sym, "name": names.get(sym) or r.get("name_en") or sym, "price": px, "pct": chg,
                      "value": _f(r.get("turnover"))})
        tot["n"] += 1
        f = fund.get(sym) or {}
        sh = f.get("shares")
        if sh and not f.get("verified"):
            # غيرُ المتحقَّق منه يُقبل إن عقل مضاعفُ دفتريته (‏0.05–50) — وإلا يُستبعد ولا يُرتَّب
            eq = f.get("eq")
            if not (eq and eq > 0 and 0.05 <= sh * px / eq <= 50):
                sh = None
        name_sec = sectors.get(sym) or "غير مصنّف"
        s = sec.setdefault(name_sec, {"name": name_sec, "cap": 0.0, "prev_cap": 0.0, "ni": 0.0, "value": None, "up": 0, "down": 0, "n": 0, "pcts": []})
        s["n"] += 1
        if _f(r.get("turnover")) is not None:
            s["value"] = (s["value"] or 0.0) + _f(r.get("turnover"))
        if chg is not None:
            s["pcts"].append(chg)
            if chg > 0:
                s["up"] += 1
            elif chg < 0:
                s["down"] += 1
        if sh:
            cap = sh * px
            pcap = sh * (prev or (px / (1 + chg / 100) if chg is not None else px))
            caps.append({"symbol": sym, "name": plain[-1]["name"], "price": px, "pct": chg, "cap": cap})
            s["cap"] += cap
            s["prev_cap"] += pcap
            tot["cap"] += cap
            tot["with"] += 1
            if f.get("ni") is not None:
                s["ni"] += f["ni"]
                tot["ni"] += f["ni"]
            if f.get("eq") is not None and f["eq"] > 0:
                tot["eq"] += f["eq"]
            y = dy.get(sym)
            if y is not None:
                tot["dyw"] += cap * y
                tot["dyc"] += cap
    out_sec = []
    for s in sec.values():
        if s["name"] == "غير مصنّف":
            continue
        pct = _pct(s["cap"], s["prev_cap"]) if s["prev_cap"] > 0 else (sum(s["pcts"]) / len(s["pcts"]) if s["pcts"] else None)
        out_sec.append({"name": s["name"], "pct": pct, "value": s["value"], "weight": (s["cap"] / tot["cap"] * 100) if tot["cap"] else None,
                        "pe": (s["cap"] / s["ni"]) if s["ni"] > 0 and s["cap"] else None, "up": s["up"], "down": s["down"]})
    out_sec.sort(key=lambda x: -(x["pct"] if x["pct"] is not None else -999))
    movers = [p for p in plain if p["pct"] is not None]
    cover = tot["with"] / tot["n"] if tot["n"] else 0
    fin = None
    if cover >= 0.75 and tot["cap"] > 0:
        fin = {"cap": tot["cap"], "pe": tot["cap"] / tot["ni"] if tot["ni"] > 0 else None, "pb": tot["cap"] / tot["eq"] if tot["eq"] > 0 else None,
               "roe": tot["ni"] / tot["eq"] * 100 if tot["eq"] > 0 else None, "dy": tot["dyw"] / tot["dyc"] if tot["dyc"] > 0 else None,
               "cover": round(cover * 100)}
    return {"sectors": out_sec,
            "gainers": sorted(movers, key=lambda p: -p["pct"])[:5],
            "losers": sorted(movers, key=lambda p: p["pct"])[:5],
            "active": sorted([p for p in plain if p["value"] is not None], key=lambda p: -p["value"])[:5],
            "heavy": sorted(caps, key=lambda c: -c["cap"])[:5],
            "fin": fin}


def quote_row(sym: str, name: str, pts: list[dict], bp: bool = False, upto: str | None = None) -> dict | None:
    """إغلاقٌ وتغيّرٌ يوميّ وشهريّ ومنذ بداية العام من تاريخٍ يوميّ — حتى يومٍ بعينه (`upto`) لأرشيف ما مضى؛ والفائدةُ بنقاط الأساس."""
    pts = [p for p in pts or [] if _f(p.get("close")) and (upto is None or str(p.get("date"))[:10] <= upto)]
    if len(pts) < 30:
        return None
    last, prev = pts[-1], pts[-2]
    d = str(last.get("date"))[:10]
    mb = [p for p in pts if str(p.get("date"))[:7] < d[:7]]
    yb = [p for p in pts if str(p.get("date"))[:4] < d[:4]]
    c, pc = _f(last["close"]), _f(prev["close"])
    mbase, ybase = (_f(mb[-1]["close"]) if mb else None), (_f(yb[-1]["close"]) if yb else None)
    if bp:
        ch = lambda b: (c - b) * 100 if b is not None else None   # noqa: E731
        return {"symbol": sym, "name": name, "close": c, "d1": ch(pc), "mtd": ch(mbase), "ytd": ch(ybase), "date": d, "bp": True}
    return {"symbol": sym, "name": name, "close": c, "d1": _pct(c, pc), "mtd": _pct(c, mbase), "ytd": _pct(c, ybase), "date": d}


async def _histories(spec) -> dict:
    from app.services.market_data import market_service as M

    async def one(sym):
        try:
            return sym, await asyncio.wait_for(M.get_history(sym, "1y"), 25) or []
        except Exception:                                         # noqa: BLE001
            return sym, []
    return dict(await asyncio.gather(*(one(s) for s, _ in spec)))


async def _quote_table(spec, bp: bool = False) -> list[dict]:
    """إغلاقٌ وتغيّرٌ يوميّ وشهريّ ومنذ بداية العام لكلّ رمز — من تاريخه اليوميّ؛ والفائدةُ تغيّرُها بنقاط الأساس."""
    h = await _histories(spec)
    return [r for r in (quote_row(s, n, h.get(s), bp) for s, n in spec) if r]


def history_append(store: dict, day: str, rec: dict) -> dict:
    """سجلُّ الجلسات (قيمةٌ وكمّيةٌ وصفقاتٌ وعمق) — رقمُ التطبيق يتقدّم على المقروء من التقارير، ويُحفظ سنةً."""
    store = dict(store or {})
    old = store.get(day) or {}
    if rec.get("src") == "app" or old.get("src") != "app":
        store[day] = {**old, **{k: v for k, v in rec.items() if v is not None}}
    keep = sorted(store)[-260:]
    return {k: store[k] for k in keep}


def averages(store: dict, day: str) -> dict:
    """معدّلُ القيم لخمسة أيامٍ وعشرةٍ وعشرين، والأسبوعُ الحاليّ والسابق — ما لا يكفيه السجلُّ لا يُحسب."""
    days = [d for d in sorted(store) if d <= day]

    def avg(key, n, scale):
        xs = [_f(store[d].get(key)) for d in days[-n:]]
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) / scale if len(xs) == n else None
    out = {}
    for key, scale, lbl in (("value", 1e9, "القيمة (مليار ريال)"), ("volume", 1e6, "الكمية (مليون سهم)"), ("trades", 1e3, "الصفقات (ألف)")):
        out[key] = {"label": lbl, "a5": avg(key, 5, scale), "a10": avg(key, 10, scale), "a20": avg(key, 20, scale)}
    d0 = date.fromisoformat(day)
    wk0 = d0 - timedelta(days=(d0.weekday() + 1) % 7)            # الأحد
    pw0, pw1 = wk0 - timedelta(days=7), wk0 - timedelta(days=1)

    def week(a: date, b: date):
        ds = [d for d in days if a.isoformat() <= d <= b.isoformat()]
        if not ds:
            return None
        s = lambda k: sum(_f(store[d].get(k)) or 0 for d in ds)   # noqa: E731
        return {"days": len(ds), "value": s("value") / 1e9, "volume": s("volume") / 1e6, "trades": s("trades") / 1e3}
    out["week"] = week(wk0, d0)
    out["prev_week"] = week(pw0, pw1)
    prev = [d for d in days if d < day]
    out["prev_value"] = _f(store[prev[-1]].get("value")) if prev else None
    out["n_days"] = len(days)
    out["avg63_value"] = (sum(_f(store[d].get("value")) or 0 for d in days[-63:]) / len(days[-63:])) if len(days) >= 20 else None
    out["avg63_volume"] = (sum(_f(store[d].get("volume")) or 0 for d in days[-63:]) / len(days[-63:])) if len(days) >= 20 else None
    return out


async def corporate_actions(today: date, days: int = 7, limit: int = 10) -> list[dict]:
    try:
        from app.services.content_engine import market_wide_events, clean_events
        from app.data.universe import is_main
        ev = clean_events(await market_wide_events()) or []
    except Exception:                                             # noqa: BLE001
        return []
    lo, hi = today.isoformat(), (today + timedelta(days=days)).isoformat()
    out, seen = [], set()
    for e in sorted(ev, key=lambda e: str(e.get("date") or "")):
        d = str(e.get("date") or "")[:10]
        sym = str(e.get("symbol") or "")
        key = (d, sym, e.get("title"))
        if not (lo <= d <= hi) or not is_main(sym) or key in seen:
            continue
        seen.add(key)
        out.append({"date": d, "company": e.get("company_name") or sym, "type": e.get("title") or "—"})
    return out[:limit]


async def gather(today: date | None = None) -> dict | None:
    """أرقامُ جلسة اليوم كلُّها — أو None إن لم تكن اليومَ جلسة (عطلةٌ أو لم يُغلق السوق بعد)."""
    from app.services import tadawul_market as TM
    from app.services.market_data import market_service as M
    from app.data.market_universe import MARKET_UNIVERSE as U
    from app.data.universe import is_main
    today = today or date.today()
    raw = await _index_raw()
    daily = await M.get_bars("^TASI.SR", "1d") or []
    t = technicals(daily)
    if not t or t["date"] != today.isoformat():
        logger.info("قسم الأبحاث: لا جلسةَ اليوم ({})", t["date"] if t else "—")
        return None
    tasi = _summary(raw.get("tasiBean")) if raw else {}
    for k, v in (("close", t["close"]), ("high", t["high"]), ("low", t["low"]), ("open", t["open"]), ("prev", t["prev"])):
        if tasi.get(k) is None:
            tasi[k] = v
    if tasi.get("pct") is None:
        tasi["pct"] = _pct(tasi["close"], tasi["prev"])
    if tasi.get("chg") is None and tasi.get("prev"):
        tasi["chg"] = tasi["close"] - tasi["prev"]
    mt = _summary(raw.get("mt30Bean")) if raw else {}
    if mt.get("close") is None and raw.get("mt30IndexValue") is not None:
        mt = {"close": _f(raw.get("mt30IndexValue")), "pct": _f(raw.get("mt30IndexPercentageChange")), "chg": _f(raw.get("mt30IndexNetChange"))}
    mb = raw.get("marketBean") or {}
    rows_all, _live, at = TM.usable_rows()
    rows = {s: r for s, r in (rows_all or {}).items() if is_main(s)}
    breadth = {"up": _f(mb.get("noOfUps")), "down": _f(mb.get("noOfDowns")), "unch": _f(mb.get("noOfNoChanges")),
               "value": _f(mb.get("turnover")), "volume": _f(mb.get("volumeTraded")), "trades": _f(mb.get("noOfTrades"))}
    if breadth["up"] is None and rows:
        ch = [_f(r.get("change_pct")) for r in rows.values()]
        breadth.update(up=sum(1 for c in ch if c and c > 0), down=sum(1 for c in ch if c and c < 0), unch=sum(1 for c in ch if c == 0))
    for k in ("value", "volume", "trades"):
        if breadth[k] is None and rows:
            breadth[k] = sum(_f(r.get({"value": "turnover"}.get(k, k))) or 0 for r in rows.values())
    names = {s: (U.get(s) or {}).get("name_ar") for s in rows}
    sectors = {s: (U.get(s) or {}).get("sector") for s in rows}
    fund = dict(zip(rows, await asyncio.to_thread(lambda: [_fundamentals(s) for s in rows])))
    dy = {}
    try:
        from app.services.market_screener import get_cached_screener
        for r in get_cached_screener() or []:
            y = _f(r.get("dividend_yield"))
            if y is not None:
                dy[str(r.get("symbol") or "").replace(".SR", "")] = y
    except Exception:                                             # noqa: BLE001
        pass
    tables = market_tables(rows, names, sectors, fund, dy)
    intra = [b for b in _bars_ok(await M.get_bars("^TASI.SR", "5m") or []) if b["date"][:10] == today.isoformat()]
    vol = daily_volume(await M.get_bars("^TASI.SR", "1h") or [])
    glob, com, fx, rates = await asyncio.gather(_quote_table(GLOBAL), _quote_table(COMMOD), _quote_table(FX), _quote_table(RATES, bp=True))
    return {"date": today.isoformat(), "at": at, "tasi": tasi, "mt30": mt, "tech": t, "breadth": breadth, **tables,
            "intraday": [{"t": b["date"][11:16], "c": b["close"], "v": b["volume"]} for b in intra],
            "daily": [{"d": b["date"][:10], "o": b["open"], "h": b["high"], "l": b["low"], "c": b["close"], "v": vol.get(b["date"][:10]) or b["volume"]}
                      for b in _bars_ok(daily)[-260:]],
            "global": glob, "commodities": com, "fx": fx, "rates": rates,
            "actions": await corporate_actions(today)}


# ── أرشيفُ الجلسات الماضية (‏D749 · بأمر المالك: «يتوفّر لجميع الأيام بتسلسلٍ تاريخيّ») ──────────────────────
async def history_context() -> dict:
    """ما يُبنى منه سوقُ أيّ جلسةٍ مضت — يُجمع مرّةً للأرشيف كلِّه: شموعُ تاسي اليومية وشموعُه دون اليوم، وإغلاقاتُ كلِّ شركةٍ في
    السوق الرئيسي سنةً، والإفصاحُ، وتواريخُ الأسواق العالمية والسلع والعملات والفائدة، ومفكرةُ السوق."""
    from app.services import tadawul_market as TM
    from app.services.market_data import market_service as M
    from app.data.market_universe import MARKET_UNIVERSE as U
    from app.data.universe import is_main
    syms = [s for s in (TM.usable_rows()[0] or {}) if is_main(s)]
    sem = asyncio.Semaphore(6)

    async def one(sym):
        async with sem:
            try:
                pts = await asyncio.wait_for(M.get_bars(f"{sym}.SR", "1d"), 30) or []
            except Exception:                                     # noqa: BLE001
                pts = []
            return sym, {str(p.get("date"))[:10]: _f(p.get("close")) for p in pts if _f(p.get("close"))}
    closes = dict(await asyncio.gather(*(one(s) for s in syms)))
    fund = dict(zip(syms, await asyncio.to_thread(lambda: [_fundamentals(s) for s in syms])))
    hist = {}
    for spec in (GLOBAL, COMMOD, FX, RATES):
        hist.update(await _histories(spec))
    try:
        from app.services.content_engine import market_wide_events, clean_events
        events = clean_events(await market_wide_events()) or []
    except Exception:                                             # noqa: BLE001
        events = []
    dy = {}
    try:
        from app.services.market_screener import get_cached_screener
        dy = {str(r.get("symbol") or "").replace(".SR", ""): _f(r.get("dividend_yield")) for r in get_cached_screener() or []
              if _f(r.get("dividend_yield")) is not None}
    except Exception:                                             # noqa: BLE001
        pass
    return {"tasi": _bars_ok(await M.get_bars("^TASI.SR", "1d") or []), "intra": _bars_ok(await M.get_bars("^TASI.SR", "5m") or []),
            "vol": daily_volume(await M.get_bars("^TASI.SR", "1h") or []),
            "closes": closes, "fund": fund, "hist": hist, "events": events, "dy": dy,
            "names": {s: (U.get(s) or {}).get("name_ar") for s in syms}, "sectors": {s: (U.get(s) or {}).get("sector") for s in syms}}


def market_at(day: str, ctx: dict, store: dict | None = None) -> dict | None:
    """سوقُ جلسةٍ مضت من سياقها — كلُّ رقمٍ حتى ذلك اليوم لا بعده: الشموعُ حتّاه، والقطاعاتُ والأكثرُ ارتفاعاً وانخفاضاً وعمقُ السوق من
    إغلاقات الشركات يومَها وما قبله، والقيمةُ والكمّيةُ والصفقاتُ من سجلّ الجلسات إن حُفظت، والأسواقُ العالمية بآخر إغلاقٍ حتّاه."""
    bars = [b for b in ctx["tasi"] if b["date"][:10] <= day]
    t = technicals(bars)
    if not t or t["date"] != day:
        return None
    rows = {}
    for sym, cl in ctx["closes"].items():
        c = cl.get(day)
        prev = [v for d, v in cl.items() if d < day]
        if c and prev:
            pk = max(d for d in cl if d < day)
            rows[sym] = {"price": c, "prev_close": cl[pk], "change_pct": _pct(c, cl[pk]), "turnover": None}
    tables = market_tables(rows, ctx["names"], ctx["sectors"], ctx["fund"], ctx["dy"])
    ch = [r["change_pct"] for r in rows.values() if r["change_pct"] is not None]
    rec = (store or {}).get(day) or {}
    breadth = {"up": sum(1 for c in ch if c > 0) if ch else None, "down": sum(1 for c in ch if c < 0) if ch else None,
               "unch": sum(1 for c in ch if c == 0) if ch else None,
               "value": _f(rec.get("value")), "volume": _f(rec.get("volume")), "trades": _f(rec.get("trades"))}
    d0 = date.fromisoformat(day)
    acts, seen = [], set()
    for e in sorted(ctx["events"], key=lambda e: str(e.get("date") or "")):
        ed = str(e.get("date") or "")[:10]
        k = (ed, e.get("symbol"), e.get("title"))
        if day <= ed <= (d0 + timedelta(days=7)).isoformat() and k not in seen and str(e.get("symbol") or "") in ctx["closes"]:
            seen.add(k)
            acts.append({"date": ed, "company": e.get("company_name") or e.get("symbol"), "type": e.get("title") or "—"})
    q = lambda spec, bp=False: [r for r in (quote_row(s, n, ctx["hist"].get(s), bp, upto=day) for s, n in spec) if r]   # noqa: E731
    intra = [b for b in ctx["intra"] if b["date"][:10] == day]
    return {"date": day, "at": None, "past": True,
            "tasi": {"close": t["close"], "high": t["high"], "low": t["low"], "open": t["open"], "prev": t["prev"], "chg": t["chg"], "pct": t["chg_pct"]},
            "mt30": {}, "tech": t, "breadth": breadth, **tables,
            "intraday": [{"t": b["date"][11:16], "c": b["close"], "v": b["volume"]} for b in intra],
            "daily": [{"d": b["date"][:10], "o": b["open"], "h": b["high"], "l": b["low"], "c": b["close"], "v": ctx.get("vol", {}).get(b["date"][:10]) or b["volume"]}
                      for b in bars[-260:]],
            "global": q(GLOBAL), "commodities": q(COMMOD), "fx": q(FX), "rates": q(RATES, True), "actions": acts[:10]}


# ── الاختيارات ونظرتُنا للمراكز ───────────────────────────────────────────
ADVISOR_VIEW = {"أضف على دفعتين": "شراء", "انتظر الشرط ثمّ أضف على دفعات": "شراء حذر", "احتفظ": "احتفاظ", "راقب": "محايد",
                "استبدل": "استبدال", "خفّف": "تخفيف"}


def position_view(p: dict) -> str:
    """نظرتُنا للمركز = موقفُ مستشار التطبيق نفسِه بمفردات بيوت الأبحاث — فلا تخالف الورقةُ شاشةَ المستشار.
    والتخفيفُ والمركزُ رابحٌ «جني الأرباح»."""
    v = ADVISOR_VIEW.get(str(p.get("action") or "").strip())
    if v == "تخفيف" and (_f(p.get("pnl")) or 0) > 0:
        return "جني الأرباح"
    return v or "محايد"


def trend_of(row: dict | None) -> str | None:
    if not row:
        return None
    a50, a200, mb = row.get("above_sma50"), row.get("above_sma200"), row.get("macd_bullish")
    if a50 and a200 and mb:
        return "صاعد"
    if a50 is False and a200 is False and mb is False:
        return "هابط"
    return "عرضي" if a50 is not None else None


def pick_candidates(screener: list[dict], held: set[str], limit: int = 5) -> list[dict]:
    """أفضلُ اختياراتنا — انتقائيةٌ بشروطٍ مجتمعةٍ كلِّها: قرارُ التطبيق شراء، وصعودٌ إلى القيمة العادلة 10٪ فأكثر، وفوق متوسّطَي 50 و200،
    والماكد إيجابيّ، والقوةُ النسبية بين 45 و68 (لا تشبّع)، ولا مخالفةَ شرعية. المراكزُ القائمةُ أوّلاً ثمّ الأعلى صعوداً."""
    out = []
    for r in screener or []:
        sym = str(r.get("symbol") or "").replace(".SR", "")
        dec = str(r.get("decision") or "").strip()
        up = _f(r.get("fair_value_upside_pct"))
        if up is None:
            up = _f(r.get("upside_pct"))
        rsi = _f(r.get("rsi"))
        sh = str(r.get("sharia") or "").lower()
        if (dec in BUY_DECISIONS and up is not None and up >= 10 and r.get("above_sma50") and r.get("above_sma200")
                and r.get("macd_bullish") and rsi is not None and 45 <= rsi <= 68 and "non" not in sh and "غير" not in sh):
            out.append({"symbol": sym, "name": r.get("name") or sym, "decision": dec, "upside": up, "rsi": rsi,
                        "fv": _f(r.get("fair_value")), "held": sym in held})
    out.sort(key=lambda x: (not x["held"], x["decision"] != "شراء قوي", -x["upside"]))
    return out[:limit]


def pick_levels(bars: list[dict]) -> dict | None:
    """نطاقُ الشراء بين الدعم الأوّل والإغلاق، والمستهدفُ بين المقاومتين الأولى والثانية، ووقفُ الخسارة بالتذبذب (مرّةٌ ونصفٌ من متوسّط المدى)."""
    t = technicals(bars)
    if not t or not t.get("atr"):
        return None
    rb = [{"d": b["date"][:10], "o": b["open"], "h": b["high"], "l": b["low"], "c": b["close"], "v": b["volume"]} for b in _bars_ok(bars)[-260:]]
    ri = research_ind(rb)
    c, a = t["close"], t["atr"]
    p = {**t["piv"], **{k: v for k, v in ((ri or {}).get("levels") or {}).items() if isinstance(v, (int, float))}}
    lo = max(p["s1"], c - 0.5 * a)
    tgt_lo, tgt_hi = max(p["r1"], c + 0.5 * a), max(p["r2"], c + a)
    stop = min(p["s2"], c - 1.5 * a)
    return {"close": c, "buy": [round(min(lo, c), 2), round(c, 2)], "target": [round(tgt_lo, 2), round(tgt_hi, 2)], "stop": round(stop, 2),
            "rsi": t["rsi"], "sma50": t["sma50"], "sma200": t["sma200"], "macd_hist": t["macd_hist"],
            "bars": rb}


async def picks_for(held: set[str]) -> list[dict]:
    from app.services.market_data import market_service as M
    try:
        from app.services.market_screener import get_cached_screener
        sc = get_cached_screener() or []
    except Exception:                                             # noqa: BLE001
        sc = []
    out = []
    for c in pick_candidates(sc, held):
        try:
            lv = pick_levels(await asyncio.wait_for(M.get_bars(f"{c['symbol']}.SR", "1d"), 25) or [])
        except Exception:                                         # noqa: BLE001
            lv = None
        if lv:
            out.append({**c, **lv})
    return out


# ── النصُّ المحسوب (لا نموذج) ───────────────────────────────────────────────
def n0(v) -> str:
    return "—" if _f(v) is None else f"{_f(v):,.0f}"


def n2(v) -> str:
    return "—" if _f(v) is None else f"{_f(v):,.2f}"


def p2(v) -> str:
    return "—" if _f(v) is None else f"{_f(v):+.2f}%"


def market_analysis(m: dict, av: dict) -> str:
    t, b = m["tasi"], m["breadth"]
    wd = WEEKDAYS[date.fromisoformat(m["date"]).weekday()]
    up = (t.get("pct") or 0) >= 0
    s = [f"أنهى مؤشر السوق الرئيسي تداولات يوم {wd} على {'ارتفاع' if up else 'انخفاض'} بنحو {abs(t.get('pct') or 0):.2f}% "
         f"عند {n2(t['close'])} نقطة."]
    if b.get("value"):
        v = f"بلغت قيمة التداولات {b['value'] / 1e9:,.2f} مليار ريال"
        if av.get("prev_value"):
            d = _pct(b["value"], av["prev_value"])
            v += f"، {'بارتفاع' if d >= 0 else 'بانخفاض'} بنحو {abs(d):.1f}% عن الجلسة السابقة"
        if (av.get("value") or {}).get("a20"):
            v += f"، مقارنةً بمتوسّط عشرين جلسةً البالغ {av['value']['a20']:,.2f} مليار ريال"
        s.append(v + ".")
    if b.get("up") is not None and b.get("down") is not None:
        s.append(f"بلغ عدد الأسهم المرتفعة إلى المنخفضة {int(b['up'])}/{int(b['down'])}.")
    if m.get("mt30", {}).get("close") and m["mt30"].get("pct") is not None:
        s.append(f"وأغلق مؤشر إم تي 30 عند {n2(m['mt30']['close'])} نقطة ({p2(m['mt30']['pct'])}).")
    sec = [x for x in m.get("sectors") or [] if x.get("pct") is not None]
    ups = [x for x in sec if x["pct"] > 0][:2]
    dns = sorted([x for x in sec if x["pct"] < 0], key=lambda x: x["pct"])[:2]

    def names(xs):
        q = [f"«{x['name']}»" for x in xs]
        return ("قطاعا " + " و".join(q)) if len(q) == 2 else ("قطاع " + q[0])

    def vals(xs):
        v = [f"{abs(x['pct']):.1f}%" for x in xs]
        return " و".join(v) + (" على التوالي" if len(v) == 2 else "")
    if ups:
        s.append(f"وكان {names(ups)} الأكثرَ ارتفاعاً بنحو {vals(ups)}.")
    if dns:
        s.append(f"{'بينما سجّل' if ups else 'وسجّل'} {names(dns)} أكبرَ انخفاضٍ بنحو {vals(dns)}.")
    return " ".join(s)


def tech_commentary(m: dict) -> tuple[str, str, str]:
    """(التعليق، التوقّعات، النصيحة) — جملٌ من الأرقام وحدها."""
    t, b = m["tech"], m["breadth"]
    wd = WEEKDAYS[date.fromisoformat(m["date"]).weekday()]
    up = t["chg"] >= 0
    c1 = (f"{'ارتفع' if up else 'تراجع'} مؤشر السوق الرئيسي يوم {wd} ليغلق عند {n2(t['close'])} نقطة "
          f"{'بمكسبٍ' if up else 'بخسارةٍ'} قدرُها {abs(t['chg']):,.2f} نقطة ({p2(t['chg_pct'])})، متحرّكاً بين {n2(t['low'])} و{n2(t['high'])} نقطة.")
    if b.get("value"):
        c1 += f" من حيث النشاط، بلغت قيمة التداول {b['value'] / 1e9:,.2f} مليار ريال"
        if b.get("volume"):
            c1 += f" وعدد الأسهم المتداولة نحو {b['volume'] / 1e6:,.1f} مليون سهم"
        c1 += "."
    cand = {"green": "شمعةً خضراء تعكس سيطرة معنويات الشراء", "red": "شمعةً حمراء تعكس ضغط البيع",
            "doji": "شمعةَ دوجي تعكس تردّد المتعاملين"}[t["candle"]]
    at = {"low": "، وأغلق قرب أدنى مستوياته في الجلسة", "high": "، وأغلق قرب أعلى مستوياته في الجلسة", "mid": ""}[t["close_at"]]
    o = [f"شكّل المؤشر {cand}{at}."]
    sm = []
    ri = ri_of(m)
    s20, s50 = (ri["sma20"][-1], ri["sma50"][-1]) if ri else (t.get("sma20"), t.get("sma50"))
    for v, lbl in ((s20, "لعشرين يوماً"), (s50, "لخمسين يوماً"), (t.get("sma200"), "لمئتي يوم")):
        if v:
            sm.append(f"{'فوق' if t['close'] > v else 'دون'} المتوسّط المتحرّك البسيط {lbl} ({n0(v)})")
    if sm:
        o.append("ويتداول المؤشر " + "، و".join(sm) + ".")
    fib = (ri or {}).get("fib")
    if fib:
        ext = [x for x in fib["levels"] if x["k"] > 1]
        under = [x for x in ext if x["p"] <= t["close"]]
        above = [x for x in ext if x["p"] > t["close"]]
        if under:
            o.append(f"ويتداول فوق امتداد {under[-1]['k'] * 100:g}٪ فيبوناتشي حول {n0(under[-1]['p'])} نقطة"
                     + (f"، والامتدادُ التالي {above[0]['k'] * 100:g}٪ حول {n0(above[0]['p'])} نقطة." if above else "."))
        elif above:
            o.append(f"وأوّلُ امتدادات فيبوناتشي {above[0]['k'] * 100:g}٪ حول {n0(above[0]['p'])} نقطة.")
    if t.get("rsi") is not None:
        r = t["rsi"]
        zone = ("في منطقة التشبّع الشرائي" if r >= 70 else "في منطقة التشبّع البيعي" if r <= 30 else "فوق مستوى 50" if r >= 50 else "دون مستوى 50")
        mc = ""
        if t.get("macd_hist") is not None:
            mc = f"، والماكد {'إيجابيّ' if t['macd_hist'] > 0 else 'سلبيّ'}"
            if t.get("macd_cross") == "up":
                mc += " بعد تقاطعٍ صاعدٍ حديث"
            elif t.get("macd_cross") == "down":
                mc += " بعد تقاطعٍ هابطٍ حديث"
        o.append(f"ويقف مؤشر القوة النسبية RSI عند {r:.1f} {zone}{mc}.")
    p = levels_of(m)
    nm = lambda k: f" ({p[k + '_name']})" if p.get(k + "_name") and p[k + "_name"] != "المحور الكلاسيكي" else ""   # noqa: E731
    if all(p.get(k) for k in ("s1", "s2", "r1", "r2")):
        o.append(f"يوجد دعمٌ فوريّ حول مستوى {n0(p['s1'])} نقطة{nm('s1')}، وقد يؤدّي كسره إلى التراجع نحو {n0(p['s2'])}{nm('s2')}"
                 + (f" ثمّ {n0(p['s3'])} نقطة{nm('s3')}" if p.get("s3") else " نقطة") + ". "
                 f"في المقابل، توجد مقاومةٌ فورية حول {n0(p['r1'])} نقطة{nm('r1')}، وقد يدفع اختراقها المؤشرَ نحو {n0(p['r2'])}{nm('r2')}"
                 + (f" ثمّ {n0(p['r3'])} نقطة{nm('r3')}" if p.get("r3") else " نقطة") + ".")
    adv = {"شراء": f"ننصح المتداولين بالشراء عند التراجع نحو الدعم الفوري {n0(p['s1'])}، مع مراقبة المقاومة {n0(p['r1'])}.",
           "شراء حذر": f"ننصح بالشراء الحذر والجزئيّ، على ألّا يُكسر الدعم {n0(p['s1'])} نقطة.",
           "احتفاظ": f"ننصح بالاحتفاظ بالمراكز القائمة ومراقبة الدعم {n0(p['s1'])} نقطة.",
           "محايد": f"ننصح بالانتظار حتى يتّضح الاتجاه باختراق {n0(p['r1'])} أو كسر {n0(p['s1'])} نقطة.",
           "نظرة حذرة": f"ننصح بالحذر وتقليل المخاطرة ما دام المؤشر دون {n0(p['r1'])} نقطة.",
           "جني الأرباح": f"المؤشر في منطقة تشبّعٍ شرائيّ؛ ننصح بجني جزءٍ من الأرباح قرب المقاومة {n0(p['r1'])} نقطة.",
           "اتجاه هابط": f"الاتجاه هابط؛ ننصح بتجنّب الشراء حتى يستعيد المؤشر مستوى {n0(p['r1'])} نقطة."}[t["view"]]
    return c1, " ".join(o), adv


def ri_of(m: dict) -> dict | None:
    """مؤشّرُ الأبحاث لشموع الورقة (سنةٌ يومية) — يُحسب مرّةً لكلّ ورقة."""
    if "_ri" not in m:
        m["_ri"] = research_ind(m.get("daily") or [])
    return m["_ri"]


def levels_of(m: dict) -> dict:
    """الدعومُ والمحورُ والمقاوماتُ بتلاقي مؤشّر الأبحاث — وإن قصرت الشموعُ فالمحورُ الكلاسيكيّ."""
    ri = ri_of(m)
    if ri:
        return ri["levels"]
    return dict((m.get("tech") or {}).get("piv") or {})


def pick_note(k: dict) -> str:
    s = []
    if k.get("sma50") and k.get("sma200"):
        s.append(f"يتداول السهم فوق متوسّطيه لخمسين يوماً ({n2(k['sma50'])}) ومئتي يوم ({n2(k['sma200'])})")
    if k.get("rsi") is not None:
        s.append(f"القوةُ النسبية عند {k['rsi']:.0f}")
    if (k.get("macd_hist") or 0) > 0:
        s.append("الماكد إيجابيّ")
    if k.get("upside") is not None:
        s.append(f"الصعودُ إلى القيمة العادلة {k['upside']:.0f}%")
    return (s[0] + "".join("، و" + x for x in s[1:]) + ".") if s else ""


# ── الرسوم (SVG) ───────────────────────────────────────────────────────────
# ‏D752 (بأمر المالك: «الرسمُ البيانيُّ نفسُ الذي في الجزيرة كابيتال» — رسمُ تريدنق فيو): شموعُ تريدنق فيو بألوانها، ومتوسّطاها الأزرقُ
# والبرتقاليّ، ومحورُ السعر يمينَ الرسم ببطاقة آخر سعر، وسطرُ الأسعار أعلاه (‏O H L C)، ولوحةُ القوة النسبية بنطاقها البنفسجيّ.
# وما سوى الرسوم بهويّة تقارير التطبيق (‏saqr_report): البنفسجيُّ والذهبيُّ على الورق الكريميّ.
TV_UP, TV_DN, TV_GRID, TV_AX, TV_BORDER = "#26a69a", "#ef5350", "#f0f3fa", "#787b86", "#e0e3eb"
TV_MA = ("#2962ff", "#ff6d00", "#9c27b0")
TV_RSI, TV_RSI_BAND = "#7e57c2", "rgba(126,87,194,.10)"
try:
    from app.services.saqr_report import NAVY, NAVY_2, GOLD, GOLD_L, GREEN, RED, PAPER, INK, LINE, ZEBRA, MUTED
except Exception:                                                 # noqa: BLE001
    NAVY, NAVY_2, GOLD, GOLD_L = "#3b1e78", "#6d28d9", "#d4af37", "#f3d98b"
    GREEN, RED, PAPER, INK, LINE, ZEBRA, MUTED = "#0f9d63", "#c0273c", "#faf6ee", "#241f1a", "#e4dcc2", "#f6f2e4", "#6b6459"
MUT, POS, NEG = MUTED, GREEN, RED


def _scale(lo, hi, a, b):
    span = (hi - lo) or 1
    return lambda v: b - (v - lo) / span * (b - a)


def _ticks(lo, hi, n):
    step = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(step)) if step > 0 else 1
    step = next((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= step), step)
    v = math.ceil(lo / step) * step
    out = []
    while v <= hi and len(out) < 8:
        out.append(v)
        v += step
    return out


def _fmt(v: float) -> str:
    return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:,.2f}"


def _tag(x: float, y: float, txt: str, fill: str, w: int = 44) -> str:
    """بطاقةُ قيمةٍ على محور السعر كتريدنق فيو."""
    return (f'<rect x="{x:.1f}" y="{y - 7:.1f}" width="{w}" height="14" rx="2" fill="{fill}"/>'
            f'<text x="{x + 3:.1f}" y="{y + 3.5:.1f}" font-size="9.5" fill="#fff" font-family="Arial,sans-serif">{txt}</text>')


def svg_intraday(pts: list[dict], w: int = 340, h: int = 150) -> str:
    """حركةُ المؤشر خلال الجلسة — خطٌّ بمساحةٍ متدرّجة وأعمدةُ كمّيةٍ بلون اتجاهها، كخطّ تريدنق فيو."""
    if len(pts) < 3:
        return ""
    cs = [p["c"] for p in pts]
    lo, hi = min(cs), max(cs)
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    X0, X1, Y0, Y1, VB = 4, w - 46, 8, h - 34, h - 16
    y = _scale(lo, hi, Y0, Y1)
    x = lambda i: X0 + i / (len(pts) - 1) * (X1 - X0)   # noqa: E731
    vmax = max(p["v"] for p in pts) or 1
    out = [f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" fill="#fff" stroke="{TV_BORDER}"/>',
           '<defs><linearGradient id="ig" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2962ff" stop-opacity=".28"/>'
           '<stop offset="1" stop-color="#2962ff" stop-opacity="0"/></linearGradient></defs>']
    out += [f'<line x1="{X0}" x2="{X1}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{TV_GRID}"/>'
            f'<text x="{X1 + 4}" y="{y(v) + 3:.1f}" font-size="9.5" fill="{TV_AX}" font-family="Arial,sans-serif">{_fmt(v)}</text>'
            for v in _ticks(lo, hi, 4)]
    for i, p in enumerate(pts):
        up = i == 0 or p["c"] >= pts[i - 1]["c"]
        bh = p["v"] / vmax * 18
        out.append(f'<rect x="{x(i) - 1.4:.1f}" y="{VB - bh:.1f}" width="2.8" height="{bh:.1f}" fill="{TV_UP if up else TV_DN}" opacity=".5"/>')
    line = " ".join(f"{x(i):.1f},{y(p['c']):.1f}" for i, p in enumerate(pts))
    out.append(f'<polygon points="{X0},{Y1} {line} {x(len(pts) - 1):.1f},{Y1}" fill="url(#ig)"/>'
               f'<polyline points="{line}" fill="none" stroke="#2962ff" stroke-width="1.6"/>')
    seen = set()
    for i, p in enumerate(pts):
        if p["t"].endswith(":00") and p["t"] not in seen:
            seen.add(p["t"])
            out.append(f'<text x="{x(i):.1f}" y="{h - 3}" font-size="9.5" fill="{TV_AX}" text-anchor="middle" font-family="Arial,sans-serif">{p["t"]}</text>')
    out.append(_tag(X1 + 1, y(cs[-1]), _fmt(cs[-1]), TV_UP if cs[-1] >= cs[0] else TV_DN))
    return f'<svg direction="ltr" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="حركة المؤشر خلال الجلسة">{"".join(out)}</svg>'


_LVL = {"s1": "دعم 1", "s2": "دعم 2", "r1": "مقاومة 1", "r2": "مقاومة 2", "p": "المحور"}


def svg_candles(bars: list[dict], w: int = 470, h: int = 270, sma=(10, 50), levels: dict | None = None, rsi: bool = True,
                band: tuple | None = None, label: str = "") -> str:
    """الرسمُ اليوميّ بهيئة تريدنق فيو: سطرُ الأسعار، والشموع، والمتوسّطان، ومستوياتُ الدعم والمقاومة ببطاقاتها على المحور، والكمّية،
    ولوحةُ القوة النسبية — كرسم التقرير المرجعيّ."""
    if len(bars) < 10:
        return ""
    cl = [b["c"] for b in bars]
    smas = {n: [(_sma(cl[:i + 1], n)) for i in range(len(cl))] for n in sma}
    lvl = levels or {}
    vals = [b["h"] for b in bars] + [b["l"] for b in bars] + [v for v in lvl.values() if v] + ([v for v in band if v] if band else [])
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.05 or 1
    lo, hi = lo - pad, hi + pad
    RH = 58 if rsi else 0
    X0, X1, Y0, Y1 = 4, w - 50, 20, h - 16 - RH
    y = _scale(lo, hi, Y0, Y1)
    n = len(bars)
    bw = (X1 - X0) / n
    x = lambda i: X0 + (i + 0.5) * bw   # noqa: E731
    out = [f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" fill="#fff" stroke="{TV_BORDER}"/>']
    out += [f'<line x1="{X0}" x2="{X1}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{TV_GRID}"/>'
            f'<text x="{X1 + 4}" y="{y(v) + 3:.1f}" font-size="9.5" fill="{TV_AX}" font-family="Arial,sans-serif">{_fmt(v)}</text>'
            for v in _ticks(lo, hi, 5)]
    vols = [b.get("v") or 0 for b in bars]
    vmax = max(vols) or 0
    if vmax:
        for i, b in enumerate(bars):
            vh = (b.get("v") or 0) / vmax * (Y1 - Y0) * 0.18
            out.append(f'<rect x="{x(i) - bw * 0.34:.1f}" y="{Y1 - vh:.1f}" width="{bw * 0.68:.1f}" height="{vh:.1f}" '
                       f'fill="{TV_UP if b["c"] >= b["o"] else TV_DN}" opacity=".28"/>')
    if band and band[0] and band[1]:
        out.append(f'<rect x="{X0}" y="{y(max(band)):.1f}" width="{X1 - X0}" height="{max(1.0, abs(y(band[0]) - y(band[1]))):.1f}" fill="{TV_UP}" opacity=".14"/>')
    for i, b in enumerate(bars):
        col = TV_UP if b["c"] >= b["o"] else TV_DN
        out.append(f'<line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{y(b["h"]):.1f}" y2="{y(b["l"]):.1f}" stroke="{col}" stroke-width=".9"/>'
                   f'<rect x="{x(i) - bw * 0.36:.1f}" y="{y(max(b["o"], b["c"])):.1f}" width="{bw * 0.72:.1f}" '
                   f'height="{max(0.8, abs(y(b["o"]) - y(b["c"]))):.1f}" fill="{col}"/>')
    for (k, ser), col in zip(smas.items(), TV_MA):
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(ser) if v is not None)
        if pts:
            out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.3"/>')
    last = bars[-1]
    # بطاقاتُ المحور لا تتراكب: آخرُ سعرٍ أوّلاً ثمّ المستوياتُ تُزاح عنه وعن بعضها، واسمُ المستوى يُكتب إن اتّسع له المكان
    tags = [(y(last["c"]), _fmt(last["c"]), TV_UP if last["c"] >= last["o"] else TV_DN)]
    names_y: list[float] = []
    for name, v in sorted(((k, v) for k, v in lvl.items() if v and lo <= v <= hi), key=lambda kv: -kv[1]):
        col = TV_DN if name.startswith(("s", "وقف")) else TV_UP if name.startswith(("r", "هدف")) else TV_AX
        out.append(f'<line x1="{X0}" x2="{X1}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{col}" stroke-width=".9" stroke-dasharray="5 4"/>')
        if all(abs(y(v) - z) >= 11 for z in names_y):
            names_y.append(y(v))
            out.append(f'<text x="{X0 + 3}" y="{y(v) - 2.5:.1f}" font-size="9.5" fill="{col}">{_html.escape(_LVL.get(name, name))}</text>')
        tags.append((y(v), _fmt(v), col))
    placed: list[float] = []
    for ty, txt, col in tags:
        t = ty
        while any(abs(t - z) < 14 for z in placed):
            t += 14 if t >= ty else -14
            if t > Y1 + 6:
                t = ty - 14
        placed.append(t)
        out.append(_tag(X1 + 1, t, txt, col))
    prev = bars[-2]["c"]
    chg = last["c"] - prev
    leg = (f'<tspan fill="{INK}" font-weight="700">{_html.escape(label or "يومي")}</tspan>'
           + "".join(f'<tspan fill="{TV_AX}"> {k} </tspan><tspan fill="{TV_UP if last["c"] >= last["o"] else TV_DN}">{_fmt(last[k2])}</tspan>'
                     for k, k2 in (("O", "o"), ("H", "h"), ("L", "l"), ("C", "c")))
           + f'<tspan fill="{TV_UP if chg >= 0 else TV_DN}"> {chg:+,.2f} ({chg / prev * 100:+.2f}%)</tspan>')
    out.append(f'<text x="{X0 + 4}" y="13" font-size="9.5" font-family="Arial,sans-serif">{leg}</text>')
    ma = "".join(f'<tspan fill="{c}">SMA {k} </tspan>' for k, c in zip(sma, TV_MA))
    out.append(f'<text x="{X0 + 4}" y="{Y1 - 4 if not vmax else Y0 + 12}" font-size="9.5" font-family="Arial,sans-serif">{ma}</text>')
    if rsi:
        rs = [_rsi(cl[:i + 1]) if i >= 15 else None for i in range(len(cl))]
        ry = _scale(0, 100, h - RH + 2, h - 14)
        out.append(f'<line x1="0" x2="{w}" y1="{h - RH - 2}" y2="{h - RH - 2}" stroke="{TV_BORDER}"/>'
                   f'<rect x="{X0}" y="{ry(70):.1f}" width="{X1 - X0}" height="{ry(30) - ry(70):.1f}" fill="{TV_RSI_BAND}"/>')
        for lv in (30, 70):
            out.append(f'<line x1="{X0}" x2="{X1}" y1="{ry(lv):.1f}" y2="{ry(lv):.1f}" stroke="{TV_AX}" stroke-width=".6" stroke-dasharray="3 3"/>'
                       f'<text x="{X1 + 4}" y="{ry(lv) + 3:.1f}" font-size="9.5" fill="{TV_AX}" font-family="Arial,sans-serif">{lv}</text>')
        pts = " ".join(f"{x(i):.1f},{ry(v):.1f}" for i, v in enumerate(rs) if v is not None)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{TV_RSI}" stroke-width="1.2"/>')
        if rs[-1] is not None:
            out.append(f'<text x="{X0 + 4}" y="{h - RH + 12}" font-size="9.5" font-family="Arial,sans-serif"><tspan fill="{INK}">RSI 14</tspan>'
                       f'<tspan fill="{TV_RSI}"> {rs[-1]:.2f}</tspan></text>')
    # التواريخ أسفلَ الرسم
    step = max(1, n // 5)
    for i in range(step // 2, n, step):
        d = bars[i]["d"]
        out.append(f'<text x="{x(i):.1f}" y="{h - 3}" font-size="9.5" fill="{TV_AX}" text-anchor="middle" font-family="Arial,sans-serif">{d[8:10]}/{d[5:7]}</text>')
    return f'<svg direction="ltr" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="الرسم البياني اليومي">{"".join(out)}</svg>'


def svg_research(bars: list[dict], w: int = 470, h: int = 330, title: str = "", ri: dict | None = None, extra: dict | None = None) -> str:
    """رسمُ مؤشّر الأبحاث بهيئة رسم التقرير المرجعيّ (تريدنق فيو): لوحةُ السعر بشموعها ومتوسّطَي 20 و50 وفيبوناتشي بتسمياته وخطَّي الاتجاه
    وأسهمِ الشراء والبيع، ثمّ لوحةُ الكمّية، ثمّ لوحةُ RSI 14 بحدَّيها ونطاقها. و`extra` مستوياتٌ إضافية (نطاقُ الشراء والهدفُ والوقف للاختيارات)."""
    if len(bars) < 30:
        return ""
    ri = ri or research_ind(bars)
    if not ri:
        return ""
    n = len(bars)
    PT, PB = 34, h - 132                                       # لوحةُ السعر — تحت سطرَي العنوان والمتوسّطين
    VT, VB = PB + 6, PB + 46                                   # لوحةُ الكمّية
    RT, RB = VB + 8, h - 16                                    # لوحةُ RSI
    X0, X1 = 4, w - 52
    fl = [x["p"] for x in (ri["fib"] or {}).get("levels", []) if x["k"] <= 2]
    ex = [v for v in (extra or {}).values() if v]
    vals = [b["h"] for b in bars] + [b["l"] for b in bars]
    lo, hi = min(vals + ex), max(vals + ex)
    lo2 = min([lo] + [v for v in fl if v >= lo - (hi - lo) * 0.25])
    hi2 = max([hi] + [v for v in fl if v <= hi + (hi - lo) * 0.25])
    pad = (hi2 - lo2) * 0.04 or 1
    lo, hi = lo2 - pad, hi2 + pad
    y = _scale(lo, hi, PT, PB)
    bw = (X1 - X0) / n
    x = lambda i: X0 + (i + 0.5) * bw   # noqa: E731
    out = [f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" fill="#fff" stroke="{TV_BORDER}"/>']
    for v in _ticks(lo, hi, 5):
        out.append(f'<line x1="{X0}" x2="{X1}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{TV_GRID}"/>'
                   f'<text x="{X1 + 4}" y="{y(v) + 3:.1f}" font-size="9.5" fill="{TV_AX}" font-family="Arial,sans-serif">{_fmt(v)}</text>')
    # فيبوناتشي — خطوطٌ زرقاء بتسميةٍ يسارَها كأداة تريدنق فيو: «1.618 (10,490.82)»
    if ri["fib"]:
        x1f = x(ri["fib"]["i0"]) - bw / 2
        for lv in ri["fib"]["levels"]:
            if lo <= lv["p"] <= hi:
                out.append(f'<line x1="{x1f:.1f}" x2="{X1}" y1="{y(lv["p"]):.1f}" y2="{y(lv["p"]):.1f}" stroke="{RI_COLORS["fib"]}" stroke-width=".8" opacity=".85"/>'
                           f'<text x="{max(X0 + 2, x1f - 2):.1f}" y="{y(lv["p"]) - 2:.1f}" font-size="9.5" fill="{RI_COLORS["fib"]}" font-family="Arial,sans-serif">'
                           f'{lv["k"]:g} ({lv["p"]:,.2f})</text>')
    if extra and extra.get("buy_lo") and extra.get("buy_hi"):
        out.append(f'<rect x="{X0}" y="{y(extra["buy_hi"]):.1f}" width="{X1 - X0}" height="{max(1.0, y(extra["buy_lo"]) - y(extra["buy_hi"])):.1f}" fill="{TV_UP}" opacity=".13"/>')
    vmax = max((b.get("v") or 0) for b in bars) or 0
    for i, b in enumerate(bars):
        col = TV_UP if b["c"] >= b["o"] else TV_DN
        out.append(f'<line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{y(b["h"]):.1f}" y2="{y(b["l"]):.1f}" stroke="{col}" stroke-width=".7"/>'
                   f'<rect x="{x(i) - bw * 0.38:.1f}" y="{y(max(b["o"], b["c"])):.1f}" width="{max(.6, bw * 0.76):.1f}" '
                   f'height="{max(0.7, abs(y(b["o"]) - y(b["c"]))):.1f}" fill="{col}"/>')
        if vmax:
            vh = (b.get("v") or 0) / vmax * (VB - VT)
            out.append(f'<rect x="{x(i) - bw * 0.38:.1f}" y="{VB - vh:.1f}" width="{max(.6, bw * 0.76):.1f}" height="{vh:.1f}" fill="{col}" opacity=".55"/>')
    for key in ("sma20", "sma50"):
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(ri[key]) if v is not None)
        if pts:
            out.append(f'<polyline points="{pts}" fill="none" stroke="{RI_COLORS[key]}" stroke-width="1.5"/>')
    for t in (ri["trend"]["res"], ri["trend"]["sup"]):
        if t:
            out.append(f'<line x1="{x(t["x1"]):.1f}" y1="{y(t["y1"]):.1f}" x2="{x(t["x2"]):.1f}" y2="{y(t["y2"]):.1f}" stroke="{RI_COLORS["trend"]}" stroke-width="1"/>')
    for name, v in (extra or {}).items():
        if name in ("stop", "target") and v and lo <= v <= hi:
            col = TV_DN if name == "stop" else TV_UP
            out.append(f'<line x1="{X0}" x2="{X1}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{col}" stroke-width=".9" stroke-dasharray="5 4"/>'
                       f'<text x="{X0 + 3}" y="{y(v) - 2.5:.1f}" font-size="9.5" fill="{col}">{"وقف الخسارة" if name == "stop" else "الهدف"}</text>')
    # أسهمُ الشراء والبيع (عبورُ RSI حدَّي 30 و70) على الشموع وعلى لوحة RSI
    ry = _scale(0, 100, RT, RB)
    for s_ in ri["signals"]:
        i = s_["i"]
        if s_["side"] == "buy":
            yy = y(bars[i]["l"]) + 9
            out.append(f'<path d="M{x(i):.1f},{yy - 6:.1f} l-4,6 h8 z" fill="{RI_COLORS["buy"]}"/>')
        else:
            yy = y(bars[i]["h"]) - 9
            out.append(f'<path d="M{x(i):.1f},{yy + 6:.1f} l-4,-6 h8 z" fill="{RI_COLORS["sell"]}"/>')
    last, prev = bars[-1], bars[-2]["c"]
    chg = last["c"] - prev
    tags = [(y(last["c"]), _fmt(last["c"]), TV_UP if last["c"] >= last["o"] else TV_DN)]
    placed: list[float] = []
    for ty, txt, col in tags:
        placed.append(ty)
        out.append(_tag(X1 + 1, ty, txt, col))
    leg = (f'<tspan fill="{INK}" font-weight="700">{_html.escape(title or "")} · 1D</tspan>'
           + "".join(f'<tspan fill="{TV_AX}"> {k} </tspan><tspan fill="{TV_UP if last["c"] >= last["o"] else TV_DN}">{_fmt(last[k2])}</tspan>'
                     for k, k2 in (("O", "o"), ("H", "h"), ("L", "l"), ("C", "c")))
           + f'<tspan fill="{TV_UP if chg >= 0 else TV_DN}"> {chg:+,.2f} ({chg / prev * 100:+.2f}%)</tspan>')
    out.append(f'<text x="{X0 + 4}" y="13" font-size="9.5" font-family="Arial,sans-serif" direction="ltr" unicode-bidi="embed">{leg}</text>')
    s20, s50 = ri["sma20"][-1], ri["sma50"][-1]
    out.append(f'<text x="{X0 + 4}" y="26" font-size="9.5" font-family="Arial,sans-serif">'
               f'<tspan fill="{RI_COLORS["sma20"]}">20 SMA {_fmt(s20) if s20 else "—"}</tspan>'
               f'<tspan fill="{RI_COLORS["sma50"]}">  50 SMA {_fmt(s50) if s50 else "—"}</tspan></text>')
    # لوحةُ الكمّية
    out.append(f'<line x1="0" x2="{w}" y1="{PB + 3}" y2="{PB + 3}" stroke="{TV_BORDER}"/>')
    if vmax:
        out.append(f'<text x="{X0 + 4}" y="{VT + 9}" font-size="9.5" fill="{TV_AX}" font-family="Arial,sans-serif">Volume '
                   f'<tspan fill="{INK}">{(last.get("v") or 0) / 1e6:,.2f} M</tspan></text>')
    # لوحةُ RSI
    out.append(f'<line x1="0" x2="{w}" y1="{VB + 4}" y2="{VB + 4}" stroke="{TV_BORDER}"/>'
               f'<rect x="{X0}" y="{ry(70):.1f}" width="{X1 - X0}" height="{ry(30) - ry(70):.1f}" fill="{RI_COLORS["rsi_band"]}"/>')
    for lv in (30, 70):
        out.append(f'<line x1="{X0}" x2="{X1}" y1="{ry(lv):.1f}" y2="{ry(lv):.1f}" stroke="{TV_AX}" stroke-width=".6" stroke-dasharray="3 3"/>'
                   f'<text x="{X1 + 4}" y="{ry(lv) + 3:.1f}" font-size="9.5" fill="{TV_AX}" font-family="Arial,sans-serif">{lv}</text>')
    pts = " ".join(f"{x(i):.1f},{ry(v):.1f}" for i, v in enumerate(ri["rsi"]) if v is not None)
    out.append(f'<polyline points="{pts}" fill="none" stroke="{RI_COLORS["rsi"]}" stroke-width="1.1"/>')
    for s_ in ri["signals"]:
        v = ri["rsi"][s_["i"]]
        if v is not None:
            col = RI_COLORS["buy"] if s_["side"] == "buy" else RI_COLORS["sell"]
            out.append(f'<circle cx="{x(s_["i"]):.1f}" cy="{ry(v):.1f}" r="2.4" fill="{col}"/>')
    rv = ri["rsi"][-1]
    out.append(f'<text x="{X0 + 4}" y="{RT + 10}" font-size="9.5" font-family="Arial,sans-serif"><tspan fill="{INK}">RSI 14 close</tspan>'
               + (f'<tspan fill="{RI_COLORS["rsi"]}"> {rv:.2f}</tspan>' if rv is not None else "") + '</text>')
    step = max(1, n // 6)
    for i in range(step // 2, n, step):
        d = str(bars[i].get("d") or "")
        if d:
            out.append(f'<text x="{x(i):.1f}" y="{h - 4}" font-size="9.5" fill="{TV_AX}" text-anchor="middle" font-family="Arial,sans-serif">{d[8:10]}/{d[5:7]}/{d[2:4]}</text>')
    return f'<svg direction="ltr" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="الرسم البياني اليومي — مؤشر الأبحاث">{"".join(out)}</svg>'


def svg_gauge(view: str, w: int = 230, h: int = 136) -> str:
    cx, cy, R, r = w / 2, h - 18, 96, 58
    nV = len(VIEWS)
    k = VIEWS.index(view) if view in VIEWS else 3
    shades = ("#8c1d2f", RED, "#d98c6a", "#b8ad94", NAVY_2, "#3f9e76", GREEN)
    out = []
    for i in range(nV):
        a0, a1 = math.pi - i * math.pi / nV, math.pi - (i + 1) * math.pi / nV

        def pt(a, rr):
            return cx + rr * math.cos(a), cy - rr * math.sin(a)
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pt(a0, R), pt(a1, R), pt(a1, r), pt(a0, r)
        on = i == k
        out.append(f'<path d="M{x0:.1f},{y0:.1f} A{R},{R} 0 0 1 {x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f} A{r},{r} 0 0 0 {x3:.1f},{y3:.1f} Z" '
                   f'fill="{shades[i]}" opacity="{1 if on else .2}" stroke="{PAPER}" stroke-width="1.5"/>')
        lx, ly = pt((a0 + a1) / 2, (R + r) / 2)
        words = VIEWS[i].split(" ")
        for j, wd in enumerate(words):
            out.append(f'<text x="{lx:.1f}" y="{ly + (j - (len(words) - 1) / 2) * 10 + 3:.1f}" font-size="9.5" text-anchor="middle" '
                       f'fill="{"#fff" if on else INK}">{wd}</text>')
    am = math.pi - (k + 0.5) * math.pi / nV
    nx, ny = cx + (r - 8) * math.cos(am), cy - (r - 8) * math.sin(am)
    out.append(f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="{NAVY}" stroke-width="2.4" stroke-linecap="round"/>'
               f'<circle cx="{cx}" cy="{cy}" r="5" fill="{GOLD}" stroke="{NAVY}" stroke-width="1.5"/>'
               f'<text x="{cx}" y="{h - 2}" font-size="12" text-anchor="middle" fill="{NAVY}">{_html.escape(view)}</text>')
    return f'<svg direction="ltr" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="نظرتنا: {_html.escape(view)}">{"".join(out)}</svg>'


def svg_breadth(up, unch, down, w: int = 230, h: int = 118) -> str:
    vals = [("ارتفاع", _f(up) or 0, GREEN), ("استقرار", _f(unch) or 0, "#b8ad94"), ("انخفاض", _f(down) or 0, RED)]
    mx = max(v for _, v, _ in vals) or 1
    out, bw = [], 46
    for i, (lbl, v, col) in enumerate(vals):
        xr = w - 30 - i * (bw + 26)
        bh = v / mx * (h - 40)
        out.append(f'<rect x="{xr - bw:.1f}" y="{h - 20 - bh:.1f}" width="{bw}" height="{bh:.1f}" rx="2" fill="{col}"/>'
                   f'<text x="{xr - bw / 2:.1f}" y="{h - 24 - bh:.1f}" font-size="11" text-anchor="middle" fill="{INK}">{int(v)}</text>'
                   f'<text x="{xr - bw / 2:.1f}" y="{h - 5}" font-size="9.5" text-anchor="middle" fill="{MUT}">{lbl}</text>')
    return f'<svg direction="ltr" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="عمق السوق">{"".join(out)}</svg>'


# ── الورقة (HTML) ───────────────────────────────────────────────────────────
def _e(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def _num(v, fmt=n2, cls: bool = False) -> str:
    s = fmt(v)
    c = "" if not cls or _f(v) is None else (" pos" if _f(v) > 0 else " neg" if _f(v) < 0 else "")
    return f'<span class="n{c}">{s}</span>'


def _tbl(head: list[str], rows: list[list[str]], cls: str = "") -> str:
    if not rows:
        return ""
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def _iso(v) -> str:
    """الرقمُ المفردُ (بعلامته ونسبته) يُعزل باتجاهه اللاتينيّ فلا تقفز العلامة؛ وما فيه كلامٌ أو رقمان يبقى بالاتجاه العربيّ."""
    return ' class="n"' if re.fullmatch(r"[+\-−]?[\d,.]+%?", str(v or "").strip()) else ""


def _band(t: str) -> str:
    return f'<div class="band">{_e(t)}</div>'


def _bul(rows: list[dict]) -> str:
    return "<ul class=\"bul\">" + "".join(f"<li>{_e(r.get('text'))}</li>" for r in rows) + "</ul>" if rows else ""


def _pc(v) -> str:
    return _num(v, lambda x: "—" if _f(x) is None else f"{_f(x):+.2f}", cls=True)


def _bp(v) -> str:
    return _num(v, lambda x: "—" if _f(x) is None else f"{_f(x):+.0f}", cls=True)


def _page(n: int, total: int, title: str, day: str, body: str, pname: str) -> str:
    """الصفحةُ بهويّة تقارير التطبيق: ترويسةٌ بنفسجيةٌ بالاسم والتاريخ والعنوان، وشريطٌ ذهبيّ، وتذييلٌ برقم الصفحة."""
    return (f'<section class="page"><header class="ph"><div class="brand">المحفظة الذكية<small>قسم الأبحاث · {_e(pname)}</small></div>'
            f'<div class="pt"><div class="d">{_e(day_label(day))}</div><h1>{_e(title)}</h1></div></header><div class="gold"></div>'
            f'<div class="pb">{body}</div><footer class="pf"><span>المحفظة الذكية · قسم الأبحاث · {_e(day_label(day))}</span><b class="pn">{n}</b></footer></section>')


def _fonts() -> str:
    """خطُّ تقارير التطبيق نفسُه (‏saqr_report): الرِقعيُّ العريض بأوزانه الثلاثة."""
    try:
        from app.services.saqr_report import _fonts as f
        return f()
    except Exception:                                             # noqa: BLE001
        return ""


CSS = f"""
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0}}
body{{background:#ebe5d4;color:{INK};font-family:'Thmanyah Serif Display','Segoe UI',Tahoma,sans-serif;direction:rtl;text-align:right;
      font-size:10.5px;line-height:1.6;font-weight:400;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.page{{width:794px;min-height:1123px;margin:0 auto 18px;background:{PAPER};position:relative;box-shadow:0 1px 4px rgba(36,31,26,.16)}}
.ph{{background:linear-gradient(135deg,{NAVY},{NAVY_2});padding:18px 32px 14px;display:flex;justify-content:space-between;align-items:center;gap:12px}}
.brand{{color:#fff;font-size:20px;font-weight:500;line-height:1.25}}
.brand small{{display:block;color:{GOLD_L};font-size:11px;font-weight:300}}
.pt{{text-align:left;color:{GOLD_L}}} .pt .d{{font-size:11px;font-weight:300}} .pt h1{{margin:0;color:#fff;font-size:18px;font-weight:500;line-height:1.3}}
.gold{{height:4px;background:linear-gradient(90deg,{GOLD},{GOLD_L},{GOLD})}}
.pb{{padding:16px 30px 58px}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.cols.w{{grid-template-columns:1.45fr 1fr}}
.band{{background:#efe7cf;color:{NAVY};border-bottom:2px solid {GOLD};font-weight:500;font-size:11px;padding:4px 8px;margin:10px 0 0}}
.blk > .band:first-child{{margin-top:0}}
h2{{color:{NAVY};font-size:13.5px;font-weight:500;margin:12px 0 6px;line-height:1.3;border-inline-start:3px solid {GOLD};padding-inline-start:8px}}
h2:first-child{{margin-top:0}}
h3{{color:{NAVY};font-size:12px;font-weight:500;margin:8px 0 4px}}
.tw{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:9.5px;line-height:1.35}}
th{{font-weight:500;color:{NAVY};border-bottom:1px solid {LINE};padding:3px 4px;text-align:right;vertical-align:bottom;line-height:1.25}}
td{{padding:2.4px 4px;border-bottom:1px solid #e9e2cc;text-align:right}}
tbody tr:nth-child(even) td{{background:{ZEBRA}}} tbody tr:nth-child(odd) td{{background:#fff}}
.n{{direction:ltr;unicode-bidi:isolate;font-variant-numeric:tabular-nums;white-space:nowrap}}
.pos{{color:{GREEN}}} .neg{{color:{RED}}} .mut{{color:{MUTED}}}
p{{margin:0 0 6px}} .para{{text-align:justify;background:#fff;border:1px solid {LINE};border-radius:8px;padding:8px 10px}}
ul.bul{{list-style:none;margin:0;padding:0}}
ul.bul li{{position:relative;padding-inline-start:13px;margin-bottom:6px;text-align:justify}}
ul.bul li::before{{content:'';position:absolute;inset-inline-start:0;top:.55em;width:6px;height:6px;border-radius:1px;background:{GOLD}}}
.kv{{display:grid;grid-template-columns:1fr auto;gap:2px 10px;font-size:10.5px}} .kv span:nth-child(odd){{color:{MUTED}}}
.kv span:nth-child(even){{font-weight:500;color:{NAVY}}}
.box{{border:1px solid {LINE};border-radius:8px;background:#fff;padding:8px 10px;margin-top:10px;overflow:hidden}}
.box .band{{margin:-8px -10px 8px}}
.lv{{display:grid;grid-template-columns:repeat(7,1fr);text-align:center;font-size:10.5px;margin-top:6px;border-radius:8px;overflow:hidden;border:1px solid {LINE}}}
.lv div{{padding:4px 2px}} .lv .h{{background:{NAVY};color:#fff;font-weight:500}} .lv .h.s{{background:{RED}}} .lv .h.r{{background:{GREEN}}}
.lv .v{{background:#fff;font-weight:500;color:{NAVY}}} .lv .v small{{display:block;font-size:9.5px;font-weight:300;color:{MUTED};line-height:1.2}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:12px 0}}
.kpis div{{background:#fff;border:1px solid {LINE};border-radius:8px;padding:6px 8px}} .kpis b{{display:block;font-size:14px;font-weight:300;color:{NAVY}}}
.kpis span{{color:{MUTED};font-size:9.5px}}
.view{{display:inline-block;color:#fff;font-weight:500;padding:1px 9px;font-size:10.5px;border-radius:999px;background:{NAVY}}}
.view.buy{{background:{GREEN}}} .view.sell{{background:{RED}}} .view.hold{{background:{NAVY}}} .view.warn{{background:#a0662f}}
.headline{{font-size:15px;font-weight:500;color:{NAVY};background:{ZEBRA};border:1px solid {GOLD};border-radius:8px;padding:8px 12px;margin:0 0 12px}}
.pf{{position:absolute;bottom:0;left:0;right:0;height:38px;background:linear-gradient(135deg,{NAVY},{NAVY_2});display:flex;
     justify-content:space-between;align-items:center;padding:0 30px;color:{GOLD_L};font-size:9.5px;font-weight:300}}
.pn{{background:{GOLD};color:{NAVY};min-width:28px;height:22px;border-radius:6px;display:flex;align-items:center;justify-content:center;
     font-size:12px;font-weight:500;order:-1}}
.empty{{color:{MUTED};padding:6px 0}}
.chart{{margin-top:6px;border-radius:6px;overflow:hidden}}
@page{{size:A4;margin:0}}
@media print{{body{{background:{PAPER}}} .page{{margin:0;box-shadow:none;page-break-after:always;break-after:page}}}}
@media screen and (max-width:820px){{
  body{{font-size:12px;background:{PAPER}}}
  .page{{width:auto;min-height:0;margin:0 0 12px;box-shadow:none}}
  .ph{{flex-wrap:wrap;padding:14px}} .pt{{text-align:right}} .pb{{padding:14px 14px 52px}} .pf{{padding:0 14px}}
  .cols,.cols.w{{grid-template-columns:1fr}} .kpis{{grid-template-columns:repeat(2,1fr)}}
}}
"""


VIEW_CLS = {"شراء": "buy", "شراء حذر": "buy", "احتفاظ": "hold", "محايد": "hold", "استبدال": "warn", "نظرة حذرة": "warn",
            "جني الأرباح": "sell", "تخفيف": "sell", "اتجاه هابط": "sell"}


def _view(v: str) -> str:
    return f'<span class="view {VIEW_CLS.get(v, "hold")}">{_e(v)}</span>'


def render(r: dict, part: str = "all") -> str:
    """الورقةُ كاملةً (‏all) أو صفحاتُ السوق (‏market) أو صفحةُ المحفظة (‏portfolio) — وثيقةٌ واحدةٌ للشاشة والطباعة وتلغرام."""
    m = r.get("market") or {}
    day, pname = r.get("date"), r.get("portfolio_name") or ""
    t, b, tech = m.get("tasi") or {}, m.get("breadth") or {}, m.get("tech") or {}
    av = r.get("averages") or {}
    fin = m.get("fin") or {}
    pages = []

    # ═══ ١ التقرير اليوميّ ═══
    idx_rows = [["تاسي", _num(t.get("close")), _num(t.get("high")), _num(t.get("low")), _pc(t.get("pct")), _pc(tech.get("ytd"))]]
    if (m.get("mt30") or {}).get("close"):
        mt = m["mt30"]
        idx_rows.append(["إم تي 30", _num(mt.get("close")), _num(mt.get("high")), _num(mt.get("low")), _pc(mt.get("pct")), _num(None)])
    fin_rows = [[k, _num(v, f)] for k, v, f in (("مكرّر الربحية (مرّة)", fin.get("pe"), n2), ("السعر إلى القيمة الدفترية (مرّة)", fin.get("pb"), n2),
                                              ("عائد التوزيع (%)", fin.get("dy"), n2), ("العائد على حقوق المساهمين (%)", fin.get("roe"), n2))
                if _f(v) is not None]
    sec_rows = [[_e(s["name"]), _pc(s.get("pct")), _num(s["value"] / 1e6 if s.get("value") is not None else None, n0), _num(s.get("weight"), n2), _num(s.get("pe"), n2)]
                for s in m.get("sectors") or []]
    avg_rows = [[_e(a["label"]), _num(a.get("a5")), _num(a.get("a10")), _num(a.get("a20"))]
                for k, a in av.items() if isinstance(a, dict) and "label" in a and any(_f(a.get(x)) is not None for x in ("a5", "a10", "a20"))]
    wk_rows = [[lbl, _num(w["value"]), _num(w["volume"], n0), _num(w["trades"], n0)]
               for lbl, w in (("الأسبوع الحالي", av.get("week")), ("الأسبوع السابق", av.get("prev_week"))) if w]
    heavy = [[_e(h["name"]), _num(h["price"]), _pc(h.get("pct"))] for h in m.get("heavy") or []]
    gl = [[_e(g["name"]), _num(g["price"]), _pc(g.get("pct"))] for g in m.get("gainers") or []]
    ls = [[_e(g["name"]), _num(g["price"]), _pc(g.get("pct"))] for g in m.get("losers") or []]
    left = (_band("مؤشر السوق السعودي") + _tbl(["المؤشر", "الإغلاق", "الأعلى", "الأدنى", "التغيّر %", "منذ بداية العام %"], idx_rows)
            + (f'<div class="cols" style="grid-template-columns:1fr 1.25fr;gap:10px;margin-top:8px"><div>{_band("المؤشرات المالية لتاسي")}'
               f'{_tbl(["المؤشّر", "القيمة"], fin_rows)}</div><div><h3>حركة المؤشر خلال الجلسة</h3>{svg_intraday(m.get("intraday") or [])}</div></div>'
               if fin_rows else f'<h3>حركة المؤشر خلال الجلسة</h3>{svg_intraday(m.get("intraday") or [])}')
            + (_band("أداء القطاعات") + _tbl(["القطاع", "التغيّر %", "القيمة (مليون)", "الوزن %", "المكرّر"], sec_rows) if sec_rows else "")
            + (_band("معدّل القيم") + _tbl(["", "معدّل 5 أيام", "معدّل 10 أيام", "معدّل 20 يوماً"], avg_rows) if avg_rows else "")
            + (_band("الإحصاءات المجمّعة للسوق") + _tbl(["", "القيمة (مليار ريال)", "الكمية (مليون سهم)", "الصفقات (ألف)"], wk_rows) if wk_rows else ""))
    right = ((f'<p class="headline">{_e(r.get("headline"))}</p>' if r.get("headline") else "")
             + "<h2>الأخبار المحلية</h2>" + (_bul((r.get("local") or [])[:6]) or '<p class="empty">لا أخبارَ محليةً جديدة.</p>')
             + f'<h2>تحليل السوق</h2><p class="para">{_e(r.get("analysis") or "")}</p>'
             + (_band("الأكثر ارتفاعاً") + _tbl(["الشركة", "السعر", "التغيّر %"], gl) if gl else "")
             + (_band("الأكثر انخفاضاً") + _tbl(["الشركة", "السعر", "التغيّر %"], ls) if ls else "")
             + (_band("الشركات الأكبر وزناً بالمؤشر") + _tbl(["الشركة", "السعر", "التغيّر %"], heavy) if heavy else ""))
    pages.append(("التقرير اليومي", f'<div class="cols"><div class="blk">{right}</div><div class="blk">{left}</div></div>', "market"))

    # ═══ ٢ الأسواق ═══
    def qrows(rows, unit=n2, bp=False):
        f = _bp if bp else _pc
        return [[_e(q["name"]), _num(q.get("close"), unit), f(q.get("d1")), f(q.get("mtd")), f(q.get("ytd"))] for q in rows]
    reg = r.get("regional") or {}
    reg_rows = [["السعودية (تاسي)", _num(t.get("close")), _pc(t.get("pct")), _pc(tech.get("mtd")), _pc(tech.get("ytd"))]]
    reg_rows += [[_e(x["market"]), _num(x.get("close")), _pc(x.get("d1")), _pc(x.get("mtd")), _pc(x.get("ytd"))] for x in reg.get("rows") or []
                 if "سعود" not in str(x.get("market"))]
    rate_rows = qrows(m.get("rates") or [], bp=True)
    rate_rows += [[_e(x["name"]), _num(x.get("value")), _bp(x.get("d1_bp")), _bp(x.get("mtd_bp")), _bp(x.get("ytd_bp"))] for x in r.get("saibor") or []]
    act = [[_e(short_day(a["date"])), _e(a["company"]), _e(a["type"])] for a in m.get("actions") or []]
    hd = ["الإغلاق", "يوميّ %", "شهريّ %", "منذ بداية العام %"]
    l2 = (_band("الأسواق الإقليمية" + (f" — كما في {short_day(reg['date'])}" if reg.get("rows") and reg.get("date") else ""))
          + _tbl(["السوق"] + hd, reg_rows)
          + _band("الأسواق العالمية") + _tbl(["المؤشّر"] + hd, qrows(m.get("global") or []))
          + (_band("أسعار الفائدة") + _tbl(["الأداة", "العائد %", "يوميّ (نقطة)", "شهريّ (نقطة)", "منذ بداية العام (نقطة)"], rate_rows) if rate_rows else ""))
    r2 = (_band("أسواق السلع (دولار أمريكي)") + _tbl(["السلعة", "السعر", "يوميّ %", "شهريّ %", "منذ بداية العام %"], qrows(m.get("commodities") or []))
          + _band("العملات والعملات المشفّرة") + _tbl(["العملة / الدولار", "السعر", "يوميّ %", "شهريّ %", "منذ بداية العام %"], qrows(m.get("fx") or [], unit=lambda v: "—" if _f(v) is None else (f"{_f(v):,.4f}" if _f(v) < 10 else f"{_f(v):,.2f}")))
          + (_band("إجراءات الشركات السعودية") + _tbl(["التاريخ", "الشركة", "نوع الحدث"], act) if act else "")
          + "<h2>الأخبار العالمية</h2>" + (_bul(r.get("global") or []) or '<p class="empty">لا أخبارَ عالميةً جديدة.</p>'))
    pages.append(("الأسواق الإقليمية والعالمية", f'<div class="cols"><div class="blk">{r2}</div><div class="blk">{l2}</div></div>', "market"))

    # ═══ ٣ النظرة الفنية اليومية ═══
    if tech:
        c1, c2, adv = tech_commentary(m)
        p = levels_of(m)
        lv = ('<div class="lv">' + "".join(f'<div class="h {c}">{h}</div>' for h, c in (("دعم 3", "s"), ("دعم 2", "s"), ("دعم 1", "s"), ("المحور", ""),
                                                                                      ("مقاومة 1", "r"), ("مقاومة 2", "r"), ("مقاومة 3", "r")))
              + "".join(f'<div class="v">{_num(p.get(k), n0)}<small>{_e(p.get(k + "_name") or "")}</small></div>'
                        for k in ("s3", "s2", "s1", "p", "r1", "r2", "r3")) + "</div>")
        kp = [(n2(fin.get("pe")) + " مرّة", "مكرّر الربحية"), (n2(fin.get("roe")) + "%", "العائد على الحقوق"), (n2(fin.get("pb")) + " مرّة", "مكرّر القيمة الدفترية"),
              (n2(fin.get("dy")) + "%", "عائد التوزيع"), ((f"{fin['cap'] / 1e9:,.0f} مليار") if fin.get("cap") else "—", "القيمة السوقية")]
        kpis = ('<div class="kpis">' + "".join(f'<div><b>{_e(v)}</b><span>{_e(l)}</span></div>' for v, l in kp if not v.startswith("—")) + "</div>") if fin else ""
        rgt = (f'<h2>التعليق على مؤشر السوق الرئيسي</h2><ul class="bul"><li>{_e(c1)}</li></ul>'
               f'<h2>التوقعات الفنية</h2><ul class="bul"><li>{_e(c2)} {_e(adv)}</li></ul>'
               f'<h2>المقاومة والدعم للمؤشر</h2>{lv}{kpis}'
               f'<h2>الرسم البياني اليومي — مؤشر السوق الرئيسي</h2><div class="chart">'
               f'{svg_research(m.get("daily") or [], title="TASI · Tadawul All Shares Index", ri=ri_of(m))}</div>')
        notes = [("المؤشر", "تاسي"), ("آخر إغلاق", n2(tech.get("close"))), ("نظرة قريبة المدى", tech.get("view")),
                 ("الأعلى – الأدنى خلال 52 أسبوعاً", f"{n0(tech.get('hi52'))} – {n0(tech.get('lo52'))}")]
        mkt = [("قيمة التداول (مليون ريال)", n2((b.get("value") or 0) / 1e6) if b.get("value") else "—"),
               ("حجم التداول (مليون سهم)", n2((b.get("volume") or 0) / 1e6) if b.get("volume") else "—"),
               ("عدد الصفقات", n0(b.get("trades"))), ("الأسهم المرتفعة : المنخفضة", f"{n0(b.get('up'))} : {n0(b.get('down'))}")]
        if fin.get("cap"):
            mkt.insert(0, ("القيمة السوقية (مليار ريال)", n2(fin["cap"] / 1e9)))
        stats = [("التغيّر اليومي", p2(t.get("pct"))), ("منذ بداية الشهر", p2(tech.get("mtd"))), ("منذ بداية الربع", p2(tech.get("qtd"))),
                 ("منذ بداية العام", p2(tech.get("ytd")))]
        if av.get("avg63_value"):
            stats.append(("متوسّط قيمة التداول اليومي (مليون ريال)", n2(av["avg63_value"] / 1e6)))
        if av.get("avg63_volume"):
            stats.append(("متوسّط كمية التداول اليومي (مليون سهم)", n2(av["avg63_volume"] / 1e6)))
        kv = lambda rows: '<div class="kv">' + "".join(f'<span>{_e(k)}</span><span{_iso(v)}>{_e(v)}</span>' for k, v in rows) + "</div>"   # noqa: E731
        lft = (f'<div class="box">{_band("ملاحظات فنية")}{kv(notes)}</div><div class="box">{_band("بيانات السوق")}{kv(mkt)}</div>'
               f'<div class="box">{_band("الإحصاءات الرئيسية")}{kv(stats)}</div>'
               f'<div class="box">{_band("نظرتنا")}{svg_gauge(tech.get("view") or "محايد")}</div>'
               f'<div class="box">{_band("عمق السوق")}{svg_breadth(b.get("up"), b.get("unch"), b.get("down"))}</div>')
        pages.append(("النظرة الفنية اليومية", f'<div class="cols w"><div class="blk">{rgt}</div><div class="blk">{lft}</div></div>', "market"))

    # ═══ ٤ محفظتنا ═══
    ps = r.get("positions") or []
    pos_rows = [[f'<b>{_e(x.get("name"))}</b> <span class="mut n">{_e(x["symbol"])}</span>', _num(x.get("price")), _pc(x.get("pct")),
                 _num(x.get("weight"), n2), _num(x.get("fv")), _pc(x.get("upside")), _e(x.get("trend") or "—"), _view(x["view"])] for x in ps]
    notes = {n["symbol"]: n["text"] for n in r.get("portfolio") or []}
    note_li = [{"text": f"{x['name']}: {notes[x['symbol']]}"} for x in ps if x["symbol"] in notes]
    pk = r.get("picks") or []
    pk_rows = [[_e(k["symbol"]), f'<b>{_e(k["name"])}</b>' + (' <span class="mut">(في المحفظة)</span>' if k.get("held") else ""), _num(k["close"]),
                f'<span class="n">{n2(k["buy"][0])} – {n2(k["buy"][1])}</span>', f'<span class="n">{n2(k["target"][0])} – {n2(k["target"][1])}</span>',
                _num(k["stop"])] for k in pk]
    charts = "".join(f'<div class="box">{_band(k["name"] + " — ملاحظات فنية")}<p>{_e(pick_note(k))}</p>'
                     f'{svg_research(k.get("bars") or [], w=470, h=300, title=k["symbol"], extra={"buy_lo": k["buy"][0], "buy_hi": k["buy"][1], "stop": k["stop"], "target": k["target"][1]})}</div>'
                     for k in pk[:2])
    body4 = ((f'<p class="headline">{_e(r.get("portfolio_headline") or r.get("headline"))}</p>' if (r.get("portfolio_headline") or r.get("headline")) else "")
             + _band("نظرتنا لمراكز المحفظة")
             + (_tbl(["الشركة", "الإغلاق", "التغيّر %", "الوزن %", "القيمة العادلة", "الصعود %", "الاتجاه", "نظرتنا"], pos_rows) or '<p class="empty">لا مراكز.</p>')
             + (("<h2>ما يعني مراكزنا اليوم</h2>" + _bul(note_li)) if note_li else "")
             + _band("أفضل اختياراتنا لليوم — السوق السعودي")
             + (_tbl(["الرمز", "الشركة", "الإغلاق", "نطاق الشراء", "نطاق البيع", "وقف الخسارة (بالتذبذب)"], pk_rows)
                if pk_rows else f'<p class="empty">لا اختياراتِ اليوم: {_e(r.get("no_pick_reason") or "لم تجتمع الشروط في أيّ سهم.")}</p>')
             + (f'<div class="cols" style="margin-top:4px">{charts}</div>' if charts else "")
             + (("<h2>للمتابعة</h2>" + _bul(r.get("watch") or [])) if r.get("watch") else ""))
    if r.get("backfill"):
        body4 = ((f'<p class="headline">{_e(r.get("headline"))}</p>' if r.get("headline") else "")
                 + '<p class="empty">صفحةُ المحفظة تُكتب يومَ الجلسة نفسِها بمراكزها وقتئذٍ — ولا تُعاد كتابتُها لجلسةٍ مضت بمراكز اليوم.</p>'
                 + (("<h2>للمتابعة</h2>" + _bul(r.get("watch") or [])) if r.get("watch") else ""))
    pages.append(("محفظتنا واختياراتنا", body4, "portfolio"))

    keep = [pg for pg in pages if part == "all" or pg[2] == part]
    total = len(keep)
    sections = "".join(_page(i + 1, total, title, day, body, pname) for i, (title, body, _k) in enumerate(keep))
    return (f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>التقرير اليومي — {_e(day_label(day))}</title><style>{_fonts()}{CSS}</style></head><body>{sections}</body></html>')


async def pdf(r: dict) -> bytes | None:
    from app.services.saqr_report import to_pdf
    return await to_pdf(render(r, "all"))
