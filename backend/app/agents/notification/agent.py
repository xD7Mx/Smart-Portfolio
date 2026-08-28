from app.agents.base import BaseAgent
class NotificationAgent(BaseAgent):
    name = "NotificationAgent"
    description = "Evaluates events and dispatches relevant notifications."
    async def _analyze(self, context):
        events = context.get("events", [])
        return {"summary": f"Evaluated {len(events)} events.", "score": None, "confidence": 95, "evidence": [], "suggested_action": "", "data": {"notifications_queued": 0}}
