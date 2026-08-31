"""الجودةُ المطلقة — ما لا يتغيّر بتغيّر الأقران.

## لماذا طبقةٌ ثانية

الترتيبُ في القطاع نسبيّ، وأسوأُ قطاعٍ في السوق يبقى فيه «الأفضل».
فشركةٌ لا تغطّي أرباحُها فائدةَ دَينها قد تخرج في المئين ‎80 لأن
أقرانَها أسوأ — والمئينُ صادقٌ والقراءةُ كاذبة.

فبجانب النسبيّ طبقةٌ **مطلقة**: وقائعُ لا تحتاج قريناً ولا يختلف
عليها اثنان، ولا واحدةَ منها عتبةٌ من رأيي:

  · **حقوقُ ملكيةٍ موجبة** — سالبُها يعني أن الالتزامات تفوق الأصول.
    تعريفٌ محاسبيّ لا رأي.
  · **ربحٌ في آخر سنة** — الخسارةُ خسارةٌ في كلّ قطاع.
  · **تغطيةُ فائدةٍ تبلغ الواحد** — «واحد» ليست عتبةً مختارة: هي نقطةُ
    التساوي التي تكفي عندها الأرباحُ التشغيلية فائدةَ الدين بالضبط.
  · **توزيعٌ لا يفوق الربح** — «مئة بالمئة» تعريفُ الاستنزاف لا رأيٌ فيه.
  · **تدفّقٌ تشغيليٌّ موجب** — حيث يكون للنشاط تدفّقٌ تشغيليٌّ معنىً.

## كيف تلتقي الطبقتان

النسبيُّ هو الدرجة، والمطلقُ **سقفٌ عليها**. فمن سقط في واقعةٍ مطلقة
لا يتجاوز سقفَها مهما علا ترتيبُه — وهو نصُّ المادة ٨: لا يُخفي
الترتيبُ ضعفاً مالياً مطلقاً واضحاً. ولا يُخصم شيءٌ ولا يُضاف: يُقصّ
السقفُ فقط، ويُقال أيُّ واقعةٍ قصّته.

وليس فيه مكافأةٌ للسلامة: من لم يسقط في شيءٍ يبقى سقفُه مئةً، فدرجتُه
درجتُه النسبية كما هي. السلامةُ لا تُكافأ، وإنّما يُمنع الضعفُ من
الاختباء.
"""

from __future__ import annotations

NOT_APPLICABLE = "NOT_APPLICABLE"

# ── الوقائعُ وسقفُ كلٍّ منها ─────────────────────────────────────────
# والسقفُ متدرّجٌ بجسامة الواقعة لا برقمٍ موحّد: حقوقُ ملكيةٍ سالبة
# أفدحُ من توزيعٍ يفوق الربح.
CEILINGS = {
    "negative_equity": (25.0, "حقوقُ ملكيةٍ سالبة"),
    "loss_last_year": (45.0, "خسارةٌ في آخر سنة"),
    "interest_below_one": (35.0, "الأرباحُ التشغيلية دون فائدة الدين"),
    "payout_over_earnings": (60.0, "التوزيعُ يفوق الربح"),
    "negative_ocf": (50.0, "تدفّقٌ تشغيليٌّ سالب"),
}

# أنماطٌ لا معنى للتدفّق التشغيليّ عندها: نموُّ دفتر القروض والأقساط
# والمخزونِ العقاريّ يقع كلُّه في القسم التشغيليّ فيظهر سالباً وهو نموّ.
_OCF_NA = ("FINANCIAL", "REAL_ESTATE")


def _n(d, k):
    v = (d or {}).get(k)
    if isinstance(v, dict):
        v = v.get("value")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if v == v and abs(v) != float("inf") else None


def evaluate(rows: list[dict] | None, features: dict,
             model: str | None) -> dict:
    """الوقائعُ المطلقة وسقفُها — ومعها ما لم يُقَس منها.

    وما لم تصل بياناتُه **لا يُعدّ سقوطاً**: يُسجَّل غيرَ مقيسٍ ويُخفض
    به عددُ الوقائع المفحوصة، فينعكس في الثقة لا في الدرجة.
    """
    rows = rows or []
    last = rows[-1] if rows else {}
    hit: list[dict] = []
    unchecked: list[str] = []
    checked = 0

    def _fact(key: str, verdict: bool | None):
        nonlocal checked
        if verdict is None:
            unchecked.append(key)
            return
        checked += 1
        if verdict:
            cap, why = CEILINGS[key]
            hit.append({"key": key, "ceiling": cap, "why": why})

    eq = _n(last, "total_equity")
    _fact("negative_equity", None if eq is None else eq < 0)

    ni = _n(last, "net_income")
    _fact("loss_last_year", None if ni is None else ni < 0)

    op, ie = _n(last, "operating_income"), _n(last, "interest_expense")
    _fact("interest_below_one",
          None if (op is None or ie is None or ie == 0)
          else (op / abs(ie)) < 1.0)

    payout = _n(features, "payout_ratio")
    _fact("payout_over_earnings", None if payout is None else payout > 100.0)

    if model in _OCF_NA:
        unchecked.append("negative_ocf:" + NOT_APPLICABLE)
    else:
        ocf = _n(last, "operating_cash_flow")
        _fact("negative_ocf", None if ocf is None else ocf < 0)

    ceiling = min([h["ceiling"] for h in hit], default=100.0)
    return {"ceiling": ceiling, "breaches": hit, "unchecked": unchecked,
            "facts_checked": checked, "facts_total": len(CEILINGS)}


def apply_ceiling(relative_score: float | None,
                  absolute: dict) -> tuple[float | None, str | None]:
    """الدرجةُ النهائية بعد السقف — ونصُّ السبب إن قُصَّت.

    ولا تُرفع درجةٌ أبداً بهذه الطبقة: السلامةُ لا تُكافأ.
    """
    if relative_score is None:
        return None, None
    cap = absolute.get("ceiling", 100.0)
    if relative_score <= cap:
        return relative_score, None
    why = "، ".join(h["why"] for h in absolute.get("breaches", []))
    return cap, f"قُصَّت من {relative_score:.1f} إلى {cap:.0f} — {why}"
