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


# ══ قطاعاتٌ تُقاس بغير المسطرة العامّة ══
# الأصلُ في هذا المحرّك أن يستدلّ من **البيانات** لا من اسم القطاع —
# وذاك التحفّظُ كان في محلّه حين كان الاسمُ يأتي من ياهو بالإنجليزية
# فلا يُطابق شيئاً. أمّا هذه فأسماءٌ من دليل السوق المعتمَد عندنا،
# قاطعةٌ لا تُخمَّن. والاسمُ الغائبُ يعني «المسطرة العامّة» لا خطأً:
# فالمحرّكُ بدون قطاعٍ يعمل كما كان قبل هذا التحسين حرفاً بحرف.
#
# ولا يُضاف بها مؤشّرٌ ولا عتبة: تُسقَط إشارةٌ لا تناسب النموذج فيُعاد
# توزيعُ وزنها على الباقي، أو يُستبدَل **مدخلُها** لا حدُّها.
_CYCLICAL_SECTORS = frozenset({"الطاقة", "المواد الأساسية"})


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


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


def _finance_score_from_periods(periods: list,
                                sector: str | None = None) -> int | None:
    """Weighs six real, multi-year signals — every one traceable back to a
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
    latest = periods[-1]
    prev = periods[-2] if len(periods) >= 2 else None
    first = periods[0]
    signals: list[tuple[float, float]] = []

    looks_like_financial_institution = (
        latest.get("debt_ratio") is not None and latest["debt_ratio"] > 0.75
        and all(p.get("interest_coverage") is None for p in periods)
    )
    _sec = (sector or "").strip()
    # ══ إعفاءُ الصناديق العقارية أُلغي — نقضه القياس ══ (D154)
    # افتُرض أنّ تدفّقَها الحرَّ سالبٌ بنيةً (تشتري عقاراتٍ وتوزّع أغلبَ
    # دخلها)، فأُعفيت منه. ثمّ قِيست تسعَ عشرةَ شركةً على بيانات السوق
    # الحقيقية: **لا واحدةَ** تدفّقُها سالبٌ في كلّ سنواتها، ووسيطُ هامش
    # الحرّ ‎+67.9٪، والإعفاءُ يحسم منها **سبعَ نقاط**. فالافتراضُ جاء من
    # عيّنةٍ صنعتُها بيدي ولا تشبه المصدر — وهو ثامنُ وقوعٍ من صنفه.
    # والقاعدةُ التي أثبتها هذا: لا تعديلَ قطاعيٌّ قبل قياسٍ على بياناتٍ
    # حقيقية، لا على فرضيةٍ مهما بدت معقولة.
    # والدوريّةُ تُقاس عبر الدورة: سنةُ القاع تُظهر العائدَ 2.5٪ وعبر
    # الدورة 23٪ — ثمانُ نقاطٍ سببُها اختيارُ السنة لا حالُ الشركة.
    # فيُستبدَل **مدخلُ** العائد بمتوسّط الدورة، وحدُّه كما هو.
    is_cyclical = _sec in _CYCLICAL_SECTORS

    # ══ الجذرُ الكسريُّ لعددٍ سالبٍ عددٌ مركّب ══ (D153)
    # كان الشرطُ يفحص أوّلَ إيرادٍ موجباً ولا يفحص آخرَه. وشركةٌ إيرادُها
    # الأخير سالب (تصحيحاتٌ تفوق الإيراد — يقع في التأمين والمقاولات)
    # تُخرج `(-0.5) ** (1/3)` عدداً مركّباً، فيسقط `round` بـTypeError
    # وتسقط معه درجةُ الشركة كلُّها. والانهيارُ أسوأُ من درجةٍ منخفضة.
    # فيُشترط الطرفان موجبَين، وإلّا انتقل الحسابُ إلى فرع التغيّر
    # السنويّ أدناه — وهو يقسم على القيمة المطلقة فيحتمل السالب.
    if (len(periods) >= 3 and first.get("revenue") and latest.get("revenue")
            and first["revenue"] > 0 and latest["revenue"] > 0):
        n = len(periods) - 1
        cagr_pct = ((latest["revenue"] / first["revenue"]) ** (1 / n) - 1) * 100
        signals.append((_clamp(round(50 + cagr_pct * 2)), 0.20))
    elif prev and prev.get("revenue") and latest.get("revenue") is not None:
        growth_pct = (latest["revenue"] - prev["revenue"]) / abs(prev["revenue"]) * 100
        signals.append((_clamp(round(50 + growth_pct * 2)), 0.20))

    if not looks_like_financial_institution:
        quality_ratios = [
            p["operating_cash_flow"] / p["net_income"]
            for p in periods
            if p.get("net_income") and p.get("operating_cash_flow") is not None and p["net_income"] != 0
        ]
        if quality_ratios:
            avg_ratio = sum(quality_ratios) / len(quality_ratios)
            signals.append((_clamp(round(50 + (avg_ratio - 1) * 40)), 0.20))

        fcf_margins = [
            p["free_cash_flow"] / p["revenue"] * 100
            for p in periods
            if p.get("revenue") and p["revenue"] > 0 and p.get("free_cash_flow") is not None
        ]
        if fcf_margins:
            avg_margin = sum(fcf_margins) / len(fcf_margins)
            signals.append((_clamp(round(50 + avg_margin * 2.5)), 0.15))

    if latest.get("net_income") is not None and latest.get("equity"):
        _ni = latest["net_income"]
        if is_cyclical:
            _series = [p["net_income"] for p in periods
                       if p.get("net_income") is not None]
            if len(_series) >= 3:
                _ni = sum(_series) / len(_series)
        roe_pct = _ni / latest["equity"] * 100
        signals.append((_clamp(round(40 + roe_pct * 2)), 0.20))

    if latest.get("debt_ratio") is not None and not looks_like_financial_institution:
        debt_score = _clamp(round(100 - latest["debt_ratio"] * 100))
        if prev and prev.get("debt_ratio") is not None:
            delta = latest["debt_ratio"] - prev["debt_ratio"]
            # Debt-funded expansion (heavy capex, revenue still holding) is a
            # materially different risk than debt taken on to cover a
            # shrinking business — so a rising ratio is penalized less
            # harshly when it looks investment-driven, not eliminated.
            penalty_factor = 0.4 if (delta > 0 and is_investment_phase(periods)) else 1.0
            debt_score = _clamp(round(debt_score - delta * 100 * penalty_factor))
        signals.append((debt_score, 0.15))

    if latest.get("interest_coverage") is not None:
        signals.append((_clamp(round(40 + latest["interest_coverage"] * 4)), 0.10))

    if not signals:
        return None
    total_w = sum(w for _, w in signals)
    return round(sum(s * w for s, w in signals) / total_w)


# Public alias — this IS the single source of truth for "how healthy/safe
# is this company's balance sheet", used by the governance page, the
# scheduler's company scoring pass, and the AI company-analysis score alike.
finance_score_from_periods = _finance_score_from_periods


def financial_verdict(periods: list, sector: str | None = None) -> str:
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
        latest.get("debt_ratio") is not None and latest["debt_ratio"] > 0.75
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
        latest.get("debt_ratio") is not None and latest["debt_ratio"] > 0.75
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

    if not is_fi and latest.get("debt_ratio") is not None:
        if latest["debt_ratio"] <= 0.4:
            strengths.append("مديونية منخفضة")
        elif latest["debt_ratio"] >= 0.7:
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
            gov = await evaluate_company(sym, db=db, company_status=status_value, sector=c.sector)
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
