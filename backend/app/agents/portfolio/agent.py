from app.agents.base import BaseAgent
class PortfolioAgent(BaseAgent):
    name = "PortfolioAgent"
    description = "Portfolio analysis: diversification, weights, income, goal progress."
    async def _analyze(self, context):
        holdings = context.get("holdings", [])
        return {"summary": f"Portfolio has {len(holdings)} active positions.", "score": None, "confidence": 85, "evidence": [], "suggested_action": "Monitor sector diversification.", "data": {"positions": len(holdings)}}
