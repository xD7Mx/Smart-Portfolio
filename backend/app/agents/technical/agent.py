"""Technical Agent — analyzes price action and entry zones."""
from app.agents.base import BaseAgent

class TechnicalAgent(BaseAgent):
    name = "TechnicalAgent"
    description = "Price trend, support/resistance, entry zones, installment quality."

    async def _analyze(self, context: dict) -> dict:
        symbol = context.get("symbol", "N/A")
        price_data = context.get("price_data", {})
        return {
            "summary": f"Technical analysis for {symbol} — awaiting price data.",
            "score": price_data.get("technical_score", 50),
            "confidence": 60,
            "evidence": [],
            "suggested_action": "Review technical levels before executing installment.",
            "data": {"symbol": symbol, "trend": price_data.get("trend", "NEUTRAL")},
        }
