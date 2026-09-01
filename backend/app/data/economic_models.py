"""النماذجُ الاقتصادية الخمسة — قطاعاتُ السوق كما يقرؤها مستثمرُ دخل.

## لماذا خمسةٌ لا اثنان وعشرون

للسوق اثنان وعشرون قطاعاً، ولا يحتاج كلُّ قطاعٍ محرّكاً: مصرفٌ وشركةُ
تمويلٍ يُقرآن بالمنطق نفسه (رأسُ المال يُقرض فيُولّد عائداً على حقوق
الملكية)، ومصنعُ بتروكيماوياتٍ ومنتجُ طاقةٍ كلاهما يُقاس عبر الدورة لا
في سنةٍ واحدة. فالنماذجُ خمسةٌ لأنها خمسُ **بنياتِ قائمةٍ مالية**
مختلفة، والقطاعُ يختار نموذجَه ولا يملك محرّكاً خاصّاً به.

وهذا الفصلُ يمنع عطبين وقعا معاً في هذا المشروع: قياسُ السوق كلِّه
بمسطرةٍ واحدة (فتُدان البنوكُ بتدفّقٍ حرٍّ لا معنى له عندها)، وبناءُ
منطقٍ لكلّ قطاعٍ على حِدة (فيصير اثنان وعشرون محرّكاً لا يُراجَع أحدُها).

## البنياتُ الخمس

  · **FINANCIAL** — الرافعةُ نموذجُ العمل لا عيبُه، والنقدُ التشغيليّ
    مشوّهٌ بنموّ دفتر القروض. فالقياسُ على حقوق الملكية ونموّها.
  · **REIT** — كِيانُ تمريرٍ يوزّع أغلبَ دخله نظاماً، فالأموالُ من
    العمليات أصدقُ من الربح المحاسبيّ، والدفتريُّ تقريبٌ لصافي الأصول.
  · **CYCLICAL** — سنةُ القاع تُظهرها غاليةً وسنةُ القمّة رخيصة، فالقياسُ
    على أرباحٍ معياريةٍ عبر الدورة لا على آخر سنة.
  · **OPERATING** — النموذجُ الصناعيّ المعتاد: هامشٌ وتدفّقٌ حرٌّ وعائدٌ
    على رأس المال المستثمر.
  · **REAL_ESTATE** — مطوّرٌ لا صندوق: قيمتُه في أرضه ومشاريعه، وبناؤها
    يستهلك النقدَ سنواتٍ وهو عينُ نموذج العمل لا ضعفٌ فيه.
"""

from __future__ import annotations

FINANCIAL = "FINANCIAL"
REIT = "REIT"
CYCLICAL = "CYCLICAL"
OPERATING = "OPERATING"
REAL_ESTATE = "REAL_ESTATE"

MODELS = (FINANCIAL, REIT, CYCLICAL, OPERATING, REAL_ESTATE)

# ── القطاعُ يختار نموذجَه ────────────────────────────────────────────
# اثنان وعشرون قطاعاً كما هي في قاعدة السوق حرفاً بحرف. وقطاعٌ لا يُطابق
# لا يُلحَق بـ«العامّ» تخميناً: يُعاد `None` ويُعلَن أن النموذج غيرُ
# معروف — فإلحاقُ بنكٍ بالنموذج التشغيليّ أسوأُ من الامتناع عنه.
MODEL_OF_SECTOR: dict[str, str] = {
    # ── مالية ──
    "البنوك": FINANCIAL,
    "التأمين": FINANCIAL,
    "الخدمات المالية": FINANCIAL,
    # ══ الاسمُ المسجَّل والاسمُ في المواصفة كلاهما يُربَط ══
    # المادة ١٠ تسمّي «الخدمات المالية والاستثمار» و«تجزئة الأغذية»
    # و«التجزئة المتنوعة»، والمسجَّلُ في قاعدة السوق غيرُها. ولا يُعاد
    # تسميةُ بياناتِ المالك لتوافق ورقة؛ يُربَط الاسمان فلا تيتم شركةٌ
    # مهما اختلفت التسمية، ويُكشف الفرقُ في اختبار القبول.
    "الخدمات المالية والاستثمار": FINANCIAL,
    # ── صناديق عقارية ──
    "الصناديق العقارية المتداولة": REIT,
    # ── دورية ──
    "الطاقة": CYCLICAL,
    "المواد الأساسية": CYCLICAL,
    # ── تطوير عقاريّ — وليس صندوقاً ──
    "إدارة وتطوير العقارات": REAL_ESTATE,
    # ── تشغيلية ──
    "الاتصالات": OPERATING,
    "المرافق العامة": OPERATING,
    "الرعاية الصحية": OPERATING,
    "الأدوية": OPERATING,
    "إنتاج الأغذية": OPERATING,
    "تجزئة وتوزيع السلع الاستهلاكية": OPERATING,
    "تجزئة وتوزيع السلع الكمالية": OPERATING,
    "تجزئة الأغذية": OPERATING,
    "التجزئة المتنوعة": OPERATING,
    "الخدمات الاستهلاكية": OPERATING,
    "النقل": OPERATING,
    "السلع الرأسمالية": OPERATING,
    "الخدمات التجارية والمهنية": OPERATING,
    "التطبيقات وخدمات التقنية": OPERATING,
    "السلع طويلة الأجل": OPERATING,
    "الإعلام والترفيه": OPERATING,
    "المنتجات المنزلية والشخصية": OPERATING,
}


def model_of(sector: str | None) -> str | None:
    """نموذجُ القطاع، أو `None` إن لم يُعرف — ولا يُخمَّن."""
    if not sector:
        return None
    return MODEL_OF_SECTOR.get(sector.strip())


# ══ مكوّناتُ الدرجة ══
#
# لكلّ نموذجٍ أربعةُ مكوّنات، ولكلّ مكوّنٍ مؤشّراتُه بأوزانها. والصيغة:
#
#     (مفتاحُ السمة، الاسم، الوزن، الاتّجاه)
#
# والاتّجاه:
#   "higher" · "lower"  ⇒ يُرتَّب في عشيرة القطاع (مئينٌ نسبيّ)
#   ("band", lo, hi)    ⇒ عتبةٌ منشورةٌ لا تُرتَّب (نطاقٌ صحّيّ معروف)
#
# ولا عتبةَ مخترَعة: ما لا يحمل معياراً منشوراً يُرتَّب بين أقرانه،
# فالمسطرةُ من السوق لا من رأيي.

# ── التوزيعات: الاستدامةُ أوّلاً والعائدُ آخراً ──────────────────────
# ترتيبُ الأهمية بنصّ المادة ٣: الاستدامة ثم النموّ ثم التاريخ ثم
# العائد. والعائدُ آخرُها عمداً — عائدٌ مرتفعٌ سببُه هبوطُ السهم ليس
# ميزة، وبوزنٍ صغيرٍ لا يستطيع وحده أن يرفع المكوّنَ إلى المئة.
_DIVIDEND = (
    ("payout_ratio", "استدامةُ التوزيع (نسبة التوزيع)",
     0.35, ("band", 20.0, 80.0)),
    ("dividend_growth", "نموّ التوزيع", 0.25, "higher"),
    ("dividend_years", "تاريخُ التوزيع", 0.22, "higher"),
    ("dividend_yield", "العائد التوزيعيّ", 0.18, "higher"),
)

# ── التقييم: مضاعفاتٌ نسبيّة على وسيط القطاع — لا قيمةَ عادلة ────────
# درجةُ الحوكمة تقيس **سلامة الورقة المالية** لا سعرَها العادل. فخرج
# `fv_discount` من المكوّن كلِّه: تقديرُ القيمة العادلة محرّكٌ مستقلّ،
# وإدخالُه هنا كان يخلط قياسَ الشركة بتقديرِ سعرها.
#
# والباقي **مضاعفاتٌ نسبيّة**: تُقاس على وسيط القطاع لا على قيمةٍ
# نقدّرها نحن — تجيب «أين هذه الورقةُ من أقرانها» لا «كم تساوي». وهي
# مؤشّراتٌ معتمَدةٌ في المواصفة، ولم تُغيَّر أوزانُها النسبية بينها.
COMPONENTS: dict[str, dict[str, tuple]] = {
    FINANCIAL: {
        # ROE · جودةُ الأرباح · قوّةُ الميزانية · اتّجاهُ الربحية
        "quality": (
            ("roe", "العائد على حقوق الملكية", 0.35, "higher"),
            ("earnings_stability", "جودةُ الأرباح واستقرارُها", 0.25, "lower"),
            ("leverage_x", "قوّةُ الميزانية (الرافعة)", 0.20, "lower"),
            ("roe_trend", "اتّجاهُ الربحية", 0.20, "higher"),
        ),
        "dividend": _DIVIDEND,
        "growth": (
            ("eps_cagr_5y", "نموّ ربحية السهم", 0.35, "higher"),
            ("book_value_cagr_5y", "نموّ القيمة الدفترية", 0.30, "higher"),
            ("revenue_cagr_5y", "نموّ الدخل", 0.20, "higher"),
            ("roe_trend", "اتّجاهُ الربحية", 0.15, "higher"),
        ),
        "valuation": (
            ("p_b", "السعر إلى الدفتريّ", 0.30, "lower"),
            ("p_e", "مضاعفُ الربحية (تحقّقٌ ثانويّ)", 0.20, "lower"),
        ),
    },
    REIT: {
        "quality": (
            ("roe", "العائد على حقوق الملكية", 0.20, "higher"),
            ("ltv_pct", "الرافعة على الأصول", 0.25, "lower"),
            ("interest_coverage", "تغطيةُ الفوائد", 0.20, "higher"),
            ("earnings_stability", "استقرارُ الدخل والتوزيع", 0.20, "lower"),
            # تقريبُ جودة الأصول: دورانُ الأصول — كم إيراداً تولّده
            # الأصول. ولا يصلنا إشغالٌ ولا تقييمٌ عقاريّ، فيُسمّى تقريباً.
            ("asset_turnover", "تقريبُ جودة الأصول", 0.15, "higher"),
        ),
        "dividend": _DIVIDEND,
        "growth": (
            ("revenue_cagr_5y", "نموّ الإيراد", 0.40, "higher"),
            ("book_value_cagr_5y", "نموّ حقوق الملكية", 0.35, "higher"),
            ("roe_trend", "اتّجاهُ الربحية", 0.25, "higher"),
        ),
        "valuation": (
            ("p_ffo", "السعر إلى الأموال من العمليات", 0.30, "lower"),
            ("p_b", "الدفتريُّ تقريباً لصافي الأصول", 0.20, "lower"),
        ),
    },
    CYCLICAL: {
        "quality": (
            ("roe", "العائد على حقوق الملكية", 0.25, "higher"),
            ("net_debt_ebitda", "الدَّين إلى الأرباح التشغيلية", 0.20, "lower"),
            ("interest_coverage", "تغطيةُ الفوائد", 0.20, "higher"),
            ("earnings_stability", "استقرارُ الربح عبر الدورة", 0.20, "lower"),
            ("operating_margin", "الهامشُ التشغيليّ", 0.15, "higher"),
        ),
        "dividend": _DIVIDEND,
        "growth": (
            ("revenue_cagr_5y", "نموّ الإيراد عبر الدورة", 0.40, "higher"),
            ("eps_cagr_5y", "نموّ الربحية", 0.30, "higher"),
            ("book_value_cagr_5y", "نموّ حقوق الملكية", 0.30, "higher"),
        ),
        "valuation": (
            ("p_e_normalized", "المضاعفُ على أرباحٍ معيارية", 0.30, "lower"),
            ("ev_ebitda", "قيمةُ المنشأة إلى الأرباح التشغيلية", 0.20, "lower"),
        ),
    },
    OPERATING: {
        # ROIC وبديلُه ROE — المادة ٢: إن غاب الأوّلُ استُعمل الثاني.
        "quality": (
            ("roic", "العائد على رأس المال المستثمر", 0.25, "higher"),
            ("roe", "العائد على حقوق الملكية", 0.15, "higher"),
            ("operating_margin", "الهامشُ التشغيليّ", 0.20, "higher"),
            ("cash_conversion_ratio", "تحويلُ الربح إلى نقد", 0.20, "higher"),
            ("earnings_stability", "استقرارُ الربح", 0.20, "lower"),
        ),
        "dividend": _DIVIDEND,
        "growth": (
            ("revenue_cagr_5y", "نموّ الإيراد", 0.40, "higher"),
            ("eps_cagr_5y", "نموّ ربحية السهم", 0.35, "higher"),
            ("roic_trend", "اتّجاهُ العائد على رأس المال", 0.25, "higher"),
        ),
        "valuation": (
            ("p_e", "مضاعفُ الربحية", 0.30, "lower"),
            ("ev_ebitda", "قيمةُ المنشأة إلى الأرباح التشغيلية", 0.20, "lower"),
        ),
    },
    REAL_ESTATE: {
        "quality": (
            ("roe", "العائد على حقوق الملكية", 0.25, "higher"),
            ("ltv_pct", "الدَّين إلى الأصول", 0.25, "lower"),
            ("interest_coverage", "تغطيةُ الفوائد", 0.20, "higher"),
            ("earnings_stability", "استقرارُ الربح", 0.15, "lower"),
            ("book_value_cagr_3y", "اتّجاهُ الأصول والقيمة الدفترية",
             0.15, "higher"),
        ),
        "dividend": _DIVIDEND,
        "growth": (
            ("revenue_cagr_5y", "نموّ الإيراد", 0.35, "higher"),
            ("eps_cagr_5y", "نموّ الربحية", 0.30, "higher"),
            ("book_value_cagr_5y", "نموّ حقوق الملكية", 0.35, "higher"),
        ),
        "valuation": (
            ("p_b", "الدفتريُّ تقريباً لصافي الأصول", 0.30, "lower"),
            ("p_e", "مضاعفُ الربحية", 0.20, "lower"),
        ),
    },
}

# ── ما لا يجوز لكلّ نموذج ────────────────────────────────────────────
# قائمةُ منعٍ صريحة، يقرؤها اختبارُ القبول فيفشل إن تسلّل مؤشّرٌ لا
# يناسب بنيةَ القائمة. وهي أوقعُ من التعليق: التعليقُ يُقرأ والقائمةُ
# تُنفَّذ.
FORBIDDEN: dict[str, tuple[str, ...]] = {
    FINANCIAL: ("fcf_margin", "roic", "roic_cycle", "current_ratio",
                "quick_ratio", "ev_ebitda", "graham_number",
                "cash_conversion_ratio", "net_debt_ebitda"),
    REIT: ("graham_number", "roic", "roic_cycle", "current_ratio",
           "quick_ratio", "fcf_margin"),
    CYCLICAL: ("graham_number",),
    REAL_ESTATE: ("graham_number", "roic_cycle", "quick_ratio"),
    OPERATING: ("graham_number",),
}

# ── التصنيفُ النهائيّ ────────────────────────────────────────────────
GRADES = (
    (85, "A", "مرشّحٌ استثماريٌّ قويّ"),
    (75, "B", "مرشّحٌ استثماريٌّ جيّد"),
    (65, "C", "يحتاج انتقاءً أو سعراً مناسباً"),
    (50, "D", "غيرُ جذّابٍ حالياً"),
    (0,  "E", "غيرُ مناسبٍ حالياً"),
)

# ══ الأوزانُ تتبع النموذج لا السوقَ كلَّه ══
#
# وزنٌ واحدٌ لكلّ القطاعات يُسوّي بين ما لا يستوي: التقييمُ عند مصرفٍ
# يُقاس على الدفتريّ يستحقّ ثقلاً أكبرَ منه عند شركةٍ تشغيلية يُقاس
# نموُّها أوّلاً؛ والصندوقُ العقاريّ كِيانُ توزيعٍ بالنظام، فتوزيعُه
# ثلاثون بالمئة لا خمسَ عشرة.
#
# ولكلّ نموذجٍ مجموعُه واحدٌ صحيح — يفحصه اختبارُ القبول فيفشل إن اختلّ.
WEIGHTS_OF_MODEL: dict[str, dict[str, float]] = {
    FINANCIAL:   {"quality": 0.35, "dividend": 0.20,
                  "growth": 0.15, "valuation": 0.30},
    REIT:        {"quality": 0.30, "dividend": 0.30,
                  "growth": 0.15, "valuation": 0.25},
    CYCLICAL:    {"quality": 0.30, "dividend": 0.15,
                  "growth": 0.25, "valuation": 0.30},
    OPERATING:   {"quality": 0.30, "dividend": 0.20,
                  "growth": 0.25, "valuation": 0.25},
    REAL_ESTATE: {"quality": 0.30, "dividend": 0.15,
                  "growth": 0.20, "valuation": 0.35},
}

COMPONENT_NAMES = ("quality", "dividend", "growth", "valuation")


def weights_of(model: str | None) -> dict[str, float]:
    """أوزانُ النموذج — ولا وزنَ افتراضيّ لنموذجٍ مجهول."""
    return dict(WEIGHTS_OF_MODEL.get(model or "", {}))


# ── المحورُ الجوهريّ لكلّ نموذج ──────────────────────────────────────
# محورٌ لا يقوم عليه القرارُ في هذا القطاع فلا جاهزيةَ بدونه، مهما علت
# الدرجة. فالمصرفُ لا يُرشَّح بلا تقييمٍ دفتريّ، والصندوقُ لا يُرشَّح
# بلا توزيعٍ مقيس — وهو نصُّ المادتين ٧ و٨.
CORE_AXES: dict[str, tuple[str, ...]] = {
    FINANCIAL:   ("quality", "valuation"),
    REIT:        ("quality", "dividend", "valuation"),
    CYCLICAL:    ("quality", "growth", "valuation"),
    OPERATING:   ("quality", "growth", "valuation"),
    REAL_ESTATE: ("quality", "valuation"),
}



# ══ لكلّ مؤشّرٍ مفهومٌ يقيسه — والتكرارُ ممنوع ══ (المادتان ٥ و٦)
#
# المعلومةُ الواحدة تحت اسمين تُحتسب مرّتين فيتضخّم وزنُها بلا إعلان:
# العائدُ على حقوق الملكية والعائدُ على رأس المال المستثمر يقيسان
# الرِّبحيّةَ على رأس المال، فوجودُهما معاً في مكوّنٍ واحدٍ يجعل الرِّبحيّة
# نصفَ الجودة وهي مكتوبةٌ ربعاً.
#
# فلكلّ مؤشّرٍ **مفهومٌ** معلَن، ولا يتكرّر مفهومٌ في مكوّنٍ واحد إلّا
# بإعلانٍ صريح في `ALLOWED_REPEAT`. ويفحصه اختبارُ القبول.
CONCEPT_OF: dict[str, str] = {
    # الرِّبحيّة على رأس المال
    "roe": "PROFITABILITY_ON_CAPITAL",
    "roic": "PROFITABILITY_ON_CAPITAL",
    "roic_cycle": "PROFITABILITY_ON_CAPITAL",
    "roe_trend": "PROFITABILITY_TREND",
    "roic_trend": "PROFITABILITY_TREND",
    # هامشُ التشغيل
    "operating_margin": "MARGIN",
    # استقرارُ الأرباح
    "earnings_stability": "EARNINGS_STABILITY",
    "eps_stability": "EARNINGS_STABILITY",
    "roe_stability": "EARNINGS_STABILITY",
    "normalized_eps": "MID_CYCLE_EARNINGS",
    # المتانةُ المالية
    "leverage_x": "SOLVENCY",
    "ltv_pct": "SOLVENCY",
    "net_debt_ebitda": "SOLVENCY",
    "worst_leverage": "SOLVENCY",
    "interest_coverage": "DEBT_SERVICE",
    # جودةُ النقد
    "cash_conversion_ratio": "CASHFLOW_QUALITY",
    "fcf_margin": "CASHFLOW_QUALITY",
    # كفاءةُ رأس المال
    "asset_turnover": "CAPITAL_EFFICIENCY",
    "inventory_intensity": "CAPITAL_EFFICIENCY",
    # النموّ
    "revenue_cagr_5y": "GROWTH_REVENUE",
    "revenue_cagr_3y": "GROWTH_REVENUE",
    "eps_cagr_5y": "GROWTH_EARNINGS",
    "eps_cagr_3y": "GROWTH_EARNINGS",
    "book_value_cagr_5y": "GROWTH_BOOK",
    "book_value_cagr_3y": "GROWTH_BOOK",
    "ffo": "GROWTH_FFO",
    # التوزيعات
    "payout_ratio": "DIVIDEND_SUSTAINABILITY",
    "ffo_payout": "DIVIDEND_SUSTAINABILITY",
    "dividend_growth": "DIVIDEND_GROWTH",
    "dividend_years": "DIVIDEND_HISTORY",
    "dividend_yield": "DIVIDEND_YIELD",
    # التقييم
    "fv_discount": "VALUE_GAP",
    "p_e": "VALUATION_EARNINGS",
    "p_e_normalized": "VALUATION_EARNINGS",
    "ev_ebitda": "VALUATION_ENTERPRISE",
    "p_b": "VALUATION_BOOK",
    "p_ffo": "VALUATION_FFO",
}

# استثناءٌ واحدٌ معلَن: النموذجُ التشغيليّ يحمل العائدَ على رأس المال
# المستثمر **وبديلَه** العائدَ على حقوق الملكية معاً، لأن المواصفة تنصّ
# على أن يُستعمل الثاني حين يتعذّر الأوّل. ووزنُهما مجتمعَين ‎40٪ من
# الجودة، وهو وزنُ مفهومٍ واحدٍ لا مفهومين.
ALLOWED_REPEAT: dict[tuple[str, str], str] = {
    ("OPERATING", "quality"): "PROFITABILITY_ON_CAPITAL",
}

# ── الأبعادُ التي تقيسها المكوّنات (المادة ٦) ─────────────────────────
DIMENSIONS = {
    "quality": ("PROFITABILITY_ON_CAPITAL", "MARGIN", "EARNINGS_STABILITY",
                "SOLVENCY", "DEBT_SERVICE", "CASHFLOW_QUALITY",
                "CAPITAL_EFFICIENCY", "MID_CYCLE_EARNINGS",
                "PROFITABILITY_TREND", "GROWTH_BOOK"),
    "dividend": ("DIVIDEND_SUSTAINABILITY", "DIVIDEND_GROWTH",
                 "DIVIDEND_HISTORY", "DIVIDEND_YIELD"),
    "growth": ("GROWTH_REVENUE", "GROWTH_EARNINGS", "GROWTH_BOOK",
               "GROWTH_FFO", "PROFITABILITY_TREND"),
    "valuation": ("VALUE_GAP", "VALUATION_EARNINGS", "VALUATION_ENTERPRISE",
                  "VALUATION_BOOK", "VALUATION_FFO", "DIVIDEND_YIELD"),
}


def concept_of(key: str) -> str | None:
    return CONCEPT_OF.get(key)


def grade_of(score: float) -> tuple[str, str]:
    for cut, letter, label in GRADES:
        if score >= cut:
            return letter, label
    return "E", "غيرُ مؤهَّل"
