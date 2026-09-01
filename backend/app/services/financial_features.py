"""
Financial Feature Engine — Phase 1 of the governance-engine redesign.

Pure, independent layer with zero knowledge of scoring, weighting, sectors,
or the UI: given the multi-year `periods` list already returned by
market_service.get_financials(), it derives every ratio/growth/stability
metric a professional fund analyst would compute by hand. Nothing here
judges "good" or "bad" — that is the Rule Engine's job (Phase 2+). A
missing input always yields Feature(value=None, note="...") rather than a
fabricated number, so downstream consumers (rules, Confidence Score) can
tell a real 0 from data that was never available.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Feature:
    value: Optional[float]
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _cagr(first: Optional[float], last: Optional[float], years: int) -> Optional[float]:
    if first is None or last is None or years <= 0:
        return None
    if first <= 0 or last <= 0:
        return None  # CAGR is undefined starting from a negative/zero base
    return round(((last / first) ** (1 / years) - 1) * 100, 2)


def _avg(values: list) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def _stability_pct(values: list) -> Optional[float]:
    """Coefficient of variation (stdev / |mean|) as a %. Lower = more stable.
    Needs ≥3 points to mean anything — 2 points always look "perfectly
    stable" by this formula, which would be misleading."""
    vals = [v for v in values if v is not None]
    if len(vals) < 3:
        return None
    mean = sum(vals) / len(vals)
    if mean == 0:
        return None
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return round((var ** 0.5) / abs(mean) * 100, 1)


def _ratio(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den in (None, 0):
        return None
    return num / den


def compute_features(periods: list[dict]) -> dict[str, dict]:
    """periods: the raw list from market_service.get_financials()['periods'],
    any order — sorted ascending by year internally. Returns a flat dict of
    feature_name -> {"value": float|None, "note": str}."""
    periods = sorted([p for p in periods if p.get("year")], key=lambda p: p["year"])
    feats: dict[str, Feature] = {}
    if not periods:
        return {}

    n_years = len(periods)

    def series(key):
        return [p.get(key) for p in periods]

    revenue = series("revenue")
    net_income = series("net_income")
    equity = series("equity")
    eps = series("eps")
    op_cf = series("operating_cash_flow")
    fcf = series("free_cash_flow")
    debt_ratio = series("debt_ratio")
    total_assets = series("total_assets")
    gross_profit = series("gross_profit")
    operating_income = series("operating_income")
    current_assets = series("current_assets")
    current_liabilities = series("current_liabilities")
    inventory = series("inventory")
    total_debt = series("total_debt")
    interest_coverage = series("interest_coverage")
    dividends_paid = series("dividends_paid")
    shares = series("shares_outstanding")
    capex = series("capex")

    def span(n: int):
        """(first_period, last_period, actual_years) over the trailing n
        years, capped by what's actually available; None if <2 years total."""
        if n_years < 2:
            return None
        yrs = min(n, n_years - 1)
        return periods[-1 - yrs], periods[-1], yrs

    # ══ النموّ يُقاس على أطول نافذةٍ صالحة، وتُسجَّل ══
    #
    # كان يأخذ الطرفين وحدهما: الفترةَ الأولى في النافذة والأخيرة. فإن
    # غاب البندُ في إحداهما — أو كانت السنةُ الأولى خسارةً فالأساسُ غيرُ
    # موجب — سقط الحسابُ كلُّه ولو صحّت السنواتُ الوسطى. وقِيس أثرُه على
    # السوق: مكوّنُ النموّ قام لسبع عشرةَ شركةً من ‎268.
    #
    # فصار يُجرَّب من الأطول إلى الأقصر (‎5 ← ‎4 ← ‎3 ← ‎2 سنوات) ويُؤخذ
    # أوّلُ ما صحّ، **ويُسجَّل عددُ سنواته** في `growth_period_years`
    # فتنزل الثقةُ حين تقصر النافذة. ونافذةٌ دون سنتين لا تُنتج نموّاً:
    # نقطتان لا تصنعان اتّجاهاً.
    def _cagr_best(key: str, want: int) -> tuple:
        """(القيمة، سنواتُ النافذة) لأطول نافذةٍ صالحة — أو (None, None).

        والطرفُ الأخير يُثبَّت على آخر فترةٍ ورد فيها البند: تحريكُه
        يغيّر معنى «الأحدث»، وتحريكُ الأساس وحده يبحث عن أطول مدىً
        يصلح للقياس.
        """
        idx = [i for i, p in enumerate(periods)
               if isinstance(p.get(key), (int, float))]
        if len(idx) < 2:
            return None, None
        end = idx[-1]
        for start in idx:
            yrs = end - start
            if yrs < 2 or yrs > want:
                continue
            v = _cagr(periods[start].get(key), periods[end].get(key), yrs)
            if v is not None:
                return v, yrs
        return None, None

    _spans: list[int] = []
    for n, tag in ((3, "3y"), (5, "5y")):
        for feat_key, line, label in (
                ("revenue_cagr", "revenue", "نمو الإيرادات المركب"),
                ("eps_cagr", "eps", "نمو ربحية السهم المركب"),
                ("book_value_cagr", "equity", "نمو القيمة الدفترية المركب")):
            v, yrs = _cagr_best(line, n)
            if v is None:
                feats[f"{feat_key}_{tag}"] = Feature(
                    None, f"لا نافذةَ صالحة ({n_years} فترة متاحة)")
            else:
                feats[f"{feat_key}_{tag}"] = Feature(
                    v, f"{label} ({yrs} سنة فعلية)")
                if tag == "5y":
                    _spans.append(yrs)
    feats["growth_period_years"] = Feature(
        max(_spans) if _spans else None,
        "طولُ النافذة التي قِيس عليها النموّ فعلاً — أقصرُ من خمسٍ تخفض الثقة")

    # ── Profitability / returns ────────────────────────────────────
    # ══ العائدُ ينقلب إشارةً على حقوقٍ سالبة ══ (كشفه `decide.py` — D137)
    # ‏`صافي الربح ÷ حقوق الملكية` يفترض مقاماً موجباً. فحين تكون الحقوقُ
    # سالبة تنقلب الإشارة: شركةٌ خاسرةٌ ‎50 على حقوقٍ ‎−10 تُظهر **‎+500٪
    # عائداً**، فيُقرأ الأسوأُ أفضلَ ويُرتَّب في قمّة قطاعه. وهذا خطأُ
    # حسابٍ لا تطرّفٌ اقتصاديّ، ولا يُعالَج بقصٍّ ولا بتشذيب.
    #
    # فالمقامُ غيرُ الموجب يُعلن المؤشّرَ غيرَ منطبق. أمّا الحقوقُ
    # **الضئيلةُ الموجبة** فتُنتج عائداً متطرّفاً صحيحاً حسابياً
    # (‏−7230٪ مثلاً) — فيبقى كما هو: ملاحظةٌ مالية حقيقية، والترتيبُ
    # بالرتب لا بالقيَم فلا يفسدها طرفٌ واحد.
    roe_series = [(ni / eq * 100.0)
                  if (ni is not None and eq is not None and eq > 0) else None
                  for ni, eq in zip(net_income, equity)]
    feats["roe"] = Feature(roe_series[-1], "العائد على حقوق الملكية (آخر سنة)")
    feats["roe_avg"] = Feature(_avg(roe_series), "متوسط العائد على حقوق الملكية عبر السنوات المتاحة")

    # ── اتّجاهُ الربحية — تطلبه المواصفة ركناً في نموذج المالية ──
    # فرقُ آخر عائدٍ عن متوسّط ما قبله: موجبٌ يعني ربحيةً تتحسّن، وسالبٌ
    # يعني تآكلاً. ولا يقوم بأقلّ من ثلاث سنواتٍ — نقطتان تُنتجان فرقاً
    # لا اتّجاهاً. ولا بندَ جديداً يُطلب من المصدر: يُشتقّ من السلسلة
    # المحسوبة أصلاً.
    _roe_seen = [r for r in roe_series if r is not None]
    if len(_roe_seen) >= 3:
        _prior = _roe_seen[:-1]
        feats["roe_trend"] = Feature(
            round(_roe_seen[-1] - sum(_prior) / len(_prior), 2),
            "اتجاه الربحية (آخر عائد ناقص متوسط ما قبله — موجب = تحسّن)")
    else:
        feats["roe_trend"] = Feature(None, "بيانات غير كافية (أقل من ثلاث سنوات)")

    roa_series = [_ratio(ni, ta) for ni, ta in zip(net_income, total_assets)]
    roa_series = [r * 100 if r is not None else None for r in roa_series]
    feats["roa"] = Feature(roa_series[-1], "العائد على الأصول (آخر سنة)")

    # ROIC ≈ NOPAT / Invested Capital, with invested capital ≈ equity + total debt
    roic_series = []
    for ni, eq, td in zip(net_income, equity, total_debt):
        ic = (eq or 0) + (td or 0) if eq is not None or td is not None else None
        roic_series.append(ni / ic * 100 if ni is not None and ic else None)
    feats["roic"] = Feature(roic_series[-1], "العائد على رأس المال المستثمر (تقريبي: صافي الربح ÷ (حقوق الملكية + الدين))")
    feats["capital_efficiency"] = Feature(_avg(roic_series), "متوسط كفاءة رأس المال (ROIC) عبر السنوات")
    valid_roic = [r for r in roic_series if r is not None]
    if len(valid_roic) >= 2:
        feats["roic_trend"] = Feature(round(roic_series[-1] - next(r for r in roic_series if r is not None), 2)
                                       if roic_series[-1] is not None else None,
                                       "تغيّر ROIC من أول سنة متاحة إلى الأحدث (موجب = تحسّن)")
    else:
        feats["roic_trend"] = Feature(None, "بيانات غير كافية")

    gross_margin = [_ratio(gp, rev) for gp, rev in zip(gross_profit, revenue)]
    gross_margin = [m * 100 if m is not None else None for m in gross_margin]
    feats["gross_margin"] = Feature(gross_margin[-1], "هامش الربح الإجمالي")
    feats["margin_stability_gross"] = Feature(_stability_pct(gross_margin), "استقرار الهامش الإجمالي (أقل = أكثر استقراراً)")

    operating_margin = [_ratio(oi, rev) for oi, rev in zip(operating_income, revenue)]
    operating_margin = [m * 100 if m is not None else None for m in operating_margin]
    feats["operating_margin"] = Feature(operating_margin[-1], "هامش الربح التشغيلي")

    net_margin = [_ratio(ni, rev) for ni, rev in zip(net_income, revenue)]
    net_margin = [m * 100 if m is not None else None for m in net_margin]
    feats["net_margin"] = Feature(net_margin[-1], "هامش صافي الربح")
    feats["margin_stability"] = Feature(_stability_pct(net_margin), "استقرار صافي هامش الربح عبر السنوات (أقل = أكثر استقراراً)")

    fcf_margin = [_ratio(x, rev) for x, rev in zip(fcf, revenue)]
    fcf_margin = [m * 100 if m is not None else None for m in fcf_margin]
    feats["fcf_margin"] = Feature(fcf_margin[-1], "هامش التدفق النقدي الحر")

    # ── CapEx-aware read of a low FCF margin ────────────────────────
    # A low/negative FCF margin funded by *expansionary* CapEx (rising
    # investment alongside improving revenue and operating income) is a
    # growth signal, not a distress signal — so it's split into two
    # mutually-exclusive derived features the Rule Engine can penalize at
    # different severities, instead of one blanket "low FCF is bad" rule.
    capex_abs = [abs(c) if c is not None else None for c in capex]
    capex_growth = None
    if len(capex_abs) >= 2 and capex_abs[0] and capex_abs[-1] is not None:
        capex_growth = (capex_abs[-1] / capex_abs[0] - 1) * 100 if capex_abs[0] else None
    revenue_improving = len(revenue) >= 2 and revenue[-1] is not None and revenue[0] is not None and revenue[-1] > revenue[0]
    operating_income_improving = (len(operating_income) >= 2 and operating_income[-1] is not None
                                   and operating_income[0] is not None and operating_income[-1] > operating_income[0])
    is_expansionary = bool(capex_growth is not None and capex_growth > 15 and revenue_improving and operating_income_improving)
    feats["capex_expansionary"] = Feature(1.0 if is_expansionary else 0.0,
        "توسّع رأسمالي حقيقي: ارتفاع CapEx مصحوب بتحسّن الإيرادات والربح التشغيلي" if is_expansionary
        else "لا يوجد توسّع رأسمالي واضح يفسّر ضعف التدفق النقدي الحر")

    low_margin_threshold = 3.0  # % — below this, FCF margin is "thin" enough to flag
    latest_fcf_margin = fcf_margin[-1]
    if latest_fcf_margin is not None and latest_fcf_margin < low_margin_threshold:
        if is_expansionary:
            feats["fcf_low_explained_by_capex"] = Feature(latest_fcf_margin, "هامش تدفق نقدي منخفض لكنه مفسَّر بتوسع رأسمالي حقيقي — عقوبة مخفَّفة")
            feats["fcf_low_unexplained"] = Feature(None, "غير منطبق — الانخفاض مفسَّر بتوسع رأسمالي")
        else:
            feats["fcf_low_unexplained"] = Feature(latest_fcf_margin, "هامش تدفق نقدي حر منخفض دون أي مؤشر توسع رأسمالي يفسّره")
            feats["fcf_low_explained_by_capex"] = Feature(None, "غير منطبق")
    else:
        feats["fcf_low_unexplained"] = Feature(None, "غير منطبق — الهامش ليس منخفضاً")
        feats["fcf_low_explained_by_capex"] = Feature(None, "غير منطبق — الهامش ليس منخفضاً")

    # ── Cash quality ───────────────────────────────────────────────
    ccr = [_ratio(ocf, ni) for ocf, ni in zip(op_cf, net_income)]
    feats["cash_conversion_ratio"] = Feature(round(ccr[-1], 2) if ccr[-1] is not None else None, "التدفق النقدي التشغيلي ÷ صافي الربح — كلما اقترب من 1 أو زاد كانت جودة الأرباح أعلى")

    accrual = []
    for ni, ocf, ta in zip(net_income, op_cf, total_assets):
        accrual.append((ni - ocf) / ta * 100 if ni is not None and ocf is not None and ta else None)
    feats["accrual_ratio"] = Feature(accrual[-1], "نسبة الاستحقاق — كلما ارتفعت زادت شكوك جودة الأرباح (أرباح دفترية لا يدعمها نقد فعلي)")

    # ── Balance-sheet health ───────────────────────────────────────
    if n_years >= 2 and debt_ratio[-1] is not None and debt_ratio[0] is not None:
        feats["debt_trend"] = Feature(round(debt_ratio[-1] - debt_ratio[0], 3), "تغيّر نسبة الدين إلى الأصول من أول سنة متاحة إلى الأحدث (سالب = تحسّن)")
    else:
        feats["debt_trend"] = Feature(None, "بيانات غير كافية")

    # ══ سقفٌ لتغطية الفوائد ══ (كشفه المسبار على السوق)
    # خرجت «دار الأركان» بتغطيةِ ‎1,473× ورتبةٍ في المئين ‎93 — ومطوّرٌ
    # مثقلٌ بالدَّين لا تكون تغطيتُه ألفاً وأربعمئة ضعف. والسببُ أن
    # مصروفَ الفائدة يقارب الصفر في القائمة (يُرسمَل على المشاريع بدل أن
    # يُصرَف)، فينفجر القسمة. وفوق خمسين ضعفاً لا فرقَ عملياً بين رقمٍ
    # ورقم: الدَّينُ مغطّىً بلا إشكال. فيُسقَّف عندها، فلا يُكافأ رقمٌ
    # مصدرُه خللٌ محاسبيّ بترتيبٍ في القمّة.
    _ic = interest_coverage[-1]
    if isinstance(_ic, (int, float)) and _ic > 50:
        _ic = 50.0
    feats["interest_coverage"] = Feature(_ic, "تغطية الفوائد (EBIT ÷ مصروف الفوائد) — مسقوفة عند 50×")

    current_ratio = [_ratio(ca, cl) for ca, cl in zip(current_assets, current_liabilities)]
    feats["current_ratio"] = Feature(round(current_ratio[-1], 2) if current_ratio[-1] is not None else None, "نسبة التداول (الأصول المتداولة ÷ الالتزامات المتداولة)")

    quick_ratio = []
    for ca, cl, inv in zip(current_assets, current_liabilities, inventory):
        quick_ratio.append((ca - inv) / cl if ca is not None and cl not in (None, 0) and inv is not None else None)
    feats["quick_ratio"] = Feature(round(quick_ratio[-1], 2) if quick_ratio[-1] is not None else None, "نسبة السيولة السريعة (تستثني المخزون)")

    asset_turnover = [_ratio(rev, ta) for rev, ta in zip(revenue, total_assets)]
    feats["asset_turnover"] = Feature(round(asset_turnover[-1], 2) if asset_turnover[-1] is not None else None, "معدل دوران الأصول (الإيرادات ÷ إجمالي الأصول)")

    # ── Shareholder-friendliness ────────────────────────────────────
    if n_years >= 2 and shares[-1] is not None and shares[0] not in (None, 0):
        feats["share_dilution"] = Feature(round((shares[-1] / shares[0] - 1) * 100, 2), "تغيّر عدد الأسهم القائمة (موجب = تخفيف للمساهمين)")
    else:
        feats["share_dilution"] = Feature(None, "بيانات غير كافية")

    div_span = span(5) or span(3)
    if div_span:
        first, last, yrs = div_span
        fd = abs(first["dividends_paid"]) if first.get("dividends_paid") is not None else None
        ld = abs(last["dividends_paid"]) if last.get("dividends_paid") is not None else None
        feats["dividend_growth"] = Feature(_cagr(fd, ld, yrs), "نمو إجمالي التوزيعات النقدية المدفوعة")
    else:
        feats["dividend_growth"] = Feature(None, "بيانات غير كافية")

    # ── Payout Ratio = التوزيعات ÷ صافي الربح — «أمان التوزيعات» (منهج تداول) ─
    # السوق السعودي يعشق التوزيعات، لكن العائد المرتفع ليس بالضرورة آمناً:
    # المهم أن نسبة التوزيع لا تلتهم كل الربح (سقف صحي ~70–80%) فيبقى للشركة
    # فائضٌ للنمو والاستمرار. نحسبها من متوسط السنتين الأخيرتين المتاحتين
    # لتفادي تشوّه سنة واحدة، مقابل متوسط صافي الربح لنفس المدة.
    _div_recent = [abs(d) for d in dividends_paid[-2:] if d is not None and d != 0]
    _ni_recent = [ni for ni in net_income[-2:] if ni is not None and ni > 0]
    if _div_recent and _ni_recent:
        payout = sum(_div_recent) / len(_div_recent) / (sum(_ni_recent) / len(_ni_recent)) * 100
        feats["payout_ratio"] = Feature(round(payout, 1), "نسبة توزيع الأرباح (التوزيعات ÷ صافي الربح) — أمان واستدامة التوزيع")
    else:
        feats["payout_ratio"] = Feature(None, "غير محتسب (لا توزيعات أو لا ربحية موجبة)")

    # ── Stability / consistency ──────────────────────────────────────
    feats["earnings_stability"] = Feature(_stability_pct(net_income), "استقرار صافي الربح عبر السنوات (أقل = أكثر استقراراً)")
    feats["eps_stability"] = Feature(_stability_pct(eps), "استقرار ربحية السهم عبر السنوات (أقل = أكثر استقراراً)")
    feats["roe_stability"] = Feature(_stability_pct(roe_series), "استقرار العائد على حقوق الملكية عبر السنوات (أقل = أكثر استقراراً)")
    feats["fcf_stability"] = Feature(_stability_pct(fcf), "استقرار التدفق النقدي الحر عبر السنوات (أقل = أكثر استقراراً)")
    feats["years_available"] = Feature(n_years, "عدد السنوات المتاحة في القوائم المالية")
    # ══ العدُّ على سلسلةٍ لم تصل يُخرج صفراً لا امتناعاً ══
    #
    # كان `sum(...)` يمرّ على قائمةٍ كلُّها `None` فيعيد **صفراً**، فشركةٌ
    # لم يرد عنها بندُ التوزيع تُسجَّل «صفرُ سنواتِ توزيع» — رقمٌ يُقرأ
    # متاحاً ثم يُرتَّب في قاع القطاع. فاجتمع الممنوعان: الناقصُ صار
    # صفراً، ثم صار عقوبة. وكشفه المالك من تناقضٍ في التدقيق: سنواتُ
    # التوزيع متاحةٌ لـ‎268 شركة، وبندُ التوزيع غائبٌ عن ‎74 منها.
    #
    # والفرقُ الذي يجب حفظُه: بندٌ ورد بقيمة صفرٍ يعني **لم توزّع**،
    # وبندٌ لم يرد يعني **لا نعلم**. والأوّلُ حكمٌ والثاني صمت.
    _ni_seen = [ni for ni in net_income if ni is not None]
    feats["profitable_years"] = Feature(
        sum(1 for ni in _ni_seen if ni > 0) if _ni_seen else None,
        "عدد سنوات الربحية من أصل السنوات المتاحة")
    _dv_seen = [d for d in dividends_paid if d is not None]
    feats["dividend_years"] = Feature(
        sum(1 for d in _dv_seen if d != 0) if _dv_seen else None,
        "عدد سنوات دفع التوزيعات من أصل السنوات المتاحة")

    # ═══════════════════════════════════════════════════════════════════
    # معايير رواد الاستثمار (Expert frameworks) — تحكيم مُثبَّت أكاديمياً
    # وعملياً بدل عتبات عامة. كل معيار قابل للتفسير ويعود لمرجعه.
    # ═══════════════════════════════════════════════════════════════════
    total_liabilities = series("total_liabilities")
    operating_income_s = series("operating_income")

    # ── Piotroski F-Score (0-9) — مِعيار جودة/قوة مالية أكاديمي شهير ─────
    # يُختبر منه فقط ما تتوفر بياناته؛ نُبقي عدد المُختبَر (f_applicable)
    # لأمانة القراءة (٩/٩ ليست كـ ٧/٧).
    f_score = 0
    f_applicable = 0
    f_hits: list[str] = []

    def _f(cond: bool | None, label: str):
        nonlocal f_score, f_applicable
        if cond is None:
            return
        f_applicable += 1
        if cond:
            f_score += 1
            f_hits.append(label)

    roa_series = [_ratio(ni, ta) for ni, ta in zip(net_income, total_assets)]
    cur_series = [_ratio(ca, cl) for ca, cl in zip(current_assets, current_liabilities)]
    turnover_series = [_ratio(rev, ta) for rev, ta in zip(revenue, total_assets)]
    gm_series = [_ratio(gp, rev) for gp, rev in zip(gross_profit, revenue)]

    _f(net_income[-1] > 0 if net_income[-1] is not None else None, "ربحية موجبة")
    _f(op_cf[-1] > 0 if op_cf[-1] is not None else None, "تدفق تشغيلي موجب")
    _f((roa_series[-1] > roa_series[-2]) if (n_years >= 2 and roa_series[-1] is not None and roa_series[-2] is not None) else None, "تحسّن العائد على الأصول")
    _f((op_cf[-1] > net_income[-1]) if (op_cf[-1] is not None and net_income[-1] is not None) else None, "جودة أرباح (تدفق>ربح)")
    _f((debt_ratio[-1] < debt_ratio[-2]) if (n_years >= 2 and debt_ratio[-1] is not None and debt_ratio[-2] is not None) else None, "تراجع الرافعة المالية")
    _f((cur_series[-1] > cur_series[-2]) if (n_years >= 2 and cur_series[-1] is not None and cur_series[-2] is not None) else None, "تحسّن السيولة")
    _f((shares[-1] <= shares[-2]) if (n_years >= 2 and shares[-1] is not None and shares[-2] not in (None, 0)) else None, "لا تخفيف أسهم")
    _f((gm_series[-1] > gm_series[-2]) if (n_years >= 2 and gm_series[-1] is not None and gm_series[-2] is not None) else None, "تحسّن الهامش الإجمالي")
    _f((turnover_series[-1] > turnover_series[-2]) if (n_years >= 2 and turnover_series[-1] is not None and turnover_series[-2] is not None) else None, "تحسّن كفاءة الأصول")

    feats["piotroski_f_score"] = Feature(f_score if f_applicable else None,
        f"Piotroski F-Score = {f_score}/{f_applicable} معيار مُختبَر (بيوتروسكي — القوة المالية)" if f_applicable else "بيانات غير كافية")
    feats["piotroski_applicable"] = Feature(f_applicable or None, "عدد معايير بيوتروسكي القابلة للاختبار بالبيانات المتاحة")

    # ── Altman Z''-Score — نموذج التنبؤ بالتعثر (النسخة المعدّلة للأسواق
    # الناشئة/غير الصناعية). لا يُطبَّق على البنوك/التأمين (يُعطَّل عبر النمط).
    # الأرباح المحتجزة مُقرَّبة بمجموع الأرباح الموجبة في النافذة المتاحة.
    ta_l = total_assets[-1]
    wc = (current_assets[-1] - current_liabilities[-1]) if (current_assets[-1] is not None and current_liabilities[-1] is not None) else None
    ebit = operating_income_s[-1]  # EBIT ≈ الربح التشغيلي
    tl_l = total_liabilities[-1]
    eq_l = equity[-1]
    re_proxy = sum(ni for ni in net_income if ni is not None and ni > 0)
    if ta_l and ta_l > 0 and wc is not None and ebit is not None and tl_l and eq_l is not None:
        x1, x2, x3, x4 = wc / ta_l, re_proxy / ta_l, ebit / ta_l, eq_l / tl_l
        z = 3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
        feats["altman_z"] = Feature(round(z, 2), "Altman Z''-Score (ألتمان — التنبؤ بالتعثر): >2.6 آمن، 1.1–2.6 رمادي، <1.1 خطر")
    else:
        feats["altman_z"] = Feature(None, "بيانات غير كافية لاحتساب Altman Z")

    # ── Graham Number = √(22.5 × الربحية المُطبَّعة × القيمة الدفترية للسهم) —
    # سقف القيمة العادلة عند جراهام. المقارنة بالسعر تتم في طبقة التقييم.
    #
    # معايرة للسوق السعودي (سوق دوري قليل السيولة): جراهام نفسه أوصى بألا
    # يُبنى التقييم على ربحية سنة واحدة بل على *متوسط ربحية* عبر دورة كاملة
    # (7–10 سنوات مثالياً)، لأن سنة قمة أو قاع في قطاع دوري (بتروكيماويات،
    # أسمنت، حديد) تُنتج «قيمة عادلة» وهمية. لذا نستخدم متوسط ربحية السهم
    # على السنوات المتاحة (حتى 5) بدل eps[-1] — فيصبح الرقم منطقياً عبر
    # الدورة بدل أن يقفز مع ربح سنة استثنائية. للشركات المستقرة المتوسط ≈
    # السنة الأخيرة، فالتعديل آمن لكل القطاعات لا الدورية وحدها.
    eps_hist = [e for e in eps[-5:] if e is not None]
    normalized_eps = (sum(eps_hist) / len(eps_hist)) if eps_hist else None
    feats["normalized_eps"] = Feature(
        round(normalized_eps, 3) if normalized_eps is not None else None,
        f"ربحية السهم المُطبَّعة (متوسط {len(eps_hist)} سنة — منهج جراهام الأصلي عبر الدورة)" if eps_hist else "بيانات غير كافية")
    bvps = _ratio(equity[-1], shares[-1])
    feats["book_value_per_share"] = Feature(round(bvps, 2) if bvps is not None else None, "القيمة الدفترية للسهم")
    if normalized_eps is not None and normalized_eps > 0 and bvps is not None and bvps > 0:
        feats["graham_number"] = Feature(round((22.5 * normalized_eps * bvps) ** 0.5, 2), "رقم جراهام (بربحية مُطبَّعة عبر الدورة) — سقف القيمة العادلة")
    else:
        feats["graham_number"] = Feature(None, "غير محتسب (يتطلب ربحية مُطبَّعة وقيمة دفترية موجبتين)")

    # ── Greenblatt Return on Capital = EBIT / رأس المال المستثمر
    # (رأس المال المستثمر ≈ إجمالي الأصول − الالتزامات المتداولة). EBIT/EV
    # (عائد الأرباح) يُحتسب في طبقة التقييم لحاجته للقيمة السوقية.
    if ebit is not None and ta_l and current_liabilities[-1] is not None:
        invested = ta_l - current_liabilities[-1]
        feats["return_on_capital"] = Feature(round(ebit / invested * 100, 1) if invested else None,
            "العائد على رأس المال (جرينبلات) = EBIT ÷ رأس المال المستثمر")
    else:
        feats["return_on_capital"] = Feature(None, "بيانات غير كافية")
    feats["ebit"] = Feature(ebit, "الربح التشغيلي (EBIT) — لاحتساب عائد الأرباح")

    # ── Warren Buffett — قائمة تحقّق الجودة الدائمة والخندق التنافسي ─────
    # ليست مؤشراً واحداً بل مجموعة معايير بافيت المعروفة: عائد مستدام على
    # حقوق الملكية، هامش مرتفع ومستقر (قوة تسعير = خندق)، دين يمكن سداده،
    # وتوليد نقد حر دون تخفيف للمساهمين. يُختبر منها ما تتوفر بياناته.
    b_score = 0
    b_applicable = 0

    def _b(cond: bool | None):
        nonlocal b_score, b_applicable
        if cond is None:
            return
        b_applicable += 1
        if cond:
            b_score += 1

    roe_avg_v = feats["roe_avg"].value
    gm_stab_v = feats["margin_stability_gross"].value
    dil_v = feats["share_dilution"].value
    _b((roe_avg_v >= 15) if roe_avg_v is not None else None)                 # عائد مستدام ≥15%
    _b((gross_margin[-1] >= 40) if gross_margin[-1] is not None else None)   # هامش إجمالي مرتفع (خندق)
    _b((gm_stab_v <= 15) if gm_stab_v is not None else None)                 # ثبات الهامش (قوة تسعير دائمة)
    _b((net_margin[-1] >= 10) if net_margin[-1] is not None else None)       # هامش صافي صحي
    _b((debt_ratio[-1] <= 0.5) if debt_ratio[-1] is not None else None)      # دين محدود يمكن سداده
    _b((fcf_margin[-1] > 0) if fcf_margin[-1] is not None else None)         # توليد تدفق نقدي حر
    _b((dil_v <= 0) if dil_v is not None else None)                          # لا تخفيف للمساهمين

    feats["buffett_quality_score"] = Feature(b_score if b_applicable else None,
        f"معايير بافيت للجودة الدائمة = {b_score}/{b_applicable} (عائد مستدام + خندق تنافسي + دين محدود + تدفق حر)" if b_applicable else "بيانات غير كافية")
    feats["buffett_applicable"] = Feature(b_applicable or None, "عدد معايير بافيت القابلة للاختبار بالبيانات المتاحة")

    # ── Consistency Engine (المرحلة 9) ──────────────────────────────
    # مؤشر واحد يلخّص كل مقاييس الاستقرار أعلاه في رقم 0-100 — ليس قاعدة
    # عقوبة/مكافأة بذاته، بل مدخل جاهز لدرجة الثقة (Confidence Score) ولوحة
    # الحوكمة لاحقاً. كل مؤشر تذبذب (CV%) يُحوَّل لدرجة فرعية (كلما زاد
    # التذبذب انخفضت)، ويُضاف إليها معدّل سنوات الربحية كمكوّن مستقل.
    def _cv_to_subscore(cv):
        return None if cv is None else max(0.0, min(100.0, 100 - cv * 2))

    sub_scores = [
        _cv_to_subscore(feats["earnings_stability"].value),
        _cv_to_subscore(feats["eps_stability"].value),
        _cv_to_subscore(feats["roe_stability"].value),
        _cv_to_subscore(feats["fcf_stability"].value),
        _cv_to_subscore(feats["margin_stability"].value),
        _cv_to_subscore(feats["margin_stability_gross"].value),
    ]
    # وسنواتُ الربحية قد تكون غيرَ متاحة (لم يصل صافي الربح لسنةٍ واحدة)،
    # فالنسبةُ عندها غيرُ متاحةٍ كذلك — ولا تُحسب صفراً.
    _py = feats["profitable_years"].value
    profitable_ratio = (_py / n_years * 100) if (n_years and _py is not None) else None
    available = [s for s in sub_scores if s is not None]
    if available:
        stability_component = sum(available) / len(available)
        consistency = stability_component * 0.75 + (profitable_ratio or stability_component) * 0.25
        feats["consistency_index"] = Feature(
            round(consistency, 1),
            f"مؤشر استقرار مركّب من {len(available)} مقياس تذبذب + معدّل سنوات الربحية"
        )
    else:
        feats["consistency_index"] = Feature(None, "بيانات غير كافية لاحتساب مؤشر الاستقرار")

    return {k: v.to_dict() for k, v in feats.items()}
