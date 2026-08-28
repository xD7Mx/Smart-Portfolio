from app.agents.base import BaseAgent
class CashAgent(BaseAgent):
    name = "CashAgent"
    description = "Cash management: available, pending, reinvestment readiness."
    async def _analyze(self, context):
        cash = context.get("cash", {})
        return {"summary": f"Available cash: {cash.get('available_cash', 0)}", "score": None, "confidence": 90, "evidence": [], "suggested_action": "Ensure liquidity for upcoming installments.", "data": cash}
