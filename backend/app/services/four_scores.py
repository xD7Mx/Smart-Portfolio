"""
Four independent governance scores — Phase 3 of the redesign.

Replaces the old single finance_score with four scores that deliberately
never bleed into each other, each built purely from Financial Feature
Engine output (Phase 1) run through the Governance Rule Engine (Phase 2):

  - Quality:   is this a good business? (never looks at price)
  - Valuation: is the current price fair? (never looks at business quality)
  - Safety:    debt/liquidity/earnings-quality/solvency
  - Timing:    technical only (trend/RSI/MACD/moving averages/volume)

No AI decides any of these — every point gained or lost traces back to one
named rule in governance_rules.yaml. A Hard Filter hit disqualifies the
company outright (Quality/Safety forced to 0, Valuation/Timing become
irrelevant — None) rather than letting a cheap price offset a fatal flaw.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.services import financial_features
from app.services import governance_rules

# Yahoo returns GICS sector names in English; the governance sector archetypes
# (governance_rules.yaml) are keyed by the app's canonical ARABIC names. Using
# the raw English string silently skips every sector exemption (e.g. a bank
# scored as a generic company → Piotroski penalty → unfairly crushed). This
# resolver maps any raw sector to canonical Arabic, falling back to the app's
# own curated directory by symbol.
_SECTOR_EN_AR = {
    "Energy": "الطاقة", "Basic Materials": "المواد الأساسية", "Materials": "المواد الأساسية",
    "Industrials": "الصناعات", "Consumer Cyclical": "السلع الكمالية", "Consumer Defensive": "السلع الأساسية",
    "Financial Services": "الخدمات المالية", "Financials": "الخدمات المالية", "Financial": "الخدمات المالية",
    "Healthcare": "الرعاية الصحية", "Health Care": "الرعاية الصحية",
    "Technology": "التقنية", "Communication Services": "الاتصالات", "Communications": "الاتصالات",
    "Utilities": "المرافق العامة", "Real Estate": "العقارات",
    "Consumer Staples": "السلع الأساسية", "Consumer Discretionary": "السلع الكمالية",
}


def resolve_sector(raw_sector: Optional[str], symbol: Optional[str] = None) -> Optional[str]:
    """Canonical Arabic sector for archetype matching. Priority: an already-
    Arabic name is used as-is; an English GICS name is translated; otherwise
    the app's curated symbol→sector directory decides."""
    if raw_sector:
        s = raw_sector.strip()
        if s in _SECTOR_EN_AR:
            return _SECTOR_EN_AR[s]
        # already Arabic (or an unknown string) — keep it; archetype lookup
        # will simply fall through to general rules if it doesn't match.
        if any("؀" <= ch <= "ۿ" for ch in s):
            return s
    if symbol:
        try:
            from app.data.company_sectors import SYMBOL_TO_SECTOR_AR
            return SYMBOL_TO_SECTOR_AR.get(str(symbol).replace(".SR", "")) or raw_sector
        except Exception:
            pass
    return raw_sector

# Normalized scoring: a category score reflects how much of the POSITIVE
# potential the company actually demonstrated on the signals we could
# measure — never the raw sum of a few threshold bonuses, which unfairly
# trapped fundamentally strong companies near the base whenever the data
# provider returned only a handful of the many statement lines the rules
# look at. BASE is the neutral anchor; a company that aces every
# measurable positive signal reaches BASE+POSITIVE_SPAN before penalties.
BASE_SCORE = 50
MAX_CATEGORY_PENALTY = 28   # شُدَّ مع الأوزان: الانحرافُ المقيس 22.1 والهدف 16
POSITIVE_SPAN = 50  # BASE + full positive potential = 100 (before penalties)


@dataclass
class CategoryScore:
    score: Optional[float]
    hits: list = field(default_factory=list)  # governance_rules.RuleHit
    # نسبةُ ما أمكن قياسه من مؤشّرات هذه الفئة — تُقرأ في بوّابة القرار:
    # درجةٌ عالية على شاهدين ليست شهادةَ سلامة.
    coverage: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            # ══ التغطيةُ تُسلسَل ══ (كشفه فحصٌ خارجيّ على مخرَج السوق)
            # كانت تُحسب وتُحمل على الكائن ولا تخرج في القاموس، فتصل
            # الواجهةَ والقياسَ فارغةً في ٤٠٦ صفوفٍ من ٤٠٦. وهي بوّابةُ
            # «شراء قوي» (‏≥0.70) و«شراء» (‏≥0.60) و«امتناع» (‏<0.50) —
            # فبوّابةٌ لم تُقيَّم مرّةً واحدة، ومرّ خمسون اسماً إلى الشراء
            # بلا أن تُسأل. وحقلٌ يُحسب ولا يُعرض أخطرُ من حقلٍ لا يُحسب:
            # الأوّل يُظنّ عاملاً وهو معطَّل.
            "coverage": self.coverage,
            "reasons": [
                {"id": h.id, "kind": h.kind, "severity": h.severity,
                 "points": h.points, "message": h.message}
                for h in self.hits
            ],
            "hits": [
                {"id": h.id, "kind": h.kind, "severity": h.severity,
                 "points": h.points, "message": h.message}
                for h in self.hits
            ],
        }


@dataclass
class FourScores:
    rejected: bool
    hard_filter_message: Optional[str]
    quality: CategoryScore
    valuation: CategoryScore
    safety: CategoryScore
    timing: CategoryScore

    def to_dict(self) -> dict:
        return {
            "rejected": self.rejected,
            "hard_filter_message": self.hard_filter_message,
            "quality": self.quality.to_dict(),
            "valuation": self.valuation.to_dict(),
            "safety": self.safety.to_dict(),
            "timing": self.timing.to_dict(),
        }


def _consecutive_loss_years(periods: list[dict]) -> int:
    """Trailing streak of loss-making years, most-recent year first."""
    ordered = sorted([p for p in periods if p.get("year")], key=lambda p: p["year"])
    streak = 0
    for p in reversed(ordered):
        ni = p.get("net_income")
        if ni is None:
            break
        if ni < 0:
            streak += 1
        else:
            break
    return streak


def hard_filter_flags_from_company(company_status: Optional[str]) -> dict:
    """Wires the "trading_suspended" hard filter to the one real, already-
    tracked signal for it in this app: Company.status == DELISTED (set
    manually today, same as ARCHIVED — there is no live Tadawul "suspended"
    feed wired up yet). "qualified_audit_opinion" and "bankruptcy_risk_flag"
    stay in governance_rules.yaml but are deliberately left unfed here: no
    provider in this app currently exposes an audit opinion or a bankruptcy
    signal, and fabricating one would violate the "no invented penalties"
    principle the whole engine is built on. Wire them the same way once a
    real source exists (a manual admin flag, a filings feed, etc.) — the
    Rule Engine already skips any hard filter whose feature is absent, so
    this is a pure additive step whenever that data shows up."""
    return {"trading_suspended": company_status == "DELISTED"}


def enrich_periods(periods: list[dict], info: Optional[dict]) -> tuple[list[dict], dict, list[str]]:
    """Phase-A enrichment: fill gaps the provider left in the LATEST year by
    deriving from the trailing figures we DO have (company_info), so the
    expert panel can judge instead of abstaining. Deliberately touches only
    the most-recent period — the year-over-year CHANGE checks (Piotroski's
    margin/liquidity-trend factors) need TWO real years and will simply skip
    when the prior year is still missing, so a single derived latest value
    can never fabricate a trend. Every derived field is tagged so the UI can
    show it's an estimate, not a reported line.

      gross_profit    ← revenue × trailing gross margin
      operating_income← revenue × trailing operating margin (EBIT proxy)
      current/quick ratio ← taken directly from the provider's own ratios
    """
    ordered = sorted([p for p in periods if p.get("year")], key=lambda p: p["year"])
    derived: dict = {}
    tags: list[str] = []
    if not info or not ordered:
        return ordered, derived, tags
    latest = dict(ordered[-1])
    rev = latest.get("revenue")
    gm, om = info.get("gross_margin"), info.get("operating_margin")
    if latest.get("gross_profit") is None and rev and gm is not None:
        latest["gross_profit"] = round(rev * gm / 100)
        tags.append("الربح الإجمالي")
    if latest.get("operating_income") is None and rev and om is not None:
        latest["operating_income"] = round(rev * om / 100)
        tags.append("الربح التشغيلي")
    ordered[-1] = latest
    # Direct liquidity ratios — a feature-level fallback (no raw current
    # assets/liabilities needed).
    if info.get("current_ratio") is not None:
        derived["current_ratio"] = round(info["current_ratio"], 2)
    if info.get("quick_ratio") is not None:
        derived["quick_ratio"] = round(info["quick_ratio"], 2)
    return ordered, derived, tags


def build_company_features(
    periods: list[dict],
    info: Optional[dict] = None,
    sector: Optional[str] = None,
    valuation_snapshot: Optional[dict] = None,
    timing_snapshot: Optional[dict] = None,
    hard_filter_flags: Optional[dict] = None,
) -> tuple[dict, dict, dict]:
    """مصدرٌ واحد لسمات الشركة — يُعيد (‏السمات، الأساسيات المدقَّقة، تقرير التدقيق).

    ══ لماذا وُجدت ══ (بأمر المالك)
    كان في التطبيق **محرّكان** يجيبان السؤال نفسه عن الشركة نفسها:
      • `analysis.analyze_company` — يخدم صفحة الشركة، ويُدقّق الأساسيات
        مقابل القوائم ويُضيف أركان الإطار القطاعيّ إلى السمات.
      • `governance_engine.evaluate_company` — يخدم نافذة الحوكمة وصفوف
        المحفظة، ولا يفعل أيّاً من الاثنين.
    فتختلف السمات، فيختلف مجلس الخبراء، فيختلف القرار — **في الشركة
    الواحدة**. ورآها المالك: نافذةٌ تقول «شراء بثقة ٨٤٫٧٪» بمؤشّرين
    أخضرين، وصفحتُها تقول «انتظار» بثلاثة مؤشّرات حمراء ودرجة ٥٧.
    وذلك أسوأ من الخطأ: خطأٌ واحدٌ يُصحَّح، أمّا حكمان متضادّان فيُبطلان
    الثقة بالأداة كلّها.

    والعلاج ليس نسخَ الخطوتين إلى المحرّك الثاني — فثالثٌ يُضاف غداً
    يرثُ النقص. بل موضعٌ واحد يبني السمات، ولا يُبنى منها شيءٌ خارجه.
    """
    from app.services.data_quality import audit as _audit
    from app.services import sector_metrics
    from app.services.governance_rules import archetype_for

    q = _audit(info or {}, periods or [])
    info = q["values"]
    feats = build_features(periods, valuation_snapshot=valuation_snapshot,
                           timing_snapshot=timing_snapshot,
                           hard_filter_flags=hard_filter_flags, info=info)
    # ══ محلِّلُ نمطٍ واحد للتطبيق كلِّه ══
    # كشفه قياسُ السوق: وسيطُ تغطية المواصفة ‎0.50، ونصفُ الشركات تحت ‎42،
    # ولا شركةَ واحدة فوق ‎75 من ‎386. ولم يكن السببُ عتباتٍ قاسية بل
    # **سباكة**: مقاييسُ القطاع تُحسب بنمطٍ من خريطة الـ‎YAML القديمة،
    # وبطاقةُ الدرجة تُقرأ بنمطٍ من خريطة المواصفة — والخريطتان تختلفان
    # في ‎51 قطاعاً من ‎63. فبطاقةُ البنك تطلب هامشَ العمولة وتكلفةَ
    # المخاطر ونسبةَ التكلفة إلى الدخل، والخريطةُ القديمة تُصنّف
    # «‏Banks» الإنجليزية `general` فلا يُحسب منها شيء — فتُعدّ الأركانُ
    # غائبةً وتنكمش الدرجةُ بجذر تغطيةٍ نصفُها مصنوعٌ عندنا لا عند الشركة.
    # فصار المحلِّلُ واحداً: خريطةُ المواصفة (وفيها التسمياتُ الإنجليزية
    # وقواعدُ الحلّ الحتميّة)، وتبقى الخريطةُ القديمة سنداً إن تعذّر الحلّ.
    try:
        from app.services.spec_score import resolve_archetype_ex
        _arch, _ok = resolve_archetype_ex(sector, feats)
        if not _ok:
            _arch = archetype_for(sector) or _arch
        sm = sector_metrics.compute(_arch, periods, info,
                                    (info or {}).get("current_price"))
        for k, v in (sm.get("features") or {}).items():
            feats.setdefault(k, v)
        if sm.get("metrics"):
            feats["_sector_metrics"] = sm["metrics"]
    except Exception:                                             # noqa: BLE001
        pass
    # ══ تاريخُ آخر قائمةٍ يمرّ مع السمات ══
    # قاعدةُ الإطار المهنيّ تجعل فجوةَ تسعةِ أشهر مانعاً من إصدار حكم،
    # وبوّابةُ القرار لا تراه إن لم يصلها. فيُمرَّر صريحاً.
    try:
        _last = (periods or [])[-1] if periods else None
        _ao = (_last or {}).get("as_of") or (_last or {}).get("year")
        if _ao:
            feats["_asof"] = str(_ao)
    except Exception:                                             # noqa: BLE001
        pass
    return feats, info, q


def build_features(
    periods: list[dict],
    valuation_snapshot: Optional[dict] = None,
    timing_snapshot: Optional[dict] = None,
    hard_filter_flags: Optional[dict] = None,
    info: Optional[dict] = None,
) -> dict:
    """Merges every available feature source into one flat dict for the
    Rule Engine. Any snapshot may be omitted entirely — the rules that
    depend on it simply won't fire (not a fabricated penalty).

    `info` (company_info) enables Phase-A enrichment (see enrich_periods):
    filling provider gaps in the latest year from trailing figures so the
    expert panel abstains far less often."""
    periods, _derived_ratios, _enrich_tags = enrich_periods(periods, info)
    ordered = sorted([p for p in periods if p.get("year")], key=lambda p: p["year"])
    feats: dict = dict(financial_features.compute_features(periods))
    # Feature-level fallback for liquidity ratios the raw lines couldn't give.
    for k in ("current_ratio", "quick_ratio"):
        cur = feats.get(k)
        cur_val = cur.get("value") if isinstance(cur, dict) else cur
        if cur_val is None and k in _derived_ratios:
            feats[k] = {"value": _derived_ratios[k], "note": "من نِسب المزوّد المباشرة (تقدير)"}
    feats["_enriched_fields"] = {"value": _enrich_tags or None, "note": "حقول مُكمَّلة اشتقاقاً من الهوامش/النِسب"}
    feats["equity"] = ordered[-1].get("equity") if ordered else None
    feats["total_debt"] = ordered[-1].get("total_debt") if ordered else None
    feats["ending_cash"] = ordered[-1].get("ending_cash") if ordered else None
    feats["consecutive_loss_years"] = _consecutive_loss_years(periods)
    if valuation_snapshot:
        feats.update(valuation_snapshot)
    if timing_snapshot:
        feats.update(timing_snapshot)
    if hard_filter_flags:
        feats.update(hard_filter_flags)

    # Expert valuation metrics that need BOTH statements (Graham number,
    # EBIT — from the feature engine) AND live market data (price, market
    # cap — from the valuation snapshot): computed here, once both are
    # merged, so the rules can reference plain numbers.
    def _v(name):
        raw = feats.get(name)
        return raw.get("value") if isinstance(raw, dict) else raw

    price = _v("price")
    graham = _v("graham_number")
    if price and graham and price > 0:
        # % the price sits BELOW Graham's fair-value ceiling (positive = a
        # margin of safety, Graham's core idea).
        feats["graham_discount_pct"] = round((graham - price) / price * 100, 1)

    # ── Peter Lynch PEG — معايرة للسوق السعودي ──────────────────────────
    # Yahoo's pegRatio is FORWARD (analyst estimates) and is missing or stale
    # for most Saudi small/mid caps, and forward estimates barely exist here.
    # Lynch's own method uses the growth actually delivered — so we compute a
    # TRAILING PEG = P/E ÷ historical EPS growth% (our own 5y, else 3y CAGR),
    # and prefer it over Yahoo's number. Only meaningful for real growth
    # (>0%); for a flat/shrinking earner PEG is undefined (division by ~0),
    # which correctly abstains rather than fabricating a signal.
    pe = _v("pe_ratio")
    eps_growth = _v("eps_cagr_5y")
    if eps_growth is None:
        eps_growth = _v("eps_cagr_3y")
    if pe and pe > 0 and eps_growth and eps_growth > 0:
        feats["peg_ratio"] = round(pe / eps_growth, 2)  # trailing PEG wins over Yahoo forward

    # Analyst consensus upside — % the mean target sits ABOVE the live price.
    target = _v("analyst_target")
    if price and target and price > 0:
        feats["analyst_upside_pct"] = round((target - price) / price * 100, 1)

    market_cap = _v("market_cap")
    ebit = _v("ebit")
    total_debt = _v("total_debt")
    cash = _v("ending_cash")
    if market_cap and ebit is not None:
        ev = market_cap + (total_debt or 0) - (cash or 0)
        if ev and ev > 0:
            # Greenblatt's earnings yield — the other half of the Magic Formula.
            feats["earnings_yield"] = round(ebit / ev * 100, 1)
    return feats


def _category_score(hits: list, achievable_bonus: float,
                    coverage: float | None = None) -> float:
    """Normalized 0-100 for one category.

      positive = (bonus points earned / bonus points earnable on available
                  data) × POSITIVE_SPAN
      penalty  = sum of penalty points that actually fired (each a REAL
                 problem crossing a bad-territory threshold, not merely a
                 missed bonus)
      score    = BASE + positive − penalty

    A company with strong-but-sparse data that aces the few signals it does
    report reaches ~100 on this category (Confidence Score, separately,
    tells the user how thin that data was) — instead of being capped near
    50 for lines the provider simply never returned."""
    earned_bonus = sum(h.points for h in hits if h.kind == "bonus")
    penalty = sum(-h.points for h in hits if h.kind == "penalty")  # positive magnitude
    positive = (earned_bonus / achievable_bonus * POSITIVE_SPAN) if achievable_bonus > 0 else 0.0
    # ══ سقفُ العقوبات في الفئة الواحدة ══
    # تكدُّسُ العقوبات يدفع الفئةَ إلى الصفر فينفخ انحرافَ التوزيع — وشركةٌ
    # عند الصفر لا تختلف عن أخرى عند الصفر مهما تفاوتتا. فالسقفُ يُبقي
    # التمييز حيث يهمّ ولا يُلغي الإشارة.
    penalty = min(penalty, MAX_CATEGORY_PENALTY)
    raw = BASE_SCORE + positive - penalty
    # ══ غيابُ الدليل ليس دليلَ سلامة ══ (مراجعةٌ خارجية، وبرهانُها حسابيّ)
    # المقامُ `achievable_bonus` لا يُحتسب إلا للقواعد التي **وُجدت
    # بياناتها**. فشركةٌ لها قاعدةُ أمانٍ واحدة قابلة للقياس ونجحت فيها
    # تخرج بدرجة **مئة من مئة** — وتعبر بوّابة «شراء قوي» بيسرٍ أكبر من
    # شركةٍ أفصحت عن خمسة بنود ونجحت في أربعة. والانحيازُ ليس عشوائياً:
    # يميل إلى الشركات الصغيرة ضعيفة التغطية، وهي حيث تلزم الحماية أشدّ.
    # ولا يصحّ **العقاب** على النقص — مصدرُه أنبوبُنا غالباً لا الشركة —
    # بل **الانكماشُ نحو الأساس** بجذر التغطية: الخطأُ المعياريّ لمتوسّطٍ
    # يتناسب عكسياً مع جذر العدد، فالانكماشُ بجذر التغطية يطابق محتوى
    # المعلومة. (تغطية ‎60٪ ودرجة ‎90 ⇒ ‎81 — لا ‎74 كما يفعل الخطّيّ.)
    if coverage is not None and 0 < coverage < 1:
        raw = BASE_SCORE + (raw - BASE_SCORE) * (coverage ** 0.5)
    return max(0, min(100, round(raw)))


def compute_four_scores(features: dict, sector: Optional[str] = None) -> FourScores:
    result = governance_rules.evaluate(features, sector=sector)

    if result.rejected():
        return FourScores(
            rejected=True,
            hard_filter_message=result.hard_filter.message,
            quality=CategoryScore(0, []),
            valuation=CategoryScore(None, []),
            safety=CategoryScore(0, []),
            timing=CategoryScore(None, []),
        )

    scores = {}
    for cat in ("quality", "valuation", "safety", "timing"):
        hits = result.hits_by_category.get(cat, [])
        achievable = result.achievable_bonus_by_category.get(cat, 0)
        # A category with no measurable positive signals AND no penalties is
        # genuinely "unknown", not "average" — leave it None (irrelevant)
        # rather than asserting a base 50 the data can't support. Timing/
        # valuation legitimately hit this when price/history is missing.
        if achievable == 0 and not hits:
            scores[cat] = CategoryScore(None, [])
        else:
            total = result.total_bonus_by_category.get(cat, 0) or 0
            cov = (achievable / total) if total > 0 else None
            scores[cat] = CategoryScore(
                _category_score(hits, achievable, cov), hits, cov)

    return FourScores(rejected=False, hard_filter_message=None, **scores)


def composite_finance_score(scores: FourScores) -> Optional[int]:
    """Backward-compatible single 0-100 number for the many existing UI
    surfaces that still expect one Company.finance_score. A weighted blend
    of Quality (60%) and Safety (40%) ONLY — the two scores computable
    purely from multi-year statements, with no extra provider calls beyond
    what the scheduled refresh already fetches. Valuation/Timing are
    price-dependent and deliberately excluded from this fundamentals
    number (same reason the four scores are kept separate in the first
    place) — they're available live via the interactive Governance
    Dashboard (governance-v2) instead.

    Safety only participates when it carries a REAL signal (at least one
    rule actually fired): for banks/insurers the statement lines safety
    reads (interest coverage, current/quick ratio) are absent from the
    provider and structurally meaningless anyway, leaving safety at a
    hollow neutral that must not drag an otherwise excellent company down —
    in that case the composite rests on quality, the meaningful read."""
    if scores.rejected:
        return 0
    q = scores.quality.score
    s = scores.safety.score
    if q is None:
        return round(s) if s is not None else None
    if s is None or not scores.safety.hits:
        return round(q)  # safety uninformative → judge on quality alone
    return round(q * 0.6 + s * 0.4)


def technical_to_timing_snapshot(tech: Optional[dict]) -> Optional[dict]:
    """Adapts technical.analyze()'s output (raw SMA/RSI/MACD values) into
    the feature names governance_rules.yaml's timing rules expect. Kept
    here (not inside technical.py) since it's a Rule-Engine-specific view,
    not a change to what technical.py itself computes/returns."""
    if not tech:
        return None
    price = tech.get("price")
    sma50 = tech.get("sma50")
    sma200 = tech.get("sma200")
    macd, macd_signal_line = tech.get("macd"), tech.get("macd_signal")
    snap = {
        "trend": "up" if tech.get("trend") == "صاعد" else ("down" if tech.get("trend") == "هابط" else None),
        "rsi": tech.get("rsi"),
    }
    if macd is not None and macd_signal_line is not None:
        snap["macd_signal"] = "bullish" if macd > macd_signal_line else "bearish"
    if price is not None and sma50:
        snap["price_vs_ma50_pct"] = round((price - sma50) / sma50 * 100, 2)
    if price is not None and sma200:
        snap["price_vs_ma200_pct"] = round((price - sma200) / sma200 * 100, 2)
    return snap


def valuation_to_snapshot(info: Optional[dict], valuation_ctx: Optional[dict]) -> Optional[dict]:
    """Adapts market_data.get_company_info() + valuation.get_valuation_context()
    into the feature names governance_rules.yaml's valuation rules expect."""
    if not info and not valuation_ctx:
        return None
    snap: dict = {}
    if info:
        snap["pe_ratio"] = info.get("pe_ratio")
        snap["peg_ratio"] = info.get("peg_ratio")
        snap["ev_ebitda"] = info.get("ev_to_ebitda")
        snap["pb_ratio"] = info.get("price_to_book")
        snap["dividend_yield"] = info.get("dividend_yield")  # جوهر عائد الريت
        # For the Graham-number / Greenblatt-earnings-yield rules (computed
        # in build_features once statements + market data are merged).
        snap["price"] = info.get("current_price") or info.get("price")
        snap["market_cap"] = info.get("market_cap")
        # Real analyst consensus (Yahoo aggregator) — the honest "house
        # recommendation" surrogate: a genuine target price + buy/hold/sell,
        # never a fabricated per-firm call.
        snap["analyst_target"] = info.get("target_mean_price")
        snap["analyst_recommendation"] = info.get("recommendation")
    if valuation_ctx and valuation_ctx.get("sector_avg_pe") and snap.get("pe_ratio"):
        avg = valuation_ctx["sector_avg_pe"]
        snap["pe_vs_sector_pct"] = round((snap["pe_ratio"] - avg) / avg * 100, 2)
    return snap
