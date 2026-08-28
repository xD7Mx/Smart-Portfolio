"""ركنُ الحوكمة — بمعناه الذي يضرّ المساهمَ أو ينفعه.

## لماذا

اسمُ الشاشة «درجة الحوكمة»، وكلُّ ما كانت تقيسه **جودةٌ مالية**: هوامشُ
وعوائدُ ورافعة. وهي نافعة، لكنها ليست حوكمة. والحوكمةُ في سوقٍ كثيرُ
شركاته عائليُّ السيطرة قد تضرّ حائزاً طويلَ الأجل أكثرَ من نسبةِ ربحيةٍ
ضعيفة.

ولم نكن نملك ما يقيسها — حتى تبيّن أننا نملك ثلاثةَ أركانٍ حقيقية:

  · **تركّزُ الملكية والتداولُ الحرّ** — من تفصيل كبار الملّاك في ياهو.
    سيطرةٌ مطلقة تعني أن قراراتِ الشركة تُتَّخذ لمصلحة المالك المسيطر،
    وقد لا تكون مصلحتَك. وتداولٌ حرٌّ ضئيل يعني أنك قد لا تخرج حين تريد.
  · **تخفيفُ حصّتك** — سلسلةُ الأسهم القائمة. شركةٌ تُصدر أسهماً باستمرار
    تأخذ من حصّتك بلا أن تسألك. وهذا لا يظهر في أيّ نسبةِ ربحية: الربحُ
    الإجماليّ ينمو وحصّتُك منه تنكمش.
  · **انضباطُ تخصيص رأس المال** — أتوزّع الشركةُ أكثرَ ممّا تكسب نقداً؟
    أتعيد استثمارَ أرباحها بعائدٍ دون كلفة رأس مالها؟ سجلُّ الإدارة في
    هذا هو أصدقُ ما يُعرف به مجلسٌ لا نراه.

## ما لا يقيسه هذا الركن — ويُقال

استقلالُ المجلس · معاملاتُ الأطراف ذات العلاقة · مكافآتُ التنفيذيين ·
جودةُ الإفصاح. مصدرُها التقريرُ السنويّ لا القوائمُ المالية، ولا يوفّرها
ياهو. فلا تُقدَّر ولا يُوهَم أن الركنَ يغني عنها.
"""

from __future__ import annotations

# ما يقرؤه بناءُ التوزيع من السمات لهذا الركن
METRIC_KEYS = ("share_dilution", "payout_ratio", "roic", "cash_conversion_ratio")


def _val(features: dict, key: str):
    raw = (features or {}).get(key)
    v = raw.get("value") if isinstance(raw, dict) else raw
    return v if isinstance(v, (int, float)) else None


def build(features: dict, periods: list[dict] | None,
          ownership: dict | None) -> dict:
    """أركانُ الحوكمة المقيسة — وما تعذّر قياسُه صريحاً.

    يُعاد عددٌ بين صفرٍ ومئة **مع** عدد الأركان التي أمكن قياسها. ولا
    يُضرب أحدُهما في الآخر: «متوسّطٌ على ثلاثة أركان» و«متوسّطٌ على ركنٍ
    واحد» حكمان مختلفان في القرار، ودمجُهما في رقمٍ يخفي الفرق.
    """
    reads: list[dict] = []
    blind: list[str] = []

    # ── تركّزُ الملكية والتداولُ الحرّ ──
    own = ownership or {}
    insiders = own.get("insiders")
    public = own.get("public")
    if isinstance(insiders, (int, float)):
        if insiders >= 75:
            sc, tone = 25.0, "red"
            verdict = "سيطرةٌ شبه مطلقة — قراراتُ الشركة بيد مالكٍ واحد"
        elif insiders >= 50:
            sc, tone = 55.0, "yellow"
            verdict = "سيطرةُ أغلبية — للمالك المسيطر أن يُمرّر ما يشاء"
        elif insiders >= 20:
            sc, tone = 85.0, "green"
            verdict = "ملكيةٌ مؤثّرة بلا سيطرةٍ مطلقة — مصلحةٌ مشتركة معك"
        else:
            sc, tone = 70.0, "yellow"
            verdict = "ملكيةٌ داخلية منخفضة — لا مالكَ تتوافق مصلحتُه مع مصلحتك"
        reads.append({"key": "insider_ownership", "label": "ملكيةُ الداخل",
                      "value": insiders, "unit": "%", "score": sc,
                      "tone": tone, "verdict": verdict})
    else:
        blind.append("تفصيلُ كبار الملّاك")

    if isinstance(public, (int, float)):
        if public < 15:
            sc, tone = 30.0, "red"
            verdict = "تداولٌ حرّ ضئيل — قد يتعذّر الخروجُ بالحجم المطلوب"
        elif public < 30:
            sc, tone = 60.0, "yellow"
            verdict = "تداولٌ حرّ محدود"
        else:
            sc, tone = 90.0, "green"
            verdict = "تداولٌ حرّ كافٍ للدخول والخروج"
        reads.append({"key": "free_float", "label": "التداولُ الحرّ",
                      "value": public, "unit": "%", "score": sc,
                      "tone": tone, "verdict": verdict})

    # ── تخفيفُ حصّة المساهم ──
    sh = [p.get("shares_outstanding") for p in (periods or [])
          if isinstance(p.get("shares_outstanding"), (int, float)) and p.get("shares_outstanding")]
    if len(sh) >= 4:
        base, now = sh[-4], sh[-1]
        chg = (now / base - 1) * 100 if base > 0 else None
        if chg is not None:
            if chg > 10:
                sc, tone = 20.0, "red"
                verdict = "حصّتُك تتقلّص — إصدارٌ متكرّر للأسهم"
            elif chg > 2:
                sc, tone = 55.0, "yellow"
                verdict = "تخفيفٌ محدود"
            elif chg < -2:
                sc, tone = 100.0, "green"
                verdict = "إعادةُ شراءٍ — حصّتُك تكبر بلا أن تدفع"
            else:
                sc, tone = 85.0, "green"
                verdict = "عددُ الأسهم مستقرّ — لا تخفيف"
            reads.append({"key": "share_dilution", "label": "تخفيفُ الحصّة (٣ سنوات)",
                          "value": round(chg, 1), "unit": "%", "score": sc,
                          "tone": tone, "verdict": verdict})
    else:
        blind.append("سلسلةُ الأسهم القائمة")

    # ── انضباطُ تخصيص رأس المال ──
    # أتوزّع الشركةُ أكثرَ ممّا تولّد نقداً؟ التوزيعُ من الدَّين ليس دخلاً.
    covered = []
    for p in (periods or [])[-3:]:
        dv, fcf = p.get("dividends_paid"), p.get("free_cash_flow")
        if isinstance(dv, (int, float)) and isinstance(fcf, (int, float)) and dv:
            covered.append(abs(dv) <= max(fcf, 0))
    if covered:
        ok = sum(1 for c in covered if c)
        ratio = ok / len(covered)
        sc = 100.0 * ratio
        tone = "green" if ratio >= 0.99 else "yellow" if ratio >= 0.5 else "red"
        verdict = ("التوزيعُ مغطّىً بالتدفّق الحرّ" if ratio >= 0.99 else
                   f"التوزيعُ فاق التدفّقَ الحرّ في {len(covered) - ok} من "
                   f"{len(covered)} سنوات — يُموَّل بدَينٍ أو بالنقد المتراكم")
        reads.append({"key": "payout_funding", "label": "تمويلُ التوزيع",
                      "value": round(ratio * 100), "unit": "%", "score": sc,
                      "tone": tone, "verdict": verdict})

    blind.append("استقلالُ المجلس ومعاملاتُ الأطراف ذات العلاقة "
                 "(مصدرُها التقريرُ السنويّ)")

    score = round(sum(r["score"] for r in reads) / len(reads), 1) if reads else None
    return {"score": score, "pillars": len(reads), "reads": reads, "blind": blind}
