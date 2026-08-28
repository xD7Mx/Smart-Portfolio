"""
Evaluation Engine — Smart Portfolio
======================================
Receives results from all AI Agents, resolves conflicts,
removes duplicates, and produces a unified evaluation.

RULES:
- Does NOT generate new data.
- Does NOT make investment decisions.
- Does NOT hide agent disagreements — shows them clearly.
- Final decision always remains with the investor.
"""

from typing import Optional
from loguru import logger


PRIORITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


class EvaluationEngine:
    """
    Central evaluation layer.
    Receives multi-agent outputs and produces a single coherent evaluation.
    """

    async def evaluate(self, agent_results: dict, context: dict) -> dict:
        """
        Main evaluation entry point.
        agent_results: {agent_name: agent_output_dict}
        """
        try:
            # 1. Validate & filter successful results
            valid = {k: v for k, v in agent_results.items() if v.get("success", True)}

            # 2. Extract key signals
            scores = self._extract_scores(valid)
            conflicts = self._detect_conflicts(valid)
            opportunities = self._classify_opportunities(valid)
            risks = self._classify_risks(valid)

            # 3. Compute confidence
            confidence = self._compute_overall_confidence(valid)

            # 4. Build executive summary
            summary = self._build_summary(valid, conflicts, opportunities, risks)

            return {
                "success": True,
                "executive_summary": summary,
                "scores": scores,
                "overall_confidence": confidence,
                "conflicts": conflicts,
                "opportunities": opportunities,
                "risks": risks,
                "agent_count": len(valid),
                "failed_agents": [k for k, v in agent_results.items() if not v.get("success", True)],
            }
        except Exception as e:
            logger.error(f"EvaluationEngine error: {e}")
            return {"success": False, "error": str(e)}

    def _extract_scores(self, results: dict) -> dict:
        scores = {}
        for name, result in results.items():
            if result.get("score") is not None:
                scores[name] = {
                    "score": result["score"],
                    "confidence": result.get("confidence", 0),
                }
        return scores

    def _detect_conflicts(self, results: dict) -> list:
        """
        Detect when agents disagree significantly.
        Conflicts are SHOWN to the investor — never hidden.
        """
        conflicts = []

        finance = results.get("finance", {})
        technical = results.get("technical", {})

        f_score = finance.get("score")
        t_score = technical.get("score")

        if f_score is not None and t_score is not None:
            if abs(f_score - t_score) > 30:
                conflicts.append({
                    "type": "SCORE_DIVERGENCE",
                    "description": (
                        f"Finance Agent ({f_score:.0f}) and Technical Agent ({t_score:.0f}) "
                        f"have significantly different scores. "
                        "Consider both perspectives before deciding."
                    ),
                    "agents": ["finance", "technical"],
                })

        return conflicts

    def _classify_opportunities(self, results: dict) -> list:
        """
        Classify opportunities — never use buy/sell language.
        """
        opportunities = []

        installment = results.get("installment", {})
        near_targets = installment.get("data", {}).get("near_targets", [])

        if near_targets:
            opportunities.append({
                "type": "INSTALLMENT_NEAR_TARGET",
                "priority": "HIGH",
                "description": f"{len(near_targets)} installment(s) are near their target price.",
                "action": "Review installment plan — decision is yours.",
            })

        return opportunities

    def _classify_risks(self, results: dict) -> list:
        risks = []

        risk_data = results.get("risk", {}).get("data", {})
        if risk_data.get("risk_level") == "HIGH":
            risks.append({
                "type": "HIGH_RISK_DETECTED",
                "priority": "HIGH",
                "description": "Risk agent has flagged elevated risk.",
            })

        return risks

    def _compute_overall_confidence(self, results: dict) -> float:
        confidences = [r.get("confidence", 0) for r in results.values() if r.get("confidence")]
        if not confidences:
            return 0.0
        return round(sum(confidences) / len(confidences), 1)

    def _build_summary(
        self,
        results: dict,
        conflicts: list,
        opportunities: list,
        risks: list,
    ) -> str:
        parts = []

        portfolio = results.get("portfolio", {})
        if portfolio.get("summary"):
            parts.append(portfolio["summary"])

        market = results.get("market", {})
        if market.get("summary"):
            parts.append(market["summary"])

        if opportunities:
            parts.append(f"⚡ {len(opportunities)} opportunity/ies identified.")
        if risks:
            parts.append(f"⚠️ {len(risks)} risk(s) flagged.")
        if conflicts:
            parts.append(f"⚖️ {len(conflicts)} agent conflict(s) detected — review details.")

        parts.append("All findings are for decision support only. Final decision is yours.")

        return " | ".join(parts)
