from app.agents.base import BaseAgent
class GoalAgent(BaseAgent):
    name = "GoalAgent"
    description = "Goal tracking: capital target, income target, time-to-completion."
    async def _analyze(self, context):
        goals = context.get("goals", [])
        return {"summary": f"Tracking {len(goals)} investment goal(s).", "score": None, "confidence": 95, "evidence": [], "suggested_action": "Review goal progress monthly.", "data": {"goals_count": len(goals)}}
