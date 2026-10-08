"""
Technical analysis — pure math on a daily close-price series (no network cost).
Computes moving averages, RSI(14), MACD, support/resistance and a trend read,
then a 0-100 technical score with an Arabic verdict and reasons. Runs
automatically whenever a company's history is available.
"""

from typing import Optional


def _sma(values: list[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    ema = [values[0]]
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def _rsi(values: list[float], period: int = 14) -> Optional[float]:
    if len(values) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(values)):
        d = values[i] - values[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _macd(values: list[float]):
    if len(values) < 35:
        return None, None
    ema12 = _ema_series(values, 12)
    ema26 = _ema_series(values, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal = _ema_series(macd_line, 9)
    return round(macd_line[-1], 3), round(signal[-1], 3)


# ‏D636: حدُّ التذبذب اليوميّ في «تداول» 10٪ — فقفزةٌ يوميةٌ فوق 40٪ ليست حركةَ سوقٍ بل حدثُ رأس مالٍ أو بيانٌ معطوب.
# قِيس في بوابة الإصدار الأوّل: كيمائيات الميثانول +350٪ (تخفيضُ رأس مال) · التعاونية +50٪ · نسيج +49٪، والأسماك
# 64←18←65 ثلاثَ مرّاتٍ في شهر (شرائحُ معطوبةٌ من المزوّد). والمؤشّراتُ المحسوبةُ عبرها تقيس القفزةَ لا السوق.
LIMIT_JUMP = 0.40
_REVERT_WITHIN = 15      # قفزتان متعاكستان خلال 15 جلسةً يلغي حاصلُهما الأخرى ← الشريحةُ بينهما معطوبة


def clean_series(history: list) -> tuple[list, list[dict]]:
    """السلسلةُ كما تُحسب عليها المؤشّرات ← (السلسلةُ المصحَّحة، الأحداثُ المكتشَفة بتاريخها ونوعها).

    ١ شريحةٌ معطوبة: قفزةٌ تعقبها خلال 15 جلسةً قفزةٌ تعاكسها (حاصلُهما بين 0.85 و1.15) ← تُحذف الشريحة.
    ٢ قفزةٌ دائمة: حدثُ رأس مال ← يُعدَّل ما قبلها بنسبتها كما يُعدَّل التاريخُ عند التجزئة."""
    pts = [dict(p) for p in (history or []) if p.get("close") not in (None, 0)]
    events: list[dict] = []
    jump = lambda a, b: a > 0 and abs(b / a - 1) > LIMIT_JUMP   # noqa: E731
    i = 1
    while i < len(pts):
        a, b = float(pts[i - 1]["close"]), float(pts[i]["close"])
        if jump(a, b):
            for j in range(i + 1, min(i + 1 + _REVERT_WITHIN, len(pts))):
                c, d = float(pts[j - 1]["close"]), float(pts[j]["close"])
                if jump(c, d) and 0.85 <= (b / a) * (d / c) <= 1.15:
                    events.append({"date": str(pts[i].get("date"))[:10], "kind": "شريحةٌ معطوبة",
                                   "days": j - i, "until": str(pts[j].get("date"))[:10]})
                    del pts[i:j]
                    break
        i += 1
    for k in range(len(pts) - 1, 0, -1):
        a, b = float(pts[k - 1]["close"]), float(pts[k]["close"])
        if jump(a, b):
            f = b / a
            for p in pts[:k]:
                for key in ("open", "high", "low", "close"):
                    if isinstance(p.get(key), (int, float)):
                        p[key] = p[key] * f
            events.append({"date": str(pts[k].get("date"))[:10], "kind": "حدثُ رأس مال", "factor": round(f, 4)})
    return pts, events


def analyze(history: list) -> Optional[dict]:
    """history: [{'date','close'}, ...] ascending. Returns indicators + verdict."""
    history, _events = clean_series(history)
    closes = [float(p["close"]) for p in (history or []) if p.get("close") is not None]
    if len(closes) < 15:
        return None
    price = closes[-1]
    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200)
    rsi = _rsi(closes)
    macd, signal = _macd(closes)
    window = closes[-60:] if len(closes) >= 60 else closes
    support = round(min(window), 2)
    resistance = round(max(window), 2)

    reasons: list[str] = []
    score = 50

    if sma50:
        if price > sma50:
            score += 12
            reasons.append("السعر فوق متوسط 50 يوماً (اتجاه صاعد)")
        else:
            score -= 12
            reasons.append("السعر تحت متوسط 50 يوماً (ضغط هابط)")
    if sma20 and sma50:
        if sma20 > sma50:
            score += 8
            reasons.append("متوسط 20 فوق متوسط 50 (زخم إيجابي)")
        else:
            score -= 6
    if sma200:
        if price > sma200:
            score += 8
            reasons.append("السعر فوق متوسط 200 يوم (اتجاه طويل صاعد)")
        else:
            score -= 8
            reasons.append("السعر تحت متوسط 200 يوم")
    if rsi is not None:
        if rsi >= 70:
            score -= 10
            reasons.append(f"RSI مرتفع {rsi} (تشبع شرائي)")
        elif rsi <= 30:
            score += 8
            reasons.append(f"RSI منخفض {rsi} (تشبع بيعي — ارتداد محتمل)")
        elif 45 <= rsi <= 60:
            score += 4
            reasons.append(f"RSI متوازن {rsi}")
    if macd is not None and signal is not None:
        if macd > signal:
            score += 8
            reasons.append("MACD فوق خط الإشارة (إشارة إيجابية)")
        else:
            score -= 8
            reasons.append("MACD تحت خط الإشارة (إشارة سلبية)")

    # proximity to support/resistance
    if resistance > support:
        pos = (price - support) / (resistance - support)
        if pos <= 0.15:
            score += 5
            reasons.append("قريب من الدعم")
        elif pos >= 0.85:
            score -= 5
            reasons.append("قريب من المقاومة")

    score = max(0, min(100, round(score)))
    verdict = ("قوي جداً" if score >= 80 else "قوي" if score >= 65
               else "متوسط" if score >= 45 else "ضعيف")
    trend = ("صاعد" if sma50 and price > sma50 else "هابط" if sma50 else "غير محدد")

    # Plain-language mean-reversion read: is the price stretched away from
    # its own long-run average (a real, computed number — SMA200, falling
    # back to SMA50), or sitting close to it? A price far above its average
    # is statistically more likely to correct down toward it, and vice
    # versa — the logical read a technical verdict should actually give,
    # not just a jargon score.
    avg_basis = sma200 or sma50
    pct_from_avg = round((price - avg_basis) / avg_basis * 100, 1) if avg_basis else None
    # ══ هذا **متوسطُ السعر**، وليس القيمة العادلة ══ (بأمر المالك)
    # كان يُسمّى `fair_value` ويُعرض «السعر العادل» في صفحة الشركة، بينما
    # صفحة الذكاء تعرض تحت الاسم نفسه `target_mean_price` — إجماعَ أهداف
    # المحللين. فرقمان مختلفان تماماً باسمٍ واحد: أحدهما متوسطٌ متحرّك
    # لسعر السهم نفسه (‏SMA200)، والآخر تقديرُ قيمةٍ من محلّلين. والمالك
    # يقرأ الشاشتين فيرى تناقضاً — وهو تناقضٌ حقيقيّ لا وهم.
    # فالاسم عاد إلى مسمّاه: متوسطُ السعر يُسمّى متوسطاً، والقيمة العادلة
    # اسمٌ محجوز لمصدرٍ واحد في التطبيق كلّه.
    mean_note = None
    if pct_from_avg is not None:
        if pct_from_avg >= 15:
            mean_note = f"السعر أعلى من متوسطه المتحرّك بنسبة {pct_from_avg}% — احتمال تصحيح لأسفل نحو المتوسط"
        elif pct_from_avg <= -15:
            mean_note = f"السعر أقل من متوسطه المتحرّك بنسبة {abs(pct_from_avg)}% — احتمال تعافٍ نحو المتوسط"
        else:
            mean_note = f"السعر قريب من متوسطه المتحرّك (فرق {pct_from_avg:+.1f}%)"

    return {
        "price": round(price, 2),
        "sma20": round(sma20, 2) if sma20 else None,
        "sma50": round(sma50, 2) if sma50 else None,
        "sma200": round(sma200, 2) if sma200 else None,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": signal,
        "support": support,
        "resistance": resistance,
        "trend": trend,
        "score": score,
        "verdict": verdict,
        "reasons": reasons,
        "pct_from_avg": pct_from_avg,
        "mean_note": mean_note,
        "mean_basis": round(avg_basis, 2) if avg_basis else None,
    }
