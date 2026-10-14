"""
Automatic company scoring — no manual "run analysis" button.

Runs at startup and on the daily scheduler: for every active company it
computes a finance score and a technical score and persists them, plus
sharia status and a logo from the Sahmak monthly library when available.
All inputs come through the cached provider layer, so a full pass costs
at most one call per company per cache window — quota-safe by
construction.

The finance score is derived from the SAME multi-year financial
statements shown on the company's governance page (get_financials) —
not a separate single-snapshot heuristic — so the score the AI assigns
is always explainable by the numbers the investor is actually looking
at, and reflects the company's balance-sheet safety from real risk, not
its share-price mood. See `_finance_score_from_periods` for the six
signals it weighs.
"""

from loguru import logger

# Yahoo returns GICS sector names in English; translate the common ones so
# the sector always matches the site's Arabic — same table as the frontend's
# StockLookup.tsx sectorAr() for consistency across the app.
_SECTOR_AR = {
    "Energy": "الطاقة", "Basic Materials": "المواد الأساسية", "Materials": "المواد الأساسية",
    "Industrials": "الصناعات", "Consumer Cyclical": "السلع الكمالية", "Consumer Defensive": "السلع الأساسية",
    "Financial Services": "الخدمات المالية", "Financials": "الخدمات المالية", "Healthcare": "الرعاية الصحية",
    "Technology": "التقنية", "Communication Services": "الاتصالات", "Utilities": "المرافق العامة", "Real Estate": "العقارات",
}
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Company


# ══ لا استثناءَ قطاعيّ — والقياسُ هو الذي حكم ══ (D154 · D155)
# جُرِّب استثناءان: إعفاءُ الصناديق العقارية من هامش التدفّق الحرّ،
# وقياسُ عائد الدوريّة عبر الدورة. وقِيسا على ‎268 شركةً حقيقية:
#
#   · الإعفاءُ يحسم من الصناديق سبعَ نقاطٍ — تدفّقُها الحرُّ موجبٌ
#     بوسيطٍ ‎+67.9٪، ولا واحدةَ من التسعَ عشرةَ سالبةٌ في كلّ سنواتها.
#   · وقياسُ الدورة أثرُه ‎+1.0 و‎0.0 — دون عتبةِ الخمسِ نقاطٍ التي
#     اشترطناها لأيّ تعديل.
#
# وكلاهما بُني على عيّنةٍ صنعناها بأيدينا فأكّدت فرضيتَها بدل أن
# تختبرها. فأُلغيا معاً: **الشرطُ واحدٌ ولا استثناءَ لتعديلٍ أعجبنا**.
#
# والقطاعُ ما يزال مؤثّراً حيث يثبته الدليل: البنوكُ والتأمين تُعفى من
# ثلاثِ إشاراتٍ — لكن **باستدلالٍ من البيانات** (لا مصروفَ فوائدَ عبر
# السلسلة مع مديونيةٍ عالية) لا باسمِ قطاعٍ مكتوب.
#
# والبابُ مفتوح: `sector_probe.py` يقيس، فإن بلغ عطبٌ خمسَ نقاطٍ
# وكان سببُه بنيوياً، عاد التعديلُ بدليله.


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


# ══ المقياسُ يُعايَر على عتباتٍ مهنية لا على خطٍّ مستقيم ══ (D162)
# كانت الإشاراتُ الستُّ كلُّها من صيغة `50 + قيمة × معامل`: الصفرُ خمسون،
# ثمّ ارتفاعٌ خطّيّ. فكان السقفُ يستلزم — في الشركة الواحدة معاً — نموّاً
# ‎٢٠٪ سنوياً، وتحويلَ كلِّ ريال ربحٍ إلى **ريالَي** نقد، ومديونيةً ‎١٠٪،
# وتغطيةَ فوائدَ ‎١٢٫٥ ضعفاً. ولا شركةَ قياديةٌ في السوق تجمعها، فتكدّست
# الشركاتُ القويّة عند السبعين وصار «الممتاز» يُقرأ «متوسّطاً».
#
# فصار لكلِّ إشارةٍ منحنىً بعُقَدٍ مأخوذةٍ من عتباتِ التحليل المالي
# المعروفة لا من خطٍّ مخترَع: عائدُ حقوقِ الملكية ‎١٥٪ عتبةُ الجودة،
# وتغطيةُ الفوائدِ ‎٥ أضعافٍ عتبةُ الأمان، والتدفّقُ التشغيليُّ المساوي
# للربح تغطيةٌ كاملة. من بلغ العتبةَ نال درجةَ العتبة — لا خمسين.
#
# والمعايرةُ مطلقةٌ لكلّ الشركات: عتباتٌ ماليةٌ عامّة، لا نِسَبٌ مئينيّةٌ
# مُفصَّلةٌ على محفظةٍ بعينها ولا استثناءَ لرمزٍ أو قطاع.


def _curve(value: float, anchors: list[tuple[float, float]]) -> int:
    """Piecewise-linear map from a real financial ratio to a 0–100 score.
    `anchors` is an ascending list of (ratio, score) knots; anything below
    the first or above the last knot flattens onto it."""
    if value <= anchors[0][0]:
        return anchors[0][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if value <= x1:
            return round(y0 + (value - x0) / (x1 - x0) * (y1 - y0))
    return anchors[-1][1]


# النموُّ السنويُّ المركَّب للإيراد ‎٪ — الثباتُ عند الصفر ليس فشلاً،
# والتضخّمُ الاسميُّ ‎٦٪ بدايةُ النموِّ الحقيقي.
_CURVE_REVENUE_CAGR = [(-20, 0), (-10, 20), (0, 45), (3, 60), (6, 72), (10, 82), (15, 90), (25, 97), (40, 100)]
# التدفّقُ التشغيليُّ ÷ صافي الربح — الواحدُ الصحيحُ تغطيةٌ كاملةٌ للربح بالنقد.
_CURVE_EARNINGS_QUALITY = [(0, 0), (0.4, 25), (0.7, 45), (0.9, 62), (1.0, 75), (1.2, 88), (1.5, 95), (2.0, 100)]
# هامشُ التدفّقِ النقديِّ الحرِّ ‎٪ من الإيراد.
_CURVE_FCF_MARGIN = [(-15, 0), (-5, 25), (0, 45), (3, 60), (7, 73), (12, 85), (18, 93), (30, 100)]
# العائدُ على حقوق الملكية ‎٪ — ‎١٥٪ عتبةُ الجودة و‎٢٠٪ التميّز.
_CURVE_ROE = [(-5, 0), (0, 25), (5, 45), (10, 62), (15, 76), (20, 87), (25, 93), (35, 100)]
# نسبةُ الدين إلى الأصول — خلوُّ الميزانيةِ من الدين ليس كمالاً مطلقاً.
_CURVE_DEBT_RATIO = [(0, 95), (0.15, 92), (0.30, 85), (0.45, 72), (0.60, 55), (0.75, 35), (0.90, 12), (1.0, 0)]
# تغطيةُ الفوائد أضعافاً — ‎٢ حدُّ الخطر و‎٥ عتبةُ الأمان و‎٨ قوّةٌ ظاهرة.
_CURVE_INTEREST_COVERAGE = [(0, 0), (1, 20), (2, 40), (3, 55), (5, 72), (8, 85), (12, 93), (20, 100)]
# ‏D703: نموُّ صافي الربح سنوياً ‎٪ (مقيَّدٌ ±200) — الثباتُ دون المنتصف، و‎١٠٪ نموٌّ قياديّ، والانهيارُ إلى النصف قاعٌ قريب.
_CURVE_NI_GROWTH = [(-100, 0), (-50, 10), (-20, 25), (0, 45), (5, 70), (10, 90), (20, 96), (40, 100)]

# ‏D703 · أوزانُ الدرجة بالنتيجة (بأمر المالك 2026-10-13: «كلُّ رقمٍ يظهر محلَّ ثقة… سواءٌ درجةٌ ماليةٌ أو سعرٌ عادل»):
# قِيست مكوّناتُها داخل كلّ قطاعٍ بما كان منشوراً منذ 2023 (‏fv_universe_d701 · 2,976 مشاهدة) — ارتباطُ الرتبة بالتفوّق بعد سنة:
#   نموُّ صافي الربح +0.07 و+0.07 (الأثبتُ — ولم يكن في الدرجة) · العائدُ على الحقوق +0.04 و+0.12 · تغطيةُ الفوائد +0.01 و+0.10 ·
#   نموُّ الإيراد +0.02 و+0.03 · وانخفاضُ المديونية لا يرفع العائدَ ويُنقص الخسارةَ الكبيرة في النصفين؛
#   وجودةُ الربح (−0.02 · +0.04) وهامشُ التدفّق الحرّ (−0.11 · +0.15) ينقلبان بين النظامين — فلا يُبنى عليهما وزن.
# الدرجةُ القديمة −0.04 و+0.13 داخل القطاع (−0.13 و+0.17 في السوق كلّه)، وهذه +0.055 و+0.076 (‏+0.014 و+0.079) — الوحيدةُ
# الموجبةُ في النصفين بالمقياسين بين ستّ أوزانٍ مجرَّبة. والخطوطُ الحمراءُ صفرٌ كما هي.
# ‏D720 (المالك 2026-10-14: «أرقامٌ ظالمة لا تنمّ عن صدق القوائم المالية»): كانت أوزانُ ‏D703 تقيس «هل يتفوّق السهمُ بعد سنة»
# لا «هل القوائمُ متينة» — فصافي ربح **سنةٍ واحدة** ‎35٪‎ من الدرجة، وجودةُ الربح بالنقد بلا وزن. وقِيس على الخادم
# (‏finance_score_door · run 38628527640): الاتّصالات ‎46‎ بعائدٍ على الحقوق ‎18٪‎ وربحٍ مغطًّى بالنقد ‎1.21‎ لأنّ ربحَ سنةٍ نزل ‎39٪‎،
# وأرامكو ‎56‎. فالدرجةُ **جودةُ القوائم**: ربحيّةٌ بمتوسّط ثلاث سنوات، ونموُّ ربحٍ وإيرادٍ **مركّبٌ عبر السنوات** لا سنةٌ واحدة،
# وربحٌ مغطًّى بالنقد، وميزانيةٌ ومديونيةٌ وتغطيةُ فوائد. وما يسبق السعرَ مكانُه محرّكُ القرار لا درجةُ الجودة.
FINANCE_WEIGHTS = {"revenue_growth": 0.15, "roe": 0.22, "ni_growth": 0.18, "debt": 0.15, "coverage": 0.15,
                   "earnings_quality": 0.15, "fcf_margin": 0.0}
# ‏D720: الريتُ ورقةٌ بنيتُها غيرُ بنية الشركة: يوزّع ‎90٪‎ من ربحه نظاماً، وربحُه المحاسبيّ يتقلّب بإعادة تقييم العقار، وشراءُ
# العقار يُقرأ «تدفّقاً حرّاً سالباً»، وإصدارُ الوحدات لشراء الأصول ليس تخفيفاً ضارّاً. فيُقرأ بما يُقرأ به الريت: نموُّ دخل الإيجار،
# وهامشُ التدفّق التشغيليّ ونموُّه (ما يموّل التوزيع)، والمديونيةُ دون سقف الـ‎50٪‎ النظاميّ، وتغطيةُ الفوائد.
REIT_WEIGHTS = {"revenue_growth": 0.20, "ocf_margin": 0.25, "ocf_growth": 0.15, "debt": 0.25, "coverage": 0.15}
_CURVE_NI_CAGR = [(-25, 5), (-10, 25), (0, 45), (3, 60), (6, 74), (10, 88), (15, 94), (25, 98), (40, 100)]
_CURVE_OCF_MARGIN = [(0, 10), (20, 35), (40, 60), (55, 78), (70, 92), (85, 100)]
_CURVE_REIT_DEBT = [(0, 95), (0.20, 90), (0.30, 82), (0.40, 66), (0.50, 42), (0.60, 18), (0.70, 5)]


def _frac(v):
    """نسبةُ المديونية كسراً — ومئويٌّ مخزَّنٌ قبل ‏D720 يُطبَّع (فوق 2.5 لا يكون كسراً لشركةٍ قائمة)."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f / 100.0 if f > 2.5 else f


def _cagr(first, last, years):
    """نموٌّ مركّبٌ ‎٪‎ بين قيمتين موجبتين — أو None."""
    if not first or not last or first <= 0 or last <= 0 or years <= 0:
        return None
    return ((last / first) ** (1 / years) - 1) * 100


# Heavy reinvestment threshold: capex at or above 8% of revenue is a
# capital-intensive spend, not routine maintenance — a reasonable general
# heuristic, not an industry-specific benchmark.
INVESTMENT_CAPEX_RATIO = 0.08


def is_investment_phase(periods: list) -> bool | None:
    """True when the company is plausibly funding real growth (heavy capex
    while revenue holds or grows) rather than distress-borrowing or a demand
    decline. Used to avoid unfairly penalizing rising debt or a profit dip
    that's really reinvestment, not weakness — but this is inferred from
    real capex/revenue data, never assumed. Returns None when there isn't
    enough data (capex or a prior year) to judge either way."""
    if not periods:
        return None
    latest = periods[-1]
    prev = periods[-2] if len(periods) >= 2 else None
    revenue = latest.get("revenue")
    capex = latest.get("capex")
    if not revenue or revenue <= 0 or capex is None or not prev or prev.get("revenue") is None:
        return None
    capex_ratio = abs(capex) / revenue
    revenue_holding = latest["revenue"] >= prev["revenue"]
    return capex_ratio >= INVESTMENT_CAPEX_RATIO and revenue_holding


def _finance_score_from_periods(periods: list) -> int | None:
    """‏D720: quality of the statements, multi-year — weighs six real signals — every one traceable back to a
    row the investor sees in the financial statements table:

      revenue growth (20%)     — compound annual growth rate across every
                                  available year (falls back to a simple
                                  YoY change when only two years exist).
      earnings quality (20%)   — operating cash flow vs. net income,
                                  averaged across every year both are
                                  known; below 1 means profit isn't backed
                                  by cash ("paper profit"). Skipped for
                                  banks/insurers (see below).
      FCF margin (15%)         — free cash flow as a share of revenue,
                                  averaged across available years. Skipped
                                  for banks/insurers for the same reason.
      ROE (20%)                — latest year's net income / equity.
      debt trend (15%)         — latest debt ratio, penalized further if it
                                  rose vs. the prior year. Skipped for
                                  banks/insurers.
      interest coverage (10%)  — latest EBIT / interest expense: the
                                  margin of safety before debt service
                                  becomes a real risk.

    Banks/insurers are structurally different in two ways this function
    must not judge like a regular company: (1) deposits/policy reserves
    inflate their debt ratio to 80%+ as a normal, healthy state, and (2) a
    growing loan book shows up as *negative* operating cash flow in their
    statements (writing more loans is a cash outflow) even though it's
    real, healthy growth — not the "paper profit" warning it would be for
    a non-financial company. Detected the same way both times: no
    EBIT/interest expense reported across the whole series (interest IS
    their business, not a financing cost) alongside a high debt ratio —
    inferred from real data, never guessed from a sector name string.

    Any signal whose inputs are missing is simply left out and the
    remaining signals are re-weighted — never a guessed number for a
    signal we can't actually compute. Returns None only if not a single
    signal could be computed (i.e. periods carries no usable figures)."""
    if not periods:
        return None
    periods = [dict(p, debt_ratio=_frac(p.get("debt_ratio"))) for p in periods]
    latest = periods[-1]
    prev = periods[-2] if len(periods) >= 2 else None
    first = periods[0]
    signals: list[tuple[float, float]] = []

    looks_like_financial_institution = (
        latest.get("debt_ratio") is not None and latest["debt_ratio"] > 0.75
        and all(p.get("interest_coverage") is None for p in periods)
    )
    # ══ الجذرُ الكسريُّ لعددٍ سالبٍ عددٌ مركّب ══ (D153) — الطرفان موجبان أو التغيّرُ السنويّ
    if (len(periods) >= 3 and first.get("revenue") and latest.get("revenue")
            and first["revenue"] > 0 and latest["revenue"] > 0):
        cagr_pct = _cagr(first["revenue"], latest["revenue"], len(periods) - 1)
        signals.append((_curve(cagr_pct, _CURVE_REVENUE_CAGR), FINANCE_WEIGHTS["revenue_growth"]))
    elif prev and prev.get("revenue") and latest.get("revenue") is not None:
        growth_pct = (latest["revenue"] - prev["revenue"]) / abs(prev["revenue"]) * 100
        signals.append((_curve(growth_pct, _CURVE_REVENUE_CAGR), FINANCE_WEIGHTS["revenue_growth"]))

    if not looks_like_financial_institution:
        # جودةُ الربح: التدفّقُ التشغيليُّ ÷ صافي الربح فوق ربحٍ موجب (‏D163) — ربحٌ مغطًّى بالنقد
        quality_ratios = [
            p["operating_cash_flow"] / p["net_income"]
            for p in periods
            if p.get("net_income") and p["net_income"] > 0 and p.get("operating_cash_flow") is not None
        ]
        if quality_ratios:
            avg_ratio = sum(quality_ratios) / len(quality_ratios)
            signals.append((_curve(avg_ratio, _CURVE_EARNINGS_QUALITY), FINANCE_WEIGHTS["earnings_quality"]))

    # الربحيّةُ بمتوسّط آخر ثلاث سنوات — سنةٌ استثنائيّةٌ لا تصنع الدرجةَ ولا تهدمها
    roes = [p["net_income"] / p["equity"] * 100 for p in periods[-3:]
            if p.get("net_income") is not None and p.get("equity") and p["equity"] > 0]
    if roes:
        signals.append((_curve(sum(roes) / len(roes), _CURVE_ROE), FINANCE_WEIGHTS["roe"]))

    # نموُّ الربح **مركّباً عبر السنوات** — والخسارةُ لا «تنمو» (‏D703): سنةٌ أخيرةٌ خاسرةٌ صفر، وكلُّ سنةٍ خاسرةٍ في النافذة تُنقص
    nis = [p.get("net_income") for p in periods]
    if latest.get("net_income") is not None and len([v for v in nis if v is not None]) >= 2:
        losses = sum(1 for v in nis[-4:] if v is not None and v <= 0)
        if latest["net_income"] <= 0:
            ni_sc = 0
        else:
            k0 = next((i for i, v in enumerate(nis) if v is not None and v > 0), None)
            g = _cagr(nis[k0], latest["net_income"], len(nis) - 1 - k0) if k0 is not None and k0 < len(nis) - 1 else None
            if g is None and prev and prev.get("net_income"):
                g = (latest["net_income"] - prev["net_income"]) / abs(prev["net_income"]) * 100
            ni_sc = _curve(max(-100.0, min(200.0, g)), _CURVE_NI_CAGR) if g is not None else None
            if ni_sc is not None:
                ni_sc = _clamp(ni_sc - 12 * losses)
        if ni_sc is not None:
            signals.append((ni_sc, FINANCE_WEIGHTS["ni_growth"]))

    if latest.get("debt_ratio") is not None and not looks_like_financial_institution:
        debt_score = _curve(latest["debt_ratio"], _CURVE_DEBT_RATIO)
        if prev and prev.get("debt_ratio") is not None:
            delta = latest["debt_ratio"] - prev["debt_ratio"]
            penalty_factor = 0.4 if (delta > 0 and is_investment_phase(periods)) else 1.0
            debt_score = _clamp(round(debt_score - delta * 100 * penalty_factor))
        signals.append((debt_score, FINANCE_WEIGHTS["debt"]))

    if latest.get("interest_coverage") is not None:
        signals.append((_curve(latest["interest_coverage"], _CURVE_INTEREST_COVERAGE), FINANCE_WEIGHTS["coverage"]))

    signals = [(sc, w) for sc, w in signals if w > 0]
    if not signals:
        return None
    total_w = sum(w for _, w in signals)
    return round(sum(s * w for s, w in signals) / total_w)


def reit_finance_score(periods: list) -> int | None:
    """‏D720: درجةُ جودة القوائم للريت — بما يُقرأ به الريت (انظر ‎REIT_WEIGHTS‎): نموُّ دخل الإيجار مركّباً، وهامشُ التدفّق
    التشغيليّ ونموُّه، والمديونيةُ دون سقف الـ‎50٪‎، وتغطيةُ الفوائد. لا عائدَ على الحقوق ولا نموَّ ربحٍ محاسبيّ (يتقلّبان بإعادة
    التقييم)، ولا «تخفيفَ» بإصدار الوحدات."""
    if not periods:
        return None
    periods = [dict(p, debt_ratio=_frac(p.get("debt_ratio"))) for p in periods]
    latest, first = periods[-1], periods[0]
    n = len(periods) - 1
    sig: list[tuple[float, float]] = []
    g = _cagr(first.get("revenue"), latest.get("revenue"), n) if n >= 1 else None
    if g is not None:
        sig.append((_curve(g, _CURVE_REVENUE_CAGR), REIT_WEIGHTS["revenue_growth"]))
    margins = [p["operating_cash_flow"] / p["revenue"] * 100 for p in periods[-3:]
               if p.get("revenue") and p["revenue"] > 0 and p.get("operating_cash_flow") is not None]
    if margins:
        sig.append((_curve(sum(margins) / len(margins), _CURVE_OCF_MARGIN), REIT_WEIGHTS["ocf_margin"]))
    ocfs = [p.get("operating_cash_flow") for p in periods]
    k0 = next((i for i, v in enumerate(ocfs) if v is not None and v > 0), None)
    if k0 is not None and ocfs[-1] is not None and k0 < len(ocfs) - 1:
        og = _cagr(ocfs[k0], ocfs[-1], len(ocfs) - 1 - k0)
        sig.append((_curve(og, _CURVE_REVENUE_CAGR) if og is not None else 0, REIT_WEIGHTS["ocf_growth"]))
    if latest.get("debt_ratio") is not None:
        sig.append((_curve(latest["debt_ratio"], _CURVE_REIT_DEBT), REIT_WEIGHTS["debt"]))
    if latest.get("interest_coverage") is not None:
        sig.append((_curve(latest["interest_coverage"], _CURVE_INTEREST_COVERAGE), REIT_WEIGHTS["coverage"]))
    if not sig:
        return None
    return round(sum(s * w for s, w in sig) / sum(w for _, w in sig))


finance_score_from_periods = _finance_score_from_periods


def financial_verdict(periods: list) -> str:
    """Deterministic, rule-based executive verdict — computed from the exact
    same real signals as finance_score_from_periods, not a free-text AI
    guess. Chosen deliberately: an investor's decision sentence must be as
    traceable and reproducible as the numbers behind it.

    Rising debt and a profit dip are not automatically treated as weakness:
    when heavy capex accompanies steady-or-growing revenue (see
    is_investment_phase), that pattern is a plausible sign of funded
    expansion, not distress — and the verdict says so explicitly rather
    than silently scoring it either way, so the investor sees the
    reasoning, not just a conclusion.

    Banks/insurers get the same structural exemptions as the score (see
    finance_score_from_periods's docstring) — detected market-wide from
    the data shape, not any specific symbol or sector string."""
    if not periods:
        return "بيانات متاحة"
    latest = periods[-1]
    prev = periods[-2] if len(periods) >= 2 else None

    def yoy(field):
        if not prev:
            return None
        a, b = latest.get(field), prev.get(field)
        if a is None or not b:
            return None
        return (a - b) / abs(b) * 100

    rev_g = yoy("revenue")
    ni_g = yoy("net_income")
    ni = latest.get("net_income")
    ocf = latest.get("operating_cash_flow")
    fcf = latest.get("free_cash_flow")

    is_financial_institution = (
        _frac(latest.get("debt_ratio")) is not None and _frac(latest.get("debt_ratio")) > 0.75
        and all(p.get("interest_coverage") is None for p in periods)
    )
    quality_ok = True if is_financial_institution else (
        ocf is not None and ni and ni != 0 and (ocf / ni) >= 0.8
    )
    fcf_ok = True if is_financial_institution else (fcf is not None and fcf > 0)
    debt_rising = (
        not is_financial_institution
        and prev and latest.get("debt_ratio") is not None and prev.get("debt_ratio") is not None
        and latest["debt_ratio"] > prev["debt_ratio"]
    )
    coverage = latest.get("interest_coverage")
    weak_coverage = coverage is not None and coverage < 2
    profit_declining = ni_g is not None and ni_g < 0
    inv_phase = is_investment_phase(periods)

    if ni is not None and ni < 0:
        return "خسائر تشغيلية — يتطلب حذراً"
    if weak_coverage:
        return "تغطية فوائد ضعيفة — مخاطر خدمة الدين"
    if not is_financial_institution and ocf is not None and ni and ocf < 0 < ni:
        return "نمو محاسبي بلا نقد — تحذير جودة الأرباح"

    if debt_rising and inv_phase:
        if rev_g is not None and rev_g >= 0 and quality_ok:
            return "توسع استثماري مموَّل بالدين — الإيرادات مستقرة/نامية ورأس المال يُعاد استثماره؛ ارتفاع الدين هنا لا يعني ضعفاً بالضرورة"
        if profit_declining:
            return "انخفاض مؤقت في الربح مع دين مرتفع، مرتبطان بنفقات رأسمالية توسعية — راقب تحوّل الاستثمار إلى نمو قادم"

    if rev_g is not None:
        if rev_g > 0 and quality_ok and fcf_ok and not debt_rising:
            return "قوة أرباح ونمو حقيقي مدعوم بنقد ✓"
        if rev_g > 0 and quality_ok and debt_rising:
            return "نمو مدعوم بأرباح سليمة، مع ارتفاع دين غير مرتبط بوضوح باستثمار رأسمالي — راقب السبب"
        if rev_g > 0 and quality_ok:
            return "نمو مدعوم بأرباح سليمة"
        if rev_g > 0:
            return "نمو إيرادات مع ضغط على جودة الأرباح"
        if rev_g < 0:
            return "تراجع في الإيرادات — يتطلب مراجعة"
    if quality_ok and not debt_rising:
        return "ربحية مستقرة بلا نمو ملحوظ"
    return "بيانات متاحة"


_VERDICT_TONE_RED = {
    "خسائر تشغيلية — يتطلب حذراً",
    "تغطية فوائد ضعيفة — مخاطر خدمة الدين",
    "نمو محاسبي بلا نقد — تحذير جودة الأرباح",
}
_VERDICT_TONE_GREEN = {
    "توسع استثماري مموَّل بالدين — الإيرادات مستقرة/نامية ورأس المال يُعاد استثماره؛ ارتفاع الدين هنا لا يعني ضعفاً بالضرورة",
    "قوة أرباح ونمو حقيقي مدعوم بنقد ✓",
}


def verdict_tone(verdict: str) -> str:
    """Maps the verdict sentence to a single traffic-light signal — green
    only for a genuinely excellent read, red only for a real, confirmed
    risk, yellow for everything in between (has notes, but neither
    excellent nor dangerous). Kept as a lookup over the verdict's exact,
    deterministic strings so the color is never a second, drifting
    judgment about the same data."""
    if verdict in _VERDICT_TONE_RED:
        return "red"
    if verdict in _VERDICT_TONE_GREEN:
        return "green"
    if verdict == "بيانات متاحة":
        return "neutral"
    return "yellow"


def financial_strengths_weaknesses(periods: list) -> tuple[list[str], list[str]]:
    """Arabic strength/weakness bullet points, derived from the exact same
    signals as the score and verdict above — so the AI-analysis page's list
    is always consistent with the number and the sentence, not a separate
    read of the data."""
    strengths, weaknesses = [], []
    if not periods:
        return strengths, weaknesses
    latest = periods[-1]
    prev = periods[-2] if len(periods) >= 2 else None
    is_fi = (
        _frac(latest.get("debt_ratio")) is not None and _frac(latest.get("debt_ratio")) > 0.75
        and all(p.get("interest_coverage") is None for p in periods)
    )

    if prev and prev.get("revenue") and latest.get("revenue") is not None:
        g = (latest["revenue"] - prev["revenue"]) / abs(prev["revenue"]) * 100
        if g >= 10:
            strengths.append(f"نمو إيرادات قوي {g:.0f}%")
        elif g < 0:
            weaknesses.append(f"تراجع الإيرادات {g:.0f}%")

    ni = latest.get("net_income")
    if ni is not None and ni < 0:
        weaknesses.append("خسائر تشغيلية في آخر سنة مالية")

    if not is_fi:
        ocf, fcf = latest.get("operating_cash_flow"), latest.get("free_cash_flow")
        if ocf is not None and ni and ni > 0:
            if ocf / ni >= 1:
                strengths.append("أرباح مدعومة بتدفق نقدي حقيقي")
            elif ocf < 0:
                weaknesses.append("ربح محاسبي بلا تدفق نقدي حقيقي")
        if fcf is not None:
            if fcf > 0:
                strengths.append("تدفق نقدي حر موجب")
            else:
                weaknesses.append("تدفق نقدي حر سالب")

    if ni is not None and latest.get("equity"):
        roe = ni / latest["equity"] * 100
        if roe >= 20:
            strengths.append(f"عائد ممتاز على حقوق الملكية {roe:.0f}%")
        elif roe < 6:
            weaknesses.append(f"عائد ضعيف على حقوق الملكية {roe:.0f}%")

    if not is_fi and _frac(latest.get("debt_ratio")) is not None:
        if _frac(latest["debt_ratio"]) <= 0.4:
            strengths.append("مديونية منخفضة")
        elif _frac(latest["debt_ratio"]) >= 0.7:
            weaknesses.append("مديونية مرتفعة نسبةً للأصول")

    coverage = latest.get("interest_coverage")
    if coverage is not None:
        if coverage >= 5:
            strengths.append(f"تغطية فوائد قوية ({coverage:.1f}×)")
        elif coverage < 2:
            weaknesses.append(f"تغطية فوائد ضعيفة ({coverage:.1f}×)")

    if is_investment_phase(periods):
        strengths.append("توسع استثماري مموَّل — نفقات رأسمالية مرتفعة مع إيرادات نامية")

    return strengths[:6], weaknesses[:6]


async def refresh_company_scores(db: AsyncSession) -> int:
    from app.services.market_data import market_service
    from app.services import sahmak_library
    from app.services import maqasid
    from app.api.v1.endpoints.holdings import yahoo_symbol

    companies = (
        await db.execute(select(Company).where(Company.status != "ARCHIVED"))
    ).scalars().all()
    updated = 0
    for c in companies:
        try:
            sym = yahoo_symbol(c.symbol)
            price = await market_service.get_price(sym)

            # Correct the sector FIRST (before scoring) — our curated Arabic
            # directory is the source of truth and self-heals any stale/Yahoo
            # misclassification, so the score below runs on the right archetype.
            from app.data.company_sectors import SYMBOL_TO_SECTOR_AR
            curated = SYMBOL_TO_SECTOR_AR.get(c.symbol.replace(".SR", ""))
            if curated and c.sector != curated:
                c.sector = curated

            # The stored finance_score is now just a CACHE of the ONE source
            # of truth — governance_engine.evaluate_company — never a separate
            # computation that could drift from the live governance page/panel.
            from app.services.governance_engine import evaluate_company
            status_value = c.status.value if hasattr(c.status, "value") else c.status
            gov = await evaluate_company(sym, db=db, company_status=status_value,
                                         sector=c.sector, with_decision=False)
            finance = (gov or {}).get("finance_score")
            if finance is not None:
                c.finance_score = finance
            if price:
                chg = price.get("change_pct") or 0
                c.technical_score = _clamp(round(55 + chg * 6))

            # sahmak_library never had a sharia_status function (this call
            # was dead code left over from before maqasid.rating() became
            # the site's real شرعية source — see governance.py) and raised
            # an AttributeError on EVERY company every refresh, silently
            # skipping the rest of that company's score update (price/
            # finance/technical) in the same try block.
            r = maqasid.rating(c.symbol)
            if r and r.get("status"):
                c.sharia_status = r["status"]

            # Sector fallback for symbols NOT in our curated directory and
            # still without any sector: use Yahoo's (coarse) classification —
            # curated symbols were already corrected above, before scoring.
            if not curated and not c.sector:
                info = await market_service.get_company_info(sym)
                y_sector = (info or {}).get("sector")
                if y_sector:
                    c.sector = _SECTOR_AR.get(y_sector, y_sector)

            # Logo: resolved once per company, then never re-fetched (a logo
            # doesn't change). Three sources, in order of how directly
            # verified each one is:
            #  1. TradingView's own logo CDN — real (symbol, logoid) pairs
            #     captured live from tradingview.com's market-movers screener
            #     (app/data/tradingview_logos.json), the same "collect from a
            #     real source, commit as a static file" pattern already used
            #     for شرعية compliance (maqasid JSON).
            #  2. Sahmak's verified company website, via Clearbit.
            #  3. Wikipedia's infobox image.
            if not c.logo_url:
                from app.data.tradingview_logos import TRADINGVIEW_LOGOS
                base_symbol = c.symbol.replace(".SR", "")
                tv = TRADINGVIEW_LOGOS.get(base_symbol)
                logo = tv["logo_url"] if tv else None
                if not logo:
                    logo = await sahmak_library.company_logo_url(c.symbol)
                if not logo:
                    from app.data.company_names_en import SYMBOL_TO_NAME_EN
                    name_en = SYMBOL_TO_NAME_EN.get(base_symbol)
                    if name_en:
                        logo = await sahmak_library.resolve_logo_wikipedia(name_en)
                if logo:
                    c.logo_url = logo

            if finance is not None or price:
                updated += 1
        except Exception as e:
            logger.warning(f"score refresh failed for {c.symbol}: {e}")
    if updated:
        await db.commit()
        logger.info(f"Company scores refreshed for {updated} companies.")
    return updated


def governed_finance_score(periods: list, symbol: str | None = None) -> tuple:
    """‏D640 · الإصدارُ الثاني: الدرجةُ الأصليةُ مع الخطوط الحمراء من منتِجٍ واحد ← (الدرجة، الخطوط، التحذيرات).

    الخطُّ الأحمر «يُبطل الترتيبَ ولا يُخصم منه — يُستبعد ويُقال السبب» (red_lines.py)، كما تُستبعد الخسارةُ
    التشغيلية ثلاثَ سنوات بدرجةٍ صفر. وكانت الدرجةُ النسبيةُ تُنشر معه — قِيس في بوابة الإصدار الأوّل: سينومي ريتيل
    68 بحقوقٍ سالبةٍ وخسارةِ أربع سنوات، وريدان 65 بخسارةِ ستّ، وتسعُ شركاتٍ ≥ 65.

    ويُحسب هنا لا في شاشةٍ واحدة: البطاقةُ والصفحةُ وجدولُ القوائم تقرأ هذه الدالّةَ نفسَها (D149) — طُبّق في الإصدار
    الأوّل في مخرَج الصفحة وحده فأمسكه حارسُ «محرّكٍ واحد» (البطاقة 0 والجدول 25). والخطوطُ تُقرأ من القوائم ونمطِ
    الورقة من قطاع «تداول» الرسميّ (`archetype_of`) — مصدرٌ واحدٌ للنمط فلا يشتعل خطٌّ في شاشةٍ دون أخرى."""
    arch = None
    if symbol:
        try:
            from app.services.statement_merge import archetype_of
            arch = archetype_of(symbol)
        except Exception:                                          # noqa: BLE001
            arch = None
    # ‏D720: الريتُ بمساره (بنيتُه المحاسبيّة غيرُ بنية الشركة — دليلٌ نظاميّ لا اسمُ قطاع)، وما سواه بالدالّة العامّة
    base = reit_finance_score(periods) if arch == "reit" else _finance_score_from_periods(periods)
    try:
        from app.services import red_lines as _rl
        lines, warnings = _rl.split(_rl.check({}, periods or [], arch))   # ‏D643: الإقصاءُ لتهديد البقاء وحده
    except Exception:                                              # noqa: BLE001
        lines, warnings = [], []
    if lines and isinstance(base, (int, float)) and base > 0:
        return 0, lines, warnings
    return base, lines, warnings


def exclusion_verdict(lines: list) -> str:
    """جملةُ الاستبعاد بالخطّ الأحمر — بنصّ استبعاد الخسارة التشغيلية نفسِه، وبسبب الخطّ لا بوصفٍ عامّ (D640)."""
    return "استُبعدت الشركة من التقييم: خطٌّ أحمر — " + " · ".join(str(r.get("message") or "") for r in (lines or [])[:2])
