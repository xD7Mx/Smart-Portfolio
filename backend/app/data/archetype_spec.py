"""مواصفةُ تقييم وحوكمة شركات السوق السعودي — اثنا عشر نمطاً.

## ما هذا الملفّ

هو **المنهجية كلُّها في موضعٍ واحد**، لا شيفرةٌ تُخفيها. كتبها مراجعٌ
خارجيّ بطلب المالك بعد أن قال: «أعِد الهيكلة من الصفر». وكلُّ رقمٍ فيها
مصنَّف:
  · **مقيس**  — من مصدرٍ منشور (يُذكر في التعليق)
  · **مشتقّ** — من معادلةٍ أو حدٍّ نظاميّ
  · **اجتهاد** — رأيٌ مهنيّ قابل للنقاش، ويُقال إنه كذلك

ولماذا ملفُّ بياناتٍ لا شيفرة: لأن المالك يجب أن يقرأ العتبةَ التي حُكم
بها على شركته دون أن يقرأ برنامجاً. وتغييرُ عتبةٍ هنا سطرٌ واحد، ويُقاس
أثرُه على السوق كلِّه بأداة المعايرة قبل أن يُسلَّم.

## الفرق عن سابقتها

كان المحرّك يجمع ثلاثةً وأربعين قطاعاً في عشرة أنماط، ويقيس الجميعَ
بقواعد عامّة تُعطَّل بعضُها لبعض الأنماط. فصار: **اثنا عشر نمطاً**، ولكلّ
نمطٍ بطاقتُه — خمسةٌ إلى سبعة مؤشّرات بأوزانها وعتباتها، ومؤشّراتٌ
تُستبعد صراحةً لأنها بلا معنًى فيه، وعقوباتٌ مانعة، ومنهجيةُ قيمةٍ
عادلة تخصّه.

وأُضيف نمطان بالقسمة (‏commodity وcontracting وre_developer من
`cyclical`، وconsumer_defensive وconsumer_cyclical من
`inventory_retail`)، وحُذف `general` — فلا شركةَ بلا نمطٍ يخصّها.
"""

from __future__ import annotations

# ── (١) خريطةُ الأنماط: القطاع العربيّ ← النمط ──────────────────────────
# غُطّيت القطاعات الخمسة والأربعون كلُّها. وما لم يُذكر يُسنَد بالقواعد
# الحتمية في `FALLBACK_RULES` أدناه — لا بالتخمين.
SECTOR_ARCHETYPE: dict[str, str] = {
    # مالي
    "البنوك": "bank",
    # ══ شركةُ التمويل ليست بنكاً ══ (كشفه `rank_check.py`)
    # كانت تُصنَّف `bank`، فتُقاس بهامش العمولات وتكلفةِ المخاطر
    # ونسبةِ التكلفة إلى الدخل **مقابل البنوك**. وهي لا تقبل ودائع
    # فتموّل نفسها بالدَّين بسعر السوق، ورافعتُها وهيكلُ دخلها
    # مختلفان. وقياسُها بمسطرةِ غيرها هو عينُ العطب الذي عولج في
    # هذا الملفّ كلِّه.
    "التمويل": "financial",
    "التأمين": "insurance",
    "الاستثمار": "financial",
    "الخدمات المالية": "financial",
    "أسواق رأس المال والوساطة": "financial",
    # عقاريّ متداول
    "الصناديق العقارية المتداولة": "reit",
    "ريت": "reit",
    "صناديق المؤشرات المتداولة": "fund",
    # سلعيّ متلقّي السعر
    "الطاقة": "commodity",
    "المواد الأساسية": "commodity",
    "السلع الأساسية": "commodity",
    "الأسمنت": "commodity",
    "التعدين": "commodity",
    # ══ النقلُ عملٌ كثيفُ الأصول لا منتِجُ سلعة ══
    # كان `commodity`، ومسطرتُه العائدُ عبر الدورة وأسوأُ رافعة —
    # وهي تصف منتِجَ سلعةٍ لا يملك تسعيرَها. وشركاتُ النقل تشتري
    # أصولاً طويلةَ العمر بدَينٍ طويل ودخلُها متعاقَدٌ أو منظَّم،
    # فالسؤالُ فيها: أتكفي التدفّقاتُ خدمةَ الدين؟ وأيُنفَق على الأسطول
    # ما يُبقيه حيّاً؟ وهذه أركانُ النمط كثيف الأصول.
    "النقل": "capital_infra",
    "الزراعة": "commodity",
    "الكيماويات": "commodity",
    "الصناعات": "commodity",
    "السلع الرأسمالية": "commodity",
    # بنيةٌ رأسمالية / دخلٌ متعاقَد عليه
    "المرافق": "capital_infra",
    "المرافق العامة": "capital_infra",
    "الاتصالات": "capital_infra",
    "الخدمات": "capital_infra",
    "الخدمات التجارية": "capital_infra",
    # عقاراتٌ تطويرية ومقاولات
    "العقارات": "re_developer",
    "إدارة وتطوير العقارات": "re_developer",
    "المقاولات": "contracting",
    "الخدمات التجارية والمهنية": "contracting",
    # استهلاكيّ دفاعيّ
    "إنتاج الأغذية": "consumer_defensive",
    "الأغذية": "consumer_defensive",
    "الأدوية": "consumer_defensive",
    "الرعاية الصحية": "consumer_defensive",
    "المنتجات المنزلية والشخصية": "consumer_defensive",
    "تجزئة وتوزيع السلع الاستهلاكية": "consumer_defensive",
    # استهلاكيّ تقديريّ
    "التجزئة": "consumer_cyclical",
    "تجزئة وتوزيع السلع الكمالية": "consumer_cyclical",
    "السلع الكمالية": "consumer_cyclical",
    "السلع طويلة الأجل": "consumer_cyclical",
    "الخدمات الاستهلاكية": "consumer_cyclical",
    "الفنادق": "consumer_cyclical",
    "الفنادق والترفيه": "consumer_cyclical",
    "السياحة": "consumer_cyclical",
    "الترفيه": "consumer_cyclical",
    "الإعلام": "consumer_cyclical",
    "الإعلام والترفيه": "consumer_cyclical",
    # ══ التعليمُ دفاعيٌّ لا دوريّ ══
    # كان `consumer_cyclical`، ومسطرتُه دورانُ المخزون ونموُّ الإيراد —
    # وهي تصف تجزئةً. ودخلُ التعليم تسجيلٌ متكرّرٌ متعاقَد، والأسرةُ
    # تقطع الكماليَّ قبل مدرسة أبنائها. فثباتُ الهامش هو المقياس.
    "التعليم": "consumer_defensive",
    # خفيف الأصول
    "التقنية": "asset_light",
    "التطبيقات وخدمات التقنية": "asset_light",

    # ══ أسماءُ ياهو الإنجليزية ══
    # قطاعُ المصدر يصل إنجليزياً لكثيرٍ من الشركات، ولا يطابق مفتاحاً
    # عربياً — فيسقط النمطُ إلى الإسناد الحتميّ ويُقاس الريتُ بركنٍ سلعيّ.
    # رآه المالك في «الراجحي ريت»: «العائد على رأس المال عبر الدورة» وهو
    # ركنُ النمط السلعيّ لا الريت. فتُقبل التسميتان.
    "Financial Services": "financial",
    "Banks": "bank",
    "Insurance": "insurance",
    "Real Estate": "re_developer",
    "REIT": "reit",
    "REIT—Diversified": "reit",
    "Energy": "commodity",
    "Basic Materials": "commodity",
    "Industrials": "commodity",
    "Utilities": "capital_infra",
    "Communication Services": "capital_infra",
    "Consumer Defensive": "consumer_defensive",
    "Healthcare": "consumer_defensive",
    "Consumer Cyclical": "consumer_cyclical",
    "Technology": "asset_light",

    # ══ أسماءُ «تداول» الرسمية — مصدرُ التصنيف نفسُه ══ (D398)
    #
    # قِيس على خادم المالك: لقطةُ «تداول» تحمل `sector_en` لكلّ رمز —
    # ‎272 رمزاً في الرئيسيّ، ‎100% لها قطاعٌ، و‎22 قطاعاً متمايزاً.
    # وقِيس أن تصنيفَنا يخالفه في **‎12 شركةً بإجماعٍ قويّ** وأكثرَ في
    # الخرائط الضعيفة: 4030 «البحري» عندنا نقلٌ وعندهم طاقة · 8313
    # «رسن» عندنا تقنيةٌ وعندهم تأمين · 2140 «أيان» عندنا خدماتٌ ماليةٌ
    # وعندهم أغذية. والخريطةُ تُطبَّق بالقطاع، فشركةٌ في قطاعٍ خطأ
    # تُقاس بمسطرةٍ ليست لها ويفسد حكمُها في المحرّكَين معاً.
    #
    # والأسماءُ أدناه **مطابقةٌ لقرارات المسطرة العربية حرفاً بحرف** —
    # لا تصنيفٌ جديدٌ من عندي: «السلع الرأسمالية» سلعيّةٌ عندنا فـ
    # `Capital Goods` سلعيّة، و«النقل» كثيفُ أصولٍ فـ`Transportation`
    # كذلك، و«الخدمات التجارية والمهنية» مقاولاتٌ فـ`Commercial &
    # Professional Svc` مقاولات. فمن أراد مراجعةَ تصنيفٍ راجع أصلَه
    # العربيَّ أعلاه، ولا تصنيفَ في موضعَين يختلفان.
    "Banks ": "bank",                      # احتياطاً لفراغٍ لاحقٍ في الجلب
    "Insurance ": "insurance",
    "REITs": "reit",
    "Real Estate Mgmt & Dev't": "re_developer",
    "Materials": "commodity",
    "Capital Goods": "commodity",
    "Transportation": "capital_infra",
    "Telecommunication Services": "capital_infra",
    "Food & Beverages": "consumer_defensive",
    "Consumer Staples Distribution & Retail": "consumer_defensive",
    "Household & Personal Products": "consumer_defensive",
    "Pharma, Biotech & Life Science": "consumer_defensive",
    "Health Care Equipment & Svc": "consumer_defensive",
    "Consumer Discretionary Distribution & Retail": "consumer_cyclical",
    "Consumer Durables & Apparel": "consumer_cyclical",
    "Consumer Services": "consumer_cyclical",
    "Media and Entertainment": "consumer_cyclical",
    "Software & Services": "asset_light",
    "Commercial & Professional Svc": "contracting",
}

# إسنادُ ما لم يُدرَج — قواعدُ حتميّة من البيانات نفسها، تُجرَّب بالترتيب.
# ولا «عامّ» بعد اليوم: كلُّ شركةٍ تقع في نمطٍ له بطاقةٌ تخصّه.
FALLBACK_RULES = [
    ("financial", "أصول/حقوق ملكية ≥ 4 و مصروف فوائد/إيراد ≥ 0.15"),
    ("capital_infra", "إنفاق رأسماليّ/إيراد ≥ 0.10 و إهلاك/إيراد ≥ 0.08"),
    ("consumer_cyclical", "مخزون/أصول ≥ 0.15"),
    ("commodity", "استقرار الربح < 0.55"),
    ("asset_light", "غير ذلك"),
]

# ── (٢) بطاقاتُ التقييم ─────────────────────────────────────────────────
# لكل مؤشّر: (السمة · العنوان · الوزن · عتبة الممتاز · عتبة الضعيف ·
#             الاتجاه) حيث الاتجاه: higher | lower | band
# و«band» تعني نطاقاً صحّيّاً بين رقمين: خارجه أضعف.
SCORECARDS: dict[str, dict] = {
    "bank": {
        "name": "البنوك",
        "metrics": [
            # ══ المعياران المُلزِمان أوّلاً ══ (قرارُ مجلس نِصاب)
            # كانا يُحسبان في `sector_metrics._regulatory` من إفصاحات
            # «أرقام» ولا يدخلان البطاقة — أوثقُ رقمين في المصرفية،
            # مُلزَمان رقابياً ومنشوران ربعياً، يُستخرجان ثم يُرميان.
            # وهما `*_abs`: يُقاسان بحدّهما المنشور لا برتبتهما بين
            # الأقران — فبنكٌ دون حدّ بازل لا يُنجّيه أن أقرانه أسوأ.
            ("car", "كفاية رأس المال", 20, 18, 10.5, "higher_abs"),
            ("npl", "القروض المتعثّرة", 15, 1.0, 3.0, "lower_abs"),
            ("nim", "هامش العائد المصرفيّ", 15, 2.90, 2.10, "higher"),
            ("cost_income_ratio", "التكلفة إلى الدخل", 15, 28, 40, "lower"),
            ("cost_of_risk", "تكلفة المخاطر", 15, 0.15, 0.50, "lower"),
            ("roe_avg", "العائد على حقوق الملكية", 12, 16, 11, "higher"),
            # ══ حُذفت «الرافعة المصرفية» ══
            # كانت ‎8×/10×، وبازل ٣ يحدّها عند ‎33× (نسبةُ رافعة ‎3٪) —
            # فرقمُنا لم يكن يخالف المعيار قليلاً بل يقيس شيئاً آخر.
            # وكفايةُ رأس المال هي المقياسُ الرقابيّ الصحيح لِما أرادته:
            # فهي تزن الأصولَ بمخاطرها، والرافعةُ الخام لا تفعل.
            ("earnings_stability", "استقرار الربح", 8, 12, 45, "lower"),
        ],
        # مؤشّراتٌ بلا معنًى في هذا النمط — تُستبعد صراحةً لا تُترك تصمت
        "excluded": ["cash_conversion_ratio", "net_debt_ebitda",
                     "interest_coverage", "altman_z", "current_ratio",
                     "inventory_turnover"],
        "blocking": [("leverage_x", "gt", 12, "منع شراء"),
                     ("cost_of_risk", "gt", 1.0, "سقف 35")],
    },
    "insurance": {
        "name": "التأمين",
        "metrics": [
            # ══ النسبةُ المجمّعة هي المعيارُ الأوّل ══ (قرارُ مجلس نِصاب)
            # كانت البطاقةُ بلا أشهرِ مقياسٍ في اقتصاد التأمين كلِّه، وهو
            # محسوبٌ في أنبوبنا حين يصل من «أرقام». ودونَ المئة ربحُ
            # اكتتابٍ حقيقيّ، وفوقَها خسارةُ اكتتابٍ يغطّيها دخلُ
            # الاستثمار — وانضباطُ الاكتتاب هو الميزةُ الدائمة الوحيدة في
            # هذا العمل، أمّا عائدُ الاستثمار فعائدُ سوقٍ يناله الجميع.
            # وهي `lower_abs`: المئةُ حدٌّ تعريفيّ لا رتبةٌ بين أقران.
            ("combined_ratio", "النسبة المجمّعة", 30, 92, 100, "lower_abs"),
            ("premium_to_equity", "الاكتتاب إلى رأس المال", 20, 2.5, 4.0, "lower"),
            ("earnings_stability", "استقرار الربح", 20, 20, 70, "lower"),
            # هامشُ الربح الصافي بديلٌ ضعيف عن المجمّعة — يخلط نتيجةَ
            # الاكتتاب بنتيجة الاستثمار — فبقي بوزنٍ أصغر لا بوزن الصدارة.
            ("net_margin", "هامش الربح التأميني", 20, 8, 2, "higher"),
            # ══ حُذف «نموّ الأقساط» ══
            # كان يُقاس من سطر الإيراد، والمعيارُ الدوليّ لعقود التأمين
            # (‏IFRS 17) النافذ من ٢٠٢٣ غيّر تعريفَ إيراد التأمين تغييراً
            # جوهرياً. فمقارنةُ سنواتٍ تعبر ٢٠٢٣ تقيس تغيُّرَ المحاسبة لا
            # تغيُّرَ العمل — ومصدرٌ معطوبٌ أسوأ من مؤشّرٍ غائب.
            ("profitable_years", "سنوات الربحية", 10, 5, 2, "higher"),
        ],
        # ══ ركنٌ لا تقوم الدرجةُ بدونه ══ (كشفه المسبار على السوق)
        # خرجت «بوبا» بدرجة ‎86.2 وتغطيةٍ ‎50٪ والنسبةُ المجمّعة غائبة —
        # أي أن الشاشة تقول «ممتازة» عن شركة تأمينٍ ينقصها المقياسُ الذي
        # يُعرَّف به التأمين. ومحرّكُ القيمة العادلة في الشاشة نفسها
        # يمتنع لهذا السبب بعينه، فتناقضَ شطرا الشاشة الواحدة.
        # وليس هذا نقصَ تغطيةٍ عاديّاً يُعالجه الحدُّ العامّ: انضباطُ
        # الاكتتاب هو الميزةُ الدائمة الوحيدة في هذا العمل، وما عداه
        # عائدُ سوقٍ يناله الجميع. فبلا هذا الركن لا درجة.
        "essential": ["combined_ratio"],
        "excluded": ["roic", "cash_conversion_ratio", "net_debt_ebitda",
                     "inventory_turnover", "capex_to_depreciation", "ebitda_margin"],
        "blocking": [],
    },
    "financial": {
        "name": "التمويل والوساطة",
        "metrics": [
            ("roe_avg", "العائد على حقوق الملكية", 20, 14, 7, "higher"),
            ("leverage_x", "الرافعة", 20, 5, 8, "lower"),
            ("cost_of_risk", "تكلفة المخاطر على الأصول", 15, 0.30, 1.20, "lower"),
            ("earnings_stability", "استقرار الربح", 15, 15, 55, "lower"),
            ("interest_coverage", "تغطية الفوائد", 15, 2.5, 1.3, "higher"),
            ("profitable_years", "سنوات الربحية", 15, 5, 2, "higher"),
        ],
        "excluded": ["cash_conversion_ratio", "net_debt_ebitda",
                     "inventory_turnover", "capex_to_depreciation"],
        "blocking": [("leverage_x", "gt", 9, "منع شراء")],
    },
    "reit": {
        "name": "الصناديق العقارية المتداولة",
        "metrics": [
            ("ltv_pct", "الرافعة العقارية", 25, 35, 48, "lower"),
            ("ffo_payout", "توزيع الأموال من العمليات", 20, 75, 90, "band"),
            ("dividend_yield", "العائد التوزيعي", 15, 7.0, 4.5, "higher"),
            ("interest_coverage", "تغطية الفوائد", 15, 3.0, 1.5, "higher"),
            ("earnings_stability", "استقرار الربح", 15, 15, 55, "lower"),
            ("dividend_growth", "نموّ التوزيع", 10, 0, -10, "higher"),
        ],
        "excluded": ["roic", "cash_conversion_ratio", "inventory_turnover",
                     "capex_to_depreciation", "ebitda_margin"],
        "blocking": [("ltv_pct", "gt", 55, "منع شراء")],
        "min_metrics": 3,          # ثلاثةٌ تكفي البوّابة (بدل سنتين)
    },
    "commodity": {
        "name": "السلعيّ متلقّي السعر",
        "metrics": [
            ("roic_cycle", "العائد على رأس المال عبر الدورة", 25, 11, 5, "higher"),
            ("worst_leverage", "أسوأ رافعة في الدورة", 20, 3.0, 5.0, "lower"),
            ("earnings_stability", "استقرار الربح", 15, 35, 110, "lower"),
            ("cash_conversion_ratio", "تحويل الربح إلى نقد", 15, 80, 30, "higher"),
            ("ebitda_margin", "هامش الأرباح التشغيلية", 10, 25, 10, "higher"),
            ("profitable_years", "سنوات الربحية", 10, 4, 2, "higher"),
            ("altman_z", "ألتمان", 5, 3.0, 1.8, "higher"),
        ],
        # نموُّ الإيراد يُستبعد عمداً: في السلعيّ إشارةُ سعرٍ لا إشارةُ
        # جودة، وإدخالُه يكافئ الشراءَ في قمّة الدورة.
        "excluded": ["revenue_cagr_3y"],
        "blocking": [],
    },
    "capital_infra": {
        "name": "البنية الرأسمالية والدخل المتعاقَد عليه",
        "metrics": [
            ("interest_coverage", "تغطية الفوائد", 25, 4.0, 2.0, "higher"),
            ("ebitda_margin", "هامش الأرباح التشغيلية", 20, 30, 15, "higher"),
            ("capex_to_depreciation", "الإنفاق الرأسماليّ إلى الإهلاك", 15, 0.9, 1.4, "band"),
            ("net_debt_ebitda", "صافي الدين إلى الأرباح التشغيلية", 15, 3.5, 5.5, "lower"),
            ("earnings_stability", "استقرار الربح", 15, 12, 45, "lower"),
            ("payout_ratio", "نسبة التوزيع", 10, 40, 80, "band"),
        ],
        "excluded": ["inventory_turnover", "inventory_intensity"],
        "blocking": [("capex_to_depreciation", "gt", 2.0, "سقف 35")],
    },
    "re_developer": {
        "name": "المطوّر العقاريّ",
        "metrics": [
            ("cash_conversion_ratio", "تحويل الربح إلى نقد", 20, 60, 0, "higher"),
            ("net_debt_ebitda", "صافي الدين إلى الأرباح التشغيلية", 20, 3.0, 6.0, "lower"),
            ("inventory_intensity", "كثافة المخزون", 15, 45, 70, "lower"),
            ("roic", "العائد على رأس المال", 15, 10, 4, "higher"),
            ("interest_coverage", "تغطية الفوائد", 15, 3.0, 1.2, "higher"),
            ("earnings_stability", "استقرار الربح", 15, 40, 120, "lower"),
        ],
        # الدفتريةُ هنا تكلفةٌ تاريخية لا قيمةَ سوقٍ، فالعائدُ عليها مضلّل.
        "excluded": ["roe_avg", "margin_stability"],
        "blocking": [],
    },
    "contracting": {
        "name": "المقاولات والصناعات الهندسية",
        "metrics": [
            ("current_ratio", "نسبة التداول", 20, 1.30, 1.00, "higher"),
            ("cash_conversion_ratio", "تحويل الربح إلى نقد", 20, 70, 10, "higher"),
            ("operating_margin", "الهامش التشغيليّ", 15, 8, 2, "higher"),
            ("earnings_stability", "استقرار الربح", 15, 30, 100, "lower"),
            ("interest_coverage", "تغطية الفوائد", 15, 4.0, 1.5, "higher"),
            ("profitable_years", "سنوات الربحية", 15, 5, 2, "higher"),
        ],
        "excluded": [],
        "blocking": [("current_ratio", "lt", 0.9, "منع شراء")],
    },
    "consumer_defensive": {
        "name": "الاستهلاكيّ المتكرّر والرعاية الصحية",
        "metrics": [
            ("roic", "العائد على رأس المال", 20, 14, 7, "higher"),
            ("margin_stability", "استقرار الهامش", 20, 8, 30, "lower"),
            ("cash_conversion_ratio", "تحويل الربح إلى نقد", 15, 85, 40, "higher"),
            ("net_debt_ebitda", "صافي الدين إلى الأرباح التشغيلية", 15, 2.0, 4.0, "lower"),
            ("revenue_cagr_3y", "نموّ الإيراد", 15, 8, 0, "higher"),
            ("operating_margin", "الهامش التشغيليّ", 15, 12, 4, "higher"),
        ],
        "excluded": [],
        "blocking": [],
    },
    "consumer_cyclical": {
        "name": "التجزئة التقديرية والضيافة",
        "metrics": [
            ("inventory_turnover", "دوران المخزون", 20, 6, 3, "higher"),
            ("margin_stability", "استقرار الهامش", 20, 12, 40, "lower"),
            ("cash_conversion_ratio", "تحويل الربح إلى نقد", 15, 80, 30, "higher"),
            ("roic", "العائد على رأس المال", 15, 15, 7, "higher"),
            ("net_debt_ebitda", "صافي الدين إلى الأرباح التشغيلية", 15, 2.5, 4.5, "lower"),
            ("revenue_cagr_3y", "نموّ الإيراد", 15, 10, 0, "higher"),
        ],
        "excluded": [],
        "blocking": [],
    },
    "asset_light": {
        "name": "خفيف الأصول",
        "metrics": [
            ("roic", "العائد على رأس المال المستثمر", 25, 20, 10, "higher"),
            ("cash_conversion_ratio", "تحويل الربح إلى نقد", 20, 90, 50, "higher"),
            ("revenue_cagr_3y", "نموّ الإيراد", 20, 15, 3, "higher"),
            ("operating_margin", "الهامش التشغيليّ", 15, 20, 8, "higher"),
            ("net_debt_ebitda", "صافي الدين إلى الأرباح التشغيلية", 10, 1.0, 3.0, "lower"),
            ("earnings_stability", "استقرار الربح", 10, 20, 70, "lower"),
        ],
        "excluded": ["inventory_turnover", "inventory_intensity"],
        "blocking": [],
    },
    "fund": {
        "name": "الصناديق المتداولة",
        "metrics": [],          # وعاءٌ لا شركة: لا درجةَ ولا قيمة
        "excluded": [],
        "blocking": [],
        "abstain": "الصندوقُ وعاءٌ يتبع مؤشّراً أو أصلاً — لا تُقاس جودةُ "
                   "إدارته بمقاييس الشركات، وسعرُه صافي أصوله.",
    },
}

# ── (٣) منهجيةُ القيمة العادلة لكل نمط ──────────────────────────────────
# `weights`: النموذجُ الأساسيّ ووزنه، والمساندُ ووزنه (المجموع 1.0)
# `terminal`: النموّ النهائيّ · `explicit`: قاعدةُ النموّ الصريح
# `abstain_if`: شروطُ الامتناع النهائيّ عن التقدير
VALUATION: dict[str, dict] = {
    "bank":               {"weights": {"residual_income": 0.65, "sector_pe": 0.35},
                           "terminal": 0.035, "explicit": None,
                           "abstain_if": ["leverage_gt_12", "no_roe", "loss_last_year"]},
    "insurance":          {"weights": {}, "terminal": None, "explicit": None,
                           "abstain_if": ["always"]},
    "financial":          {"weights": {"residual_income": 0.60, "sector_pe": 0.40},
                           "terminal": 0.035, "explicit": None,
                           "abstain_if": ["leverage_gt_9", "two_loss_years"]},
    "reit":               {"weights": {"capitalized_yield": 0.55, "residual_income": 0.25,
                                       "sector_pe": 0.20},
                           "terminal": None, "explicit": "dividend_growth_capped",
                           "abstain_if": ["ltv_gt_55", "no_dividend", "history_lt_1y"]},
    "fund":               {"weights": {}, "terminal": None, "explicit": None,
                           "abstain_if": ["always"]},
    "commodity":          {"weights": {"normalized_pe": 0.45, "dcf": 0.30,
                                       "residual_income": 0.25},
                           "terminal": 0.035, "explicit": 0.0,
                           "abstain_if": ["negative_normalized_eps", "history_lt_4y"]},
    "capital_infra":      {"weights": {"dcf": 0.55, "residual_income": 0.25,
                                       "sector_pe": 0.20},
                           "terminal": 0.035, "explicit": "min_growth_8",
                           "abstain_if": ["no_debt_field", "coverage_lt_1"]},
    "re_developer":       {"weights": {"nav_like": 0.50, "normalized_pe": 0.30,
                                       "residual_income": 0.20},
                           "terminal": 0.030, "explicit": 0.0,
                           "abstain_if": ["negative_equity", "three_years_negative_ccr"]},
    "contracting":        {"weights": {"normalized_pe": 0.45, "dcf": 0.35,
                                       "residual_income": 0.20},
                           "terminal": 0.030, "explicit": "min_growth_8",
                           "abstain_if": ["negative_normalized_eps", "current_ratio_lt_09"]},
    "consumer_defensive": {"weights": {"dcf": 0.45, "residual_income": 0.35,
                                       "sector_pe": 0.20},
                           "terminal": 0.035, "explicit": "min_growth_12",
                           "abstain_if": ["no_debt_field", "negative_avg_profit"]},
    "consumer_cyclical":  {"weights": {"dcf": 0.45, "residual_income": 0.35,
                                       "sector_pe": 0.20},
                           "terminal": 0.035, "explicit": "min_growth_12",
                           "abstain_if": ["no_debt_field", "negative_avg_profit"]},
    "asset_light":        {"weights": {"dcf": 0.50, "residual_income": 0.30,
                                       "sector_pe": 0.20},
                           "terminal": 0.035, "explicit": "min_growth_12",
                           "abstain_if": ["no_debt_field", "negative_avg_profit"]},
}

# معاملُ صافي الأصول للمطوّر العقاريّ: أرضُه بالتكلفة التاريخية فتُخصم.
NAV_FACTOR = {"re_developer": 0.85, "reit": 1.00}

# ── (٤) الثوابتُ العامة ─────────────────────────────────────────────────
# (مطابقةٌ لما نُفِّذ في `fair_value.py` — تُذكر هنا لتُقرأ في موضعٍ واحد)
CONSTANTS = {
    "rf": 0.050,                    # مقيس: صكوك «صح» 4.60٪ · ريبو ساما 4.25٪
    "erp": 0.050,                   # مشتقّ: ناضج 4.3٪ + قُطريّة 0.7٪
    "beta_blume": (0.67, 0.33),     # مشتقّ: تعديل بلوم
    "beta_floor_cap": (0.85, 2.00),  # اجتهاد: بيتا منحازة نزولاً بقلّة السيولة
    "min_required_return": 0.090,   # مشتقّ: أدنى r ممكن 9.25٪
    "terminal_growth": 0.035,       # مشتقّ: نموّ اسميّ 4.5–5.5٪ بقيد g ≤ rf
    "explicit_cap": 0.12,           # اجتهاد
    "fade_years": 15,               # اجتهاد: إطار الخندق
    "sane_band": (0.40, 2.50),      # مشتقّ: متماثل لوغاريتمياً (1/2.5 = 0.40)
    "dispersion_abstain": 3.0,      # اجتهاد
}

# ── (٥) قواعدُ القرار — أوّل مطابقةٍ تفوز ───────────────────────────────
DECISION_SPEC = [
    ("امتناع",   "نمط fund أو insurance · أو تشتّت ≥3× · أو تغطية <0.50 "
                 "· أو أقلّ من سنتين ماليتين (الريت: سنة)", (0.12, 0.18)),
    ("تجنب",     "عقوبة مانعة مشتعلة · أو الدرجة <42", (0.22, 0.28)),
    ("شراء قوي", "الدرجة ≥75 · وتغطية ≥0.70 · وقيمة عادلة متاحة · "
                 "والسعر ≤ سعر الدخول · وبلا عقوبة مانعة", (0.02, 0.04)),
    ("شراء",     "الدرجة ≥65 · وتغطية ≥0.60 · وقيمة عادلة متاحة · "
                 "والسعر < القيمة العادلة", (0.08, 0.12)),
    ("انتظار",   "ما بقي", (0.42, 0.52)),
]

# ── (٦) اختبارُ القبول — نطاقاتٌ تُقاس بعد التنفيذ ──────────────────────
ACCEPTANCE = {
    "وسيط القيمة ÷ السعر": (0.95, 1.10),
    "المرجَّح بالقيمة السوقية": (0.90, 1.10),
    "المدى الربيعيّ للقيمة ÷ السعر": (0.70, 1.40),
    "نسبة المسارات المُسقَطة بحدّ العقل": (0.0, 0.10),
    "متوسّط الدرجة": (52, 58),
    "انحراف الدرجة المعياريّ": (12, 16),
    "نسبة الدرجات فوق ٧٥": (0.08, 0.12),
    "نسبة الدرجات تحت ٤٢": (0.22, 0.28),
    "ارتباط الدرجة بالتغطية": (-0.10, 0.15),
    "عدد «شراء قوي»": (8, 16),
}
# شرطُ القبول الكلّيّ: تحقُّقُ (وسيط القيمة) و(المرجَّح) و(المسقَط)
# و(ارتباط التغطية) معاً. وتحقُّقُ الوسيطِ وحده مع فشل المُسقَط لا يُعتدّ
# به — فحدُّ العقل قادرٌ على تزوير الوسيط بقصّ الأطراف حول السعر.
ACCEPTANCE_GATE = ("وسيط القيمة ÷ السعر", "المرجَّح بالقيمة السوقية",
                   "نسبة المسارات المُسقَطة بحدّ العقل",
                   "ارتباط الدرجة بالتغطية")


def archetype_for(sector: str | None) -> str | None:
    """النمطُ من القطاع — وما لم يُدرَج يُسنَد بالقواعد الحتمية لاحقاً."""
    return SECTOR_ARCHETYPE.get((sector or "").strip())


# ══ سقفُ التغطية أُزيل — لم يُستعمل قطّ ══
# كانت هنا `ATTAINABLE`: سقفٌ لكلّ نمطٍ تُنسب إليه التغطية بدل الكمال
# النظريّ. والفكرةُ سليمة، لكنّ `spec_score` يحسب التغطيةَ من الأوزان
# مباشرةً (‏got_w ÷ tot_w) ولم يقرأ هذا الجدولَ يوماً — فبقي رقماً
# يُصان ويُفحص ولا يؤثّر في شيء، ويُخرج إنذاراً كاذباً في اللجنة كلّما
# تغيّرت السماتُ تحته.
#
# وإن عاد يوماً معنى «ما يمكن بلوغه»، فليُبنَ يومَها بمستهلكٍ يقرؤه.

