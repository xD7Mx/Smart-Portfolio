"""الدرجةُ الاستثمارية — أهي الشركةُ صالحةٌ لتكون أصلاً في محفظةِ دخل؟

## ما تجيب عنه هذه الدرجة وما لا تجيب

لا تقول «اشترِ». تقول: **هل هذه الشركةُ مرشَّحةٌ لمحفظةٍ طويلة الأجل**
تستهدف توزيعاتٍ مستدامةً وحفظَ رأس المال ونموَّه؟ ثم يُعرَض التقييمُ
السعريّ والتوقيتُ منفصلَين، ويقرّر المالك.

والفرقُ ليس لفظياً: درجةٌ تقول «اشترِ» تخلط سؤالين مختلفين — أجيّدةٌ
الشركة؟ وأمناسبٌ سعرُها اليوم؟ — فيُخفي الجوابُ الواحدُ كليهما.

## البنية

    الجودة ‎40٪ · التوزيعات ‎25٪ · النموّ ‎20٪ · التقييم ‎15٪

والأوزانُ مثبَّتةٌ لا تُجتهَد فيها. و**الأمانُ خارج الجمع**: بوّابةٌ
تمنع التأهّل ولا نقاطٌ تُعوَّض. لأن جمعَه وزناً يسمح لشركةٍ عاليةِ
الجودة أن تشتري بجودتها صمتاً عن خللٍ ماليٍّ جسيم — وهو ما لا يفعله
مستثمرٌ عاقل.

## من أين تأتي الأرقام

كلُّ مؤشّرٍ يُقاس **برتبته في قطاعه** (`peer_distribution`)، لا بعتبةٍ
أختارها. فالمسطرةُ من السوق نفسه: «أعلى من ‎80٪ من قطاعه» جملةٌ يقابلها
واقع، و«فوق ‎15٪ ممتاز» رأيٌ لا سند له. ويُستثنى ما له معيارٌ منشور
(نطاقُ التوزيع مثلاً) فيُقاس بمعياره ولا يُرتَّب.

## البياناتُ الناقصة

مؤشّرٌ لم يصل **يُستبعَد** من مكوّنه — لا يصير صفراً ولا يُخترَع.
فالدرجةُ تقيس ما نعرف، والثقةُ تقيس قوّةَ ما بُني عليه الحكم. ومكوّنٌ
لم يصل منه شيءٌ يُعلَن غيرَ متاح، وتُعاد قسمةُ الأوزان على ما بقي —
وهذا قياسٌ لما نعرفه لا تعديلٌ للأوزان، والبديلُ (صفرٌ مكانَ الغائب)
يُدين الشركةَ بنقصٍ في مصدرنا.
"""

from __future__ import annotations

from app.data.economic_models import (COMPONENTS, WEIGHTS, grade_of, model_of)
from app.services import peer_distribution as _pd

# ══ لكلّ سمةٍ حالةٌ صريحة ══ (المادة ٥)
# ولا رابعَ لها. و«لا تنطبق» ليست «غير متاحة»: الأولى تعني أن المؤشّرَ
# لا معنى له في بنية هذه القائمة (تدفّقٌ حرٌّ صناعيٌّ لمصرف)، والثانية
# تعني أن الرقمَ لم يصل. وخلطُهما يجعل نقصَ البيانات يبدو خصوصيةً
# قطاعية، وهو ما يستر عجزَ الأنبوب.
AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"

# أقلُّ ما يُبنى عليه مكوّن: دون ثلثِ وزنه لا يُعلَن رقمٌ له.
MIN_COMPONENT_COVERAGE = 0.34
# ودرجةٌ لا تقوم على مكوّنَين على الأقلّ ليست درجة.
MIN_COMPONENTS = 2


def _val(features: dict, key: str):
    raw = (features or {}).get(key)
    v = raw.get("value") if isinstance(raw, dict) else raw
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if v == v and abs(v) != float("inf") else None


def _band_score(v: float, lo: float, hi: float) -> float:
    """درجةُ نطاقٍ منشور: داخلَه تامّة، وخارجَه تنحدر بقدر البعد.

    ولا تهبط إلى الصفر فوراً — الخروجُ من النطاق درجاتٌ لا حالةٌ واحدة،
    وشركةٌ توزّع ‎85٪ ليست كالتي توزّع ‎300٪.
    """
    if lo <= v <= hi:
        return 100.0
    span = max(hi - lo, 1e-9)
    off = (lo - v) if v < lo else (v - hi)
    return max(0.0, 100.0 - (off / span) * 100.0)


def _vs_median(v: float, med: float, higher_is_better: bool) -> float:
    """مضاعفٌ مقابل وسيط قطاعه — نصفُ الوسيط قمّةٌ وضعفُه قاع.

    المقارنةُ لوغاريتمية لأن المضاعفات نِسَبٌ لا فروق: الفرقُ بين ‎10×
    و‎20× هو الفرقُ بين ‎20× و‎40×، والطرحُ الخطّيّ يجعل الثانيَ ضعفَ
    الأوّل. والوسيطُ لا المتوسّط: مضاعفٌ شاذٌّ واحد يجرّ المتوسّط ولا
    يُزحزح الوسيط.
    """
    from math import log2
    if med <= 0 or v <= 0:
        return 50.0
    step = log2(v / med)
    s = 50.0 + 50.0 * (step if higher_is_better else -step)
    return max(0.0, min(100.0, s))


def _metric_score(key: str, direction, value: float, arch: str | None,
                  dist: dict | None,
                  medians: dict | None = None) -> tuple[float, str] | None:
    """درجةُ مؤشّرٍ واحد ونصُّ تفسيرها — أو `None` إن تعذّر القياس."""
    if isinstance(direction, tuple) and direction and direction[0] == "band":
        _, lo, hi = direction
        return _band_score(value, lo, hi), f"النطاقُ المعتمد {lo:g}–{hi:g}"

    if direction == "discount":
        # خصمُنا عن تقديرنا: صفرٌ عند السعر، ومئةٌ عند نصفه.
        return (max(0.0, min(100.0, 50.0 + value)),
                f"{value:+.0f}٪ عن تقديرنا")

    # ── مضاعفُ سعرٍ يُقاس على وسيط قطاعه لا على عشيرة القوائم ──
    med = (medians or {}).get(key)
    if isinstance(med, (int, float)) and med > 0:
        s = _vs_median(value, float(med), direction == "higher")
        return s, f"وسيطُ القطاع {med:.1f} — والشركةُ {value:.1f}"

    cuts = (((dist or {}).get("archetypes") or {}).get(arch or "", {})
            .get(key, {}) or {}).get("cuts")
    if not cuts or len(cuts) < 2:
        return None
    p = _pd.percentile_of(value, [float(c) for c in cuts],
                          direction == "higher")
    n = (((dist or {}).get("archetypes") or {}).get(arch or "", {})
         .get(key, {}) or {}).get("n")
    return p, f"أعلى من {p:.0f}٪ من قطاعه" + (f" (n={n})" if n else "")


def _component(features: dict, metrics: tuple, arch: str | None,
               dist: dict | None, medians: dict | None = None) -> dict:
    """مكوّنٌ واحد: درجتُه وتغطيتُه وقراءةُ كلّ مؤشّرٍ فيه."""
    total = got = 0.0
    acc = 0.0
    reads: list[dict] = []
    missing: list[str] = []
    for key, label, weight, direction in metrics:
        total += weight
        v = _val(features, key)
        if v is None:
            missing.append({"key": key, "label": label,
                            "status": UNAVAILABLE,
                            "why": "البندُ لم يصل من المصدر"})
            continue
        scored = _metric_score(key, direction, v, arch, dist, medians)
        if scored is None:
            missing.append({"key": key, "label": label,
                            "status": UNAVAILABLE,
                            "why": "لا مرجعَ يُقاس عليه — عشيرةٌ أو وسيطٌ دون الحدّ"})
            continue
        s, note = scored
        got += weight
        acc += s * weight
        reads.append({"key": key, "label": label, "value": round(v, 2),
                      "score": round(s, 1), "weight": weight,
                      "status": AVAILABLE, "note": note})
    cov = (got / total) if total else 0.0
    if got <= 0 or cov < MIN_COMPONENT_COVERAGE:
        return {"score": None, "coverage": round(cov, 2), "reads": reads,
                "missing": missing,
                "reason": f"قِيس {cov:.0%} من وزن المكوّن — دون الحدّ"}
    return {"score": round(acc / got, 1), "coverage": round(cov, 2),
            "reads": reads, "missing": missing, "reason": None}


# ══ مؤشّراتُ السعر تُشتقّ هنا لا في خطّ السمات ══
#
# خطُّ السمات يُبنى من القوائم وحدها، وعمداً: قوائمُ الشركة لا تتغيّر
# بتغيّر السعر، فبناؤها مرّةً يصلح لكلّ الجلسات. ومكوّنُ التقييم وحده
# يحتاج السعر، فيُشتقّ عنده — ولا يُحشر السعرُ في سمةٍ محاسبية فتفسد
# ذاكرتُها.

def price_features(info: dict | None, features: dict,
                   periods: list[dict] | None = None,
                   fair_value: float | None = None,
                   extra: dict | None = None) -> dict:
    """مضاعفاتُ السعر والعائدُ التوزيعيّ — ما أمكن اشتقاقُه فقط.

    وما لم يصل مقامُه لا يُقدَّر: مضاعفُ ربحيةٍ بربحٍ سالبٍ ليس رقماً
    كبيراً بل **غيرُ ذي معنى**، فيُترك غائباً ولا يُحسب شيئاً.
    """
    out: dict = dict(extra or {})
    info = info or {}
    price = info.get("current_price")
    if not isinstance(price, (int, float)) or price <= 0:
        return out
    last = (periods or [{}])[-1] if periods else {}

    dps = info.get("dividend_per_share")
    if isinstance(dps, (int, float)) and dps > 0:
        out["dividend_yield"] = round(dps / price * 100, 2)

    def _num(d, k):
        v = (d or {}).get(k)
        return float(v) if isinstance(v, (int, float)) else None

    eps = _num(last, "eps")
    if eps and eps > 0:
        out["p_e"] = round(price / eps, 2)
    neps = _val(features, "normalized_eps")
    if neps and neps > 0:
        out["p_e_normalized"] = round(price / neps, 2)
    bvps = _val(features, "book_value_per_share")
    if bvps and bvps > 0:
        out["p_b"] = round(price / bvps, 2)

    shares = _num(last, "shares_outstanding")
    ebitda = _num(last, "ebitda")
    if ebitda is None:
        op, dep = _num(last, "operating_income"), _num(last, "depreciation")
        if op is not None and dep is not None:
            ebitda = op + abs(dep)
    debt, cash = _num(last, "total_debt"), _num(last, "ending_cash")
    if shares and ebitda and ebitda > 0 and debt is not None:
        ev = price * shares + abs(debt) - (cash or 0.0)
        if ev > 0:
            out["ev_ebitda"] = round(ev / ebitda, 2)

    if isinstance(fair_value, (int, float)) and fair_value > 0:
        out["fv_discount"] = round((fair_value / price - 1) * 100, 1)
    return out


def compute(features: dict, sector: str | None, dist: dict | None,
            archetype: str | None = None, medians: dict | None = None) -> dict:
    """الدرجةُ الاستثمارية بمكوّناتها الأربعة — أو امتناعٌ مُعلَّلٌ.

    `archetype` نمطُ عشيرةِ الترتيب في `peer_distribution`. وهو مستقلٌّ
    عن النموذج الاقتصاديّ: النموذجُ يقرّر **أيُّ المؤشّرات تُقاس**،
    والنمطُ يقرّر **بمن تُقارَن**.
    """
    model = model_of(sector)
    out: dict = {"model": model, "sector": sector, "components": {},
                 "score": None, "grade": None, "grade_label": None,
                 "abstain_reason": None}
    if model is None:
        out["abstain_reason"] = (
            "القطاعُ غيرُ معروف، ولا يُلحَق بنموذجٍ تخميناً"
            if not sector else
            f"القطاع «{sector}» لا نموذجَ له في المواصفة")
        return out

    spec = COMPONENTS[model]
    for name in ("quality", "dividend", "growth", "valuation"):
        out["components"][name] = _component(
            features, spec[name], archetype, dist, medians)

    live = {k: c for k, c in out["components"].items()
            if c["score"] is not None}
    if len(live) < MIN_COMPONENTS:
        have = "، ".join(live) or "لا شيء"
        out["abstain_reason"] = (
            f"قام مكوّنٌ واحدٌ فقط ({have}) — والدرجةُ لا تُبنى على أقلّ "
            f"من {MIN_COMPONENTS}")
        return out

    # ══ الوزنُ يُقسَم على ما وصل ══
    # الأوزانُ مثبَّتة، والمكوّنُ الغائب لا يصير صفراً (فيُدان بنقصٍ في
    # مصدرنا) ولا يُخترَع. فتُعاد القسمةُ على ما قام — وهو قياسُ ما
    # نعرفه، وما غاب يُعلَن باسمه وتنزل به الثقة.
    wsum = sum(WEIGHTS[k] for k in live)
    out["score"] = round(
        sum(c["score"] * WEIGHTS[k] for k, c in live.items()) / wsum, 1)
    out["weight_basis"] = round(wsum, 2)
    out["components_missing"] = [k for k in WEIGHTS if k not in live]
    out["growth_period_years"] = _val(features, "growth_period_years")
    out["grade"], out["grade_label"] = grade_of(out["score"])
    return out


# ══ الثقةُ تقيس الأدلّة لا الدرجة ══
#
# فُصلت عن الدرجة عمداً: شركةٌ درجتُها ‎88 من أربع سنواتٍ وقوائمَ ناقصة
# ليست كشركةٍ درجتُها ‎88 من ثمانٍ كاملة — والرقمُ نفسه في الحالين،
# والفرقُ كلُّه في قوّة ما بُني عليه.

def confidence_of(result: dict, years: int | None) -> tuple[str, list[str]]:
    """«مرتفعة» · «متوسطة» · «منخفضة» — ومعها أسبابُ الخفض معدودة."""
    why: list[str] = []
    live = [c for c in result.get("components", {}).values()
            if c.get("score") is not None]
    if not live:
        return "منخفضة", ["لا مكوّنَ قام"]

    cov = sum(c["coverage"] for c in live) / len(live)
    gone = result.get("components_missing") or []
    if gone:
        why.append("مكوّنٌ لم يقم: " + "، ".join(gone))
    if cov < 0.60:
        why.append(f"وسيطُ تغطية المكوّنات {cov:.0%}")
    if isinstance(years, int) and years < 5:
        why.append(f"{years} قوائمَ متاحة فقط")

    # ══ نافذةُ النموّ القصيرة تخفض الثقة ══ (المادة ١)
    # النموُّ يُقاس على أطول نافذةٍ صالحة، وقد تكون سنتين. ونموُّ سنتين
    # ليس كنموّ خمس: الأولى قد تكون تعافياً من قاعٍ والثانية اتّجاهاً.
    # فالدرجةُ تقيس ما قِيس، والثقةُ تقول على كم سنةٍ قِيس.
    span = result.get("growth_period_years")
    short = isinstance(span, (int, float)) and span < 5
    if short:
        why.append(f"النموُّ قِيس على {span:.0f} سنوات لا خمس")

    if not gone and cov >= 0.75 and (years or 0) >= 5 and not short:
        return "مرتفعة", why
    if len(gone) <= 1 and cov >= 0.55 and (years or 0) >= 3:
        return "متوسطة", why
    return "منخفضة", why
