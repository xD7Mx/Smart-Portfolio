"""جاهزيةُ الترشيح — منفصلةٌ عن الدرجة، وهي التي تحكم.

## لماذا رقمان لا رقم

كشفه المالكُ من مخرَج المسبار: «الماجد للعود» خرجت **‎89.6 · A**،
ومكوّنا النموّ والتقييم لم يُقاسا، والثقةُ منخفضة. فالدرجةُ صحيحةٌ
حسابياً وكاذبةٌ استثمارياً: هي متوسّطُ ما قِيس، وما لم يُقَس هو بالضبط
ما كان سيخفضها.

فصارت الدرجةُ **وصفاً لما عرفناه**، والجاهزيةُ **إذناً بالترشيح**:

    READY              معلوماتُنا تكفي لقرارٍ مسؤول
    WATCH              تكفي للمتابعة لا للترشيح
    INSUFFICIENT_DATA  محورٌ جوهريٌّ لم يُقَس — ممنوعُ الترشيح
    EXCLUDED           بوّابةُ مخاطرَ مغلقة

و«READY» لا تعني «ممتازة». تعني أن ما ينقصنا لا يغيّر الحكم. ودرجةٌ
‎‎89.6 بلا تقييمٍ ولا نموّ ليست مرشَّحاً — هي ملاحظةٌ تحليلية تُحفظ ولا
تعبر البوّابة.

## لماذا محورٌ «جوهريّ» يختلف بالقطاع

المصرفُ لا يُرشَّح بلا تقييمٍ دفتريّ ولو حسُنت جودتُه، والصندوقُ
العقاريّ لا يُرشَّح بلا توزيعٍ مقيسٍ لأن التوزيعَ هو نموذجُ عمله. فما
يَلزم قياسُه يحدّده `CORE_AXES` لكلّ نموذج، لا قائمةٌ واحدةٌ للسوق.
"""

from __future__ import annotations

from app.data.economic_models import CORE_AXES, COMPONENT_NAMES

# ══ ثلاثُ حالاتٍ لا رابع ══ (المادة ١٢)
# وكانت أربعاً، فصار «مستبعَدٌ لمخاطر» و«ناقصُ بيانات» حالتين متجاورتين
# والقرارُ فيهما واحد: لا ترشيح. فدُمجتا في `NOT_READY` ويبقى السببُ
# مذكوراً برمزه — والحالاتُ للقرار والأسبابُ للفهم.
INVESTMENT_READY = "INVESTMENT_READY"
WATCH = "WATCH"
NOT_READY = "NOT_READY"

# أسماءٌ قديمةٌ يُبقى عليها كي لا ينكسر نداءٌ قائم
READY = INVESTMENT_READY
INSUFFICIENT_DATA = NOT_READY
EXCLUDED = NOT_READY

# اكتمالٌ دون هذا الحدّ لا يكفي قراراً مسؤولاً (المادة ٧ · الشرط ٧).
MIN_COMPLETENESS = 0.80
_CONF_RANK = {"منخفضة": 0, "متوسطة": 1, "مرتفعة": 2}

# تصنيفُ القرار (المادة ١٤) — ولا يُقرأ إلّا بعد اجتياز الجاهزية.
HIGH_CONVICTION = 90.0
CANDIDATE = 80.0
WATCHLIST = 70.0


def evaluate(result: dict, gate_status: str, confidence: str,
             valuation_method: str | None) -> dict:
    """الجاهزيةُ وسببُها — أحدَ عشرَ شرطاً تُقرأ بالترتيب.

    ويُعاد **كلُّ** ما أخفق لا أوّلُه: المالكُ يحتاج أن يعرف ما ينقصه
    ليُكمله، لا أن يُصلح شرطاً فيظهر له غيرُه.
    """
    # ══ الأسبابُ تحمل رمزاً لا نصّاً فقط ══
    # قُرئ الفرقُ بين «ينقصنا محورٌ» و«ننتظر» من بداية النصّ العربيّ،
    # فاختلف تشكيلٌ واحد فمرّ أساسٌ ضيّقٌ إلى «WATCH» بدل المنع. والنصُّ
    # للقارئ والرمزُ للمنطق، ولا يُبنى قرارٌ على مطابقة حروف.
    codes: list[str] = []
    why: list[str] = []
    model = result.get("model")
    comps = result.get("components") or {}
    live = {k for k in COMPONENT_NAMES
            if (comps.get(k) or {}).get("score") is not None}

    if gate_status == "EXCLUDED":
        return {"readiness": NOT_READY, "codes": ["RISK_GATE"],
                "decision": "ممنوعُ الترشيح",
                "why": ["بوّابةُ المخاطر مغلقة"]}

    # ١ · ٢ — القطاعُ والنموذج
    if not result.get("sector"):
        codes.append("NO_SECTOR")
        why.append("القطاعُ غيرُ محدَّد")
    if model is None:
        codes.append("NO_MODEL")
        why.append("لا نموذجَ اقتصاديّاً لهذا القطاع")
        return {"readiness": NOT_READY, "codes": codes,
                "decision": "ممنوعُ الترشيح", "why": why}

    # ٣ · ٤ · ٥ · ٦ · ٨ — المحاورُ الجوهريةُ لهذا النموذج
    for axis in CORE_AXES.get(model, ()):
        if axis not in live:
            codes.append("CORE_AXIS_MISSING")
            why.append(f"محورٌ جوهريٌّ لم يُقَس: {_AR.get(axis, axis)}")

    # ٧ — اكتمالُ البيانات
    dc = result.get("data_completeness")
    if not isinstance(dc, (int, float)) or dc < MIN_COMPLETENESS:
        codes.append("LOW_COMPLETENESS")
        why.append(f"اكتمالُ البيانات {(dc or 0) * 100:.0f}٪ "
                   f"دون {MIN_COMPLETENESS * 100:.0f}٪")

    # ١٠ — طريقةُ التقييم معلَنة
    if not valuation_method:
        codes.append("NO_VALUATION_METHOD")
        why.append("طريقةُ التقييم غيرُ معروفة")

    # ١١ — الثقة
    if _CONF_RANK.get(confidence, 0) < 1:
        codes.append("LOW_CONFIDENCE")
        why.append("الثقةُ منخفضة")

    if not why:
        score = result.get("score") or 0.0
        return {"readiness": INVESTMENT_READY, "why": [], "codes": [],
                "decision": ("مرشّحٌ عالي القناعة" if score >= HIGH_CONVICTION
                             else "مرشّح" if score >= CANDIDATE
                             else "قائمةُ مراقبة" if score >= WATCHLIST
                             else "دون عتبة الترشيح")}

    # ══ الفرقُ بين «ينقصنا بيان» و«ننتظر» ══
    # نقصُ محورٍ جوهريّ يمنع الترشيح لأن الحكمَ لا يقوم بدونه. أمّا
    # اكتمالٌ دون الحدّ أو ثقةٌ منخفضة مع قيام المحاور كلِّها فهي حالُ
    # متابعةٍ لا حالُ عجز.
    blocking = {"CORE_AXIS_MISSING", "NO_SECTOR", "NO_VALUATION_METHOD"}
    if blocking & set(codes):
        return {"readiness": NOT_READY, "codes": codes,
                "decision": "ممنوعُ الترشيح", "why": why}
    return {"readiness": WATCH, "codes": codes,
            "decision": "لا ترشيحَ مباشر", "why": why}


_AR = {"quality": "الجودة", "dividend": "التوزيعات",
       "growth": "النموّ", "valuation": "التقييم"}


def thesis(result: dict, ready: dict, upside: float | None) -> tuple[str, str]:
    """سطرُ الأطروحة وسطرُ الخطر — بلا شرحٍ ولا حواشٍ.

    ويُبنى من الأرقام المقيسة وحدها: لا عبارةَ إنشائيةً لا يقابلها رقم.
    """
    c = result.get("components") or {}

    def _s(k):
        return (c.get(k) or {}).get("score")

    q, d, g, v = (_s("quality"), _s("dividend"), _s("growth"), _s("valuation"))
    strong = [n for n, x in (("جودةٌ", q), ("توزيعٌ", d),
                             ("نموٌّ", g)) if isinstance(x, (int, float)) and x >= 65]
    weak = [n for n, x in (("الجودة", q), ("التوزيع", d),
                           ("النموّ", g)) if isinstance(x, (int, float)) and x < 40]

    if "RISK_GATE" in (ready.get("codes") or []):
        head = "بوّابةُ المخاطر مغلقة — لا تدخل نطاقَ الترشيح"
    elif ready["readiness"] == NOT_READY:
        head = "بياناتُها لا تكفي قراراً — الدرجةُ وصفٌ لما قِيس لا حكمٌ عليها"
    else:
        head = (("، و".join(strong) + " مقيسة") if strong
                else "أركانُها متوسّطةٌ في قطاعها")
        if isinstance(v, (int, float)) and isinstance(upside, (int, float)):
            head += (f"، والسعرُ دون تقديرنا {upside:+.0f}٪" if upside > 5
                     else f"، والسعرُ فوق تقديرنا {upside:+.0f}٪" if upside < -5
                     else "، والسعرُ قربَ تقديرنا")

    risk = ("، و".join(weak) + " دون ربع قطاعها") if weak else \
           ("نقصٌ في البيانات لا في الشركة" if ready["why"] else
            "لا خطرَ ظاهرٌ في المقيس")
    return head, risk
