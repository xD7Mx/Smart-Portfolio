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
