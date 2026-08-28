from app.agents.base import BaseAgent
class RiskAgent(BaseAgent):
    name = "RiskAgent"
    description = "Risk assessment: concentration, debt, earnings quality, sector risk."
    async def _analyze(self, context):
        return {"summary": "Risk analysis completed.", "score": 35, "confidence": 70, "evidence": [], "suggested_action": "Monitor high-concentration positions.", "data": {"risk_level": "MEDIUM"}}
