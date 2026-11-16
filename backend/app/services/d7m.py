"""‏D585: أداةُ D7M على الخادم — ترجمةٌ حرفيّةٌ لـ`frontend/src/components/analysis/d7m.ts` (ترجمةِ سكربت المالك Pine v6).

بأمر المالك: الإطاران الأسبوعيّ والشهريّ «مربطُ الفرس» للحكم الفنيّ — مستوياتُ الفيبوناتشي التلقائيّ ومناطقُه
والاتجاه؛ واليوميُّ لرؤية دخول السيولة وحدَه. فيقرؤها الطيارُ الآليّ للمحفظة بعد الإغلاق بالحساب نفسِه الذي يرسمه
الرسمُ البيانيّ (الإعداداتُ الافتراضية نفسُها: الفيبوناتشي 3/7، والقناة 3/20)، فلا يختلف ما يراه المالك عمّا يحكم به.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

FIB_LEVELS = [0, 0.5, 0.618, -0.5, 1.5, 1, -1, -0.618, 1.618, -0.1, 1.1, 2, 2.1, -1.1]


def atr(bars: list[dict], length: int = 10) -> list[float | None]:
    tr = [b["high"] - b["low"] if i == 0 else max(b["high"] - b["low"], abs(b["high"] - bars[i - 1]["close"]),
                                                   abs(b["low"] - bars[i - 1]["close"])) for i, b in enumerate(bars)]
    out, r = [], None
    for i in range(len(bars)):
        if i < length - 1:
            out.append(None)
            continue
        r = sum(tr[:length]) / length if r is None else (r * (length - 1) + tr[i]) / length
        out.append(r)
    return out


def zigzag(bars: list[dict], mult: float, depth: int) -> list[dict]:
    n, L = len(bars), max(2, depth // 2)
    if n < 2 * L + 1:
        return []
    a = atr(bars, 10)
    piv: list[dict] = []
    for t in range(2 * L, n):
        if a[t] is None:
            continue
        dev = (a[t] / bars[t]["close"]) * 100 * mult
        for is_high in (True, False):
            def src(k):
                return bars[t - k]["high"] if is_high else bars[t - k]["low"]
            p = src(L)
            ok = all(not (src(k) > p if is_high else src(k) < p) for k in range(0, L))
            ok = ok and all(not (src(k) >= p if is_high else src(k) <= p) for k in range(L + 1, 2 * L + 1))
            if not ok:
                continue
            pt = {"index": t - L, "price": p, "isHigh": is_high}
            if not piv:
                piv.append(pt)
                continue
            last = piv[-1]
            if last["isHigh"] == is_high:
                if (p > last["price"]) if is_high else (p < last["price"]):
                    piv[-1] = pt
                continue
            d = 100 * (p - last["price"]) / abs(last["price"])
            if (not last["isHigh"] and d >= dev) or (last["isHigh"] and d <= -dev):
                piv.append(pt)
    return piv


def auto_fib(bars: list[dict], mult: float = 3, depth: int = 7, reverse: bool = False) -> dict | None:
    p = zigzag(bars, mult, depth)
    if len(p) < 2:
        return None
    start, end = p[-2], p[-1]
    sp, ep = (start["price"], end["price"]) if reverse else (end["price"], start["price"])
    height = (-1 if sp > ep else 1) * abs(sp - ep)
    levels = {lv: sp + height * lv for lv in FIB_LEVELS}
    main = sorted(sp + height * lv for lv in (0, 1, 1.1, -0.1))
    mid = (sp + ep) / 2
    support = resistance = None
    for i in range(len(main) - 1):
        lo, hi = main[i], main[i + 1]
        mz = (lo + hi) / 2
        upper = mz >= mid
        if upper and lo == main[-2]:
            resistance = (lo, hi)
        elif mz < mid and hi == main[1]:
            support = (lo, hi)
    return {"levels": levels, "support": support, "resistance": resistance,
            "leg": {"from": ep, "to": sp, "up": sp > ep}, "start_index": start["index"]}


def ema(src: list[float], length: int) -> list[float | None]:
    k, prev, out = 2 / (length + 1), None, []
    for i, v in enumerate(src):
        if i < length - 1:
            out.append(None)
            continue
        prev = sum(src[:length]) / length if prev is None else v * k + prev * (1 - k)
        out.append(prev)
    return out


def rma(src: list[float], length: int) -> list[float | None]:
    prev, out = None, []
    for i, v in enumerate(src):
        if i < length - 1:
            out.append(None)
            continue
        prev = sum(src[:length]) / length if prev is None else (prev * (length - 1) + v) / length
        out.append(prev)
    return out


def sma(src: list[float], length: int) -> list[float | None]:
    return [None if i < length - 1 else sum(src[i - length + 1:i + 1]) / length for i in range(len(src))]


def dmi(bars: list[dict], length: int = 14, smooth: int = 14):
    pdm, ndm, tr = [], [], []
    for i, b in enumerate(bars):
        if i == 0:
            pdm.append(0.0); ndm.append(0.0); tr.append(b["high"] - b["low"])
            continue
        up, dn = b["high"] - bars[i - 1]["high"], bars[i - 1]["low"] - b["low"]
        pdm.append(up if (up > dn and up > 0) else 0.0)
        ndm.append(dn if (dn > up and dn > 0) else 0.0)
        pc = bars[i - 1]["close"]
        tr.append(max(b["high"] - b["low"], abs(b["high"] - pc), abs(b["low"] - pc)))
    trr, p, n = rma(tr, length), rma(pdm, length), rma(ndm, length)
    plus = [None if (v is None or not trr[i]) else 100 * v / trr[i] for i, v in enumerate(p)]
    minus = [None if (v is None or not trr[i]) else 100 * v / trr[i] for i, v in enumerate(n)]
    dx = [0.0 if (v is None or minus[i] is None) else (0.0 if v + minus[i] == 0 else 100 * abs(v - minus[i]) / (v + minus[i]))
          for i, v in enumerate(plus)]
    return plus, minus, rma(dx, smooth)


def resample(bars: list[dict], unit: str) -> list[dict]:
    """شموعٌ أسبوعيةٌ (تبدأ السبت كالسكربت) أو شهرية من اليومية."""
    out: list[dict] = []
    for b in bars:
        d = b["date"][:10]
        if unit == "M":
            k = d[:7]
        else:
            dt = date.fromisoformat(d)
            k = (dt - timedelta(days=(dt.isoweekday() % 7 + 1) % 7)).isoformat()
        if out and out[-1]["_k"] == k:
            last = out[-1]
            last["high"] = max(last["high"], b["high"]); last["low"] = min(last["low"], b["low"])
            last["close"] = b["close"]; last["date"] = b["date"]; last["volume"] = last.get("volume", 0) + (b.get("volume") or 0)
        else:
            out.append({**b, "_k": k})
    return out


def liquidity(bars: list[dict], vol_len: int = 20) -> dict:
    """السيولةُ اللحظية بعتبات المستثمر — من السكربت: اندفاع · تجميع · انهيار · تصريف · جفاف."""
    vols = [b.get("volume") or 0 for b in bars]
    i = len(bars) - 1
    if not any(vols) or i < vol_len:
        return {"state": "غير متوفّر", "rvol": None}
    avg = sma(vols, vol_len)[i] or 1
    rvol = vols[i] / avg * 100
    spreads = [b["high"] - b["low"] for b in bars]
    avg_sp = sma(spreads, vol_len)[i] or 0
    b = bars[i]
    sp = b["high"] - b["low"]
    pos = 0.5 if sp == 0 else (b["close"] - b["low"]) / sp
    squeeze = rvol > 200 and pos > 0.7 and b["close"] > b["open"]
    accum = rvol > 160 and sp < avg_sp and pos > 0.5
    dump = rvol > 200 and pos < 0.3 and b["close"] < b["open"]
    dist = rvol > 160 and sp < avg_sp and pos < 0.5
    dry = rvol < 60
    state = ("اندفاع شرائي" if squeeze else "تجميع خفي" if accum else "انهيار بيعي" if dump
             else "تصريف بيعي" if dist else "جفاف سيولة" if dry else "محايد")
    return {"state": state, "rvol": round(rvol)}


def trend(bars: list[dict]) -> dict:
    """اتجاهُ الإطار من DMI/ADX كلوحة السكربت: صاعد · هابط · ضعيف (ADX دون 20 بلا صعودٍ ولا تجميع)."""
    if len(bars) < 30:
        return {"state": "غير متوفّر"}
    plus, minus, adx = dmi(bars)
    i = len(bars) - 1
    c = [b["close"] for b in bars]
    e = ema(c, min(200, max(10, len(bars) // 3)))
    rising = e[i] is not None and e[i - 1] is not None and e[i] > e[i - 1]
    vols = [b.get("volume") or 0 for b in bars]
    av = sma(vols, 20)
    accum = all(av[i - k] is not None and vols[i - k] > av[i - k] for k in range(3))
    A, P, M = adx[i], plus[i] or 0, minus[i] or 0
    weak = A is None or (A < 20 and not (rising or accum))
    state = "ضعيف" if weak else "صاعد" if P > M else "هابط" if M > P else "ضعيف"
    return {"state": state, "adx": round(A, 1) if A is not None else None, "ema_up": rising}


def frame_read(bars: list[dict], price: float) -> dict | None:
    f = auto_fib(bars, 3, 7)
    if not f:
        return None
    lv = f["levels"]
    sup, res = f["support"], f["resistance"]
    where = ("داخل منطقة الدعم" if sup and sup[0] <= price <= sup[1] else
             "داخل منطقة المقاومة" if res and res[0] <= price <= res[1] else
             "تحت الدعم" if sup and price < sup[0] else "فوق المقاومة" if res and price > res[1] else "بين الدعم والمقاومة")
    r2 = lambda x: round(x, 2)
    return {"support": [r2(sup[0]), r2(sup[1])] if sup else None,
            "resistance": [r2(res[0]), r2(res[1])] if res else None,
            "strong_support_0_5": r2(lv[0.5]), "reversal_0_618": r2(lv[0.618]),
            "target_1_618": r2(lv[1.618]), "leg_up": f["leg"]["up"], "where": where, **trend(bars)}


async def read(symbol: str) -> dict | None:
    """قراءةُ D7M لسهمٍ بعد الإغلاق: الشهريُّ والأسبوعيُّ للحكم، واليوميُّ للسيولة."""
    from app.services import cache
    sym = str(symbol).replace(".SR", "").strip()
    ck = f"d7m:v1:{sym}:{date.today().isoformat()}"
    hit = cache.get(ck)
    if hit is not None:
        return hit or None
    try:
        from app.services.market_data import market_service
        pts = await market_service._yahoo()._fetch_chart_points(f"{sym}.SR", "10y", "1d")
    except Exception:                                             # noqa: BLE001
        pts = None
    bars = [p for p in (pts or []) if p.get("close") and p.get("high") and p.get("low")]
    if len(bars) < 60:
        cache.set(ck, {}, 6 * 3600)
        return None
    price = bars[-1]["close"]
    w, m = resample(bars, "W"), resample(bars, "M")
    out = {"price": price, "asof": bars[-1]["date"][:10], "weekly": frame_read(w, price), "monthly": frame_read(m, price),
           "daily_liquidity": liquidity(bars), "daily_trend": trend(bars)["state"]}
    cache.set(ck, out, 20 * 3600)
    return out


# ══ ‏D756 (المالك 2026-11-16): «ضع مؤشّر دحم في التقرير — المناطقُ الثلاث والمتوسّطاتُ 20 و50 و200 على اليوميّ، وتحته ستوكاستيك RSI
#    كالذي عندي، والترندُ التلقائيّ والقناةُ السعرية الرئيسية» — ترجمةٌ حرفيةٌ لـ`autoChannel` و`autoTrend` و`stochRsi` من الواجهة،
#    والحارسُ (‏scripts/audit/d7m_report_d756.py) يطابق بين الشيفرتين على الشموع نفسِها. ══

def _channel_legacy(bars: list[dict], p: list[dict]) -> dict | None:
    if len(p) < 3:
        return None
    a, b, c = p[-3], p[-2], p[-1]
    if a["isHigh"] != c["isHigh"] or a["index"] == c["index"]:
        return None
    slope = (c["price"] - a["price"]) / (c["index"] - a["index"])
    ic_base, ic_par = a["price"] - slope * a["index"], b["price"] - slope * b["index"]
    x_end = len(bars) - 1
    return {"base": [[a["index"], a["price"]], [x_end, slope * x_end + ic_base]], "parallel": [[b["index"], b["price"]], [x_end, slope * x_end + ic_par]]}


def auto_channel(bars: list[dict], mult: float = 3, depth: int = 20) -> dict | None:
    """القناةُ التلقائية (‏D744): أكثرُ الخطوط لمساتٍ بين قمّتين أو قاعين لم تكسره الإغلاقات، وموازيتُها بأبعد طرفٍ مقابل."""
    p, n = zigzag(bars, mult, depth), len(bars)
    if len(p) < 3 or n < 30:
        return None
    at = atr(bars, 14)[n - 1]
    if at is None:
        at = sum(b["high"] - b["low"] for b in bars[-14:]) / 14
    if not at:
        return _channel_legacy(bars, p)
    tol = at / 3
    highs, lows = [x for x in p if x["isHigh"]][-5:], [x for x in p if not x["isHigh"]][-5:]
    best = None
    for st, is_high in ((highs, True), (lows, False)):
        for i in range(len(st)):
            for j in range(i + 1, len(st)):
                P, Q = st[i], st[j]
                if Q["index"] - P["index"] < 5:
                    continue
                slope = (Q["price"] - P["price"]) / (Q["index"] - P["index"])
                line = lambda x: P["price"] + slope * (x - P["index"])   # noqa: E731
                broken, ext = 0, float("inf") if is_high else float("-inf")
                for x in range(P["index"], n):
                    L, b = line(x), bars[x]
                    if (b["close"] > L + tol) if is_high else (b["close"] < L - tol):
                        broken += 1
                    d = (b["low"] - L) if is_high else (b["high"] - L)
                    if (d < ext) if is_high else (d > ext):
                        ext = d
                span = n - P["index"]
                if broken > max(1, span * 0.02) or ext in (float("inf"), float("-inf")):
                    continue
                c, L1 = bars[n - 1]["close"], line(n - 1)
                L2 = L1 + ext
                if c > max(L1, L2) + tol or c < min(L1, L2) - tol:
                    continue
                same = len([z for z in st if z["index"] >= P["index"] and abs(z["price"] - line(z["index"])) <= tol])
                opp = len([z for z in (lows if is_high else highs) if z["index"] >= P["index"] and abs(z["price"] - (line(z["index"]) + ext)) <= tol])
                score = same * 2 + opp * 1.5 + min(span / 60, 2) + (1 if j == len(st) - 1 else 0) - abs(ext) / at * 0.04
                if best is None or score > best["score"]:
                    best = {"score": score, "x0": P["index"], "y0": P["price"], "slope": slope, "ext": ext, "touches": same + opp}
    if best is None or best["touches"] < 3:
        return _channel_legacy(bars, p)
    x_end = n - 1
    y_end = best["y0"] + best["slope"] * (x_end - best["x0"])
    return {"base": [[best["x0"], best["y0"]], [x_end, y_end]], "parallel": [[best["x0"], best["y0"] + best["ext"]], [x_end, y_end + best["ext"]]],
            "touches": best["touches"]}


def _pivot_at(bars: list[dict], c: int, pp: int, high: bool) -> bool:
    if c - pp < 0 or c + pp >= len(bars):
        return False
    v = bars[c]["high"] if high else bars[c]["low"]
    for k in range(c - pp, c + pp + 1):
        if k == c:
            continue
        w = bars[k]["high"] if high else bars[k]["low"]
        if (w >= v if k < c else w > v) if high else (w <= v if k < c else w < v):
            return False
    return True


def auto_trend(bars: list[dict], PP: int = 15) -> dict:
    """الاتجاهُ التلقائيّ (ترجمةُ سكربت المالك): خطوطُ الاتجاه الرئيسية والفرعية على القمم والقيعان، وإشاراتُ الكسر والارتداد."""
    nan = float("nan")
    n = len(bars)
    T, V, I = [], [], []
    TA, VA, IA = [], [], []
    HV = LV = nan
    HI = LI = 0
    MjH = MjL = nan
    lock0 = lock1 = True
    prev_v = prev_t = None
    x0 = y0 = 0
    t0 = prev_t0 = ""
    types = ["MHL", "MLH", "MHH", "MLL", "mHL", "mLH", "mHH", "mLL"]
    ptr = {t: {"X0": 0, "Y0": 0, "X1": 0, "Y1": 0} for t in types}
    prev_x0: dict = {}
    checkers = [("MLL", "Up", True), ("MHH", "Down", True), ("MHL", "Up", True), ("MLH", "Down", True),
                ("mLL", "Up", False), ("mHH", "Down", False), ("mHL", "Up", False), ("mLH", "Down", False)]
    st = [{"line": None, "permit": True} for _ in checkers]
    signals = []

    def push(t, v, i):
        T.append(t); V.append(v); I.append(i)   # noqa: E702

    def pop():
        T.pop(); V.pop(); I.pop()   # noqa: E702

    def h_type():
        return ("HH" if V[-2] < HV else "LH") if len(T) > 2 else "H"

    def l_type():
        return ("HL" if V[-2] < LV else "LL") if len(T) > 2 else "L"

    for t in range(n):
        c = t - PP
        hp = c >= 0 and _pivot_at(bars, c, PP, True)
        lp = c >= 0 and _pivot_at(bars, c, PP, False)
        if hp:
            HV, HI = bars[c]["high"], c
        if lp:
            LV, LI = bars[c]["low"], c
        close = bars[t]["close"]
        HP, LP = HV, LV
        if hp and lp:
            if T:
                lt = T[-1]
                if lt in ("L", "LL"):
                    if LP < V[-1]:
                        pop(); push(l_type(), LV, LI)   # noqa: E702
                    else:
                        push(h_type(), HV, HI)
                elif lt in ("H", "HH"):
                    if HP > V[-1]:
                        pop(); push(h_type(), HV, HI)   # noqa: E702
                    else:
                        push(l_type(), LV, LI)
                elif lt == "LH":
                    if HP < V[-1]:
                        push(l_type(), LV, LI)
                    elif HP > V[-1]:
                        if close < V[-1]:
                            pop(); push(h_type(), HV, HI)   # noqa: E702
                        elif close > V[-1]:
                            push(l_type(), LV, LI)
                elif lt == "HL":
                    if LP > V[-1]:
                        push(h_type(), HV, HI)
                    elif LP < V[-1]:
                        if close > V[-1]:
                            pop(); push(l_type(), LV, LI)   # noqa: E702
                        elif close < V[-1]:
                            push(h_type(), HV, HI)
        elif hp:
            if not T:
                T.insert(0, "H"); V.insert(0, HV); I.insert(0, HI)   # noqa: E702
            else:
                lt = T[-1]
                if lt in ("L", "HL", "LL"):
                    if HP > V[-1]:
                        push(h_type(), HV, HI)
                    elif HP < V[-1]:
                        pop(); push(l_type(), LV, LI)   # noqa: E702
                elif lt in ("H", "HH", "LH"):
                    if V[-1] < HV:
                        pop(); push(h_type(), HV, HI)   # noqa: E702
        elif lp:
            if not T:
                T.insert(0, "L"); V.insert(0, LV); I.insert(0, LI)   # noqa: E702
            else:
                lt = T[-1]
                if lt in ("H", "HH", "LH"):
                    if LP < V[-1]:
                        push(l_type(), LV, LI)
                    elif LP > V[-1]:
                        pop(); push(h_type(), HV, HI)   # noqa: E702
                elif lt in ("L", "HL", "LL"):
                    if V[-1] > LV:
                        pop(); push(l_type(), LV, LI)   # noqa: E702
        if len(T) == 2:
            if T[0] == "H":
                MjH, MjL = V[0], V[1]
            elif T[0] == "L":
                MjH, MjL = V[1], V[0]
        if len(V) == 1 and lock0:
            TA.insert(0, "M" + T[0]); VA.insert(0, V[0]); IA.insert(0, I[0]); lock0 = False   # noqa: E702
        if len(V) == 2 and lock1:
            TA.insert(1, "M" + T[1]); VA.insert(1, V[1]); IA.insert(1, I[1]); lock1 = False   # noqa: E702
        if len(V) > 1:
            lv, ltp = V[-1], T[-1]
            if prev_v is not None and prev_v != lv:
                if (prev_t[-1:] if prev_t else "") != ltp[-1:]:
                    TA.append("m" + ltp); VA.append(lv); IA.append(I[-1])   # noqa: E702
                else:
                    VA.pop(); IA.pop(); VA.append(lv); IA.append(I[-1])   # noqa: E702
        prev_v = V[-1] if V else None
        prev_t = T[-1] if T else None
        if len(VA) > 1:
            if close > MjH:
                if TA[-1] == "mL":
                    TA[-1] = "ML"; MjL = VA[-1]   # noqa: E702
                elif TA[-1] in ("mHL", "mLL"):
                    TA[-1] = "M" + T[-1]; MjL = VA[-1]   # noqa: E702
                elif TA[-1] in ("mLH", "mHH", "MLH", "MHH"):
                    if TA[-2] in ("mHL", "mLL"):
                        TA[-2] = "M" + T[-2]; MjL = VA[-2]   # noqa: E702
            if VA[-1] > MjH:
                if TA[-1] == "mH":
                    TA[-1] = "MH"; MjH = VA[-1]   # noqa: E702
                elif TA[-1] in ("mLH", "mHH", "MHH"):
                    TA[-1] = "M" + T[-1]; MjH = VA[-1]   # noqa: E702
            if close < MjL:
                if TA[-1] in ("mH", "mLH", "mHH"):
                    TA[-1] = "M" + T[-1]; MjH = VA[-1]   # noqa: E702
                elif TA[-1] in ("mHL", "mLL", "MLL"):
                    if TA[-2] in ("mLH", "mHH"):
                        TA[-2] = "M" + T[-2]; MjH = VA[-2]   # noqa: E702
            if VA[-1] < MjL:
                if TA[-1] == "mL":
                    TA[-1] = "ML"; MjL = VA[-1]   # noqa: E702
                elif TA[-1] in ("mHL", "mLL", "MLL"):
                    TA[-1] = "M" + T[-1]; MjL = VA[-1]   # noqa: E702
        prev_t0 = t0
        if len(TA) > 2:
            x0, y0, t0 = IA[-1], VA[-1], TA[-1]
        for ty in types:
            p = ptr[ty]
            prev_x0[ty] = p["X0"]
            if t0 != prev_t0 and t0 == ty:
                if p["X0"] == 0:
                    p["X0"], p["Y0"] = x0, y0
                elif p["X1"] == 0:
                    p["X1"], p["Y1"] = x0, y0
                else:
                    p["X0"], p["Y0"], p["X1"], p["Y1"] = p["X1"], p["Y1"], x0, y0
        for k, (ty, dr, _major) in enumerate(checkers):
            p, s = ptr[ty], st[k]
            if p["X0"] != 0 and p["X1"] != 0 and p["X0"] != prev_x0[ty]:
                if (p["Y1"] > p["Y0"]) if dr == "Up" else (p["Y1"] < p["Y0"]):
                    slope = (p["Y1"] - p["Y0"]) / (p["X1"] - p["X0"])
                    permit = True
                    for j in range(1, t - p["X0"] + 1):
                        x = p["X0"] + j
                        if x == p["X1"]:
                            continue
                        lp2, cl = p["Y0"] + slope * j, bars[x]["close"]
                        permit = ((cl > lp2) if dr == "Up" else (cl < lp2)) and permit
                    if permit:
                        s["line"] = {"x1": p["X0"], "y1": p["Y0"], "x2": p["X1"], "y2": p["Y1"], "slope": slope}
                        s["permit"] = True
            if s["line"]:
                ln = s["line"]
                at = lambda x, ln=ln: ln["y1"] + ln["slope"] * (x - ln["x1"])   # noqa: E731
                prev_ps = s["permit"]
                if ((close > at(t)) if dr == "Up" else (close < at(t))) and s["permit"]:
                    ln["x2"] = min(t + 1, n - 1)
                    ln["y2"] = at(ln["x2"])
                else:
                    s["permit"] = False
                b = bars[t]
                if prev_ps and not s["permit"]:
                    signals.append({"index": t, "kind": "breakDown" if dr == "Up" else "breakUp"})
                if s["permit"] and ((close > at(t) and b["low"] < at(t)) if dr == "Up" else (close < at(t) and b["high"] > at(t))):
                    signals.append({"index": t, "kind": "reactUp" if dr == "Up" else "reactDown"})
    lines = [{"x1": s["line"]["x1"], "y1": s["line"]["y1"], "x2": s["line"]["x2"], "y2": s["line"]["y2"],
              "major": checkers[k][2], "up": checkers[k][1] == "Up"} for k, s in enumerate(st) if s["line"]]
    return {"lines": lines, "signals": signals}


def _rsi_w(data: list[float], p: int = 14) -> list:
    out = [None] * len(data)
    if len(data) < p + 1:
        return out
    g = sum(max(data[i] - data[i - 1], 0) for i in range(1, p + 1)) / p
    l = sum(max(data[i - 1] - data[i], 0) for i in range(1, p + 1)) / p   # noqa: E741
    out[p] = 100 if l == 0 else 100 - 100 / (1 + g / l)
    for i in range(p + 1, len(data)):
        d = data[i] - data[i - 1]
        g, l = (g * (p - 1) + max(d, 0)) / p, (l * (p - 1) + max(-d, 0)) / p   # noqa: E741
        out[i] = 100 if l == 0 else 100 - 100 / (1 + g / l)
    return out


def _sma_n(a: list, p: int) -> list:
    out = [None] * len(a)
    for i in range(p - 1, len(a)):
        w = a[i - p + 1:i + 1]
        if all(v is not None for v in w):
            out[i] = sum(w) / p
    return out


def stoch_rsi(closes: list[float], k: int = 3, d: int = 3, rsi_len: int = 14, stoch_len: int = 14) -> dict:
    """‏Stoch RSI بسكربت تريدنق فيو (‏3 3 14 14 على الإغلاق) — كدالّة الواجهة حرفاً."""
    r, n = _rsi_w(closes, rsi_len), len(closes)
    raw = [None] * n
    for i in range(stoch_len - 1, n):
        w = r[i - stoch_len + 1:i + 1]
        if any(v is None for v in w):
            continue
        hh, ll = max(w), min(w)
        if hh > ll:
            raw[i] = 100 * (r[i] - ll) / (hh - ll)
    kk = _sma_n(raw, k)
    return {"k": kk, "d": _sma_n(kk, d)}
