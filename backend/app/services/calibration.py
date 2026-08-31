"""معايرةُ المؤشّرات على توزيعها الفعليّ في القطاع — إحصاءٌ متين.

## لماذا «متين» لا «وسطيّ»

المتوسّطُ والانحرافُ المعياريّ يفترضان توزيعاً متماثلاً بلا أطراف
سميكة، والمؤشّراتُ المالية ليست كذلك: العائدُ على حقوق الملكية يخرج
‎800٪ حين تقارب حقوقُ الملكية الصفر، ومضاعفُ الربحية ينفجر عند ربحٍ
ضئيل. فشركةٌ واحدةٌ تكفي لتحريك المتوسّط عشرَ نقاطٍ فتُعاد معايرةُ
قطاعٍ كامل حولها.

فالمرجعُ هنا **الوسيطُ وانحرافُه المطلق** (‏MAD): لا يتحرّك الوسيطُ
بشاذٍّ واحد مهما بلغ، ويحتاج ‎50٪ من العيّنة لتحريكه. والمتوسّطُ
والانحرافُ يُحسبان ويُعرضان **فقط حين يصحّ استعمالُهما** — أي حين
يقارب التوزيعُ التماثلَ وتكفي العيّنة — وإلّا فيُعلَنان غيرَ صالحين
ولا يُستعملان (المادة ٣).

## معالجةُ الشواذّ

لا تُحذف: الشاذُّ واقعةٌ في السوق لا خطأٌ يُمحى، وحذفُه يُخفي شركةً
حقيقية. بل **يُقصَّر أثرُه** (‏winsorize) عند المئين الخامس والخامس
والتسعين قبل حساب المتوسّط — فيبقى في العيّنة ويُحسب طرفاً، ولا يجرّ
المعايرةَ إليه. وتُسجَّل الشواذُّ بعددها فيراها المدقّق.

## القيمُ المفقودة

تُترك مفقودةً. لا تُستبدل بصفرٍ ولا بوسيطٍ ولا بأيّ تقدير: استبدالُها
بالوسيط يجعل الشركةَ «متوسّطةَ القطاع» في شيءٍ لا نعرفه عنها، وهو
اختراعٌ صامت. ويُعرض عددُ من قِيس ومن لم يُقَس مع كلّ توزيع.
"""

from __future__ import annotations

# عشيرةٌ دون هذا العدد لا تُعاير: توزيعٌ من خمسِ شركاتٍ ليس توزيعاً.
MIN_COHORT = 8
# ودون هذا العدد لا يُعرض متوسّطٌ ولا انحراف مهما بدا التوزيع متماثلاً.
MIN_FOR_MOMENTS = 20
# حدُّ الالتواء الذي يبطل معه استعمالُ المتوسّط.
MAX_SKEW = 1.0
_MAD_TO_SIGMA = 1.4826      # يجعل MAD مكافئاً للانحراف عند التوزيع الطبيعيّ


def _clean(vals) -> list[float]:
    out = []
    for v in vals or []:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        if v != v or abs(v) == float("inf"):
            continue
        out.append(float(v))
    return out


def quantile(sorted_vals: list[float], q: float) -> float:
    """مئينٌ بالاستيفاء الخطّيّ — على عيّنةٍ مرتّبة."""
    if not sorted_vals:
        raise ValueError("عيّنةٌ فارغة")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def describe(values, n_missing: int = 0) -> dict:
    """وصفُ توزيعٍ واحد — متينٌ أوّلاً، ولحظاتٌ حين تصحّ فقط."""
    vals = _clean(values)
    n = len(vals)
    out: dict = {"n": n, "n_missing": int(n_missing),
                 "usable": n >= MIN_COHORT}
    if n == 0:
        out.update({"median": None, "mad": None, "p": {},
                    "mean": None, "std": None, "moments_valid": False,
                    "moments_reason": "لا عيّنة"})
        return out

    s = sorted(vals)
    med = quantile(s, 0.5)
    mad = quantile(sorted(abs(v - med) for v in vals), 0.5)
    out["median"] = round(med, 6)
    out["mad"] = round(mad, 6)
    out["p"] = {int(q * 100): round(quantile(s, q), 6)
                for q in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)}

    # ── الشواذُّ تُقصَّر ولا تُحذف ──
    lo, hi = quantile(s, 0.05), quantile(s, 0.95)
    wins = [min(max(v, lo), hi) for v in vals]
    out["n_outliers"] = sum(1 for v in vals if v < lo or v > hi)
    out["winsor_bounds"] = [round(lo, 6), round(hi, 6)]

    mean = sum(wins) / n
    var = sum((v - mean) ** 2 for v in wins) / max(n - 1, 1)
    std = var ** 0.5

    # ══ أيصحّ استعمالُ المتوسّط هنا؟ ══
    # يُقاس التماثلُ بمقياسٍ متينٍ لا بعزمٍ ثالثٍ يفسده الشاذُّ نفسه:
    # التواءُ بولي يقارن بُعدَ الرُّبيعين عن الوسيط، فلا يتأثّر بالأطراف.
    q1, q3 = quantile(s, 0.25), quantile(s, 0.75)
    iqr = q3 - q1
    skew = ((q3 + q1 - 2 * med) / iqr) if iqr > 0 else 0.0
    ok = n >= MIN_FOR_MOMENTS and abs(skew) <= MAX_SKEW and std > 0
    out.update({
        "mean": round(mean, 6) if ok else None,
        "std": round(std, 6) if ok else None,
        "bowley_skew": round(skew, 3),
        "moments_valid": bool(ok),
        "moments_reason": (
            None if ok else
            f"عيّنة {n} دون {MIN_FOR_MOMENTS}" if n < MIN_FOR_MOMENTS else
            f"التواء {skew:+.2f} يفوق {MAX_SKEW}" if abs(skew) > MAX_SKEW else
            "انحرافٌ صفر"),
    })
    return out


def percentile_of(value: float, dist: dict, higher_is_better: bool) -> float | None:
    """موقعُ قيمةٍ في توزيعها — مئينٌ من ‎0 إلى ‎100.

    ويُقرأ من المئينات المحفوظة بالاستيفاء، فلا يحتاج العيّنةَ كاملة.
    والتعادلُ يأخذ منتصفَ رتبته: عشيرةٌ متشابهةٌ لا يُعاقَب أفرادُها
    جميعاً بصفر.
    """
    p = (dist or {}).get("p") or {}
    if not p:
        return None
    ks = sorted(p)
    xs = [p[k] for k in ks]
    if xs[0] == xs[-1]:
        return 50.0                       # توزيعٌ متعادلٌ كلُّه — لا معلومة
    if value <= xs[0]:
        pct = float(ks[0])
    elif value >= xs[-1]:
        pct = float(ks[-1])
    else:
        pct = float(ks[-1])
        for i in range(len(xs) - 1):
            if xs[i] <= value <= xs[i + 1]:
                span = xs[i + 1] - xs[i]
                frac = ((value - xs[i]) / span) if span > 0 else 0.5
                pct = ks[i] + frac * (ks[i + 1] - ks[i])
                break
    return round(pct if higher_is_better else 100.0 - pct, 1)


def robust_z(value: float, dist: dict) -> float | None:
    """بُعدُ القيمة عن وسيطها بوحداتٍ متينة — لا بالانحراف المعياريّ."""
    med, mad = (dist or {}).get("median"), (dist or {}).get("mad")
    if med is None or not mad:
        return None
    return round((value - med) / (mad * _MAD_TO_SIGMA), 3)


def build(rows_by_cohort: dict[str, dict[str, list]],
          missing_by_cohort: dict | None = None) -> dict:
    """معايرةُ السوق كلِّه: لكلّ عشيرةٍ كلُّ مؤشّرٍ بوصفه.

    `rows_by_cohort[cohort][metric] = [قيم]`
    """
    miss = missing_by_cohort or {}
    out: dict = {"cohorts": {}, "meta": {
        "min_cohort": MIN_COHORT, "min_for_moments": MIN_FOR_MOMENTS,
        "winsor": "p5–p95", "missing_policy": "تُترك ولا تُستبدل"}}
    for cohort, metrics in (rows_by_cohort or {}).items():
        d = {}
        for metric, vals in metrics.items():
            n_missing = (miss.get(cohort) or {}).get(metric, 0)
            desc = describe(vals, n_missing)
            if desc["usable"]:
                d[metric] = desc
        out["cohorts"][cohort] = d
    return out
