from app.agents.base import BaseAgent
class AlternativeAgent(BaseAgent):
    name = "AlternativeAgent"
    description = "Finds alternative companies when existing ones deteriorate."
    async def _analyze(self, context):
        target = context.get("target_symbol", "N/A")
        return {"summary": f"Alternative search for {target}.", "score": None, "confidence": 50, "evidence": [], "suggested_action": "", "data": {"alternatives": []}}
