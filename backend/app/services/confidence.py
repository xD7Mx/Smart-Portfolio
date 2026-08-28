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


def compute_confidence(features: dict) -> Confidence:
    def value_of(name):
        raw = features.get(name)
        return raw.get("value") if isinstance(raw, dict) else raw

    years = value_of("years_available") or 0
    years_component = max(0.0, min(100.0, years / 5 * 100))  # 5 years = full marks

    present = sum(1 for k in _CORE_FEATURES if value_of(k) is not None)
    completeness_pct = round(present / len(_CORE_FEATURES) * 100, 1)

    consistency = value_of("consistency_index")
    consistency_component = consistency if consistency is not None else 50.0  # neutral, not a penalty, when unknown

    score = round(years_component * 0.4 + completeness_pct * 0.4 + consistency_component * 0.2, 1)
    score = max(0.0, min(100.0, score))

    warning = None
    if score < CONFIDENCE_WARNING_THRESHOLD:
        reasons = []
        if years < 3:
            reasons.append(f"{years} سنة مالية فقط متاحة")
        if completeness_pct < 70:
            reasons.append(f"{completeness_pct}% فقط من المؤشرات الأساسية متوفرة")
        if consistency is not None and consistency < 40:
            reasons.append("تذبذب كبير في النتائج المالية عبر السنوات")
        warning = "درجة ثقة منخفضة (" + "، ".join(reasons or ["بيانات غير كافية"]) + ") — النتيجة قد لا تعكس الوضع الحقيقي بدقة"

    return Confidence(score=score, warning=warning, years_available=years, completeness_pct=completeness_pct)
