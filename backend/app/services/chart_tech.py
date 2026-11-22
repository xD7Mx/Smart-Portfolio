"""محرّكُ الرسم على الخادم — حسابُ D7M نفسُه كما يرسمه التطبيق، ليقرأ صقرٌ الرسمَ بنفسه (‏D784 · بأمر المالك 2026-11-22).

قال المالك: «بما أنّ تحليلَ الرسم صار موجوداً وقويّاً… خلِّ صقر يفهم التحليلَ هذا ويبدأ يختار بناءً عليه — الأمريكيُّ والسعوديّ… يحلّل الرسمَ
لكامل السوق… ويعرف جودةَ الفرصة لمدّة كم: بعد شهر، بعد شهرين، حتى الربع القادم».

فهذه ترجمةٌ حرفيةٌ لحساب الواجهة (‏analysis/d7m.ts · analysis/pulse.ts · lib/indicators.ts) — لا تعريفان للمسار ولا للمستويات في التطبيق:
  · الزجزاج والفيبوناتشي التلقائيّ (آخرُ ضلع) ومستوياتُه الأربعَ عشرة، و«المختصر» ستّتُه: كلُّ خطّين منطقة (‏D784: «خطّان للدعم وخطّان للمقاومة
    وخطّان في الوسط — كلُّ خطّين منطقة») ⇐ 0 و−0.1 · 0.5 و0.618 · 1 و1.1.
  · قوّةُ الاتجاه (ستةُ شواهد + ‏ADX) وقوّةُ السيولة (‏CMF · نصيبُ الحجم الصاعد · ميلُ ‏OBV + الحجمُ النسبيّ).
  · ‏Stoch RSI (3 · 3 · 14 · 14) و‏RSI بوايلدر.
ثمّ ‏read() تقرأ الرسمَ قراءةَ المالك: أين السعرُ من المناطق الثلاث، وما تقوله السيولةُ وStoch RSI عندها، فتسمّي الفرصةَ (ارتدادٌ من دعم ·
اختراقُ مقاومة · استمرارٌ بعد تصحيح — ومقابلاتُها للبيع) وجودتَها من مئة، ومدّتَها من اتّفاق الإطارين اليوميّ والأسبوعيّ، والدخولَ والهدفَ
والوقفَ من المستويات نفسِها — أرقامٌ من الشموع وحدها، لا شيءَ مختلَق.
"""
from __future__ import annotations

from datetime import date as _date

FIB_LEVELS = (0, 0.5, 0.618, -0.5, 1.5, 1, -1, -0.618, 1.618, -0.1, 1.1, 2, 2.1, -1.1)
SIX = (0, -0.1, 0.5, 0.618, 1, 1.1)
ZONES = ((0, -0.1), (0.5, 0.618), (1, 1.1))


def _clip(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ── المتوسّطات (‏d7m.ts: ema · rma · sma — بذرتُها متوسّطُ أوّل ‏len كـPine) ─────────────────────────────
def ema(src: list[float], n: int) -> list[float | None]:
    k, prev, out = 2 / (n + 1), None, []
    for i, v in enumerate(src):
        if i < n - 1:
            out.append(None)
            continue
        prev = sum(src[:n]) / n if prev is None else v * k + prev * (1 - k)
        out.append(prev)
    return out


def rma(src: list[float], n: int) -> list[float | None]:
    prev, out = None, []
    for i, v in enumerate(src):
        if i < n - 1:
            out.append(None)
            continue
        prev = sum(src[:n]) / n if prev is None else (prev * (n - 1) + v) / n
        out.append(prev)
    return out


def sma(src: list[float], n: int) -> list[float | None]:
    return [None if i < n - 1 else sum(src[i - n + 1:i + 1]) / n for i in range(len(src))]


def atr(bars: list[dict], n: int = 10) -> list[float | None]:
    tr = [bars[0]["high"] - bars[0]["low"]] if bars else []
    for i in range(1, len(bars)):
        b, pc = bars[i], bars[i - 1]["close"]
        tr.append(max(b["high"] - b["low"], abs(b["high"] - pc), abs(b["low"] - pc)))
    out, r = [], None
    for i in range(len(bars)):
        if i < n - 1:
            out.append(None)
            continue
        r = sum(tr[:n]) / n if r is None else (r * (n - 1) + tr[i]) / n
        out.append(r)
    return out


def dmi(bars: list[dict], n: int = 14, smooth: int = 14) -> tuple[list, list, list]:
    pdm, ndm, tr = [], [], []
    for i, b in enumerate(bars):
        if i == 0:
            pdm.append(0.0); ndm.append(0.0); tr.append(b["high"] - b["low"])   # noqa: E702
            continue
        up, dn = b["high"] - bars[i - 1]["high"], bars[i - 1]["low"] - b["low"]
        pdm.append(up if up > dn and up > 0 else 0.0)
        ndm.append(dn if dn > up and dn > 0 else 0.0)
        pc = bars[i - 1]["close"]
        tr.append(max(b["high"] - b["low"], abs(b["high"] - pc), abs(b["low"] - pc)))
    trr, p, m = rma(tr, n), rma(pdm, n), rma(ndm, n)
    plus = [None if v is None or not trr[i] else 100 * v / trr[i] for i, v in enumerate(p)]
    minus = [None if v is None or not trr[i] else 100 * v / trr[i] for i, v in enumerate(m)]
    dx = [0.0 if v is None or minus[i] is None else (0.0 if v + minus[i] == 0 else 100 * abs(v - minus[i]) / (v + minus[i])) for i, v in enumerate(plus)]
    return plus, minus, rma(dx, smooth)


# ── الزجزاج والفيبوناتشي التلقائيّ (‏d7m.ts: zigzag · autoFib — مكتبةُ TradingView ZigZag/7) ─────────────────
def zigzag(bars: list[dict], mult: float, depth: int) -> list[dict]:
    n, L = len(bars), max(2, int(depth // 2))
    if n < 2 * L + 1:
        return []
    a = atr(bars, 10)
    piv: list[dict] = []
    for t in range(2 * L, n):
        if a[t] is None or not bars[t]["close"]:
            continue
        dev = (a[t] / bars[t]["close"]) * 100 * mult
        for is_high in (True, False):
            key = "high" if is_high else "low"
            p = bars[t - L][key]
            ok = all(not (bars[t - k][key] > p if is_high else bars[t - k][key] < p) for k in range(0, L))
            ok = ok and all(not (bars[t - k][key] >= p if is_high else bars[t - k][key] <= p) for k in range(L + 1, 2 * L + 1))
            if not ok:
                continue
            pt = {"index": t - L, "price": p, "high": is_high}
            if not piv:
                piv.append(pt)
                continue
            last = piv[-1]
            if last["high"] == is_high:
                if (p > last["price"]) if is_high else (p < last["price"]):
                    piv[-1] = pt
                continue
            d = 100 * (p - last["price"]) / abs(last["price"])
            if (not last["high"] and d >= dev) or (last["high"] and d <= -dev):
                piv.append(pt)
    return piv


def auto_fib(bars: list[dict], mult: float = 3, depth: int = 7, reverse: bool = False) -> dict | None:
    """{lines: {مستوى: سعر}, start, end} — آخرُ ضلعٍ للزجزاج: المستوى 0 عند آخر محور، و1 عند الذي قبله (بلا عكس)."""
    p = zigzag(bars, mult, depth)
    if len(p) < 2:
        return None
    start, end = p[-2], p[-1]
    sp, ep = (start["price"], end["price"]) if reverse else (end["price"], start["price"])
    height = (-1 if sp > ep else 1) * abs(sp - ep)
    return {"lines": {lv: sp + height * lv for lv in FIB_LEVELS}, "start": start, "end": end}


# ── لوحتا القوّة (‏pulse.ts) وراصدُ الحيتان (‏d7m.ts: liquidity) ───────────────────────────────────────────
def level_word(s: int, fem: bool = False) -> str:
    if s >= 75:
        return "قويّةٌ جدّاً" if fem else "قويٌّ جدّاً"
    if s >= 55:
        return "قويّة" if fem else "قويّ"
    if s >= 35:
        return "متوسّطة" if fem else "متوسّط"
    return "ضعيفة" if fem else "ضعيف"


def trend_force(bars: list[dict]) -> dict | None:
    n = len(bars)
    if n < 30:
        return None
    i = n - 1
    c = [b["close"] for b in bars]
    e20, e50, e200 = ema(c, 20), ema(c, 50), ema(c, 200)
    plus, minus, adx = dmi(bars, 14, 14)
    why: list[tuple[int, str]] = []

    def vote(up: bool, u: str, d: str):
        why.append((1, u) if up else (-1, d))
    E20, E50, E200 = e20[i], e50[i], e200[i]
    if E50 is not None and c[i] != E50:
        vote(c[i] > E50, "السعرُ فوق متوسّط 50", "السعرُ تحت متوسّط 50")
    if E20 is not None and E50 is not None and E20 != E50:
        vote(E20 > E50, "متوسّطُ 20 فوق متوسّط 50", "متوسّطُ 20 تحت متوسّط 50")
    if E50 is not None and E200 is not None and E50 != E200:
        vote(E50 > E200, "متوسّطُ 50 فوق متوسّط 200", "متوسّطُ 50 تحت متوسّط 200")
    P, M = plus[i], minus[i]
    if P is not None and M is not None and P != M:
        vote(P > M, "المشترون أقوى (+DI)", "البائعون أقوى (−DI)")
    E50p = e50[i - 5] if i >= 5 else None
    if E50 is not None and E50p is not None and E50 != E50p:
        vote(E50 > E50p, "متوسّطُ 50 يصعد", "متوسّطُ 50 يهبط")
    if n >= 40:
        h1 = max(b["high"] for b in bars[n - 20:]); h0 = max(b["high"] for b in bars[n - 40:n - 20])   # noqa: E702
        l1 = min(b["low"] for b in bars[n - 20:]); l0 = min(b["low"] for b in bars[n - 40:n - 20])     # noqa: E702
        if h1 > h0 and l1 > l0:
            why.append((1, "قممٌ وقيعانٌ أعلى"))
        elif h1 < h0 and l1 < l0:
            why.append((-1, "قممٌ وقيعانٌ أدنى"))
    score = sum(v for v, _ in why)
    A = adx[i]
    side = "up" if score >= 2 else "down" if score <= -2 else "flat"
    adx_n = 0.0 if A is None else _clip((A - 15) / 25, 0, 1)
    strength = round(100 * (0.55 * adx_n + 0.45 * abs(score) / 6))
    if side == "flat":
        strength = min(strength, 34)
    return {"side": side, "word": {"up": "صاعد", "down": "هابط"}.get(side, "عرضيّ"), "level": level_word(strength), "strength": strength,
            "stat": None if A is None else f"ADX {round(A)}", "adx": A, "why": why}


def liquidity_tag(bars: list[dict], vol_len: int = 20) -> str | None:
    vols = [b.get("volume") or 0 for b in bars]
    i = len(bars) - 1
    if not any(v > 0 for v in vols) or i < vol_len:
        return None
    avg = sma(vols, vol_len)[i] or 1
    rvol = vols[i] / avg * 100
    avg_sp = sma([b["high"] - b["low"] for b in bars], vol_len)[i] or 0
    b = bars[i]
    sp = b["high"] - b["low"]
    pos = 0.5 if sp == 0 else (b["close"] - b["low"]) / sp
    if rvol > 200 and pos > 0.7 and b["close"] > b["open"]:
        return "اندفاع شرائي"
    if rvol > 160 and sp < avg_sp and pos > 0.5:
        return "تجميع خفي"
    if rvol > 200 and pos < 0.3 and b["close"] < b["open"]:
        return "انهيار بيعي"
    if rvol > 160 and sp < avg_sp and pos < 0.5:
        return "تصريف بيعي"
    if rvol < 60:
        return "جفاف سيولة"
    return None


def liquidity_force(bars: list[dict]) -> dict | None:
    n = len(bars)
    if n < 30:
        return None
    v = [b.get("volume") or 0 for b in bars]
    na = {"side": "na", "word": "غير متوفّر", "level": "", "strength": 0, "stat": "لا أحجامَ من المصدر", "why": []}
    tl = v[-300:]
    if not tl or sum(1 for x in tl if x > 0) < len(tl) * 0.8:
        return na
    mfv = vs = up_v = 0.0
    for k in range(n - 20, n):
        b, r = bars[k], bars[k]["high"] - bars[k]["low"]
        m = ((b["close"] - b["low"]) - (b["high"] - b["close"])) / r if r > 0 else 0.0
        mfv += m * v[k]
        vs += v[k]
        prev = bars[k - 1]["close"]
        up_v += v[k] if b["close"] > prev else v[k] / 2 if b["close"] == prev else 0
    if vs <= 0:
        return na
    cmf, up_r = mfv / vs, up_v / vs
    obv = v10 = 0.0
    for k in range(n - 10, n):
        p = bars[k - 1]["close"]
        obv += v[k] if bars[k]["close"] > p else -v[k] if bars[k]["close"] < p else 0
        v10 += v[k]
    obv_s = obv / v10 if v10 > 0 else 0.0
    flow = (_clip(cmf / 0.2) + _clip((up_r - 0.5) / 0.2) + _clip(obv_s / 0.5)) / 3
    recent, base = sum(v[n - 5:]) / 5, sum(v[n - 25:n - 5]) / 20
    rv = recent / base if base > 0 else None
    side = "up" if flow >= 0.15 else "down" if flow <= -0.15 else "flat"
    rv_n = 0.0 if rv is None else _clip((rv - 0.8) / 1.2, 0, 1)
    strength = round(100 * _clip(0.65 * abs(flow) + 0.35 * rv_n, 0, 1))
    if side == "flat":
        strength = min(strength, 34)
    word = {"up": "داخلةٌ للصعود", "down": "خارجةٌ للهبوط"}.get(side, "متوازنة")
    why = [(1 if cmf >= 0 else -1, f"تدفّقُ المال {'موجب' if cmf >= 0 else 'سالب'} (CMF {cmf:.2f})"),
           (1 if up_r >= 0.5 else -1, f"حجمُ الشموع الصاعدة {round(up_r * 100)}% من حجم العشرين"),
           (1 if obv_s >= 0 else -1, "OBV يصعد في عشر شموع" if obv_s >= 0 else "OBV يهبط في عشر شموع")]
    return {"side": side, "word": word, "level": level_word(strength, True), "strength": strength, "stat": None if rv is None else f"الحجم {rv:.1f}×",
            "rv": rv, "why": why, "tag": liquidity_tag(bars)}


# ── ‏RSI وStoch RSI (‏lib/indicators.ts) ────────────────────────────────────────────────────────────────
def rsi(data: list[float], p: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(data)
    if len(data) < p + 1:
        return out
    g = l = 0.0
    for i in range(1, p + 1):
        d = data[i] - data[i - 1]
        g += max(d, 0.0); l += max(-d, 0.0)   # noqa: E702
    g /= p; l /= p   # noqa: E702
    out[p] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    for i in range(p + 1, len(data)):
        d = data[i] - data[i - 1]
        g = (g * (p - 1) + max(d, 0.0)) / p
        l = (l * (p - 1) + max(-d, 0.0)) / p
        out[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    return out


def _sma_n(a: list[float | None], p: int) -> list[float | None]:
    out: list[float | None] = [None] * len(a)
    for i in range(p - 1, len(a)):
        w = a[i - p + 1:i + 1]
        if all(x is not None for x in w):
            out[i] = sum(w) / p
    return out


def stoch_rsi(closes: list[float], k: int = 3, d: int = 3, rsi_len: int = 14, stoch_len: int = 14) -> tuple[list, list]:
    r, n = rsi(closes, rsi_len), len(closes)
    raw: list[float | None] = [None] * n
    for i in range(stoch_len - 1, n):
        w = r[i - stoch_len + 1:i + 1]
        if any(x is None for x in w):
            continue
        hh, ll = max(w), min(w)
        if hh > ll:
            raw[i] = 100 * (r[i] - ll) / (hh - ll)
    kk = _sma_n(raw, k)
    return kk, _sma_n(kk, d)


# ── الأسبوعيّ من اليوميّ (أسبوعُ السوق: الأحد–الخميس للسعوديّ، والاثنين–الجمعة للأمريكيّ) ────────────────────
def weekly(bars: list[dict], saudi: bool = False) -> list[dict]:
    out: list[dict] = []
    for b in bars:
        try:
            d = _date.fromisoformat(str(b.get("date") or "")[:10])
        except ValueError:
            continue
        start = d.toordinal() - ((d.weekday() + 1) % 7 if saudi else d.weekday())
        if out and out[-1]["_w"] == start:
            w = out[-1]
            w["high"], w["low"], w["close"] = max(w["high"], b["high"]), min(w["low"], b["low"]), b["close"]
            w["volume"] = (w.get("volume") or 0) + (b.get("volume") or 0)
            w["date"] = str(b.get("date"))[:10]
        else:
            out.append({"_w": start, "date": str(b.get("date"))[:10], "open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"],
                        "volume": b.get("volume") or 0})
    return out


def clean(bars) -> list[dict]:
    """شموعٌ صالحةٌ وحدها (أسعارٌ موجبةٌ متّسقة) بالترتيب — ما سواها يُسقط لا يُرمَّم."""
    out = []
    for b in bars or []:
        b = b if isinstance(b, dict) else getattr(b, "__dict__", {})
        try:
            o, h, lo, c = (float(b[k]) for k in ("open", "high", "low", "close"))
        except (KeyError, TypeError, ValueError):
            continue
        if min(o, h, lo, c) <= 0 or h < lo:
            continue
        out.append({"date": str(b.get("date") or b.get("time") or ""), "open": o, "high": max(h, o, c), "low": min(lo, o, c), "close": c,
                    "volume": float(b.get("volume") or 0)})
    return out


# ── القراءة: أين السعرُ من المناطق الثلاث، وما الفرصة، وجودتُها ومدّتُها ودخولُها وهدفُها ووقفُها ─────────────────
def zones_of(fib: dict) -> list[dict]:
    """المناطقُ الثلاث (كلُّ خطّين منطقة) مرتّبةً من الأدنى: الدعم · الوسط · المقاومة — بأسعارها ومستوياتها."""
    L = fib["lines"]
    zs = sorted(({"lo": min(L[a], L[b]), "hi": max(L[a], L[b]), "levels": (a, b)} for a, b in ZONES), key=lambda z: z["lo"])
    for z, name in zip(zs, ("الدعم", "الوسط", "المقاومة")):
        z["name"] = name
    return zs


def _where(p: float, zs: list[dict]) -> str:
    sup, mid, res = zs
    if p < sup["lo"]:
        return "تحت الدعم"
    if p <= sup["hi"]:
        return "في منطقة الدعم"
    if p < mid["lo"]:
        return "بين الدعم والوسط"
    if p <= mid["hi"]:
        return "في منطقة الوسط"
    if p < res["lo"]:
        return "بين الوسط والمقاومة"
    if p <= res["hi"]:
        return "في منطقة المقاومة"
    return "فوق المقاومة"


def frame(bars: list[dict]) -> dict | None:
    """قراءةُ إطارٍ واحد: الاتجاهُ والسيولةُ والمناطقُ وStoch RSI وRSI — أو None إن قلّت الشموع."""
    if len(bars) < 30:
        return None
    c = [b["close"] for b in bars]
    k, d = stoch_rsi(c)
    r = rsi(c)
    fib = auto_fib(bars, 3, 7)
    i = len(bars) - 1
    a = atr(bars, 14)[i]
    return {"trend": trend_force(bars), "liq": liquidity_force(bars), "fib": fib, "zones": zones_of(fib) if fib else None,
            "k": k[i], "d": d[i], "k1": k[i - 1] if i else None, "d1": d[i - 1] if i else None, "rsi": r[i], "close": c[i], "atr": a,
            "e20": ema(c, 20)[i], "e50": ema(c, 50)[i]}


HORIZON = {3: "حتى الربع القادم", 2: "شهران", 1: "شهر"}


def read(daily: list[dict], saudi: bool = False, longs_only: bool = False) -> dict | None:
    """قراءةُ الرسم لفرصة: ‏{setup, side, quality, horizon, entry, target, stop, rr, where, reasons, trend, liq, k, rsi, zones} — أو None.

    الفرصُ كما يقرؤها المالك:
      · ارتدادٌ من دعم: السعرُ في منطقة الدعم أو الوسط (أو فوقها بقليل)، وStoch RSI في تشبّعٍ بيعيٍّ أو يتقاطع صاعداً منه، والسيولةُ ليست خارجةً بقوّة.
      · اختراقُ مقاومة: إغلاقٌ فوق منطقة المقاومة بسيولةٍ داخلةٍ واتجاهٍ صاعد.
      · استمرارٌ بعد تصحيح: اتجاهٌ صاعدٌ قويّ والسعرُ عائدٌ إلى منطقة الوسط أو متوسّط 20/50 وStoch RSI منخفضٌ يتّجه صعوداً.
      ومقابلاتُها للبيع (رفضٌ من المقاومة · كسرُ دعم · استمرارٌ هابط) لعقود البيع الأمريكية — ولا بيعَ في السوق السعوديّ.
    والجودةُ من مئة: الاتجاهُ 30 · السيولةُ 25 · الموضعُ من المنطقة 20 · توقيتُ Stoch RSI 15 · الأسبوعيّ 10؛ والمدّةُ من اتّفاق الإطارين."""
    daily = clean(daily)
    D = frame(daily)
    if not D or not D["trend"] or not D["zones"]:
        return None
    W = frame(weekly(daily, saudi)) if len(daily) >= 160 else None
    p, zs, T, Lq = D["close"], D["zones"], D["trend"], D["liq"] or {"side": "na", "strength": 0}
    sup, mid, res = zs
    k, kd, k1, d1 = D["k"], D["d"], D["k1"], D["d1"]
    atr_ = D["atr"] or (p * 0.02)
    up_cross = k is not None and kd is not None and k1 is not None and d1 is not None and k > kd and k1 <= d1
    dn_cross = k is not None and kd is not None and k1 is not None and d1 is not None and k < kd and k1 >= d1
    where = _where(p, zs)
    near = lambda z: z["lo"] - 0.25 * atr_ <= p <= z["hi"] + 1.0 * atr_   # noqa: E731
    cands = []
    # الشراء
    if near(sup) or (T["side"] == "up" and near(mid)):
        z = sup if near(sup) else mid
        timing = 1.0 if (k is not None and k < 20) or (up_cross and (k1 or 0) < 35) else 0.6 if k is not None and k < 40 else 0.0
        if timing and not (Lq["side"] == "down" and Lq["strength"] >= 55):
            nxt = mid if z is sup else res
            cands.append(("ارتدادٌ من الدعم" if z is sup else "ارتدادٌ من منطقة الوسط", "long", z, timing, nxt["lo"], z["lo"] - 0.5 * atr_))
    brk = p > res["hi"] and max(b["close"] for b in daily[-3:]) > res["hi"] and min(b["close"] for b in daily[-6:-3] or daily[-3:]) <= res["hi"] * 1.01
    if brk and T["side"] == "up" and Lq["side"] == "up":
        ext = [v for lv, v in D["fib"]["lines"].items() if v > p * 1.01]
        cands.append(("اختراقُ المقاومة", "long", res, 0.8, min(ext) if ext else p + 2 * (res["hi"] - res["lo"]) + 2 * atr_, res["lo"] - 0.25 * atr_))
    e20, e50 = D["e20"], D["e50"]
    pull = any(x is not None and abs(p - x) <= 0.6 * atr_ for x in (e20, e50))
    if T["side"] == "up" and T["strength"] >= 55 and pull and k is not None and k < 45 and (up_cross or (k1 is not None and k > k1)):
        cands.append(("استمرارٌ بعد تصحيح", "long", mid if near(mid) else sup, 0.7, res["lo"] if res["lo"] > p * 1.02 else p + 3 * atr_, p - 1.5 * atr_))
    # البيع (عقودُ البيع الأمريكية وحدها)
    if not longs_only:
        if near(res) or (T["side"] == "down" and near(mid)):
            z = res if near(res) else mid
            timing = 1.0 if (k is not None and k > 80) or (dn_cross and (k1 or 100) > 65) else 0.6 if k is not None and k > 60 else 0.0
            if timing and not (Lq["side"] == "up" and Lq["strength"] >= 55):
                nxt = mid if z is res else sup
                cands.append(("رفضٌ من المقاومة" if z is res else "رفضٌ من منطقة الوسط", "short", z, timing, nxt["hi"], z["hi"] + 0.5 * atr_))
        brk_d = p < sup["lo"] and min(b["close"] for b in daily[-3:]) < sup["lo"] and max(b["close"] for b in daily[-6:-3] or daily[-3:]) >= sup["lo"] * 0.99
        if brk_d and T["side"] == "down" and Lq["side"] == "down":
            ext = [v for lv, v in D["fib"]["lines"].items() if v < p * 0.99]
            cands.append(("كسرُ الدعم", "short", sup, 0.8, max(ext) if ext else p - 2 * (sup["hi"] - sup["lo"]) - 2 * atr_, sup["hi"] + 0.25 * atr_))
    if not cands:
        return {"setup": None, "where": where, "trend": T, "liq": Lq, "k": k, "rsi": D["rsi"], "zones": zs, "close": p}
    best = None
    for name, side, z, timing, target, stop in cands:
        sgn = 1 if side == "long" else -1
        t_al = (T["strength"] / 100) if T["side"] == ("up" if sgn > 0 else "down") else 0.35 if T["side"] == "flat" else 0.0
        l_al = (Lq["strength"] / 100) if Lq["side"] == ("up" if sgn > 0 else "down") else 0.4 if Lq["side"] in ("flat", "na") else 0.0
        dist = abs(p - (z["hi"] if sgn > 0 else z["lo"])) / max(atr_, 1e-9)
        loc = _clip(1 - dist / 3, 0, 1) if name not in ("اختراقُ المقاومة", "كسرُ الدعم") else 0.7
        w_al = 0.0
        if W and W["trend"]:
            w_al = 1.0 if W["trend"]["side"] == ("up" if sgn > 0 else "down") else 0.4 if W["trend"]["side"] == "flat" else 0.0
            wk = W["k"]
            if wk is not None and ((sgn > 0 and wk > 85) or (sgn < 0 and wk < 15)):
                w_al *= 0.5
        q = round(30 * t_al + 25 * l_al + 20 * loc + 15 * timing + 10 * w_al)
        risk, reward = abs(p - stop), abs(target - p)
        rr = reward / risk if risk > 0 else 0.0
        if rr < 1.0:
            q = round(q * 0.7)
        h = 3 if w_al >= 1.0 and t_al >= 0.5 else 2 if t_al >= 0.5 or w_al >= 0.4 else 1
        if best is None or q > best["quality"]:
            best = {"setup": name, "side": side, "quality": q, "horizon": HORIZON[h], "horizon_n": h, "entry": [round(z["lo"], 4), round(z["hi"], 4)],
                    "target": round(target, 4), "stop": round(stop, 4), "rr": round(rr, 2), "zone": z["name"]}
    reasons = [f"الاتجاه {T['word']} {T['level']} ({T['strength']}/100)",
               f"السيولة {Lq.get('word', 'غير متوفّر')}" + (f" {Lq['level']}" if Lq.get("level") else ""),
               f"السعرُ {where}"]
    if k is not None:
        reasons.append(f"Stoch RSI {k:.0f}" + (" — تقاطعٌ صاعد" if up_cross else " — تقاطعٌ هابط" if dn_cross else ""))
    if W and W["trend"]:
        reasons.append(f"الأسبوعيّ {W['trend']['word']}")
    if Lq.get("tag"):
        reasons.append(Lq["tag"])
    return {**best, "where": where, "trend": T, "liq": Lq, "k": k, "rsi": D["rsi"], "zones": zs, "close": p, "reasons": reasons,
            "weekly": (W or {}).get("trend")}
