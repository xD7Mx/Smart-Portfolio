"""
Explainability Engine — Phase 11 of the governance-engine redesign.

Every score in this system already carries its own trail of named,
human-readable rule hits (governance_rules.RuleHit.message) — nothing here
invents new reasoning. This module only organizes that existing trail into
the four answers a governance report has to give: why this score, the
biggest strengths, the biggest weaknesses, and what would raise it.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.decision_engine import Decision
from app.services.four_scores import FourScores


@dataclass
class Explanation:
    decision: str
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    improve: list[str]


def _all_hits(scores: FourScores):
    for cat in ("quality", "valuation", "safety", "timing"):
        cat_score = getattr(scores, cat)
        for h in cat_score.hits:
            yield cat, h


def explain(scores: FourScores, decision: Decision, top_n: int = 5) -> Explanation:
    if scores.rejected:
        return Explanation(
            decision=decision.decision,
            summary=f"تم استبعاد الشركة قبل احتساب أي درجة: {scores.hard_filter_message}",
            strengths=[],
            weaknesses=[scores.hard_filter_message or ""],
            improve=["معالجة السبب الجذري للاستبعاد قبل أي إعادة تقييم"],
        )

    hits = list(_all_hits(scores))
    bonuses = sorted((h for _, h in hits if h.kind == "bonus"), key=lambda h: -h.points)
    penalties = sorted((h for _, h in hits if h.kind == "penalty"), key=lambda h: h.points)  # most negative first

    cat_labels = {"quality": "الجودة", "valuation": "التقييم السعري", "safety": "السلامة المالية", "timing": "التوقيت الفني"}
    cat_scores = {c: getattr(scores, c).score for c in ("quality", "valuation", "safety", "timing")}
    summary = (
        f"القرار: {decision.decision} — "
        + "، ".join(f"{cat_labels[c]} {v}/100" for c, v in cat_scores.items() if v is not None)
    )

    strengths = [h.message for h in bonuses[:top_n]]
    weaknesses = [h.message for h in penalties[:top_n]]

    # "What would improve the score" — the highest-severity penalties are
    # the highest-leverage things to fix first; critical/high get named
    # explicitly, everything else falls back to "fix the weakest point".
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    improve_targets = sorted(penalties, key=lambda h: (severity_rank.get(h.severity, 9), h.points))[:top_n]
    improve = [f"لرفع الدرجة: عالج — {h.message}" for h in improve_targets]
    if not improve:
        if cat_scores.get("valuation") is not None and cat_scores["valuation"] < 50:
            improve.append("لا توجد نقاط ضعف جوهرية — الدرجة معتدلة لعدم رخص السعر الحالي نسبياً فقط")
        else:
            improve.append("لا توجد نقاط ضعف جوهرية حالياً — استمر بمراقبة الاستقرار مع مرور الوقت")

    return Explanation(decision=decision.decision, summary=summary, strengths=strengths, weaknesses=weaknesses, improve=improve)
