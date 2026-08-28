from app.agents.base import BaseAgent
from app.engine.calculation.engine import calculate_price_proximity
class InstallmentAgent(BaseAgent):
    name = "InstallmentAgent"
    description = "Monitors installment price levels and alerts on proximity."
    async def _analyze(self, context):
        installments = context.get("installments", [])
        near = []
        for i in installments:
            if i.get("status") == "WAITING":
                p = calculate_price_proximity(i.get("current_price",0), i.get("target_price",0))
                if p["is_near"]:
                    near.append({**i, "proximity": p})
        return {"summary": f"{len(near)} installment(s) near target.", "score": None, "confidence": 90, "evidence": near, "suggested_action": "Review near-target installments." if near else "", "data": {"near_targets": near}}
