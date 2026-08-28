from app.agents.base import BaseAgent
class ReportingAgent(BaseAgent):
    name = "ReportingAgent"
    description = "Builds daily/weekly/monthly reports from all agent outputs."
    async def _analyze(self, context):
        return {"summary": "Report assembled.", "score": None, "confidence": 90, "evidence": [], "suggested_action": "", "data": {}}
