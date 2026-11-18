"""مُنتقي عقود الخيارات طويلة الأجل (‏D759 · بأمر المالك 2026-11-17).

قال المالك: «في مختبر الأبحاث خانةٌ أضع فيها قيمةَ العقد — 150 أو 100 أو 50 دولاراً — فيُخرج أفضلَ خيارٍ في السوق الأمريكيّ،
اختيارُه على التحليل الفنيّ البسيط: المسارُ صاعدٌ أو هابطٌ أو عرضيّ، ويعرف الأخبار — مثلاً استقال رئيسُ إنفيديا فالسهمُ هابط —
ويختار عقوداً طويلةَ المدى لا قصيرة حتى لا تتآكل… صفقاتٌ أختار منها ما يناسبني مع المبرّر».

ثلاثُ مراحل، وكلُّ رقمٍ من مصدره في التطبيق (لا اختلاق):
  ١ **المسار** — لكلّ سهمٍ أو صندوقٍ سائلٍ في القائمة: الإغلاقُ ومتوسّطا 50 و200 وميلُ متوسّط 50 وتغيّرُ ثلاثة أشهر من شموعه اليومية:
     صاعدٌ (متوسّطُ 50 فوق 200 بفرقٍ فوق 1٪ صاعداً بميلٍ فوق 0.3٪، والإغلاقُ فوق 200) · هابطٌ (عكسُه) · وإلا عرضيّ لا يُشترى له عقد.
  ٢ **الأخبار** — عناوينُ السهم في عشرة أيامٍ من محرّك ياهو، يقرؤها النموذجُ قراءةَ محلّل: أثرُها (إيجابيّ · سلبيّ · محايد) وقوّتُه (0–3)
     والحدثُ نفسُه بجملة — من العناوين وحدها. والخبرُ القويُّ المعاكسُ للمسار يُسقط السهم، والقويُّ جداً يعطي العرضيَّ اتجاهَه.
  ٣ **العقد** — آجالٌ بين 120 و430 يوماً (التآكلُ الزمنيُّ بطيءٌ فيها)، وكلفتُه (سعرُ الطلب × 100) ضمن الميزانية، وسيولتُه (اهتمامٌ مفتوح
     وفارقٌ معقول)؛ ويُقاس **احتمالُ الربح عند الانتهاء** من التذبذب الضمنيّ (احتمالُ تجاوز نقطة التعادل في توزيعٍ لوغاريتميّ)،
     والدلتا، والحركةُ المطلوبةُ إلى التعادل بوحدة التذبذب المتوقّع — ويُختار لكلّ سهمٍ أفضلُ عقدٍ ثمّ تُرتَّب الصفقات.
     والسوقُ مغلقٌ يُصفِّر المصدرُ الطلبَ والعرضَ والتذبذب (مقيسٌ 2026-11-17 قبل الافتتاح: صفرٌ في أغلب العقود) — فيُؤخذ سعرُ آخر صفقةٍ
     إن كانت في أربعة أيام، ويُستخرج التذبذبُ الضمنيُّ منه بمعادلة بلاك-شولز، ويُوسَم العقدُ «آخر صفقة».
     وسعرُ الأطراف البعيدة قديمٌ أو عند حدّ التسعير فيتضخّم تذبذبُه ويتضخّم معه الاحتمال (قيس: بيعُ NFLX بتنفيذ 10 والسهمُ 60 بتذبذب 214٪
     واحتمال 64٪) — فيُقاس كلُّ عقدٍ بتذبذب النقود في أجله (وسيطُ أقرب العقود إلى السعر) ويُستبعد ما خرج عن نطاقه.
والاحتمالُ تقديرٌ من سعر السوق نفسِه لا وعد؛ وأقصى الخسارة كلفةُ العقد.

‏D762 (المالك 2026-11-18: «فارقُ العرض والطلب 30 دولاراً — خسارةٌ مباشرة… والنتائجُ كلَّ يومٍ تختلف وهي طويلةُ المدى — لازم الاختيارُ
مقنع، حتى السترايك»): الفارقُ ≤ 10٪ من الوسط من عرضٍ وطلبٍ حقيقيّين (حيّين أو من آخر جلسة — لا آخرُ صفقةٍ بفارقٍ مجهول)، والتنفيذُ
يُختار على **هدفٍ فنيّ** (أقربُ قمّةٍ أو قاعٍ يبعد 5٪ فأكثر): التعادلُ دونه والعائدُ عنده ≥ 0.75 من الكلفة والدلتا بين 0.30 و0.85؛
و**دفترُ التوصيات** يحفظ كلَّ توصيةٍ بتاريخها وسعرِ دخولها وأطروحتها حتى تنكسر قاعدةُ خروجٍ مكتوبة (وقفٌ عند نصف الكلفة · هدف ·
انقلابُ المسار · ستون يوماً قبل الانتهاء)، ولا يدخل جديدٌ إلا في مقعدٍ شاغر — فلا تتبدّل القائمةُ كلَّ يوم."""
from __future__ import annotations

import asyncio
import json
import math
import os
import time
from datetime import datetime, timedelta, timezone

from loguru import logger

# الأسهمُ والصناديقُ الأمريكيةُ الأسيلُ خياراتٍ — حيث تكون للعقود الطويلة أسعارٌ حقيقيةٌ واهتمامٌ مفتوح
UNIVERSE = (
    "SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLK", "SMH", "GLD", "SLV", "TLT", "XBI", "KRE", "ARKK",
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "AVGO", "NFLX", "CRM", "ORCL", "INTC", "MU", "QCOM",
    "ADBE", "PLTR", "UBER", "SHOP", "PYPL", "BAC", "JPM", "WFC", "C", "GS", "XOM", "CVX", "OXY", "PFE", "MRK", "JNJ",
    "LLY", "ABBV", "UNH", "KO", "PEP", "WMT", "COST", "HD", "NKE", "DIS", "BA", "CAT", "F", "GM", "T", "VZ", "SOFI",
    "RIVN", "NIO", "BABA", "COIN", "MARA", "HOOD", "SNAP", "AAL", "CCL", "DAL", "UAL", "SBUX", "CVS", "WBD",
    "EEM", "FXI", "EWZ", "GDX", "KWEB", "XLU", "XLV", "XLI", "XLP", "CSCO", "CMCSA", "KMI", "HPE", "VALE", "NOK", "PLUG", "RIOT",
    "CLF", "LUV", "KHC", "GRAB",
)
MIN_DTE, MAX_DTE = 150, 430
RATE = 0.04
MIN_OI = 100
MAX_SPREAD = 0.10        # ‏D762: الفارقُ ≤ 10٪ من الوسط — كان 35٪ فظهر عقدُ NIO بفارق 30 دولاراً (خسارةٌ فوريّة)
MIN_POP = 0.20
MIN_DELTA, MAX_DELTA = 0.30, 0.85
MIN_RR = 0.75            # العائدُ عند الهدف ≥ 0.75 من الكلفة — ومع الوقف عند نصفها فالعائدُ إلى المخاطرة ≥ 1.5
NEW_MIN = 30             # عتبةُ دخول توصيةٍ جديدةٍ في الدفتر (من 100) — والشروطُ الصارمةُ قبلها هي الحَكَم
MAX_OPEN = 8
STOP_FRAC = 0.5          # وقفُ التوصية: نصفُ سعر الدخول
EXIT_DTE = 60            # الخروجُ قبل ستين يوماً من الانتهاء
COOL_DAYS = 7            # لا عودةَ إلى سهمٍ خرج بوقفٍ أو انكسارٍ أو جنيٍ قبل أسبوع
SNAP_DAYS = 5            # العرضُ والطلبُ من آخر جلسة صالحان خمسةَ أيام (تغطّي العطلةَ الطويلة)
MIN_PRICE = 2.0          # رمزٌ دون دولارين في المصدر منتهٍ أو غيرُ صالحٍ لعقدٍ طويل
STALE_DAYS = 4           # آخرُ صفقةٍ أقدمُ من أربعة أيامٍ لا يُبنى عليها سعر (يغطّي عطلةَ نهاية الأسبوع)
MIN_PX = 0.05            # عقدٌ بأقلّ من خمسة سنتات سعرُه حدُّ التسعير لا قيمتُه
IV_BAND = (0.5, 1.6)     # تذبذبُ العقد بين نصف تذبذب النقود وضعفِه إلا قليلاً — وما خرج فسعرُه شاذّ
CANDIDATES = 40
SCAN_TTL, NEWS_TTL, RES_TTL = 6 * 3600, 2 * 3600, 26 * 3600
_JOB = {"on": False, "budget": None, "msg": "", "at": None}


def _ncdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs_delta(S: float, K: float, T: float, iv: float, call: bool, r: float = RATE) -> float:
    d1 = (math.log(S / K) + (r + iv * iv / 2) * T) / (iv * math.sqrt(T))
    return _ncdf(d1) if call else _ncdf(d1) - 1


def bs_price(S: float, K: float, T: float, iv: float, call: bool, r: float = RATE) -> float:
    sq = iv * math.sqrt(T)
    d1 = (math.log(S / K) + (r + iv * iv / 2) * T) / sq
    d2 = d1 - sq
    disc = K * math.exp(-r * T)
    return S * _ncdf(d1) - disc * _ncdf(d2) if call else disc * _ncdf(-d2) - S * _ncdf(-d1)


def implied_vol(px: float, S: float, K: float, T: float, call: bool, r: float = RATE) -> float | None:
    """التذبذبُ الضمنيُّ من سعر العقد (تنصيفٌ بين 1٪ و500٪) — وسعرٌ خارجَ حدود النموذج لا تذبذبَ له."""
    lo, hi = 0.01, 5.0
    if not (px > 0 and S > 0 and K > 0 and T > 0) or not (bs_price(S, K, T, lo, call, r) < px < bs_price(S, K, T, hi, call, r)):
        return None
    for _ in range(70):
        mid = (lo + hi) / 2
        if bs_price(S, K, T, mid, call, r) < px:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def quote(o: dict, S: float, T: float, call: bool, now: float | None = None, allow_last: bool = True) -> dict | None:
    """سعرُ الشراء وتذبذبُه: الطلبُ والعرضُ الحيّان، وإلا طلبُ آخر جلسةٍ وعرضُها (‏`sbid`/`sask` — يحفظهما ‏options_chain والسوقُ مفتوح)،
    وإلا (للعرض وحده — ‏`allow_last`) آخرُ صفقةٍ في أربعة أيام بفارقٍ مجهول. والتوصيةُ لا تُبنى على فارقٍ مجهول (‏D762)."""
    ask, bid, last, K = o.get("ask") or 0, o.get("bid") or 0, o.get("last") or 0, o.get("strike")
    sask, sbid = o.get("sask") or 0, o.get("sbid") or 0
    if not K:
        return None
    if ask > 0 and bid > 0:
        px, src, spread, ref = ask, "ask", (ask - bid) / ((ask + bid) / 2), (ask + bid) / 2
    elif sask > 0 and sbid > 0:
        px, src, spread, ref = sask, "snap", (sask - sbid) / ((sask + sbid) / 2), (sask + sbid) / 2
    elif allow_last and last > 0 and o.get("last_trade"):
        try:
            age = ((now or time.time()) - datetime.fromisoformat(o["last_trade"]).timestamp()) / 86400
        except (TypeError, ValueError):
            return None
        if age > STALE_DAYS:
            return None
        px, src, spread, ref = last, "last", None, last
    else:
        return None
    # التذبذبُ يُستخرج من السعر نفسِه (الوسطُ أو آخرُ صفقة) لا من حقل المصدر: حقلُه في الأطراف قديمٌ شاذّ (قيس: 214٪ لعقدٍ بأربعة سنتات)
    iv = implied_vol(ref, S, K, T, call) or 0
    if not (0.05 <= iv <= 3):
        return None
    return {"px": px, "src": src, "spread": spread, "iv": iv}


def atm_iv(ch: dict, S: float, T: float, now: float | None = None) -> float | None:
    """تذبذبُ النقود في أجل: وسيطُ تذبذب أقرب أربعة عقودٍ إلى السعر شراءً وبيعاً — مرجعٌ يُستبعد به سعرُ الأطراف الشاذّ."""
    ivs = []
    for rows, call in ((ch.get("calls") or [], True), (ch.get("puts") or [], False)):
        for o in sorted((o for o in rows if o.get("strike")), key=lambda o: abs(o["strike"] - S))[:4]:
            q = quote(o, S, T, call, now)
            if q:
                ivs.append(q["iv"])
    if len(ivs) < 2:
        return None
    ivs.sort()
    n = len(ivs)
    return ivs[n // 2] if n % 2 else (ivs[n // 2 - 1] + ivs[n // 2]) / 2


def prob_beyond(S: float, level: float, T: float, iv: float, call: bool, r: float = RATE) -> float:
    """احتمالُ أن يكون السعرُ عند الانتهاء فوق `level` (للشراء) أو دونه (للبيع) في توزيعٍ لوغاريتميّ بتذبذبٍ ضمنيّ `iv`."""
    if level <= 0:
        return 1.0 if call else 0.0
    d2 = (math.log(S / level) + (r - iv * iv / 2) * T) / (iv * math.sqrt(T))
    return _ncdf(d2) if call else _ncdf(-d2)


def trend_of(bars: list[dict]) -> dict | None:
    """المسارُ من الشموع اليومية: الإغلاقُ ومتوسّطا 50 و200 وميلُ 50 (عشرون جلسة) وتغيّرُ ثلاثة أشهر وأعلى السنة وأدناها."""
    cl = [float(b["close"]) for b in bars if isinstance(b.get("close"), (int, float)) and b["close"] > 0]
    if len(cl) < 210 or cl[-1] < MIN_PRICE:
        return None
    sma = lambda k, end=None: sum(cl[:end][-k:]) / k   # noqa: E731
    c, s50, s200 = cl[-1], sma(50), sma(200)
    s50_prev = sma(50, -20)
    slope = (s50 / s50_prev - 1) * 100
    r3m = (c / cl[-64] - 1) * 100
    hi, lo = max(cl[-252:]), min(cl[-252:])
    hi60, lo60, hi120, lo120 = max(cl[-60:]), min(cl[-60:]), max(cl[-120:]), min(cl[-120:])
    # المسارُ الرئيسيّ: ترتيبُ المتوسّطين بفرقٍ فوق 1٪ وميلُ متوسّط 50 فوق 0.3٪ في عشرين جلسة والإغلاقُ على جهة 200 —
    # والتذبذبُ حول متوسّطٍ واحدٍ ليس مساراً. (والارتدادُ إلى ما دون متوسّط 50 في مسارٍ قائمٍ لا يلغيه — قيس 2026-11-17: اشتراطُه
    # جعل 47 من 76 رمزاً «عرضيّاً» منها ما مسارُه بيّن)
    if s50 > s200 * 1.01 and slope > 0.3 and c > s200:
        state = "صاعد"
    elif s50 < s200 * 0.99 and slope < -0.3 and c < s200:
        state = "هابط"
    else:
        state = "عرضي"
    strength = abs(slope) + abs(r3m) / 4 + abs(c / s200 - 1) * 20
    return {"close": round(c, 2), "sma50": round(s50, 2), "sma200": round(s200, 2), "slope50": round(slope, 2), "ret3m": round(r3m, 1),
            "hi52": round(hi, 2), "lo52": round(lo, 2), "hi60": round(hi60, 2), "lo60": round(lo60, 2), "hi120": round(hi120, 2),
            "lo120": round(lo120, 2), "state": state, "strength": round(strength, 2)}


def direction(tr: dict, news: dict | None) -> tuple[str | None, str]:
    """اتجاهُ الصفقة: من المسار، والخبرُ القويُّ (قوّة 2 فأكثر) المعاكسُ له يُسقطها، والقويُّ جداً (3) يعطي العرضيَّ اتجاهَه."""
    base = "call" if tr["state"] == "صاعد" else "put" if tr["state"] == "هابط" else None
    imp = {"إيجابي": 1, "سلبي": -1}.get(str((news or {}).get("impact") or ""), 0)
    st = int((news or {}).get("strength") or 0)
    if base and imp and st >= 2 and (imp > 0) != (base == "call"):
        return None, f"الأخبار {'إيجابية' if imp > 0 else 'سلبية'} قويّة تعاكس المسار {tr['state']} — لا صفقة"
    if base is None and imp and st >= 3:
        return ("call" if imp > 0 else "put"), "المسارُ عرضيّ والحدثُ قويٌّ جداً — الاتجاهُ من الخبر"
    if base is None:
        return None, "المسارُ عرضيّ — لا اتجاهَ يُشترى له عقد"
    return base, ""


def target_for(tr: dict, S: float, call: bool, iv: float, T: float) -> tuple[float, str]:
    """الهدفُ الفنيُّ على أفق العقد: أبعدُ قمّةٍ (للشراء) أو قاعٍ (للبيع) — أعلى 60 جلسة · 120 · السنة — يبعد 5٪ فأكثر ويقع ضمن الحركة
    المتوقّعة بانحرافٍ واحدٍ حتى الانتهاء (فالعقدُ الطويلُ يُقاس بما يبلغه السهمُ في أجله، لا بأقرب قمّة)؛ وإن تجاوزت القممُ ذلك المدى
    أو كان السهمُ عند قممه فالهدفُ حدُّ الحركة المتوقّعة نفسُه."""
    if call:
        cap = S * math.exp(iv * math.sqrt(T))
        lv = [(v, n) for n, v in (("أعلى 60 جلسة", tr.get("hi60")), ("أعلى 120 جلسة", tr.get("hi120")), ("قمّة السنة", tr.get("hi52")))
              if v and S * 1.05 <= v <= cap]
        if lv:
            v, n = max(lv)
            return round(v, 2), n
        return round(cap, 2), "حركةٌ متوقّعةٌ بانحرافٍ واحد"
    cap = S * math.exp(-iv * math.sqrt(T))
    lv = [(v, n) for n, v in (("أدنى 60 جلسة", tr.get("lo60")), ("أدنى 120 جلسة", tr.get("lo120")), ("قاع السنة", tr.get("lo52")))
          if v and cap <= v <= S * 0.95]
    if lv:
        v, n = min(lv)
        return round(v, 2), n
    return round(cap, 2), "حركةٌ متوقّعةٌ بانحرافٍ واحد"


def evaluate(o: dict, S: float, dte: int, call: bool, tr: dict, ref_iv: float | None, now: float | None = None,
             rules: dict | None = None) -> tuple[dict | None, str]:
    """حكمُ عقدٍ واحدٍ للمحفظة الطويلة: (البطاقة، أو None وسببُ الاستبعاد).
    الشروطُ كلُّها صريحة: عرضٌ وطلبٌ حقيقيّان (حيّان أو من آخر جلسة — لا آخرُ صفقة)، وفارقٌ ≤ 10٪ من الوسط، واهتمامٌ مفتوح ≥ 100،
    ودلتا بين 0.30 و0.85 (لا يانصيب ولا عميقٌ غالٍ)، وتذبذبٌ في نطاق النقود، ونقطةُ تعادلٍ دون الهدف الفنيّ وعائدٌ عنده ≥ 0.75 من الكلفة.
    و‏`rules` (‏D763 — صقر) تبدّل العتباتِ لأفقٍ آخر: ‏min_oi · max_spread · min_delta · max_delta · min_rr · min_pop."""
    R = {"min_oi": MIN_OI, "max_spread": MAX_SPREAD, "min_delta": MIN_DELTA, "max_delta": MAX_DELTA, "min_rr": MIN_RR, "min_pop": MIN_POP,
         **(rules or {})}
    T = max(dte, 1) / 365
    K = o.get("strike")
    if not K:
        return None, "بلا سعر تنفيذ"
    q = quote(o, S, T, call, now, allow_last=False)
    if not q:
        return None, "لا عرضَ ولا طلبَ حقيقيّين"
    if (o.get("oi") or 0) < R["min_oi"]:
        return None, "اهتمامٌ مفتوحٌ قليل"
    if q["spread"] is None or q["spread"] > R["max_spread"]:
        return None, "الفارقُ بين العرض والطلب واسع"
    px, iv = q["px"], q["iv"]
    if px < MIN_PX or (ref_iv and not (IV_BAND[0] * ref_iv <= iv <= IV_BAND[1] * ref_iv)):
        return None, "سعرٌ شاذّ"
    delta = bs_delta(S, K, T, iv, call)
    if not (R["min_delta"] <= abs(delta) <= R["max_delta"]):
        return None, "الدلتا خارج النطاق"
    tgt, tlabel = target_for(tr, S, call, ref_iv or iv, T)
    be = K + px if call else K - px
    if (call and be >= tgt) or (not call and be <= tgt):
        return None, "التعادلُ أبعدُ من الهدف"
    pay = ((tgt - K) if call else (K - tgt)) * 100 - px * 100
    rr = pay / (px * 100)
    if rr < R["min_rr"]:
        return None, "العائدُ عند الهدف ضئيل"
    pop = prob_beyond(S, be, T, iv, call)
    if pop < R["min_pop"]:
        return None, "احتمالٌ ضئيل"
    p_touch = min(1.0, 2 * prob_beyond(S, tgt, T, iv, call))
    mid = (q["px"] + (o.get("bid") or o.get("sbid") or 0)) / 2
    oi = o.get("oi") or 0
    score = 35 * pop + 25 * min(rr, 3) / 3 + 15 * p_touch + 10 * min(oi, 2000) / 2000 + 10 * (1 - q["spread"] / R["max_spread"]) + 5 * min(dte, 365) / 365
    bid = o.get("bid") if q["src"] == "ask" else o.get("sbid")
    return {"contract": o.get("contract"), "type": "call" if call else "put", "strike": K, "ask": px, "bid": bid, "mid": round(mid, 3),
            "px_src": q["src"], "quote_at": o.get("sat") if q["src"] == "snap" else None,
            "cost": round(px * 100, 2), "spread_pct": round(q["spread"] * 100, 1), "spread_usd": round((px - (bid or 0)) * 100, 2),
            "dte": dte, "breakeven": round(be, 2), "need_pct": round(((be / S - 1) if call else (1 - be / S)) * 100, 1),
            "target": tgt, "target_label": tlabel, "rr": round(rr, 2), "pop": round(pop * 100, 1), "p_touch": round(p_touch * 100, 1),
            "delta": round(delta, 2), "iv": round(iv * 100, 1), "oi": oi, "volume": o.get("volume"), "score": round(score, 2)}, ""


def candidates(rows: list[dict], S: float, dte: int, call: bool, tr: dict, ref_iv: float | None = None, now: float | None = None,
               rules: dict | None = None) -> list[dict]:
    """بطاقاتُ أجلٍ واحدٍ الصالحةُ بلا قيد الميزانية."""
    return [c for c in (evaluate(o, S, dte, call, tr, ref_iv, now, rules)[0] for o in rows) if c]


def pick_contract(rows: list[dict], S: float, dte: int, call: bool, budget: float, tr: dict, ref_iv: float | None = None,
                  now: float | None = None) -> dict | None:
    """أفضلُ عقدٍ في أجلٍ واحدٍ ضمن الميزانية (سعرُ الطلب × 100): أعلى درجةٍ بين الصالحين."""
    ok = [c for c in candidates(rows, S, dte, call, tr, ref_iv, now) if c["cost"] <= budget]
    return max(ok, key=lambda c: c["score"]) if ok else None


def exit_date(expiry: str) -> str:
    try:
        return (datetime.fromisoformat(expiry) - timedelta(days=EXIT_DTE)).date().isoformat()
    except ValueError:
        return ""


def reasons(sym: str, tr: dict, news: dict | None, k: dict, note: str) -> list[str]:
    """المبرّرُ بالعربية: الأطروحةُ (المسارُ والخبر)، ولماذا هذا التنفيذُ وهذا الأجل، والفارق، والاحتمالات، وخطّةُ الخروج."""
    pos = lambda v, ref: "فوق" if v > ref else "دون"   # noqa: E731
    call = k["type"] == "call"
    out = [f"الأطروحة: المسار {tr['state']} — الإغلاق {tr['close']:,.2f} {pos(tr['close'], tr['sma50'])} متوسّط 50 ({tr['sma50']:,.2f}) "
           f"و{pos(tr['close'], tr['sma200'])} متوسّط 200 ({tr['sma200']:,.2f})، وتغيّرُ ثلاثة أشهر {tr['ret3m']:+.1f}٪."]
    if news and news.get("event"):
        out.append(f"الأخبار ({news.get('impact') or 'محايد'}): {news['event']}")
    elif news is not None:
        out.append("الأخبار: لا حدثَ مؤثّراً في عناوين الأيام العشرة الأخيرة.")
    else:
        out.append("الأخبار: قراءتُها غيرُ متوفّرة الآن — الاختيارُ على المسار وحده.")
    if note:
        out.append(note + ".")
    out.append(f"الهدفُ الفنيّ {k['target']:,.2f} ({k['target_label']})، ونقطةُ التعادل {k['breakeven']:,.2f} ({k['need_pct']:+.1f}٪ من السعر) "
               f"{'دونه' if call else 'فوقه'} — إن بلغه السهمُ عند الانتهاء ربح العقدُ {k['rr']:.1f} ضعفَ كلفته، ومع الوقف عند نصف الكلفة "
               f"فالعائدُ إلى المخاطرة {k['rr'] * 2:.1f} إلى 1.")
    out.append(f"لماذا تنفيذ {k['strike']:g}: أعلى درجةٍ بين العقود السائلة ضمن ميزانيتك (احتمالُ الربح والعائدُ عند الهدف واحتمالُ لمسه والسيولةُ والفارق) "
               f"بدلتا {k['delta']:+.2f} — لا بعيدٌ كاليانصيب ولا عميقٌ غالٍ.")
    out.append(f"الأجل {k['dte']} يوماً: التآكلُ الزمنيُّ بطيءٌ والوقتُ كافٍ لتتحقّق الأطروحة.")
    q = "من آخر جلسة" + (f" ({k['quote_at'][:16].replace('T', ' ')})" if k.get("quote_at") else "") if k.get("px_src") == "snap" else "حيّان"
    out.append(f"الفارقُ بين العرض والطلب {k['spread_usd']:,.0f} دولار للعقد ({k['spread_pct']:.0f}٪) — العرضُ والطلبُ {q}.")
    out.append(f"احتمالُ الربح عند الانتهاء نحو {k['pop']:.0f}٪ واحتمالُ لمس الهدف قبله نحو {k['p_touch']:.0f}٪ — تقديرٌ من التذبذب الضمنيّ "
               f"({k['iv']:.0f}٪) لا وعد، والاهتمامُ المفتوح {k['oi']:,}.")
    out.append(f"خطّةُ الخروج: وقفٌ إن هبط العقدُ إلى نصف كلفته، وجنيٌ عند بلوغ السهمِ الهدفَ أو تضاعفِ العقد، وخروجٌ قبل {EXIT_DTE} يوماً "
               f"من الانتهاء ({exit_date(k.get('expiry') or '')}) — وأقصى الخسارة كلفةُ العقد {k['cost']:,.0f} دولار.")
    return out


# ══ المراحل ══

async def scan() -> dict:
    """المرحلةُ الأولى (تُخبَّأ ستّ ساعات): مسارُ كلّ رمزٍ في القائمة من شموعه اليومية."""
    from app.services import cache
    from app.services.market_data import market_service as M
    hit = cache.get("optpicks:scan:v3")
    if hit:
        return hit
    sem = asyncio.Semaphore(6)

    async def one(s):
        async with sem:
            try:
                bars = await asyncio.wait_for(M.get_bars(s, "1d"), 25) or []
            except Exception:                                     # noqa: BLE001
                return s, None
        return s, trend_of(bars)
    out = {s: t for s, t in await asyncio.gather(*(one(s) for s in UNIVERSE)) if t}
    if len(out) >= 10:
        cache.set("optpicks:scan:v3", out, SCAN_TTL)
    return out


async def headlines(sym: str, days: int = 10) -> list[dict]:
    """عناوينُ السهم في الأيام العشرة الأخيرة من محرّك ياهو — العنوانُ والناشرُ والوقت."""
    from app.services.options_chain import _get
    d = await _get("/v1/finance/search", {"q": sym, "newsCount": 10, "quotesCount": 0, "enableFuzzyQuery": "false"})
    floor = time.time() - days * 86400
    out = []
    for n in (d or {}).get("news") or []:
        t = n.get("providerPublishTime")
        if n.get("title") and isinstance(t, (int, float)) and t >= floor:
            out.append({"title": n["title"], "publisher": n.get("publisher"), "at": datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat(),
                        "link": n.get("link")})
    return out[:8]


READ_NEWS = """أنت محلّلُ أسهمٍ أمريكيّ. لكلّ رمزٍ أدناه مسارُه الفنّيّ وعناوينُ أخباره في الأيام العشرة الأخيرة.
اقرأ العناوين وحدها — لا تُضف معلومةً من خارجها — وقدّر أثرَها على السهم في الأشهر القادمة:
- impact: "إيجابي" أو "سلبي" أو "محايد"
- strength: 0 (لا حدث) · 1 (أثرٌ طفيف) · 2 (حدثٌ مهمّ: نتائجُ مفاجئة، ترقيةٌ أو تخفيضٌ مؤثّر، صفقةٌ كبيرة) · 3 (حدثٌ جوهريّ: استقالةُ رئيسٍ تنفيذيّ، تحقيقٌ أو دعوى كبرى، خسارةُ عميلٍ رئيسيّ، استحواذ)
- event: جملةٌ عربيةٌ قصيرةٌ تذكر الحدثَ كما في العنوان وتاريخَه (أو "" إن لا حدث)
JSON فقط بهذا الشكل: {"SYM": {"impact": "...", "strength": 0, "event": "..."}} — واذكر الرموزَ ذاتَ الحدث وحدها؛ ومن لم تذكره فلا حدثَ له.

"""


async def read_news(items: dict[str, dict]) -> dict:
    """المرحلةُ الثانية: عناوينُ كلّ الرموز (فالعرضيُّ قد يأخذ اتجاهَه من حدثٍ جوهريّ) يقرؤها النموذجُ دفعاتٍ من ثلاثين، وتُخبَّأ ساعتين لكلّ رمز.
    وإن تعذّر النموذجُ لدفعةٍ فقراءةُ رموزها «غير متوفّرة» (None)."""
    from app.services import cache
    from app.services import research_desk as RD
    out, todo = {}, {}
    for s, tr in items.items():
        hit = cache.get(f"optpicks:news:{s}")
        if hit is not None:
            out[s] = hit
        else:
            todo[s] = tr
    if not todo:
        return out
    sem = asyncio.Semaphore(8)

    async def head(s):
        async with sem:
            try:
                return await asyncio.wait_for(headlines(s), 20)
            except Exception:                                     # noqa: BLE001
                return []
    heads = dict(zip(todo, await asyncio.gather(*(head(s) for s in todo))))

    async def ask(chunk):
        lines = []
        for s in chunk:
            tr, h = todo[s], heads.get(s) or []
            lines.append(f"{s} — المسار {tr['state']} (تغيّر 3 أشهر {tr['ret3m']:+.1f}٪):\n"
                         + ("\n".join(f"  [{x['at']}] {x['title']} ({x.get('publisher') or ''})" for x in h) or "  لا عناوين"))
        try:
            return await RD._gemini([{"text": READ_NEWS + "\n\n".join(lines)}], max_tokens=4000, temperature=0.1)
        except Exception as e:                                    # noqa: BLE001
            logger.warning("مُنتقي الخيارات: قراءة الأخبار {}", type(e).__name__)
            return None
    keys = list(todo)
    chunks = [keys[i:i + 30] for i in range(0, len(keys), 30)]
    read = {}          # الرمزُ ← قراءتُه، لمن قُرئت دفعتُه وحدَه؛ ودفعةٌ تعذّرت فرموزُها «غير متوفّرة» ولا تُخبَّأ
    for chunk, got in zip(chunks, await asyncio.gather(*(ask(c) for c in chunks))):
        if isinstance(got, dict):
            read.update({s: got.get(s) for s in chunk})
    for s in todo:
        h = heads.get(s) or []
        if s not in read:
            out[s] = None
            continue
        r = read[s]
        r = r if isinstance(r, dict) else {}
        rec = {"impact": r.get("impact") if r.get("impact") in ("إيجابي", "سلبي", "محايد") else "محايد",
               "strength": max(0, min(3, int(r.get("strength") or 0))) if str(r.get("strength") or "0").isdigit() else 0,
               "event": str(r.get("event") or "")[:220] if h else "", "headlines": h[:3]}
        out[s] = rec
        cache.set(f"optpicks:news:{s}", rec, NEWS_TTL)
    return out


def pick_expiries(exps: list[dict]) -> list[dict]:
    """آجالٌ تمثّل المدى الطويل: الأقربُ بعد 150 يوماً ونحو ثمانية أشهر ونحو سنةٍ والأبعدُ ضمن 430."""
    win = [e for e in exps if MIN_DTE <= e["dte"] <= MAX_DTE]
    out = []
    for target in (MIN_DTE, 240, 330, MAX_DTE):
        if win:
            e = min(win, key=lambda x: abs(x["dte"] - target))
            if e not in out:
                out.append(e)
    return out


async def contracts_for(sym: str, call: bool, budget: float, tr: dict) -> tuple[dict | None, float | None]:
    """المرحلةُ الثالثة لرمزٍ واحد: آجالُه الطويلة، وأفضلُ عقدٍ ضمن الميزانية فيها — ومعه كلفةُ أرخصِ عقدٍ صالحٍ فيها كلِّها
    ليُقال للمالك بكم يُفتح هذا السهمُ إن لم يكن ضمن ميزانيته."""
    from app.services.options_chain import chain
    base = await chain(sym)
    if not base or not base.get("price"):
        return None, None
    best, cheapest = None, None
    for e in pick_expiries(base.get("expirations") or []):
        ch = await chain(sym, e["t"])
        if not ch:
            continue
        S = float(ch["price"] or base["price"])
        ref = atm_iv(ch, S, max(e["dte"], 1) / 365)
        if ref is None:          # لا مرجعَ لتذبذب النقود في هذا الأجل — فلا يُوثق بسعر أطرافه
            continue
        for k in candidates(ch["calls"] if call else ch["puts"], S, e["dte"], call, tr, ref_iv=ref):
            cheapest = k["cost"] if cheapest is None else min(cheapest, k["cost"])
            if k["cost"] <= budget and (best is None or k["score"] > best["score"]):
                best = {**k, "expiry": e["date"], "t": e["t"]}
    if best:
        best.update(symbol=sym, name=base.get("name"), price=base.get("price"))
    return best, cheapest


# ══ دفترُ التوصيات القائمة — الذاكرة ══
# كان كلُّ بحثٍ يرتّب من الصفر فتتبدّل القائمةُ كلَّ يوم (المالك 2026-11-18: «أمس ميزانية 150 وظهرت خيارات… واليوم اختلفت كاملة،
# وهي طويلةُ المدى — كيف نضع فلوساً في عقدٍ تذهب جاذبيتُه في اليوم التالي؟»). فالتوصيةُ تبقى في الدفتر بتاريخها وسعرِ دخولها
# وأطروحتها حتى تنكسر قاعدةُ خروجٍ مكتوبة، ولا يدخل جديدٌ إلا في مقعدٍ شاغرٍ ومن مسارٍ قائم.

def _book_path() -> str:
    d = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "optpicks")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "book.json")


def book_load(budget: float) -> dict:
    try:
        all_ = json.load(open(_book_path(), encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        all_ = {}
    b = all_.get(str(int(budget))) or {}
    b.setdefault("open", [])
    b.setdefault("closed", [])
    return b


def book_save(budget: float, b: dict) -> None:
    try:
        all_ = json.load(open(_book_path(), encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        all_ = {}
    all_[str(int(budget))] = b
    tmp = _book_path() + ".tmp"
    json.dump(all_, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, _book_path())


def book_budgets() -> list[int]:
    try:
        return sorted(int(k) for k in json.load(open(_book_path(), encoding="utf-8")))
    except Exception:                                             # noqa: BLE001
        return []


def verdict(e: dict, S: float | None, mid: float | None, dte: int, tr: dict | None, news: dict | None) -> tuple[str, str]:
    """قاعدةُ الخروج لتوصيةٍ قائمة: (الحال، السبب). الحالات: hold · profit · stop · broken · time — والأطروحةُ لا تنكسر بتذبذبٍ يوميّ،
    بل بانقلاب المسار أو كسرِ متوسّط 200 بأكثر من 3٪ أو خبرٍ قويٍّ معاكس (ثبوتٌ مقصود: الدخولُ صارمٌ والخروجُ بقاعدة)."""
    call = e["type"] == "call"
    if dte <= EXIT_DTE:
        return "time", f"بقي {dte} يوماً على الانتهاء — يتسارع التآكلُ الآن: اخرج أو دحرج إلى أجلٍ أبعد."
    if mid is not None and e.get("entry_mid") and mid <= e["entry_mid"] * STOP_FRAC:
        return "stop", f"هبط العقدُ إلى {mid:.2f} — نصفُ سعر الدخول ({e['entry_mid']:.2f}) أو دونه: بلغ الوقف."
    if S is not None and ((call and S >= e["target"]) or (not call and S <= e["target"])):
        return "profit", f"بلغ السهمُ الهدفَ {e['target']:,.2f} — اجنِ الربح."
    if mid is not None and e.get("entry_mid") and mid >= e["entry_mid"] * 2:
        return "profit", f"تضاعف العقدُ ({e['entry_mid']:.2f} ⇐ {mid:.2f}) — اجنِ الربح أو جزءاً منه."
    if tr:
        flip = tr["state"] == ("هابط" if call else "صاعد")
        broke = tr["close"] < tr["sma200"] * 0.97 if call else tr["close"] > tr["sma200"] * 1.03
        imp = {"إيجابي": 1, "سلبي": -1}.get(str((news or {}).get("impact") or ""), 0)
        against = imp and int((news or {}).get("strength") or 0) >= 2 and (imp > 0) != call
        if flip or broke or against:
            why = "انقلب المسارُ " + tr["state"] if flip else (f"كسر السهمُ متوسّط 200 ({tr['sma200']:,.2f}) بأكثر من 3٪" if broke
                                                              else f"خبرٌ قويٌّ معاكس: {(news or {}).get('event') or ''}")
            return "broken", f"انكسرت الأطروحة: {why} — اخرج."
    return "hold", "الأطروحةُ سليمة — احتفظ."


STATUS_AR = {"hold": "قائمة", "profit": "اجنِ الربح", "stop": "بلغ الوقف", "broken": "انكسرت الأطروحة", "time": "اقترب الأجل"}


async def _mark(e: dict) -> tuple[float | None, float | None, int]:
    """سعرُ السهم ووسطُ العقد (حيّاً أو من آخر جلسة أو آخرُ صفقة) والأيامُ الباقية لتوصيةٍ قائمة."""
    from app.services.options_chain import chain
    dte = max(0, (datetime.fromisoformat(e["expiry"]).date() - datetime.now(timezone.utc).date()).days)
    ch = await chain(e["symbol"], e.get("t")) if e.get("t") else None
    if not ch:
        return None, None, dte
    S = float(ch.get("price") or 0) or None
    row = next((r for r in ch["calls" if e["type"] == "call" else "puts"] if r.get("contract") == e["contract"]), None)
    mid = None
    if row:
        b, a = (row.get("bid") or 0), (row.get("ask") or 0)
        if not (a > 0 and b > 0):
            b, a = (row.get("sbid") or 0), (row.get("sask") or 0)
        mid = (a + b) / 2 if a > 0 and b > 0 else (row.get("last") or None)
    return S, mid, dte


async def run(budget: float) -> dict:
    """التوصياتُ لميزانيةٍ بعينها: يُراجَع الدفترُ القائمُ بقواعد خروجه أوّلاً، ثمّ تُملأ المقاعدُ الشاغرةُ من مساراتٍ قائمة —
    وتُخبَّأ النتيجةُ نصفَ ساعة."""
    from app.services import cache
    _JOB.update(on=True, budget=budget, msg="قراءةُ المسارات", at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    try:
        sc = await scan()
        top = dict(sorted(sc.items(), key=lambda kv: -kv[1]["strength"]))
        _JOB["msg"] = "قراءةُ الأخبار"
        news = await read_news(top)
        book = book_load(budget)
        today = datetime.now(timezone.utc).date().isoformat()

        # ١ مراجعةُ القائمة: كلُّ توصيةٍ بقاعدة خروجها
        _JOB["msg"] = "مراجعةُ التوصيات القائمة"
        keep, exits = [], []
        for e in book["open"]:
            S, mid, dte = await _mark(e)
            st, why = verdict(e, S, mid, dte, sc.get(e["symbol"]), news.get(e["symbol"]))
            e["last"] = {"date": today, "mid": round(mid, 3) if mid else None, "price": S, "dte": dte, "status": st, "why": why,
                         "pl_pct": round((mid / e["entry_mid"] - 1) * 100, 1) if mid and e.get("entry_mid") else None}
            (keep if st == "hold" else exits).append(e)
        for e in exits:
            e["closed"] = today
        book["open"] = keep
        book["closed"] = (exits + book["closed"])[:40]

        # ٢ المقاعدُ الشاغرة: من مساراتٍ قائمةٍ لا توصيةَ قائمةَ على سهمها — ولا عودةَ إلى سهمٍ خرج بوقفٍ أو انكسارٍ قبل أسبوع
        #    (وإلا عاد إليه في الجلسة نفسِها فتذبذبت القائمة)؛ والخروجُ لاقتراب الأجل يُدحرَج إلى أجلٍ أبعد فلا حجرَ عليه
        held = {e["symbol"] for e in keep}
        wk = (datetime.now(timezone.utc).date() - timedelta(days=COOL_DAYS)).isoformat()
        held |= {e["symbol"] for e in book["closed"] if (e.get("closed") or "") > wk and e["last"]["status"] in ("stop", "broken", "profit")}
        plan, skipped = [], []
        for s, tr in top.items():
            if s in held:
                continue
            side, note = direction(tr, news.get(s))
            if side:
                plan.append((s, tr, side, note))
            elif note:
                skipped.append({"symbol": s, "why": note})
        plan = plan[:CANDIDATES]
        _JOB["msg"] = "البحثُ في العقود"
        sem = asyncio.Semaphore(4)

        async def one(p):
            s, tr, side, note = p
            async with sem:
                try:
                    k, low = await asyncio.wait_for(contracts_for(s, side == "call", budget, tr), 90)
                except Exception:                                 # noqa: BLE001
                    k, low = None, None
            if not k:
                kind = "شراء" if side == "call" else "بيع"
                skipped.append({"symbol": s, "min_cost": low, "why": (f"أرخصُ عقد {kind} يستوفي الشروط كلفتُه {low:,.0f} دولار — فوق الميزانية"
                                                                      if low else f"لا عقدَ {kind} طويلَ الأجل يستوفي الشروط (فارقٌ ≤ 10٪ · سيولة · دلتا · هدف)")})
                return None
            return {**k, "trend": tr, "news": news.get(s), "note": note}
        fresh = sorted([x for x in await asyncio.gather(*(one(p) for p in plan)) if x], key=lambda x: -x["score"])
        for k in fresh:
            if len(book["open"]) >= MAX_OPEN:
                break
            if k["score"] < NEW_MIN:
                skipped.append({"symbol": k["symbol"], "why": f"أفضلُ عقدٍ له دون عتبة الدخول (درجة {k['score']:.0f} من 100)"})
                continue
            book["open"].append({"contract": k["contract"], "symbol": k["symbol"], "name": k.get("name"), "type": k["type"], "strike": k["strike"],
                                 "expiry": k["expiry"], "t": k["t"], "opened": today, "entry_mid": k["mid"], "entry_ask": k["ask"],
                                 "target": k["target"], "target_label": k["target_label"],
                                 "thesis": {"state": k["trend"]["state"], "close": k["trend"]["close"], "sma200": k["trend"]["sma200"]},
                                 "card": {**{x: k[x] for x in k if x not in ("trend", "news", "note")},
                                          "reasons": reasons(k["symbol"], k["trend"], k["news"], k, k["note"])},
                                 "last": {"date": today, "mid": k["mid"], "price": k.get("price"), "dte": k["dte"], "status": "hold",
                                          "why": "توصيةٌ جديدة اليوم.", "pl_pct": 0.0}})
        book_save(budget, book)

        picks = [{**e["card"], "symbol": e["symbol"], "name": e.get("name"), "opened": e["opened"], "status": "hold",
                  "new": e["opened"] == today, "pl_pct": e["last"].get("pl_pct"), "mid_now": e["last"].get("mid"), "entry_mid": e["entry_mid"],
                  "dte": e["last"].get("dte", e["card"]["dte"]), "status_why": e["last"].get("why"),
                  "trend": {"state": e["thesis"]["state"]}} for e in book["open"]]
        recent = [{"contract": e["contract"], "symbol": e["symbol"], "type": e["type"], "opened": e["opened"], "closed": e.get("closed"),
                   "status": e["last"]["status"], "status_ar": STATUS_AR[e["last"]["status"]], "why": e["last"]["why"],
                   "pl_pct": e["last"].get("pl_pct")} for e in book["closed"][:8]]
        skipped.sort(key=lambda x: (x.get("min_cost") is None, x.get("min_cost") or 0))
        try:                                                      # حالُ السوق الأمريكيّ: مغلقٌ بلا عرضٍ وطلبٍ محفوظين ⇒ القائمةُ تُبنى عند الافتتاح
            from app.services.live_quote import sessions
            us = (await sessions())["us"]
        except Exception:                                         # noqa: BLE001
            us = None
        res = {"budget": budget, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "picks": picks, "exits": recent, "us_session": us,
               "closed": any(p.get("px_src") == "snap" for p in picks), "skipped": skipped[:30], "scanned": len(sc),
               "news_ok": any(v is not None for v in news.values()),
               "limits": {"min_dte": MIN_DTE, "max_dte": MAX_DTE, "min_oi": MIN_OI, "max_spread": int(MAX_SPREAD * 100)}}
        cache.set(f"optpicks:res2:{int(budget)}", res, RES_TTL)
        return res
    finally:
        _JOB.update(on=False, msg="")


def cached(budget: float) -> dict | None:
    from app.services import cache
    return cache.get(f"optpicks:res2:{int(budget)}")
