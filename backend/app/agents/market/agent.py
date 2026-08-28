"""Market Intelligence Agent."""
from app.agents.base import BaseAgent

class MarketAgent(BaseAgent):
    name = "MarketAgent"
    description = "Market overview, news, events, financial results, corporate actions."

    async def _analyze(self, context: dict) -> dict:
        news = context.get("news", [])
        events = context.get("events", [])
        return {
            "summary": f"Market summary: {len(news)} news items, {len(events)} events tracked.",
            "score": None,
            "confidence": 80,
            "evidence": [{"type": "news_count", "value": len(news)}],
            "suggested_action": "Review market events affecting portfolio companies.",
            "data": {"news_count": len(news), "events_count": len(events)},
        }
