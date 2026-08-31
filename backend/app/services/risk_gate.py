"""بوّاباتُ المخاطر — تمنع التأهّل ولا تُخصم من الدرجة.

## لماذا بوّابةٌ لا وزن

كان الأمانُ مكوّناً موزوناً يُجمع مع الجودة والنموّ. وأثرُ ذلك أن
شركةً عاليةَ الجودة تشتري بجودتها صمتاً عن خللٍ ماليٍّ جسيم: تُخصم
عشرُ نقاطٍ من مئة فتبقى في المقدّمة، وحقوقُ ملكيتها سالبة.

فصار الأمانُ **بوّابة**: تمرّ أو لا تمرّ، ولا تُعوَّض. ودرجةٌ مرتفعةٌ
لا تتخطّى بوّابةً مغلقة.

## ما يُقصي وما يُنذر

الإقصاءُ لواقعةٍ لا يغيّرها نموذجُ عمل ولا يختلف عليها اثنان: حقوقُ
ملكيةٍ سالبة، أو تعليقٌ فعليّ. وما دون ذلك **إنذارٌ يُعرض** ويترك
للنموذج القطاعيّ أن يقرأه: خسائرُ متّصلة عند شركةٍ دورية في قاع
الدورة ليست كخسائرَ متّصلةٍ عند مرفقٍ منظَّم.

وخسائرُ متّصلة لا تُقصي برمجياً (المادة ٤٦ — البوّابة الرابعة)، لكنّها
لن تُنتج مرشّحاً قويّاً لمحفظةِ دخلٍ بحال، وذلك أثرُ الدرجة نفسها لا
أثرُ البوّابة.
"""

from __future__ import annotations

PASS = "PASS"
REVIEW = "REVIEW"
EXCLUDED = "EXCLUDED"


def _series(periods: list[dict], key: str) -> list[float]:
    return [float(p[key]) for p in (periods or [])
            if isinstance(p.get(key), (int, float))]


def evaluate(features: dict, periods: list[dict] | None,
             red_lines: list[dict] | None = None,
             halted: bool | None = None) -> dict:
    """حالةُ المخاطر: `PASS` أو `REVIEW` أو `EXCLUDED`، ومعها الأسباب."""
    periods = periods or []
    excl: list[str] = []
    flags: list[str] = []

    # ── البوّابة الأولى: حقوقُ ملكيةٍ سالبة ──
    eqs = [p.get("total_equity") if p.get("total_equity") is not None
           else p.get("equity") for p in periods]
    eqs = [e for e in eqs if isinstance(e, (int, float))]
    if eqs and eqs[-1] < 0:
        excl.append("حقوقُ الملكية سالبة — الالتزاماتُ تفوق الأصول")

    # ── البوّابة الثانية: تعليقٌ أو شطبٌ فعليّ ──
    # ولا يُستنتج من غياب السعر: الغيابُ قد يكون عطلةً أو عطلاً في
    # مصدرنا. فما لم يصل خبرٌ صريح فالحالُ غيرُ معلومة لا «معلَّق».
    if halted is True:
        excl.append("السهمُ معلَّقٌ أو مشطوب")

    # ── البوّابة الثالثة: خللٌ ماليٌّ جسيمٌ مؤكَّد ──
    # يُقرأ من الخطوط الحمراء المشتعلة — وهي وقائعُ ثابتةٌ لا لقطاتُ
    # سنة (‏`red_lines`). واثنتان منها إقصاءٌ لا إنذار.
    ids = {r.get("id") for r in (red_lines or [])}
    if "no_cash" in ids and "interest_thin" in ids:
        excl.append("تدفّقٌ تشغيليّ سالبٌ متّصل مع عجزٍ عن تغطية الفائدة")
    for r in (red_lines or []):
        if r.get("id") not in ("negative_equity",):
            flags.append(r.get("message") or str(r.get("id")))

    # ── البوّابة الرابعة: خسائرُ متّصلة — إنذارٌ لا إقصاء ──
    nis = _series(periods, "net_income")
    streak = 0
    for v in reversed(nis):
        if v < 0:
            streak += 1
        else:
            break
    if streak >= 3:
        flags.append(f"خسارةٌ {streak} سنواتٍ متتالية — إنذارٌ شديد")

    if excl:
        return {"status": EXCLUDED, "excluded_by": excl, "flags": flags}
    if flags:
        return {"status": REVIEW, "excluded_by": [], "flags": flags}
    return {"status": PASS, "excluded_by": [], "flags": []}


# ══ المتانةُ المؤسسية — صفةٌ تُعرض ولا تُضاف ══
#
# «حكوميّة» ليست درجةً ولا مكافأةً ثابتة. ملكيةُ دولةٍ كبرى تغيّر قراءةَ
# **المخاطر** (احتمالُ الإسناد عند الشدّة) ولا تغيّر جودةَ النشاط ولا
# ربحيتَه. فتُعرض مستقلّةً بجانب الدرجة، ولا تُجمع إليها نقطةً واحدة —
# ولا تُستعمل لستر ضعفٍ ماليٍّ حقيقيّ.

HIGH, MEDIUM, LOW, UNKNOWN = "HIGH", "MEDIUM", "LOW", "UNKNOWN"


def institutional_resilience(insider_pct: float | None) -> tuple[str, str]:
    """تُقرأ من تركّز الملكية وحده — ولا يُدَّعى مصدرٌ لا نملكه.

    ولا نملك في بياناتنا تمييزَ المالك الحكوميّ من العائليّ، فلا يُقال
    «حكوميّة». المقيسُ هو **تركّزُ الملكية**: مالكٌ كبيرٌ مستقرّ يقلّل
    احتمالَ تركِ الشركة عند الشدّة، ويقلّل معه سيولةَ التداول. وكلاهما
    يُعرض للقارئ ولا يُترجم إلى نقاط.
    """
    if insider_pct is None:
        return UNKNOWN, "تركّزُ الملكية لم يصل"
    if insider_pct >= 60:
        return HIGH, f"مالكٌ مسيطر {insider_pct:.0f}٪ — إسنادٌ مرجَّحٌ عند الشدّة، وسيولةٌ أقلّ"
    if insider_pct >= 30:
        return MEDIUM, f"ملكيةٌ مؤثّرة {insider_pct:.0f}٪ — مصلحةٌ مشتركة مع المساهم"
    return LOW, f"ملكيةٌ موزَّعة ({insider_pct:.0f}٪ للداخل) — لا مالكَ مرجَّحَ الإسناد"
