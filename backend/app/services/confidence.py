"""
Confidence Score — Phase 12 of the governance-engine redesign.

Answers a different question from the four scores themselves: not "is
this a good stock" but "how much should you trust the number you just
saw". Built from three honest signals, never fabricated:
  - years_available: how many years of statements actually back this up
  - completeness: what fraction of the core Feature Engine outputs
    actually resolved to a real value instead of None
  - consistency_index: Phase 9's stability composite (a company whose
    numbers bounce around wildly is harder to score with confidence than
    one with a clean trend, even given the same data completeness)

A confidence below 60 should surface a visible warning in the UI — the
four scores may still be shown, but the user needs to know they're
resting on thin data.

‏D675 (بقرار المالك 2026-10-10: «فصلُ الثبات عن الثقة»): الثقةُ كفايةُ البيانات وحدها — سنواتُ القوائم واكتمالُ
المؤشّرات بالتساوي. والثباتُ صفةٌ في الشركة لا في بياناتنا: كان خُمسَ الدرجة فلم تبلغ 90 شركةٌ أرباحُها دوريّة ولو
اكتملت بياناتُها (قِيس: 166 من 271). فصار وسماً مستقلّاً يُعرض بجانبها (مستقرّة · متوسطةُ الثبات · متذبذبة) بقيمته،
فلا تضيع المعلومة ولا تُخفض ثقةً في رقمٍ بياناتُه كاملة.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# The Quality/Safety-relevant subset of Feature Engine outputs whose
# presence actually signals "enough statement data was available" — not
# every derived key (some, like *_cagr_5y, are legitimately None for a
# perfectly healthy 2-year-old listing and shouldn't be held against it).
_CORE_FEATURES = [
    "roe", "roa", "roic", "gross_margin", "operating_margin", "net_margin",
    "fcf_margin", "cash_conversion_ratio", "accrual_ratio", "interest_coverage",
    "current_ratio", "quick_ratio", "asset_turnover", "debt_trend",
    "earnings_stability", "eps_stability", "roe_stability", "fcf_stability",
]

CONFIDENCE_WARNING_THRESHOLD = 60


@dataclass
class Confidence:
    score: float
    warning: Optional[str]
    years_available: int
    completeness_pct: float
    stability: Optional[float] = None          # ‏D675: مؤشّرُ الثبات — وسمٌ مستقلّ لا جزءٌ من الثقة
    stability_label: Optional[str] = None


def compute_confidence(features: dict) -> Confidence:
    def value_of(name):
        raw = features.get(name)
        return raw.get("value") if isinstance(raw, dict) else raw

    years = value_of("years_available") or 0
    years_component = max(0.0, min(100.0, years / 5 * 100))  # 5 years = full marks

    # ‏D671 (المرشَّح 2.3): الاكتمالُ على ما ينطبق — مؤشّرٌ لا معنى له في الشركة لا يُعدّ عليها ناقصاً. قِيس: المصارفُ
    # كلُّها «ينقصها» السيولةُ الجارية والسريعة، ومن لا دَينَ عليه «تنقصه» التغطيةُ؛ وهي ليست بياناتٍ غائبةً تُجلب.
    na = set()
    if value_of("no_interest_cost") == 1:
        na.add("interest_coverage")
    if value_of("unclassified_balance_sheet") == 1:
        na |= {"current_ratio", "quick_ratio"}
    applicable = [k for k in _CORE_FEATURES if k not in na]
    present = sum(1 for k in applicable if value_of(k) is not None)
    completeness_pct = round(present / len(applicable) * 100, 1)

    consistency = value_of("consistency_index")
    # ‏D675: الثقةُ كفايةُ البيانات بالتساوي بين السنوات والاكتمال، والثباتُ وسمٌ بجانبها
    score = round(years_component * 0.5 + completeness_pct * 0.5, 1)
    score = max(0.0, min(100.0, score))
    stability_label = (None if consistency is None else
                       "مستقرّة" if consistency >= 60 else "متوسطةُ الثبات" if consistency >= 30 else "متذبذبة")

    warning = None
    if score < CONFIDENCE_WARNING_THRESHOLD:
        reasons = []
        if years < 3:
            reasons.append(f"{years} سنة مالية فقط متاحة")
        if completeness_pct < 70:
            reasons.append(f"{completeness_pct}% فقط من المؤشرات الأساسية متوفرة")
        warning = "درجة ثقة منخفضة (" + "، ".join(reasons or ["بيانات غير كافية"]) + ") — النتيجة قد لا تعكس الوضع الحقيقي بدقة"

    return Confidence(score=score, warning=warning, years_available=years, completeness_pct=completeness_pct,
                      stability=round(consistency, 1) if isinstance(consistency, (int, float)) else None,
                      stability_label=stability_label)
