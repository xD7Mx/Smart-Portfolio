"""
Expert Consensus Panel — the trustworthy face of the unified decision.

Redesigned for the Saudi market (Tadawul-optimized). Instead of six global
frameworks whose thresholds punish excellent Saudi companies for not being
"cheap-below-book", the panel is now:

  • وارن بافيت    — الجودة الدائمة والخندق التنافسي (نموذجه يناسب تداول)
  • بيتر لينش      — النمو بسعر معقول (PEG) — لا يرفض سهماً غالياً إن كان ينمو
  • إجماع المحللين — السعر المستهدف + التوصية (شراء/احتفاظ/بيع)، مصدر حقيقي
    مجمَّع من ياهو. ليس انتحالاً لتوصية جهة بعينها — بل الإجماع الفعلي
    للمحللين الذين يغطّون السهم.
  • مؤشرات مالية مباشرة (كفاءة رأس المال ROE · أمان التوزيعات Payout) —
    بأسمائها الوصفية، لا تحت أي مظلّة.

Real analyst recommendations from individual Saudi houses (الراجحي المالية
/ الأهلي كابيتال / الجزيرة) are proprietary/paywalled with no free licensed
API, so they are NEVER fabricated. Yahoo's aggregated consensus (a real,
sourced number) is used instead.

Piotroski / Altman / Graham / Greenblatt are no longer independent panel
members (their thresholds proved too harsh for Tadawul); their features
still exist and feed the internal four scores — they're just not presented
as legend verdicts anymore.
"""

from __future__ import annotations

from typing import Optional

from app.services.governance_rules import load_rules

# Real analyst consensus (Yahoo aggregator) — a sourced number, not a firm's call.
ANALYSTS = "إجماع المحللين"

# Arabic verdict for Yahoo's recommendationKey values.
_REC_AR = {
    "strong_buy": ("شراء قوي", "green"), "buy": ("شراء", "green"),
    "outperform": ("أداء متفوّق", "green"),
    "hold": ("احتفاظ", "yellow"), "neutral": ("محايد", "yellow"),
    "underperform": ("أداء دون السوق", "red"),
    "sell": ("بيع", "red"), "strong_sell": ("بيع قوي", "red"),
}


def _val(features: dict, name: str):
    raw = features.get(name)
    return raw.get("value") if isinstance(raw, dict) else raw


def _entry(expert, metric, reading, verdict, tone, role="verdict"):
    """صفٌّ في المجلس. و`role` يفصل **الرأي** عن **تفسير الدرجة**: الأوّل
    شاهدٌ يُحسب في نصاب البوّابة، والثاني بيانُ ما خفض الرقم ولا يُعدّ
    رأياً ثانياً — وإلّا صار تفسيرُ الدرجة صوتاً يصوّت على نفسه."""
    return {"expert": expert, "metric": metric, "reading": reading,
            "verdict": verdict, "tone": tone, "role": role}




# ══ مجلسٌ لكل نمطٍ بأركانه وعتباته ══ (بأمر المالك: احترافيةٌ حسب النوع)
# قال المالك: «ميزان خبراء الحوكمة لكل شركة باحترافية تامة حسب نوعها
# وقطاعها». وكان المجلسُ عامّاً: بافيت ولينش والمحللون والعائد والتوزيع —
# صالحٌ للصناعيّ، ضعيفٌ للبنك، غريبٌ عن الريت. فأُضيف لكل نمطٍ **ثلاثةُ
# أركان** هي ما يُقاس به فعلاً في مهنته، بعتباتٍ رقمية مُعلَنة.
#
# والعتباتُ ليست ذوقاً: ما كان منها من واقع السوق السعودي مقيسٌ ومذكورٌ
# مصدرُه في التعليق، وما كان اجتهاداً مهنيّاً يُقال إنه كذلك. ومن لا
# تتوفّر بياناتُ ركنه يبقى صامتاً — لا يُختلق له رقم.
#
# مرجعُ الأرقام القطاعية (الربع الأول/الثاني 2026): هامشُ الفائدة للقطاع
# المصرفيّ ‎2.84٪ · التكلفة إلى الدخل ‎30.1٪ · المتعثّرة ‎0.9٪ وتغطيتُها
# ‎201.8٪ · العائد على حقوق الملكية ‎14.7٪ · وسوقُ التأمين نما ‎10.7٪ في
# 2025 إلى ‎84.3 مليار ريال.
#
# الصيغة: (السمة · العنوان · الوحدة · اتجاه الأفضل · عتبة الممتاز ·
#          عتبة الضعيف)
_ARCH_PILLARS: dict[str, list[tuple]] = {
    "bank": [
        ("nim", "هامش الفائدة", "%", "higher", 3.2, 2.4),
        ("cost_income_ratio", "التكلفة إلى الدخل", "%", "lower", 28, 40),
        ("roe_avg", "العائد على حقوق الملكية", "%", "higher", 16, 11),
        ("npl", "القروض المتعثّرة", "%", "lower", 1.0, 2.5),
        ("car", "كفاية رأس المال", "%", "higher", 18, 13),
    ],
    "insurance": [
        ("revenue_cagr_3y", "نموّ الأقساط", "%", "band", 8, 18),
        ("net_margin", "هامش الربح (بديلُ نتيجة الاكتتاب)", "%", "higher", 8, 2),
        # ══ التذبذّبُ يُقرأ نازلاً لا صاعداً ══ (D157)
        # الميزةُ معامِلُ تذبذّب موثَّقٌ بنصّه «أقل = أكثر استقراراً»،
        # وكانت تُقرأ "higher" — فتُعدّ شركةٌ تذبذبُها ‎70٪ ممتازةً
        # وأخرى ‎40٪ ضعيفة، وهو قلبُ الحقيقة. والعتبتان ‎70/40 قيمتا
        # **درجةٍ** لا تذبذّب: كُتبتا بمعنى الدرجة ومُرِّر إليهما الخامُ.
        # فحُوِّلتا بصيغة المحرّك نفسِه (‏درجة = 100 − تذبذّب×2):
        # درجةُ 70 ⇒ تذبذّب 15 · ودرجةُ 40 ⇒ تذبذّب 30. لا عتبةَ جديدة.
        ("earnings_stability", "استقرار الربح", "%", "lower", 15, 30),
        ("combined_ratio", "النسبة المجمّعة", "%", "lower", 95, 105),
    ],
    "financial": [
        ("roe_avg", "العائد عبر الدورة", "%", "higher", 12, 6),
        ("leverage_x", "الرافعة (الأصول ÷ حقوق الملكية)", "×", "lower", 5, 8),
        ("profitable_years", "سنواتٌ رابحة من خمس", "", "higher", 5, 3),
    ],
    "reit": [
        ("ltv_pct", "الرافعة على الأصول", "%", "lower", 35, 45),
        ("ffo_payout", "التوزيع إلى الأموال من العمليات", "%", "band", 75, 90),
        ("p_ffo", "السعر إلى الأموال من العمليات", "×", "lower", 14, 20),
    ],
    "cyclical": [
        ("roic", "العائد على رأس المال عبر الدورة", "%", "higher", 10, 5),
        ("net_debt_ebitda", "صافي الدين إلى الأرباح التشغيلية", "×", "lower", 3.0, 5.0),
        ("interest_coverage", "تغطية الفوائد", "×", "higher", 3, 1.5),
    ],
    "inventory_retail": [
        ("gross_margin", "الهامش الإجمالي", "%", "higher", 25, 15),
        # ══ نسبةٌ لا نسبةٌ مئوية ══ (D158)
        # `cash_conversion_ratio` تدفّقٌ تشغيليٌّ ÷ صافي ربح — رقمٌ حول
        # الواحد، موثَّقٌ بنصّه «كلما اقترب من 1 أو زاد». وكانت تُقارَن
        # بـ‎80 و‎85 و‎90 بوحدة «٪» في سبعة مواضع، فلا شركةَ تجتازها أبداً:
        # وسيطُ السوق ‎1.2 والعتبةُ ‎80. فكلُّ شركةٍ في ستّةٍ من ثلاثةَ عشرَ
        # نمطاً تُدان في جودة أرباحها بلا استثناء.
        # والعتباتُ لم تكن مخترَعةً بل مكتوبةً بالمئة: قُسمت على مئةٍ
        # فحُفظ قصدُ كاتبها حرفاً بحرف (‏80٪ ⇒ 0.80)، ولا عتبةَ تُخترع.
        ("cash_conversion_ratio", "تحويل الربح إلى نقد", "×", "higher", 0.80, 0.50),
        # تذبذّبٌ أيضاً — التحويلُ نفسُه. (D157)
        ("margin_stability_gross", "استقرار الهامش", "%", "lower", 15, 30),
    ],
    "capital_infra": [
        ("interest_coverage", "تغطية الفوائد", "×", "higher", 4, 2),
        ("operating_margin", "هامش التشغيل", "%", "higher", 20, 8),
        ("capital_efficiency", "كفاءة رأس المال", "", "higher", 60, 30),
    ],
    "asset_light": [
        ("rule_of_40", "قاعدة الأربعين", "", "higher", 40, 20),
        ("cash_conversion_ratio", "تحويل الربح إلى نقد", "×", "higher", 0.90, 0.50),
        ("roic", "العائد على رأس المال المستثمر", "%", "higher", 20, 10),
    ],
    "commodity": [
        ("roic_cycle", "العائد على رأس المال عبر الدورة", "%", "higher", 11, 5),
        ("worst_leverage", "أسوأ رافعة في الدورة", "×", "lower", 3.0, 5.0),
        ("cash_conversion_ratio", "تحويل الربح إلى نقد", "×", "higher", 0.80, 0.30),
    ],
    "re_developer": [
        ("cash_conversion_ratio", "تحويل الربح إلى نقد", "×", "higher", 0.60, 0.00),
        ("inventory_intensity", "كثافة المخزون", "%", "lower", 45, 70),
        ("net_debt_ebitda", "صافي الدين إلى الأرباح التشغيلية", "×", "lower", 3.0, 6.0),
    ],
    "contracting": [
        ("current_ratio", "نسبة التداول", "×", "higher", 1.30, 1.00),
        ("cash_conversion_ratio", "تحويل الربح إلى نقد", "×", "higher", 0.70, 0.10),
        ("operating_margin", "الهامش التشغيليّ", "%", "higher", 8, 2),
    ],
    "consumer_defensive": [
        ("roic", "العائد على رأس المال", "%", "higher", 14, 7),
        # تذبذّبٌ أيضاً: درجةُ 85 ⇒ تذبذّب 7.5 · ودرجةُ 60 ⇒ تذبذّب 20.
        ("margin_stability", "استقرار الهامش", "%", "lower", 7.5, 20),
        ("cash_conversion_ratio", "تحويل الربح إلى نقد", "×", "higher", 0.85, 0.40),
    ],
    # ══ الاستهلاكيُّ الدوريُّ باسمه في المواصفة ══ (D433)
    # اكتشف المالكُ «العربية للخدمات» (‏4071): سعرٌ عادلٌ من قوائمها
    # و«بانتظار القوائم» في الجودة. وقِيس: المواصفةُ تُسند `consumer_cyclical`
    # لخمسَ عشرةَ شركة، وهذا الجدولُ لا يعرف الاسم (فيه `cyclical` و
    # `inventory_retail` القديمان) — فيصمت «الإطارُ القطاعيّ» لكلّ شركةٍ في
    # النمط، ويقصر المجلسُ عن النصاب متى غاب شاهدُ ياهو.
    # والأركانُ الثلاثةُ **من مواصفة النمط نفسِها بعتباتها** لا اجتهاداً،
    # وكلُّها من القوائم لا من ياهو. و«تحويلُ الربح إلى نقد» مكتوبٌ في
    # المواصفة بالمئة (80/30) فقُسم على مئة كما في D158: نسبةٌ حول الواحد.
    "consumer_cyclical": [
        ("roic", "العائد على رأس المال", "%", "higher", 15, 7),
        ("margin_stability", "استقرار الهامش", "%", "lower", 12, 40),
        ("cash_conversion_ratio", "تحويل الربح إلى نقد", "×", "higher", 0.80, 0.30),
    ],
    "general": [
        ("roic", "العائد على رأس المال المستثمر", "%", "higher", 15, 8),
        ("net_debt_ebitda", "صافي الدين إلى الأرباح التشغيلية", "×", "lower", 2.0, 4.0),
        ("cash_conversion_ratio", "تحويل الربح إلى نقد", "×", "higher", 0.80, 0.50),
    ],
}


def _pillar_entries(features: dict, archetype: str | None) -> list[dict]:
    """أركانُ النمط شهوداً في المجلس — بعتباتها المعلَنة."""
    out: list[dict] = []
    for feat, label, unit, direction, good, weak in _ARCH_PILLARS.get(archetype or "general", []):
        v = _val(features, feat)
        if v is None:
            continue
        if direction == "higher":
            tone = "green" if v >= good else "red" if v <= weak else "yellow"
            verdict = "قويّ" if tone == "green" else "ضعيف" if tone == "red" else "مقبول"
        elif direction == "lower":
            tone = "green" if v <= good else "red" if v >= weak else "yellow"
            verdict = "مريح" if tone == "green" else "مرتفع" if tone == "red" else "مقبول"
        else:                                    # نطاقٌ صحّيّ بين حدّين
            tone = "green" if good <= v <= weak else "yellow"
            verdict = "ضمن النطاق الصحّيّ" if tone == "green" else "خارج النطاق"
        reading = f"{v:,.1f}{unit}" if unit != "" else f"{v:,.1f}"
        out.append(_entry("الإطار القطاعي", label, reading, verdict, tone))
    return out

def build_expert_panel(features: dict, sector: Optional[str],
                       scores=None) -> list[dict]:
    # ══ النمطُ من المواصفة أوّلاً ══
    # خريطةُ القواعد عربيةٌ وحدها، وقطاعُ المصدر يصل إنجليزياً كثيراً —
    # فيسقط النمطُ ويُقاس الريتُ بأركانٍ سلعية (رآه المالك في «الراجحي
    # ريت»). وخريطةُ المواصفة تقبل التسميتين، فتُقدَّم.
    from app.data.archetype_spec import SECTOR_ARCHETYPE as _SPEC_MAP
    archetype = (_SPEC_MAP.get((sector or "").strip())
                 or load_rules().get("sector_archetype", {}).get(sector))
    # ══ البنكُ والتأمينُ ماليّان أيضاً ══
    # كان الشرط `archetype == "financial"` وحده، فيسقط **البنك والتأمين**
    # خارج فرع بافيت المالي إلى الفرع العامّ الذي يقرأ الهامش والتدفّق الحرّ
    # — وهما لا يُقاسان في هذين النمطين أصلاً. فيبقى الخبيرُ صامتاً، ويقلّ
    # عددُ من حكموا عن عتبة البوّابة (٣)، فيمتنع المحرّك عن قطاع التأمين
    # كلّه: خمسٌ وعشرون شركةً تقرأ «لا ينطبق» في خريطة القطاعات بينما
    # صفحةُ «التعاونية» نفسها تعرض ٨٤ (رآه المالك في صورته).
    # والتعليق أعلى الفرع كان يقول «للبنوك» — فالنيّة كانت شاملةً منذ
    # البداية والشرطُ خالفها.
    is_financial = archetype in ("financial", "bank", "insurance")
    is_reit = archetype == "reit"
    panel: list[dict] = []

    # ── Warren Buffett — الجودة الدائمة / الخندق (للبنوك: العائد على حقوق الملكية) ──
    # الريت وعاء دخل عقاري لا شركة تشغيلية، فقائمة بافيت (هامش/تدفق حر) لا تنطبق.
    if is_financial:
        roe = _val(features, "roe_avg") if _val(features, "roe_avg") is not None else _val(features, "roe")
        if roe is not None:
            tone = "green" if roe >= 15 else "yellow" if roe >= 10 else "red"
            verdict = "عائد ممتاز مستدام" if roe >= 15 else "مقبول" if roe >= 10 else "ضعيف"
            panel.append(_entry("وارن بافيت", "العائد على حقوق الملكية", f"{roe:.1f}%", verdict, tone))
    elif not is_reit:
        b = _val(features, "buffett_quality_score")
        ba = _val(features, "buffett_applicable")
        if b is not None and ba:
            tone = "green" if b >= 6 else "yellow" if b >= 4 else "red"
            verdict = "خندق تنافسي وجودة دائمة" if b >= 6 else "متوسط" if b >= 4 else "جودة محدودة"
            panel.append(_entry("وارن بافيت", "الجودة الدائمة", f"{b}/{ba}", verdict, tone))

    # أركانُ النمط — ثلاثةُ شهودٍ بعتباتٍ مهنية معلَنة لكل نوع.
    panel.extend(_pillar_entries(features, archetype))

    # ── التقييم مقابل صافي الأصول (P/B ≈ P/NAV) — الأساس لتقييم الريت ──
    # الريت السعودي يقيّم عقاراته بالقيمة العادلة (IFRS)، فالقيمة الدفترية ≈ NAV.
    if is_reit:
        pb = _val(features, "pb_ratio")
        if pb is not None:
            tone = "green" if pb <= 1.0 else "yellow" if pb <= 1.3 else "red"
            verdict = "خصم على صافي الأصول (فرصة)" if pb <= 1.0 else "قرب صافي الأصول" if pb <= 1.3 else "علاوة على صافي الأصول"
            panel.append(_entry("التقييم مقابل صافي الأصول", "P/NAV", f"{pb:.2f}×", verdict, tone))
        dy = _val(features, "dividend_yield")
        if dy is not None:
            tone = "green" if dy >= 6 else "yellow" if dy >= 4 else "red"
            verdict = "عائد توزيع مرتفع" if dy >= 6 else "عائد معتدل" if dy >= 4 else "عائد منخفض"
            panel.append(_entry("عائد التوزيع", "التوزيع النقدي", f"{dy:.1f}%", verdict, tone))

    # ── Peter Lynch — النمو بسعر معقول (PEG) — لا ينطبق على الريت (EPS مشوَّه بإعادة التقييم) ──
    peg = _val(features, "peg_ratio")
    if peg is not None and peg > 0 and not is_reit:
        tone = "green" if peg <= 1 else "yellow" if peg <= 2 else "red"
        verdict = "نمو بسعر جذّاب" if peg <= 1 else "معقول" if peg <= 2 else "السعر يفوق النمو"
        panel.append(_entry("بيتر لينش", "PEG (نمو فعلي)", f"{peg:.2f}", verdict, tone))

    # ── إجماع المحللين — التوصية + السعر المستهدف (مصدر حقيقي: ياهو المجمِّع) ──
    rec = _val(features, "analyst_recommendation")
    upside = _val(features, "analyst_upside_pct")
    if rec or upside is not None:
        v_tone = _REC_AR.get(str(rec).lower()) if rec else None
        if upside is not None:
            up_txt = f"{'+' if upside >= 0 else ''}{upside:.0f}% للسعر المستهدف"
            tone = v_tone[1] if v_tone else ("green" if upside >= 15 else "yellow" if upside >= -5 else "red")
            verdict = v_tone[0] if v_tone else ("مجال صعود جيد" if upside >= 15 else "قرب العادل" if upside >= -5 else "فوق العادل")
            panel.append(_entry(ANALYSTS, "السعر المستهدف", up_txt, verdict, tone))
        elif v_tone:
            panel.append(_entry(ANALYSTS, "التوصية", v_tone[0], v_tone[0], v_tone[1]))

    # ── مؤشرات مالية مباشرة (بلا مظلّة) ──
    # كفاءة رأس المال — ROE مستدام 12–15%+ (للبنوك يغطّيه بافيت أعلاه، فلا نكرّره).
    # ROE مشوَّه بنيوياً للريت (إعادة تقييم عقاري) — لا يُعرض له.
    roe_avg = _val(features, "roe_avg")
    if roe_avg is not None and not is_financial and not is_reit:
        tone = "green" if roe_avg >= 15 else "yellow" if roe_avg >= 12 else "red"
        verdict = "كفاءة عالية مستدامة" if roe_avg >= 15 else "كفاءة مقبولة" if roe_avg >= 12 else "كفاءة دون المستهدف"
        panel.append(_entry("المؤشرات المالية", "كفاءة رأس المال", f"ROE {roe_avg:.1f}%", verdict, tone))

    # أمان التوزيعات — للريت التوزيع المرتفع طبيعي (يُقاس بالعائد أعلاه لا بنسبة الربح).
    payout = _val(features, "payout_ratio")
    if payout is not None and not is_reit:
        tone = "green" if payout <= 80 else "yellow" if payout <= 100 else "red"
        verdict = ("توزيع مستدام" if payout <= 80
                   else "على الحافة" if payout <= 100 else "يفوق الأرباح (غير مستدام)")
        panel.append(_entry("المؤشرات المالية", "أمان التوزيعات", f"Payout {payout:.0f}%", verdict, tone))

    # ── ما خفض الدرجة يُقال في المجلس ────────────────────────────────────
    # أخرج مسحُ السوق ثلاثَ شركاتٍ درجتُها ٢٧ و٣٥ و٣٩ **ولا خبيرَ سلبيّ
    # في مجلسها**، وواحدةً درجتُها صفر بشاهدٍ واحد. وليست الدرجةُ خاطئة:
    # هي تنزل بأمرين — عقوباتٌ اشتعلت، أو إشاراتٌ إيجابية قليلة اكتُسبت.
    # لكنّ المجلس كان يعرض المؤشّرات المختارة وحدها، فيقرأ المالك درجةً
    # منخفضة تحت صفٍّ أخضر كامل ولا يجد لها سبباً. والرقمُ الذي لا يُفسَّر
    # لا يُوثَق به، ولو كان صحيحاً.
    # فيُنقل هنا **ما خفض الدرجة فعلاً**: كلُّ عقوبةٍ اشتعلت برسالتها هي
    # (لا نصّاً مؤلَّفاً)، وإن لم تشتعل عقوبةٌ قيلت الحقيقةُ الأخرى:
    # الإشاراتُ الإيجابية قليلة. ورفضُ الفلتر الحاسم يُقال أوّلاً.
    if scores is not None:
        if getattr(scores, "rejected", False):
            panel.append(_entry("الفلتر الحاسم", "عيبٌ جوهريّ",
                                "مرفوضة",
                                getattr(scores, "hard_filter_message", None)
                                or "فشلت في فلترٍ أساسيّ", "red", role="driver"))
        else:
            fired = []
            for cat in ("quality", "safety", "valuation", "timing"):
                cs = getattr(scores, cat, None)
                for h in (getattr(cs, "hits", None) or []):
                    if getattr(h, "kind", None) == "penalty":
                        fired.append(h)
            fired.sort(key=lambda h: h.points)          # الأشدُّ خصماً أوّلاً
            for h in fired[:3]:
                panel.append(_entry("ما خفض الدرجة", "عقوبةٌ اشتعلت",
                                    f"{abs(h.points):.0f}−", h.message, "red",
                                    role="driver"))
            if not fired:
                earned = [getattr(getattr(scores, c, None), "score", None)
                          for c in ("quality", "safety")]
                earned = [e for e in earned if e is not None]
                if earned and sum(earned) / len(earned) < 50:
                    panel.append(_entry(
                        "ما خفض الدرجة", "إشاراتٌ إيجابية",
                        "قليلة",
                        "لم تشتعل عقوبة — الدرجةُ منخفضةٌ لقلّة ما اكتسبته "
                        "الشركة من إشاراتٍ إيجابية على بياناتها المتاحة",
                        "yellow", role="driver"))

    return panel
