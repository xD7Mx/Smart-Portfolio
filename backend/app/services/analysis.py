"""
Automatic company analysis engine.

Given a symbol it gathers price + full multi-year financial statements +
price history (all through the cached provider layer), then computes — with
no button and no user input —:
  • a financial score + Arabic verdict, both the EXACT SAME real,
    statement-based analysis shown on the governance page (scores.py) — not
    a separate single-snapshot heuristic. The AI's number is always
    traceable to the same rows the investor is looking at.
  • a technical score + verdict (from technical.py)
  • strengths / weaknesses derived from the same real signals
  • a valuation read (current P/E & P/B vs. sector peers) — kept as a
    SEPARATE field, deliberately not blended into the score: "is this
    company healthy" and "is this a good price right now" are two
    different questions and conflating them would obscure both answers.
  • a combined AI score /100 (financial + technical only)
  • an investment decision (شراء / تجميع / احتفاظ / تقليل / بيع)

Everything is rule-based, so it always produces a result whenever data
exists — Gemini is used only for an optional Arabic narrative on top. The
whole analysis is cached 24h so a page open costs no extra provider calls
after the first.
"""

from typing import Optional
from app.services import cache

ANALYSIS_TTL = 24 * 60 * 60


async def _financial_from_statements(
    symbol: str, sector: str | None = None,
    valuation_snapshot: dict | None = None, timing_snapshot: dict | None = None,
    info: dict | None = None, allow_supplement: bool = True,
) -> dict:
    """Financial score/verdict/strengths/weaknesses — delegates entirely to
    the redesigned governance engine (Feature Engine → Rule Engine → four
    scores → Decision Engine → Explainability), so this is never a second,
    drifting opinion about the same company. "score" here stays the
    fundamentals-only composite (Quality+Safety — see
    four_scores.composite_finance_score) for backward compatibility with
    every existing caller of this dict's shape."""
    from app.services.market_data import market_service
    from app.services.four_scores import build_features, compute_four_scores, composite_finance_score
    from app.services.decision_engine import evaluate_decision
    from app.services.explainability import explain
    from app.services.financial_narrative import rule_based_narrative

    from app.services.expert_panel import build_expert_panel
    from app.services.confidence import compute_confidence

    data = await market_service.get_financials(symbol, allow_supplement=allow_supplement)
    periods = (data or {}).get("periods") or []
    # المصدرُ الواحد للسمات — هو نفسه الذي يقرأ منه محرّك الحوكمة، فلا
    # تختلف الشركةُ الواحدة بين شاشتين.
    from app.services.four_scores import build_company_features
    features, info, _ = build_company_features(
        periods, info=info, sector=sector,
        valuation_snapshot=valuation_snapshot, timing_snapshot=timing_snapshot)
    four = compute_four_scores(features, sector=sector)

    # ══ محرّكُ المواصفة يحكم ويُعرض — لا يُحسب في الظلّ ══
    # عطبٌ رآه المالك بعد يومين: أعدنا هيكلةَ الحوكمة إلى اثني عشر نمطاً
    # ببطاقاتٍ مستقلّة، ثم بقيت الدرجةُ المعروضة تأتي من المحرّك القديم
    # لأن المواصفةَ كانت تُحسب في حقلٍ جانبيّ «للقياس ولا تحكم بعد». وكان
    # هذا تحفّظاً مقصوداً — ألّا نبدّل قبل أن نقيس — لكنّه في الأثر جعل
    # كلَّ ضبطٍ للمواصفة يجري في محرّكٍ لا يراه أحد: يضبط المهندسُ رقماً
    # ولا يتغيّر في الشاشة شيء. وتحفّظٌ لا ينتهي إلى تبديلٍ ليس تحفّظاً
    # بل تعطيل.
    #
    # فبطاقةُ النمط هي **قراءةُ الجودة** لهذه الورقة: هي التي تعرف أن
    # البنكَ يُقاس بكفاية رأس المال والتعثّر، والريتَ بالإشغال والتوزيع،
    # والسلعيَّ بالعائد عبر الدورة. فتحلّ محلَّ ركن الجودة القديم — الذي
    # كان قواعدَ عامّة يُعطَّل بعضُها لبعض الأنماط.
    #
    # ويبقى ركنُ الأمان والتقييم والتوقيت من المحرّك القديم: بطاقةُ النمط
    # لا تغطّيها، وحذفُها خسارةٌ بلا مقابل.
    #
    # وحين تمتنع المواصفة (نمطٌ لا يُحلّ · لا ركنَ مقيساً) لا يُخترع بديل:
    # يعود ركنُ الجودة القديم كما هو، ويُقال في المخرَج أيُّ محرّكٍ حكم.
    spec = None
    try:
        from app.services import spec_score as _spec
        spec = _spec.compute(features, sector)
    except Exception:                                             # noqa: BLE001
        spec = None

    # ══ الخطوطُ الحمراء تُبطِل ولا تُخصم ══
    # الترتيبُ في القطاع نسبيّ: أسوأُ قطاعٍ يبقى فيه «الأفضل». فوقائعُ
    # مطلقة — خسارةٌ ثلاثَ سنوات · تدفّقٌ سالبٌ خمساً · فائدةٌ لا تُغطّى ·
    # تخفيفٌ يبتلع حصّةَ المساهم — تُستبعد بها الورقةُ ولا تُرتَّب.
    # والخصمُ من درجةٍ يذوب في المتوسّط، والاستبعادُ لا يذوب.
    from app.services import red_lines as _rl
    _arch = spec.archetype if spec is not None else None
    lines = _rl.check(features, periods, _arch)

    # ══ ركنُ الحوكمة بمعناه الذي يضرّ المساهم ══
    # تركّزُ الملكية · التداولُ الحرّ · تخفيفُ الحصّة · تمويلُ التوزيع.
    from app.services import governance_pillar as _gp
    _own = None
    try:
        _own = await market_service.get_ownership(symbol)
    except Exception:                                             # noqa: BLE001
        _own = None
    # ══ إجراءاتُ الشركة من «أرقام» ══ (D225)
    # تُقرأ لتملأ عمى ركنِ التخفيف حيث تغيب سلسلةُ الأسهم القائمة. ومُكيَّشةٌ
    # يوماً كاملاً: إجراءُ شركةٍ لا يتغيّر في ساعة، وجلبُه مع كلّ تحليلٍ
    # يُثقل الصفحةَ ويضغط المصدر. وغيابُها يترك الركنَ أعمى كما كان — لا
    # يُسقط التحليل.
    _actions = None
    try:
        from app.services import cache as _c
        _ak = f"argaam:actions:{symbol}"
        _actions = _c.get(_ak)
        if _actions is None:
            from app.services.argaam_calendar import fetch_company_page
            _pg = await fetch_company_page(str(symbol).replace(".SR", ""))
            _actions = (_pg.get("calendar") or []) + (_pg.get("disclosures") or [])
            _c.set(_ak, _actions, 24 * 3600)
    except Exception as e:                                        # noqa: BLE001
        logger.debug(f"إجراءات أرقام {symbol}: {type(e).__name__}: {e}")
        _actions = None
    gov_pillar = _gp.build(features, periods, _own, _actions)

    # ══ منطقُ بطاقة السلامة هو المنطقُ العامّ ══ (بأمر المالك)
    # كان ركنُ الجودة يُستبدَل هنا بدرجة «المواصفة» بعد حسابه، وبطاقةُ
    # الحوكمة (‏`governance_engine`) لا تفعل ذلك. فخرجت الشركةُ الواحدة
    # برقمين: البطاقةُ ‎67 وصفحةُ الشركة ‎74 — مقيسٌ على الشركة نفسها
    # بقوائمها نفسِها. وقال المالك إن نهج البطاقة هو ما يريده في التطبيق
    # كلِّه، فأُزيل الاستبدال وبقيت الأركانُ الأربعة كما يحسبها
    # `compute_four_scores` — وهو عينُ ما تقرؤه البطاقة. (D149)
    #
    # ودرجةُ المواصفة تبقى معروضةً بياناً للمعيار القطاعيّ المطبَّق، ولا
    # تغيّر الحكم.
    engine = "بطاقة السلامة"

    decision = evaluate_decision(four, features, sector)  # gated: abstains on thin data
    explanation = explain(four, decision)
    # الدرجةُ من المحرّك الأصليّ — نفسُها التي تعرضها بطاقةُ الحوكمة
    # وقسمُ السوق. رقمٌ واحدٌ لا يختلف باختلاف الشاشة. (D151)
    from app.services.scores import _finance_score_from_periods
    score = _finance_score_from_periods(periods)
    evaluable = decision.matched_rule_id != "insufficient_data"
    # The SAME governance outputs the panel shows — so تقييم الأداء renders the
    # identical expert consensus, four scores and confidence, never a variant.
    panel = build_expert_panel(features, sector, four)
    conf = compute_confidence(features)

    return {
        # No fabricated grade when the data can't support one.
        # ══ لا خمسينَ مختلَقة ══ (D149)
        # كانت الدرجةُ تُستبدَل بـ‎50 حين يتعذّر حسابُها والبياناتُ كافيةٌ
        # للحكم — رقمٌ لم يُقَس يُعرض كأنه قياس. والبطاقةُ تعيد العدمَ في
        # هذه الحال، فيُقال «غير متاحة» ولا يُخترع وسط.
        "score": score if evaluable else None,
        "evaluable": evaluable,
        # An analytical sentence about the statements, not a buy/avoid label
        # (the decision lives at the score). Rule-based here — the Gemini
        # layer is applied on the dedicated /financials narrative only.
        "verdict": rule_based_narrative(four, explanation),
        "strengths": list(explanation.strengths),
        "weaknesses": list(explanation.weaknesses),
        "has_statements": bool(periods),
        # The governance Decision Engine's verdict — the ONE decision this
        # company gets, reused verbatim by analyze_company below so تقييم
        # الأداء shows exactly what الحوكمة does. Not a second opinion.
        "decision": decision,
        "scores": four.to_dict(),
        "expert_panel": panel,
        "confidence": {"score": conf.score, "warning": conf.warning},
        "enriched_fields": (features.get("_enriched_fields") or {}).get("value"),
        # المحرّكُ الذي أنتج ركنَ الجودة — يُقال ولا يُخمَّن.
        "score_engine": engine,
        # وقائعُ مطلقة تُبطِل الترتيب — تُعرض أوّلاً في الشاشة.
        "red_lines": lines,
        # ركنُ الحوكمة الحقيقيّ: ملكيةٌ وتخفيفٌ وتخصيصُ رأس مال.
        "governance": gov_pillar,
        # درجةُ المواصفة بمؤشّراتها — هي ركنُ الجودة نفسه حين تحكم.
        "spec": None if spec is None else {
            "archetype": spec.archetype,
            "score": spec.score,
            "coverage": spec.coverage,
            # أساسُ الدرجة: رتبةٌ في القطاع أم عتبةٌ معلَنة.
            "basis": spec.basis,
            "blocks_buy": spec.blocks_buy,
            "metrics": [{"key": m.key, "label": m.label, "value": m.value,
                         "score": round(m.score), "weight": m.weight,
                         "tone": m.tone, "basis": m.basis,
                         "cohort": m.cohort} for m in spec.metrics],
            "missing": spec.missing,
            "abstain_reason": spec.abstain_reason,
        },
    }


async def analyze_company(symbol: str, name: str | None = None, db=None, allow_supplement: bool = True) -> Optional[dict]:
    from app.services.governance_rules import rules_version
    ck = f"analysis:{symbol}:{rules_version()}"  # auto-busts on any rules edit
    cached = cache.get(ck)
    if cached is not None:
        return cached

    from app.services.market_data import market_service
    from app.services import technical

    price = await market_service.get_price(symbol)
    info = await market_service.get_company_info(symbol) or {}
    history = await market_service.get_history(symbol, "1y")

    if not price and not info and not history:
        # Reliability floor: the free source is down/rate-limited — serve
        # the last successful analysis (persisted to disk, survives
        # restarts) instead of None, which used to cascade into "تعذّر
        # توليد رأي الذكاء" and empty analysis tabs. Real data with an
        # honest timestamp beats a dead feature.
        from app.services import lastgood
        return lastgood.load(f"analysis:{symbol}", max_age_seconds=7 * 24 * 3600)

    tech = technical.analyze(history) if history else None

    # ══ التدقيق أوّلاً — قبل كل حكم ══ (بأمر المالك: جودةٌ استثمارية)
    # كان التدقيق يعمل **داخل** محرّك القيمة العادلة وحده، فتُصحَّح ربحيةُ
    # السهم والدفترية والعائد للتقييم وتبقى الخام لدرجة الحوكمة — والدرجة
    # تقرأ العائد على حقوق الملكية مباشرةً في عتباتها (‏q_roe_excellent).
    # فملخَّصٌ قديم كان يُصحَّح في شاشةٍ ويمرّ في أخرى: رقمان لشركةٍ واحدة،
    # وهو عين ما يشكو منه المالك.
    # فصار التدقيق يقع **مرّةً واحدة هنا**، وتقرأ منه الحوكمةُ والتقييم
    # معاً — والقوائم تُجلب مرّةً وتُستعمل في الاثنين (وهي مخزَّنة أصلاً).
    _stmt = None
    try:
        _stmt = await market_service.get_financials(symbol, allow_supplement=allow_supplement)
    except Exception:                                             # noqa: BLE001
        _stmt = None
    _periods = (_stmt or {}).get("periods") or []
    try:
        from app.services.data_quality import audit as _audit
        _q = _audit(info, _periods)
        info = _q["values"]
    except Exception:                                             # noqa: BLE001
        _q = {"corrected": [], "notes": []}

    # Valuation: a separate lens ("is this a good price right now?"), never
    # blended into the health score below. Needs a DB session to find real
    # sector peers; skipped gracefully if none was passed in. Computed here
    # (before _financial_from_statements) so the new governance engine's
    # valuation rules can actually see it.
    valuation = None
    if db is not None:
        try:
            from app.services.valuation import get_valuation_context
            from app.services.four_scores import resolve_sector as _rs
            valuation = await get_valuation_context(
                db, symbol, _rs(info.get("sector"), symbol), info.get("pe_ratio"), info.get("price_to_book"),
            )
        except Exception as e:
            from loguru import logger
            logger.debug(f"Valuation lookup skipped for {symbol}: {e}")

    # القيمة العادلة تُحسب هنا كي تراها كلُّ الشاشات من موضعٍ واحد،
    # ويُغذّى مضاعفا القطاع من نظائرَ حقيقية في المحفظة لا من رقمٍ عامّ.
    from app.services.governance_rules import scope_for as _scope_for
    from app.services import fair_value as _fvmod
    # تاريخُ آخر تحديثٍ للأرقام المالية — من المخزن الدائم نفسه الذي
    # يكتبه جالبُ الأساسيات. يُعرض مع التقدير: قيمةٌ لا يُعرف عمر مدخلاتها
    # لا يُبنى عليها قرار.
    _asof = None
    try:
        from app.services import lastgood
        _asof = ((lastgood.load("market:fundamentals") or {})
                 .get(str(symbol).replace(".SR", "")) or {}).get("val_asof")
    except Exception:                                             # noqa: BLE001
        pass
    # ══ النِّسَبُ الرقابية تُجلب لمن تلزمه ══
    # البنكُ والتأمين والمالي وحدها — ونداءٌ واحد لكلٍّ منها، ومخزَّنٌ يوماً
    # كاملاً. وما لم يصل يبقى غائباً صراحةً في `missing`.
    # تاريخُ أحدثِ فترةٍ ماليةٍ وعمرُها — يُرسَلان مع الدرجة (D381)
    _stmt_asof, _stmt_age = None, None
    try:
        _ds = [str(p.get("as_of") or "") for p in (_periods or [])
               if p.get("as_of")]
        if _ds:
            from datetime import date as _date
            _stmt_asof = max(_ds)[:10]
            _stmt_age = (_date.today() - _date.fromisoformat(_stmt_asof)).days
        elif _periods:
            _ys = [int(p["year"]) for p in _periods
                   if str(p.get("year") or "").isdigit()]
            if _ys:
                _stmt_asof = f"{max(_ys)}-12-31"
                from datetime import date as _date
                _stmt_age = (_date.today()
                             - _date.fromisoformat(_stmt_asof)).days
    except Exception:                                             # noqa: BLE001
        pass
    _std = _scope_for(info.get("sector"), _periods, info)
    if allow_supplement and _std.get("archetype") in ("bank", "insurance", "financial"):
        try:
            from app.services import cache as _c
            _rk = f"argaam:ratios:{symbol}"
            _rr = _c.get(_rk)
            if _rr is None:
                from app.services.argaam_calendar import fetch_company_ratios
                _rr = (await fetch_company_ratios(
                    str(symbol).replace(".SR", ""))).get("ratios") or {}
                _c.set(_rk, _rr, 24 * 3600)
            if _rr:
                info = {**info, "_regulatory_ratios": _rr}
        except Exception:                                         # noqa: BLE001
            pass
    # ══ ما تعرضه الشاشةُ يخرج من المُنتِج الواحد ══ (D240 · D244)
    # قِيس على الخادم: عائدُ التوزيعات ومضاعفُ الدفترية يختلفان بين الفرز
    # وهذه الصفحة — لا لأن الحسابَ مختلفٌ بل لأن **ترتيبَ المصادر** كان
    # مكتوباً في كلّ مسارٍ بيده. فصار `resolve_display` هو السلسلةَ
    # الواحدة، وهذه تستعملها كما يستعملها الفرز.
    # وما جاء من المزوّد صريحاً يبقى: السلسلةُ تُكمل ولا تُبدّل.
    try:
        from app.services.content_engine import fund_store_load as _fsl
        from app.services.valuation_fields import resolve_display as _disp
        _px2 = (price or {}).get("price") if isinstance(price, dict) else price
        _base2 = str(symbol).replace(".SR", "")
        # كاشُ المزوّد يُقرأ **هنا**: كان يُشار إلى متغيّرٍ يُسنَد بعد هذا
        # الموضع بخمسين سطراً فيرفع UnboundLocalError — وهو الخطأُ نفسُه
        # الذي وقعتُ فيه قبلاً في هذا الملفّ (‏`_px_now`). كشفته اللجنة.
        _fc2 = cache.get(f"fund:yahoo:{symbol}") or {}
        _add = _disp(_base2, _px2, fund=_fc2 or info,
                     store_row=(_fsl() or {}).get(_base2) or {})
        # والصفحةُ تأخذ ما لا رقمَ لها فيه فقط — ورفضُ السلسلة (`None`)
        # لا يمحو رقماً جاء من المزوّد صريحاً في هذا الموضع.
        info = {**info, **{k: v for k, v in _add.items()
                           if info.get(k) is None and v is not None}}
    except Exception as _e:                                       # noqa: BLE001
        # و`logger` يُستورَد داخل هذه الدالّة في موضعٍ لاحق، فصار اسماً
        # محلّياً — والإشارةُ إليه قبل سطر استيراده ترفع الخطأ نفسَه.
        from loguru import logger as _lg2
        _lg2.warning(f"حقولُ العرض {symbol}: {type(_e).__name__}: {_e}")

    _fv = _fvmod.compute(info, (price or {}).get("price"),
                         (valuation or {}).get("sector_avg_pe"),
                         (valuation or {}).get("sector_avg_pb"),
                         asof=_asof,
                         periods=_periods,
                         peer_count=(valuation or {}).get("peer_count"),
                         archetype=_std.get("archetype"),
                         # أحدثُ ربعٍ منشورٍ — لعمرِ الأرقام والميزانية
                         # (‏D412): السلسلةُ السنويةُ تبقى للنماذج، وهذا
                         # يقول **متى** آخرُ ما أفصحت عنه الشركة.
                         latest_quarter=(_stmt or {}).get("latest_quarter"),
                         symbol=symbol)

    _analyst_fv = (info or {}).get("target_mean_price")
    if not isinstance(_analyst_fv, (int, float)) or _analyst_fv <= 0:
        _analyst_fv = None

    # ══ الإسنادُ جُرِّب مرّتين فسقط مرّتين — ورُفع ══ (D175)
    # أراد المالك محرّكاً يسند هدفَ المحلّلين حيث تغيب التغطية. فجُرِّب،
    # وقِيس على شركاتٍ لها هدفٌ نقيس عليه — أي حيث نملك مرجعاً:
    #
    #   الجولةُ الأولى (بلا شرط · ١٢٠ شركة):  وسيطُ الانحراف ‎٤٤٪
    #   ثمّ عولج الانهيارُ بأرضية الدفترية، ورُفض تقديرٌ يشكّ في نفسه
    #   الجولةُ الثانية (الموثوقةُ وحدَها · ٢٨ شركة): وسيطٌ ‎٣٣٪ · ضمن
    #                                              ‎±٢٥٪ ‎٣٦٪ فقط
    #
    # والشرطُ المعلَن قبل كلّ جولةٍ كان ‎≤٢٥٪. فالعلاجُ حسّن ولم يكفِ:
    # ‏‎+٨٩٪ لورقةٍ و‎−٦٦٪ لأخرى ليس تحفّظاً في التقدير بل خطأً في القياس،
    # وفرقٌ بهذا الحجم يقلب قرارَ شراءٍ إلى بيع.
    #
    # فـ«السعر العادل» هدفُ بيوت الخبرة وحدَه، وما لا يصله هدفٌ يبقى «غير
    # متوفّر» — والصمتُ أصدقُ من رقمٍ يخطئ الثلث. وتقديرُ التطبيق يبقى في
    # `fair_value_detail` لمن أراد تفصيلَه، ولا يُعرض سعراً عادلاً ولا
    # يحكم به قرار.
    #
    # وأرضيةُ الدفترية تبقى في المحرّك: عالجت عطباً حقيقياً (‏٤٥ شركةً
    # كانت تنهار إلى الصفر) وتنفع كلَّ ما يقرأ التفصيل.
    _shown_fv, _fv_source = (
        (_analyst_fv, "أهداف بيوت الخبرة") if _analyst_fv is not None else (None, None)
    )

    _px_now = (price or {}).get("price") if isinstance(price, dict) else price
    _analyst_up = (round((_shown_fv - _px_now) / _px_now * 100, 1)
                   if _shown_fv and isinstance(_px_now, (int, float))
                   and _px_now > 0 else None)

    # ══ القيمةُ النسبيةُ إلى القطاع — قراءةٌ دائمةٌ لا سدَّ فراغ ══ (D232)
    # كانت تُحسب حيث لا هدفَ محلّلين وحدَه. وبأمر المالك صارت **دائمة**:
    # موضعُ السهم من نظائره خبرٌ قائمٌ بنفسه، يُقرأ مع هدفِ المحلّلين لا
    # بدلاً منه — وحين يتباعدان فذلك خبرٌ أيضاً.
    #
    # والشرطُ الباقي شرطُ عرضٍ لا شرطُ حساب: لا تُعرض في خانة «هدف
    # المحلّلين» ولا تُدسّ فيها؛ لها موضعُها المستقلّ في البيانات المالية
    # حيث مقياساها (ربحيةُ السهم والقيمةُ الدفترية) مذكوران فوقها.
    #
    # وتُحسب من المخزن القائم بلا نداءٍ جديد، وسقوطُها لا يُسقط التحليل.
    _rel_fields: dict = {}
    _fund_cache = cache.get(f"fund:yahoo:{symbol}") or {}
    try:
        # ══ مُنتِجٌ واحدٌ بمائدةٍ واحدة ══ (D240)
        # كان لكلٍّ من هذه الصفحة والفرز بناؤه الخاصّ للمائدة ومدخلاتِه،
        # فخرج رقمان لمعنًى واحد: ‎28 خلافاً في أربعين شركة (قِيس على
        # الخادم). فصار الاثنان ينزلان إلى `fields_for` — مائدةٌ من السوق
        # الرئيسيّ، ومضاعفٌ من الكاش أوّلاً ثمّ المخزن، وهو نفسُه المنزوعُ
        # من وسيط القطاع.
        from app.services.relative_value import fields_for as _rel_fields_for
        from app.services.content_engine import fund_store_load
        _rel_fields = _rel_fields_for(symbol, _px_now,
                                      store=fund_store_load(),
                                      fund=_fund_cache)
    except Exception as _e:                                   # noqa: BLE001
        from loguru import logger as _lg3
        _lg3.warning(f"السعر العادل {symbol}: {type(_e).__name__}: {_e}")

    # ══ محرّكان، واسمٌ واحدٌ يحمل الأقوى ══ (D264)
    # صار للمعايير مصدرٌ حيٌّ كامل: المعدَّلُ الخالي من المخاطر من صكٍّ
    # سياديٍّ عشريّ (‏D249)، والبيتا مقيسةٌ من سوقنا (‏D257)، والقوائمُ
    # رسميةٌ مدقَّقةٌ حيث وصلت (‏D263). فمحرّكُ خصم التدفّقات صار قادراً
    # على النطق بدل الامتناع.
    #
    # ولا يُعرض رقمان باسمٍ واحد — هذا عطبُ D147 و D174 بعينه. فالاسمُ
    # «السعر العادل» يبقى واحداً، ويحمل **الأقوى**: خصمُ التدفّقات حين
    # ينطق بثقةٍ لا تقلّ عن متوسطة، وإلا فالنظائر. و`rel_basis` يقول أيُّ
    # محرّكٍ نطق — فلا يُقرأ رقمٌ بلا معرفةِ أصله.
    _dcf: dict = {}
    try:
        from app.services.fair_value_engine.serve import value_for_symbol as _dcf_for
        _dcf = await _dcf_for(symbol, price=_px_now) or {}
    except Exception as _e:                                   # noqa: BLE001
        from loguru import logger as _lg4
        _lg4.debug(f"DCF {symbol}: {type(_e).__name__}: {_e}")
    if _dcf.get("value") and _dcf.get("confidence") in ("مرتفعة", "متوسطة"):
        _rel_fields = {
            **_rel_fields,
            "rel_value": _dcf["value"],
            "rel_low": _dcf.get("low"),
            "rel_high": _dcf.get("high"),
            "rel_conf": _dcf.get("confidence"),
            "rel_basis": "خصم التدفّقات النقدية",
            "rel_upside_pct": (round((_dcf["value"] - _px_now) / _px_now * 100, 1)
                               if _px_now else None),
            "rel_confidence_why": _dcf.get("notes") or [],
            "rel_why": None,
        }

    from app.services.four_scores import technical_to_timing_snapshot, valuation_to_snapshot, resolve_sector
    # Canonical Arabic sector drives archetype exemptions; Yahoo's English
    # sector never matches the map, so resolve it (DB sector via symbol lookup,
    # else English→Arabic) exactly as governance_engine does.
    fin = await _financial_from_statements(
        symbol, sector=resolve_sector(info.get("sector"), symbol),
        valuation_snapshot=valuation_to_snapshot(info, valuation),
        timing_snapshot=technical_to_timing_snapshot(tech),
        info=info, allow_supplement=allow_supplement,
    )

    chg = (price or {}).get("change_pct", 0) or 0
    if chg > 0:
        fin["strengths"].append(f"زخم سعري إيجابي اليوم +{chg:.2f}%")
    elif chg < 0:
        fin["weaknesses"].append(f"ضغط سعري اليوم {chg:.2f}%")

    # Purely fundamental score — technical timing never enters the verdict
    # (it lives in its own section as trading context only).
    overall = None if not fin.get("evaluable") else fin["score"]
    # ONE decision per company: the exact same governance Decision Engine
    # verdict الحوكمة shows — never a separate five-level scale that could
    # disagree with it. رأي الذكاء reads it too (see ai.py), so the whole
    # app thinks with one mind about every company.
    from app.services.decision_engine import decision_color, apply_fair_value_ceiling
    # القرارُ لا يناقض قيمتنا العادلة: يمرّ على سقفها قبل أن يُعرض، فلا
    # يقول «شراء» وسعرُ السهم فوق القيمة التي حسبناها في الصفحة نفسها.
    _cov = None
    try:
        _q4 = (fin.get("scores") or {}).get("quality") or {}
        _s4 = (fin.get("scores") or {}).get("safety") or {}
        _cs = [c for c in (_q4.get("coverage"), _s4.get("coverage"))
               if isinstance(c, (int, float))]
        _cov = (sum(_cs) / len(_cs)) if _cs else None
    except Exception:                                             # noqa: BLE001
        _cov = None
    # ══ من حمل لقبَ «السعر العادل» حكَم به القرار ══ (D237 · بأمر المالك)
    # صار التقييمُ النسبيُّ يُعرض باسم «السعر العادل». ولو بقيت البوّابةُ
    # تحكم بهدف المحلّلين وحدَه، لعادت أقبحُ صورةٍ من D174: شاشةٌ تقول
    # «السعر العادل ‎28.40» وسعرٌ ‎34 وقرارٌ يقول «شراء» — لأن الرقمَ
    # المعروضَ ليس هو المحكومَ به. فالبوّابةُ تأخذ المعروضَ نفسَه.
    #
    # وثقةٌ منخفضةٌ لا يُبنى عليها منعٌ: هي تُعرض بقيدها المعلَن ولا تُسقط
    # حكماً — كما لا يُطبَّق السقفُ حين تمتنع القيمةُ أصلاً.
    _gate_fv = _shown_fv
    if _gate_fv is None and _rel_fields.get("rel_conf") in ("مرتفعة", "متوسطة"):
        _gate_fv = _rel_fields.get("rel_value")
    # البوّابةُ تحكم بالرقم المعروض نفسِه — لا برقمٍ ثانٍ لا تراه الشاشة.
    gov = apply_fair_value_ceiling(fin["decision"],
                                   (price or {}).get("price"),
                                   _gate_fv,
                                   _fv.get("entry_price"),
                                   single_path=bool(_fv.get("single_path"))
                                   or (_shown_fv is None
                                       and _rel_fields.get("rel_paths") == 1),
                                   coverage=_cov,
                                   nomu=bool(_fv.get("nomu")),
                                   red_lines=(fin.get("red_lines") or []),
                                   implausible=bool(_fv.get("implausible")))
    fin["decision"] = gov
    # ══ المفردةُ تُترجَم في مخرَجٍ واحد ══ (قرارُ مجلس نِصاب)
    # الحكمُ الداخليّ يبقى كما هو ليعمل القياسُ والفرزُ عليه، والمعروضُ
    # للقارئ يتبع وضعَ النشر: أمرٌ للمالك، ووصفٌ للعموم.
    from app.services.decision_engine import public_label, is_public_mode
    decision = {"label": public_label(gov.decision),
                "raw": gov.decision,
                "rule_id": gov.matched_rule_id,
                "color": decision_color(gov.decision), "reason": gov.reason,
                "public_mode": is_public_mode()}

    strengths = fin["strengths"][:6] or ["بيانات مالية متاحة للتحليل"]
    weaknesses = fin["weaknesses"][:6]

    # ══ السعرُ العادل = متوسّطُ تقديرات بيوت الخبرة ══ (بأمر المالك)
    # ويُشتقّ هنا مرّةً واحدة فيقرؤه كلُّ قسمٍ من مصدرٍ واحد. وما لا يصل
    # فيه تقديرٌ يبقى «غير متاح» ولا يُستبدَل بحسابٍ آخر.

    result = {
        "symbol": symbol,
        "name": name or info.get("name") or symbol,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "price": (price or {}).get("price"),
        "change": (price or {}).get("change"),
        "change_pct": chg,
        "day_low": (price or {}).get("day_low"),
        "day_high": (price or {}).get("day_high"),
        "fundamentals": info,
        # درجةُ المواصفة تمرّ مع الماليّة — كانت تُحسب ثم تُقصّ هنا فلا
        # تصل القياسَ ولا الشاشة، فيبدو المحرّكُ الجديد كأنه لم يعمل.
        "financial": {"score": fin["score"], "verdict": fin["verdict"],
                      "spec": fin.get("spec")},
        "spec": fin.get("spec"),
        # الخطوطُ الحمراء وركنُ الحوكمة يمرّان إلى الشاشة — الحقلُ الذي
        # يُحسب ولا يصل الواجهةَ معطَّلٌ لا موجود.
        "red_lines": fin.get("red_lines") or [],
        "governance": fin.get("governance"),
        "technical": tech,
        # ══ القيمة العادلة — تُحسب من ماليّة الشركة ══ (خطٌّ أحمر للمالك)
        # كانت `target_mean_price` وحدها: هدفُ سعرٍ لاثني عشر شهراً، رقمٌ
        # حقيقيّ لكنّه **ليس** قيمةً جوهرية، ويغيب عن أكثر شركات تداول.
        # وقال المالك إنه يتّخذ هذا الرقم أداةً لقرارٍ استثماريّ ولا يريد
        # وهماً — فصار يُحسب بمساراتٍ من أرقام الشركة نفسها، وكلُّ مسارٍ
        # يُعرض بمدخلاته. (‏services/fair_value.py)
        # المعيار القطاعيّ المطبَّق — يُعرض مع الدرجة لا بعدها: درجةٌ لا
        # يُعرف إطارُها ولا نطاقُها لا يُبنى عليها قرار.
        "governance_standard": _std,
        # ══ بيانُ مصدر الدرجة ══ (بأمر المالك)
        # الدرجة صارت تحمل ما تحمله القيمة العادلة: على كم سنةٍ بُنيت، ومن
        # أيّ مصدر، وهل صُحّح مدخلٌ من مدخلاتها. ودرجةٌ بلا هذا تُقرأ حكماً
        # مطلقاً وهي حكمٌ ضمن بيانات.
        "governance_provenance": {
            "سنوات القوائم": len(_periods),
            # ══ ودرجةٌ بلا تاريخٍ تُقرأ حديثةً ══ (D381)
            # قِيس: 54 ورقةً في السوق الرئيسيّ قوائمُها أقدمُ من 200 يومٍ
            # (‏25 تأميناً أرقامُها 2022 · 6 ريتاتٍ بعمر سبعِ سنوات)، ودرجةُ
            # جودتها تُعرَض رقماً مجرَّداً كدرجةِ شركةٍ أرقامُها هذا الربع.
            # فيُرسَل **تاريخُ أحدثِ فترةٍ وعمرُها** مع الدرجة لتُعرَض معها.
            "تاريخ الأرقام": _stmt_asof,
            "عمر الأرقام أياماً": _stmt_age,
            # ══ ومصدرُ الأساسيات يُقرأ لا يُكتَب ══ (D334)
            # كان نصّاً ثابتاً «ياهو»، وقوائمُ تسعٍ من عشرٍ في محفظة المالك
            # تأتي من **«تداول — XBRL»** الرسميّ (مقيسٌ على خادمه). فبندُ
            # المنشأ — الذي وُضع أصلاً كي تُقرأ الدرجةُ ضمن بياناتها —
            # كان يقول غيرَ الحقيقة: ثقةٌ تُبنى على نسبةٍ خاطئة. فيُقرأ
            # من الطبقة التي أجابت فعلاً، ويُعلَن الإسنادُ حين يُستعمل.
            "مصدر الأساسيات": (
                (str((_stmt or {}).get("source")) if (_stmt or {}).get("source")
                 else ("ياهو" if _periods else "غير متوفّر"))
                + ("‏ + سهمك" if allow_supplement else "")),
            "تصحيحات التدقيق": _q.get("corrected") or [],
            "عمق الفحص": "كامل" if allow_supplement else "سريع",
        },
        "fair_value_detail": _fv,
        # ══ السعرُ العادل = متوسّطُ تقديرات بيوت الخبرة ══ (بأمر المالك)
        # قرارُ المالك بعد عرض البديلين: يُعتمد `target_mean_price` — متوسّطُ
        # أهداف المحلّلين — سعراً عادلاً في التطبيق كلِّه، وباسمٍ واحد في
        # صفحة الشركة وتحليل الذكاء وسائر الأقسام. وتقديرُنا المحسوب يبقى
        # في `fair_value_detail` بمساراته لمن أراد تفصيلَه، ولا يُعرض رقماً
        # منافساً. ورقمٌ واحدٌ باسمٍ واحد هو المقصود.
        # ══ الاسمُ يعود لصاحبه ══ (D386 · بأمر المالك)
        # قال: «هدفُ المحللين شيءٌ من ياهو، والسعرُ العادل شيءٌ آخرُ من
        # صنعنا». وكان الاسمانِ ملتبسَين: `fair_value` = متوسّطُ أهداف
        # بيوت الخبرة، وتقديرُ محرّكنا محجوبٌ في `fair_value_detail`،
        # واسمُ «السعر العادل» معلَّقٌ على **أضعف** الثلاثة (المقارنةُ
        # بمضاعفات القطاع). قِيس على 1120: نسبيٌّ 32.13 · محللون 74.95 ·
        # محرّكُنا 104.72 — ثلاثةُ أحكامٍ متعارضةٍ باسمٍ واحد.
        #
        # فصار: **السعرُ العادل = تقديرُ محرّكنا** من قوائم الشركة ومعه
        # مداه وثقتُه وتاريخُ أرقامه؛ وهدفُ المحللين حقلٌ مستقلٌّ باسمه
        # ومصدرِه؛ والنسبيُّ إلى القطاع لا يلبس اسمَ السعر العادل.
        "fair_value": _fv.get("value"),
        "fair_value_source": ("محرّكُنا — قوائمُ الشركة"
                              if _fv.get("value") is not None else None),
        "fair_value_upside_pct": (
            round((_fv["value"] - _px_now) / _px_now * 100, 1)
            if _fv.get("value") and isinstance(_px_now, (int, float))
            and _px_now else None),
        "fair_value_low": _fv.get("low"),
        "fair_value_high": _fv.get("high"),
        "fair_value_conf": _fv.get("confidence"),
        # والثقةُ تُبرَّر لا تُعلَن (‏D411): درجةٌ من مئة، وسلّمُها،
        # وسببُ كلّ خصمٍ باسمه — فيزن المالكُ ثقةً بأخرى ويرى ما نقصها.
        "fair_value_conf_score": _fv.get("confidence_score"),
        "fair_value_conf_scale": _fv.get("confidence_scale"),
        "fair_value_conf_why": _fv.get("confidence_why"),
        "fair_value_risk_note": _fv.get("risk_note"),
        "fair_value_risk_flags": _fv.get("risk_flags"),
        "fair_value_stale_basis": _fv.get("stale_basis"),
        "fair_value_asof": _fv.get("data_asof"),
        "fair_value_age_days": _fv.get("age_days"),
        "fair_value_stale": _fv.get("stale"),
        "fair_value_unavailable_reason": _fv.get("unavailable_reason"),
        # وهدفُ بيوت الخبرة باسمه ومصدرِه — مسانِدٌ لا منافس
        "analyst_target": _shown_fv,
        "analyst_target_source": _fv_source,
        "analyst_target_upside_pct": _analyst_up,
        # ══ حيث لا هدفَ لبيوت الخبرة ══ (D212 · D213)
        # ‎124 شركةً من ‎273 لا يُصدر لها أحدٌ توصية، فيبقى `fair_value`
        # فارغاً بحقّ. وتُشتقّ لها قيمةٌ نسبيةٌ إلى القطاع — حقلٌ مستقلٌّ
        # لا يمسّ الأوّل ولا يُخلط به في العرض.
        **_rel_fields,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "valuation": valuation,
        "ai_score": overall,
        "score": overall,
        "decision": decision,
        # Unified governance outputs — تقييم الأداء renders the SAME expert
        # consensus / four scores / confidence the الحوكمة panel shows.
        "evaluable": fin.get("evaluable"),
        "narrative": fin["verdict"],
        "scores": fin.get("scores"),
        "expert_panel": fin.get("expert_panel"),
        "confidence": fin.get("confidence"),
        "enriched_fields": fin.get("enriched_fields"),
    }
    cache.set(ck, result, ANALYSIS_TTL)
    # Persist as last-known-good (disk-backed) so a future source outage —
    # even across restarts — degrades to this real snapshot, never to None.
    from app.services import lastgood
    lastgood.save(f"analysis:{symbol}", result)
    # ══ الحكمُ العميق يُحفظ ليقرأه المسح ══ (بأمر المالك)
    # سأل: لماذا تقول خريطة القطاعات «لا ينطبق» عن شركةٍ تُظهر لها صفحتُها
    # درجةً؟ والجواب أن المسح العامّ (‏~٣٩٥ شركة) يمرّ بـallow_supplement=
    # False فلا يُنفق حصّة المصدر الشحيح، فتبقى بيانات كثيرٍ منها دون عتبة
    # الحكم؛ وصفحةُ الشركة تمرّ بـTrue فتكتمل. فالمعايير واحدة والبيانات
    # مختلفة — لكنّ المالك يرى تناقضاً، وهو محقّ في أنه تناقضٌ على الشاشة.
    #
    # فيُحفظ الحكم العميق متى تحقّق، ويقرؤه المسح بدل أن يُعيد الحكم بلا
    # بيانات. فتتراكم التغطية مع كل شركةٍ يفتحها، ولا تُنفق حصّةٌ إضافية.
    if allow_supplement and result.get("evaluable"):
        try:
            from app.services import lastgood
            from datetime import datetime, timezone
            store = lastgood.load("governance:deep") or {}
            if not isinstance(store, dict):
                store = {}
            # ══ ما يكفي لترتيب السوق كلِّه بلا إعادة حساب ══
            # «جاهزٌ لكل شركات السوق» يعني أن يجد المستثمرُ المرشّحين لا
            # أن يحكم على واحدةٍ اختارها هو. فيُحفظ مع الدرجة: أساسُها
            # وتغطيتُها ونمطُها، وهل اشتعل خطٌّ أحمر، والقيمةُ العادلة
            # ونسبتُها إلى السعر — فتُرتَّب القائمةُ وتُصفّى من مخزنٍ واحد.
            _sp = result.get("spec") or {}
            _px = (result.get("price") or 0) or 0
            _fvv = result.get("fair_value")
            store[str(symbol).replace(".SR", "")] = {
                "finance_score": (result.get("financial") or {}).get("score"),
                "ai_score": result.get("ai_score"),
                "decision": result.get("decision"),
                "quality": _sp.get("score"),
                "coverage": _sp.get("coverage"),
                "basis": _sp.get("basis"),
                "archetype": _sp.get("archetype"),
                "red_lines": len(result.get("red_lines") or []),
                "governance": (result.get("governance") or {}).get("score"),
                "fair_value": _fvv,
                "value_to_price": (round(_fvv / _px, 3)
                                   if _fvv and _px else None),
                "at": datetime.now(timezone.utc).date().isoformat(),
            }
            lastgood.save("governance:deep", store)
        except Exception:                                         # noqa: BLE001
            pass
    return result
