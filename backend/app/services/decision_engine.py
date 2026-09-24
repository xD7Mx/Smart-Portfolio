"""
Decision Engine — Phase 10 of the governance-engine redesign.

Turns the four independent scores into ONE final call — not by summing
them, but by testing them together against ordered rules from
governance_rules.yaml's `decision_rules` section (first full match wins).
This is what makes "excellent quality but terrible price → Hold" and
"cheap price but weak quality → Avoid" possible, which a pure weighted-sum
score can never express cleanly.

A Hard Filter rejection (four_scores.rejected) always short-circuits to
"تجنب" before any decision rule is even considered — no combination of
scores can override a fatal flaw.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services import governance_rules
from app.services.four_scores import FourScores

_METRIC_OPS = governance_rules.OPS


@dataclass
class Decision:
    decision: str
    matched_rule_id: str
    reason: str


# أسماءُ الأركان كما تُقرأ في الشاشة — لا كما تُسمّى في الشيفرة.
_ARKAN_AR = {
    "quality": "الجودة",
    "safety": "السلامة",
    "valuation": "التسعير",
    "timing": "التوقيت",
}


def _metric_value(scores: FourScores, metric: str) -> Optional[float]:
    return getattr(scores, metric).score


def _conditions_met(conditions: list, scores: FourScores) -> bool:
    for cond in conditions:
        value = _metric_value(scores, cond["metric"])
        if value is None:
            return False  # a metric that's None (e.g. post-rejection) can't satisfy any condition
        fn = _METRIC_OPS.get(cond["op"])
        if fn is None or not fn(value, cond["value"]):
            return False
    return True


# The abstention verdict — issued when the data is too thin for the expert
# panel to reach a trustworthy conclusion. Deliberately NOT buy/hold/avoid:
# an honest "we can't judge this yet" beats a fabricated grade.
ABSTAIN = "بيانات غير كافية"

# The ONE app-wide decision vocabulary + its colors — governance, تقييم
# الأداء, and رأي الذكاء all render decisions from this single map so the
# whole app speaks one language per company.
DECISION_COLORS = {
    # الأحمر والأخضر هنا هما درجتا المالك المعتمدتان في كامل التطبيق.
    # كان «تجنّب» على ‎#f43f5e — أحمرُ ورديّ من عائلةٍ أخرى، فكان لونُ
    # القرار يخالف لونَ الخسارة في الشاشة نفسها. قِيس فبان يظهر عشر مرّات
    # في شاشة الحوكمة وحدها.
    "شراء قوي": "#10b981",
    "شراء": "#22c55e",
    "انتظار": "#f59e0b",
    "تجنب": "#ff5252",
    ABSTAIN: "#94a3b8",
}


def decision_color(decision: str) -> str:
    return DECISION_COLORS.get(decision, "#94a3b8")


# ══ مفرداتُ النشر العامّ — وصفٌ لا أمر ══ (قرارُ مجلس نِصاب — مقعد الالتزام)
#
# كلّف المالكُ المجلسَ بإنهاء الميزة «وألّا تُسبّب إحراجاً بمخرَجاتها عندما
# تُطلَق للعموم». وأوّلُ ما نظر فيه المجلسُ ليس رقماً بل ما ينطق به
# التطبيق: «شراء قوي» · «شراء» · «تجنب» على أوراقٍ مسمّاة في تداول.
#
# وهذه **صيغةُ أمرٍ لا صيغةُ قياس**. وهي لمالكٍ يقرّر لنفسه أداةٌ خاصّة،
# أمّا توجيهُها إلى الجمهور فيدخل — بحسب فهمنا لا بحسب فتوى — نطاقَ
# الأنشطة التي تنظّمها هيئة السوق المالية وتشترط لها ترخيصاً. والمجلسُ
# لا يُفتي في نظامٍ ولا يدّعي علمَ القانون؛ يقيس المخاطرة ويُنذر، والقرارُ
# للمالك (بند ٤ من الميثاق).
#
# والعلاجُ لا يُنقص من التحليل شيئاً — بل يزيده صدقاً. فكلُّ ما يعرفه
# المحرّك **وقائعُ قابلةٌ للتحقّق**:
#   · «جودةٌ مالية عالية — أعلى من ‎82٪ من قطاعها»
#   · «السعر ‎141.40 فوق تقديرنا للقيمة ‎104.87 بـ‎35٪»
#   · «خطٌّ أحمر: خسارةٌ ثلاثَ سنوات»
# وهذه أنفعُ للقارئ من كلمةٍ واحدة تختصرها وتُخفي مدخلاتها. والكلمةُ
# الواحدة كانت أضعفَ ما في المخرَج أصلاً: تضغط سؤالين — أجيّدةٌ الشركة؟
# وأعادلٌ سعرُها؟ — في فعلِ أمرٍ واحد.
#
# فالوضعُ العامّ يعرض الوصف، والوضعُ الخاصّ (المالك) يُبقي الحكم كما هو.
PUBLIC_LABEL = {
    "شراء قوي": "جودةٌ عالية · دون تقديرنا",
    "شراء": "جودةٌ عالية · قريبٌ من تقديرنا",
    "انتظار": "لا تجتمع الشروط",
    "تجنب": "جودةٌ ضعيفة",
    ABSTAIN: ABSTAIN,
}


def is_public_mode() -> bool:
    """أمنشورٌ للعموم أم أداةُ مالكٍ خاصّة؟

    يُضبط بـ`SP_PUBLIC=1` في البيئة. والافتراضُ **خاصّ** — لأن تحوّلَ
    الأداة إلى منشورٍ عامّ قرارُ المالك وحده، ولا يقع بالسهو.
    """
    import os
    return str(os.environ.get("SP_PUBLIC", "")).strip() in ("1", "true", "yes")


def public_label(decision: str) -> str:
    """التسميةُ المعروضة — وصفٌ عند النشر، وحكمٌ في وضع المالك."""
    if not is_public_mode():
        return decision
    return PUBLIC_LABEL.get(decision, decision)


def evaluate_decision(scores, features: dict, sector: Optional[str], config: dict | None = None) -> "Decision":
    """The gated, app-wide decision. A Hard-Filter rejection still returns
    تجنب (a fatal flaw is a verdict regardless of data depth). Otherwise the
    Abstention Gate runs FIRST: if fewer than `min_experts` legends could
    actually weigh in on this company's real numbers (structural "not
    applicable" readings don't count), or there aren't enough years, the
    system abstains — «بيانات غير كافية» — instead of emitting a decision
    the data can't support. Only when the panel is adequately informed does
    the normal consensus decision (decide) run."""
    from app.services.confidence import compute_confidence
    from app.services.expert_panel import build_expert_panel

    cfg = config or governance_rules.load_rules()
    if scores.rejected:
        return decide(scores, cfg)

    # Archetype-aware gate: structurally data-light models (REITs) get a
    # lighter threshold so they're judged on their real signals (P/NAV +
    # dividend yield) instead of being unfairly abstained.
    archetype = cfg.get("sector_archetype", {}).get(sector)
    gate = {**cfg.get("decision_gate", {}),
            **cfg.get("decision_gate_overrides", {}).get(archetype, {})}
    conf = compute_confidence(features)
    # المجلسُ هنا بلا `scores` عمداً: صفوفُ «ما خفض الدرجة» تفسيرٌ للرقم
    # لا رأيٌ فيه، فلا تُحسب في نصاب البوّابة — وإلّا لبلغت شركةٌ عارية من
    # الشواهد نصابَها بعقوباتها هي.
    weighed_in = [e for e in build_expert_panel(features, sector)
                  if e.get("tone") != "na" and e.get("role") != "driver"]
    # ══ فجوةُ تسعةِ أشهر — قاعدةٌ مُلزِمة في الإطار المهنيّ ══
    # نصُّه: «إذا تجاوزت الفجوةُ تسعةَ أشهر ولم توجد بياناتٌ ربعية أحدث…
    # درجةُ الثقة منخفضة ولا يمكن إصدارُ قرارٍ استثماريّ موثوق». وكان
    # عندنا وسمُ «قديم» فوق خمسةٍ وأربعين يوماً في القيمة العادلة وحدها —
    # وسمٌ يُقرأ ويُنسى، ولا أثرَ له في القرار. والقاعدةُ تجعل القِدَمَ
    # مانعاً لا ملاحظة.
    stale_months = None
    _asof = (features.get("_asof") or {})
    _asof = _asof.get("value") if isinstance(_asof, dict) else _asof
    if _asof:
        try:
            from datetime import date
            _d = date.fromisoformat(str(_asof)[:10])
            stale_months = (date.today() - _d).days / 30.44
        except Exception:                                         # noqa: BLE001
            stale_months = None
    if stale_months is not None and stale_months > 9:
        return Decision(
            decision=ABSTAIN, matched_rule_id="stale_data",
            reason=(f"آخرُ قائمةٍ مالية وصلتنا عمرُها {stale_months:.0f} شهراً "
                    "ولم تصل بياناتٌ ربعية أحدث — فالتحليلُ يعكس أداءً "
                    "تاريخياً قد لا يمثّل الوضعَ الحالي، ولا يُبنى عليه "
                    "قرارٌ موثوق."))

    if (conf.years_available < gate.get("min_years", 2)
            or len(weighed_in) < gate.get("min_experts", 3)
            or scores.quality.score is None):
        bits = []
        if conf.years_available < gate.get("min_years", 2):
            bits.append(f"{conf.years_available} سنة مالية فقط")
        if len(weighed_in) < gate.get("min_experts", 3):
            bits.append(f"{len(weighed_in)} من الخبراء فقط استطاعوا الحكم")
        # ══ الامتناعُ يُنسب إلى مصدرنا لا إلى الشركة ══ (بأمر المالك)
        # كانت العبارة «بيانات هذه الشركة غير كافية» — وهي نسبةُ نقصٍ إلى
        # الشركة. وكلُّ شركةٍ مدرجة في تداول **مُلزَمة** بإيداع قوائمها
        # وإلا شُطبت، فالقوائم موجودةٌ بالضرورة. وإذا لم تصلنا فالنقصُ
        # في مصدرنا أو في توقيت الإفصاح، لا في الشركة.
        # والفرق ليس لفظياً: الأولى تقرأ حكماً على الشركة، والثانية تقرأ
        # إقراراً بحدّ أداتنا — وهي الصادقة.
        reason = ("لم تصلنا بياناتٌ كافية لهذه الشركة ("
                  + "، ".join(bits or ["نقص في المؤشرات الأساسية"])
                  + ") — القوائم مُلزِمةٌ لكل مدرَجٍ في السوق، فالنقص في "
                  "وصولها إلينا أو في توقيت الإفصاح لا في الشركة نفسها.")
        return Decision(decision=ABSTAIN, matched_rule_id="insufficient_data", reason=reason)

    return decide(scores, cfg)


def apply_fair_value_ceiling(decision: "Decision", price, fair_value,
                             entry_price=None, single_path: bool = False,
                             coverage=None, nomu: bool = False,
                             red_lines: list | None = None,
                             implausible: bool = False) -> "Decision":
    """سقفٌ يمنع «شراء» فوق هدف المحلّلين المعروض.

    ══ الاسمان يُفصلان ══ (D176 · بأمر المالك)
    كان متوسّطُ أهداف بيوت الخبرة يُعرض ويُحكم به باسم «السعر العادل» —
    وهما مفهومان لا يجتمعان في اسم: الهدفُ **رأيُ محلّلين** عن سعرٍ
    متوقَّعٍ خلال أفقٍ قصير، والقيمةُ العادلة **تقديرٌ جوهريّ** يُحسب من
    القوائم. فصار المعروضُ والمحكومُ به «هدف المحللين» باسمه الصريح،
    و«القيمة العادلة» اسمٌ محجوزٌ لتقدير المحرّك في `fair_value_detail`
    وحدَه — وهو لا يُعرض سعراً ولا يحكم بقرار (D175).

    ══ رقمٌ واحدٌ لا رقمان ══ (D174)
    كانت الشاشةُ تقول «السعر العادل: غير متوفّرة» ويقول القرارُ تحتها
    «فوق القيمة العادلة ⇐ انتظار» — نفيٌ وإثباتٌ في شاشةٍ واحدة، رآهما
    المالك في «الراجحي ريت». والسببُ أنّ المعروضَ هدفُ المحلّلين وحدَه
    وهذه البوّابةَ تحكم بتقديرِ التطبيق.
    فصار «السعر العادل» رقماً واحداً بمصدرين مرتَّبين: هدفُ بيوت الخبرة
    إن وُجد، وإلّا فتقديرُ التطبيق — **وهو الذي تحكم به هذه البوّابةُ
    نفسُها**. فالمعروضُ والمحكومُ به واحدٌ دائماً، ومصدرُه معلَنٌ تحته.

    ══ عطبٌ رآه المالك في «التعاونية للتأمين» ══
    درجةُ حوكمةٍ ٨٤، وقيمةٌ عادلة ١٠٤٫٨٧، وسعرٌ ١٤١٫٤٠ — أي أعلى من قيمته
    بربعه — والشريطُ يقول «مبالغ فيه»، والحكمُ يقول «فوق القيمة العادلة»،
    ثم يقول القرار: **شراء**. والسبب أن محرّك القرار يقرأ ركنَ التسعير من
    مضاعفات القطاع ولا يقرأ القيمة التي يحسبها التطبيق ويعرضها في الصفحة
    نفسها. فالتطبيق يحسب قيمةً ثم يتجاهلها في قراره — وهذا أسوأ من ألّا
    يحسبها.

    والسقفُ لا يخترع رأياً: هو يمنع القرارَ من مناقضة حسابنا فحسب.
      · سعرٌ فوق القيمة العادلة  → «شراء» تنزل إلى «انتظار».
      · سعرٌ فوق سعر الدخول ودون القيمة → «شراء قوي» تنزل إلى «شراء»،
        لأن «القوي» يعني هامشَ أمانٍ محقَّقاً لا مجرّدَ عدالةِ سعر.
    وما دون ذلك يُترك كما هو. ولا يُطبَّق السقفُ حين تمتنع القيمة (تشتّتُ
    المسارات مثلاً) — لا نبني حكماً على رقمٍ امتنعنا عن عرضه.
    """
    if decision is None:
        return decision

    # ══ الخطُّ الأحمر يُبطِل ولا يُخصم ══
    # الترتيبُ في القطاع نسبيّ، فأسوأُ قطاعٍ يبقى فيه «الأفضل» — وقد تخرج
    # شركةٌ خاسرةٌ ثلاثَ سنواتٍ بدرجةٍ عالية لأن أقرانها أسوأ. والوقائعُ
    # المطلقة لا تُوزن مع غيرها: من لا تغطّي أرباحُه فائدةَ دينه لا
    # يُشترى مهما حسنت بقيةُ أرقامه.
    if red_lines:
        return Decision(
            decision="تجنب",
            matched_rule_id="red_line",
            reason=("خطٌّ أحمر: " + " · ".join(
                r.get("message", "") for r in red_lines[:2])),
        )

    # ══ لا قيمةَ عادلة ⇒ امتناع، لا «تجنّب» ══
    # كشفه المسحُ الكامل للسوق: ‎143 شركةً خرجت بلا قيمةٍ عادلة، ولم
    # يُصنَّف منها «بيانات غير كافية» إلا عشرون. أمّا الباقي فوُزّع ‎85 إلى
    # «تجنّب» و‎44 إلى «انتظار» — أي أن سبعةً وثمانين بالمئة من أحكام
    # «تجنّب» لم تكن رسوباً بل جهلاً، معروضاً على المالك بلون الرسوب.
    # و«تجنّب» حكمٌ يقول إن الشركة رديئة، ولا يجوز أن يصدر عن عجزنا عن
    # تقييمها. والفلترُ الحاسم وحده يُستثنى: عيبٌ قاتلٌ مُثبَت حكمٌ في
    # ذاته لا يحتاج قيمةً عادلة ليصدر.
    if (not fair_value or fair_value <= 0) and decision.matched_rule_id != "hard_filter":
        if decision.decision != ABSTAIN:
            return Decision(
                decision=ABSTAIN,
                matched_rule_id=f"{decision.matched_rule_id}+بلا_قيمة_عادلة",
                reason=("لم يُنشر لهذه الورقة سعرٌ عادلٌ موثوق، فلا يصحّ "
                        "إصدارُ حكمٍ عليها — العجزُ عن التقييم ليس رسوباً "
                        f"فيها. {decision.reason}"),
            )
        return decision

    if decision.decision not in ("شراء", "شراء قوي"):
        return decision

    # تغطيةُ البيانات بوّابةٌ لا وسم — كانت تُحسب ولا تُسلسَل فلم تُقيَّم.
    if coverage is not None and coverage < 0.60:
        return Decision(
            decision="انتظار",
            matched_rule_id=f"{decision.matched_rule_id}+تغطية_دون_الحد",
            reason=(f"تغطيةُ المؤشّرات {coverage:.0%} دون الحدّ (‏60٪) — "
                    f"لا شراءَ على بياناتٍ ناقصة. {decision.reason}"),
        )

    # ══ الامتناعُ ليس رخصةَ شراء ══ (ثغرةٌ كشفتها مراجعةٌ خارجية)
    # كان السقفُ يُعيد القرارَ كما هو حين تكون القيمة العادلة `None` — أي
    # أن الشركات التي **عجزنا عن تقييمها** كانت الوحيدة التي تمرّ بلا
    # بوّابة سعرٍ إطلاقاً: أربعون شركةً ممتنعةً للتشتّت، وقطاعُ التأمين
    # كلُّه، والصناديق. فكلّما ازداد تحفّظُنا اتّسعت الثغرة — وهذا انقلابٌ
    # تامّ في معنى الامتناع.
    # فمن لا قيمةَ له لا يُشترى. والحدّ الأعلى «انتظار» لا «تجنب»: غيابُ
    # التقدير ليس حكماً على الشركة.
    if single_path:
        # مسارٌ واحد يُعرض ولا يُشترى عليه — لا شاهدَ يكذّبه.
        return Decision(
            decision="انتظار",
            matched_rule_id=f"{decision.matched_rule_id}+مسار_واحد",
            reason=("التقديرُ من مسارٍ واحد بلا شاهدٍ ثانٍ — "
                    f"يُعرض ولا يُبنى عليه شراء. {decision.reason}"),
        )
    # ══ تقديرٌ شاذُّ النسبة يُعرض ولا يُبنى عليه ══
    # فارقٌ يفوق ‎2.5× بين تقديرنا والسعر مصدرُه غالباً خللٌ في مُدخَل.
    # فيبقى الرقمُ معروضاً بتحفّظه، ولا يُشترى عليه.
    if implausible:
        return Decision(
            decision="انتظار",
            matched_rule_id=f"{decision.matched_rule_id}+تقدير_شاذّ",
            reason=("الفارقُ بين تقديرنا والسعر خارج النطاق المعقول — "
                    f"يُعرض ولا يُبنى عليه قرار. {decision.reason}"),
        )

    # ══ «نمو» تُعرض ولا يُبنى عليها شراء ══
    # خصمُ السيولة يعالج السعرَ ولا يعالج تعذّرَ الخروج: سهمٌ لا يُتداول
    # قد لا يُباع أصلاً حين يُراد بيعُه، وذلك مخاطرةٌ لا يشتريها خصمٌ.
    if nomu:
        return Decision(
            decision="انتظار",
            matched_rule_id=f"{decision.matched_rule_id}+سوق_موازية",
            reason=("ورقةٌ في السوق الموازية «نمو» — رقيقةُ التداول "
                    "محدودةُ الإفصاح، تُعرض ولا يُبنى عليها قرارُ شراء. "
                    f"{decision.reason}"),
        )
    if not price:
        return decision

    if price > fair_value:
        gap = (price / fair_value - 1) * 100
        return Decision(
            decision="انتظار",
            matched_rule_id=f"{decision.matched_rule_id}+سقف_القيمة_العادلة",
            reason=(f"السعر {price:,.2f} أعلى من هدف المحللين "
                    f"{fair_value:,.2f} بـ{gap:.0f}٪ — "
                    f"{decision.reason}"),
        )
    if (decision.decision == "شراء قوي" and entry_price
            and price > entry_price):
        return Decision(
            decision="شراء",
            matched_rule_id=f"{decision.matched_rule_id}+هامش_الأمان",
            reason=(f"السعر {price:,.2f} دون هدف المحللين "
                    f"{fair_value:,.2f} وفوق سعر الدخول "
                    f"{entry_price:,.2f} — {decision.reason}"),
        )
    return decision


def tone_for_decision(decision: str) -> str:
    """Traffic-light signal for a decision label — same purpose as the old
    scores.verdict_tone() but matched to this engine's four labels instead
    of the old free-form verdict sentences."""
    if decision in ("شراء قوي", "شراء"):
        return "green"
    if decision == "تجنب":
        return "red"
    return "yellow"  # "انتظار"


def decide(scores: FourScores, config: dict | None = None) -> Decision:
    if scores.rejected:
        return Decision(
            decision="تجنب",
            matched_rule_id="hard_filter",
            reason=scores.hard_filter_message or "فشلت الشركة في أحد الفلاتر الأساسية",
        )

    cfg = config or governance_rules.load_rules()

    # ══ عقوبةٌ حرجة تمنع الشراء ══ (مراجعةٌ خارجية)
    # وزنُ العقوبة الحرجة ‎25 نقطة، والأساسُ ‎50 والمدى ‎50. فشركةٌ كاملةُ
    # الدرجة (‏100) بعقوبةٍ حرجةٍ واحدة تنزل إلى ‎75 — وهي **فوق** عتبة
    # «شراء» للجودة (‏70). أي أن ورقةً تحمل عيباً حوكميّاً حرجاً كانت
    # تُصنَّف «شراء» بلا مانع. والعيبُ الحرج ليس خصماً من درجةٍ بل واقعةٌ
    # تمنع، فيُمنع الشراءُ عنده كما يمنعه الفلتر الحاسم.
    critical = [h for cat in ("quality", "safety", "valuation", "timing")
                for h in (getattr(getattr(scores, cat, None), "hits", None) or [])
                if getattr(h, "severity", None) == "critical"]

    # وتغطيةُ البيانات بوّابةٌ لا وسمٌ: الدرجةُ العالية على شاهدين ليست
    # شهادةً على سلامة، والانكماشُ وحده لا يكفي لقرار شراء.
    covs = [c for c in (
        getattr(getattr(scores, cat, None), "coverage", None)
        for cat in ("quality", "safety")) if isinstance(c, (int, float))]
    coverage = (sum(covs) / len(covs)) if covs else None

    for rule in cfg.get("decision_rules", []):
        if rule.get("decision") in ("شراء", "شراء قوي"):
            if critical:
                continue
            if coverage is not None and coverage < 0.60:
                continue
        if _conditions_met(rule.get("conditions", []), scores):
            # ══ السببُ نصٌّ للمالك لا سطرُ تشخيص ══ (D172)
            # كان يُعرض حرفياً: «القاعدة 'hold_decent' تحققت: quality=59،
            # safety=63» — معرّفُ قاعدةٍ بالإنجليزية وأسماءُ متغيّراتٍ
            # داخلية في شاشةٍ يقرأها المالك. فصار أرقاماً وعناوينَ عربية،
            # ومعرّفُ القاعدة يبقى في `matched_rule_id` للتشخيص وحدَه.
            parts = [f"{_ARKAN_AR.get(c['metric'], c['metric'])} "
                     f"{_metric_value(scores, c['metric'])}"
                     for c in rule.get("conditions", [])]
            reason = " · ".join(parts) if parts else "لا قاعدةَ أكثرُ تحديداً تنطبق"
            return Decision(decision=rule["decision"], matched_rule_id=rule["id"], reason=reason)

    # Should never happen if governance_rules.yaml keeps its catch-all rule,
    # but never silently return nothing — surface the gap instead of a
    # crash if someone edits the YAML and removes the catch-all by mistake.
    return Decision(decision="انتظار", matched_rule_id="no_rule_matched", reason="لم تُطابق أي قاعدة قرار معرَّفة")
