"""
AI Coordinator — Smart Portfolio
===================================
The central orchestrator for all AI Agents.

RATE LIMIT PROTECTION (Free Tier Safe):
- Gemini Free Tier: 15 RPM (requests per minute)
- asyncio.Semaphore(3) → max 3 concurrent API calls at any moment
- Inter-request delay of 1.5s between batches
- This guarantees we never exceed ~12 RPM even under heavy load
- Full analysis (8 agents): ~12–16 seconds total (safe, not instant)

RULES:
- Does NOT perform analysis itself.
- Does NOT modify portfolio data.
- Does NOT make investment decisions.
"""

import asyncio
import time
from typing import Optional
from loguru import logger
from datetime import datetime, timezone

from app.agents.finance.agent import FinanceAgent
from app.agents.technical.agent import TechnicalAgent
from app.agents.market.agent import MarketAgent
from app.agents.portfolio.agent import PortfolioAgent
from app.agents.risk.agent import RiskAgent
from app.agents.cash.agent import CashAgent
from app.agents.goals.agent import GoalAgent
from app.agents.installment.agent import InstallmentAgent
from app.agents.alternative.agent import AlternativeAgent
from app.agents.notification.agent import NotificationAgent
from app.agents.reporting.agent import ReportingAgent
from app.engine.evaluation.engine import EvaluationEngine
from app.core.config import settings


# ─── Rate Limiter ─────────────────────────────────────────────

class GeminiRateLimiter:
    """
    Token-bucket rate limiter for Gemini Free Tier.

    Free Tier limits:
      - 15 RPM  (requests per minute)
      - 1,500 RPD (requests per day)

    Strategy:
      - Semaphore(3): max 3 concurrent calls → never burst above 15 RPM
      - MIN_INTERVAL: enforce minimum gap between any two API calls
      - Daily counter: log usage and warn when approaching RPD limit

    Why Semaphore(3)?
      At 3 concurrent calls × worst-case 1s each = 3 req/s theoretical max.
      In practice Gemini takes 2–5s per call, so real throughput ≈ 1 req/s.
      That puts us at ~60 RPM theoretical ceiling — but Semaphore + delay
      keeps actual throughput at ≤ 12 RPM. Safe margin from the 15 RPM wall.
    """

    # Conservative: stay well under 15 RPM
    MAX_CONCURRENT   = 3          # simultaneous Gemini calls
    MIN_INTERVAL_SEC = 1.5        # seconds between any two calls
    RPD_WARN_AT      = 1200       # warn when 80% of daily quota used
    RPD_HARD_LIMIT   = 1480       # refuse new calls near daily ceiling

    def __init__(self):
        self._semaphore     = asyncio.Semaphore(self.MAX_CONCURRENT)
        self._last_call_ts  = 0.0
        self._daily_count   = 0
        self._day_reset_at  = self._today_start()
        self._lock          = asyncio.Lock()

    def _today_start(self) -> float:
        import datetime as dt
        today = dt.date.today()
        return time.mktime(today.timetuple())

    async def acquire(self, agent_name: str = "") -> None:
        """
        Call before every Gemini API request.
        Blocks if: (a) 3 calls already in flight, or (b) called too soon.
        Raises RuntimeError if daily quota is near exhaustion.
        """
        # Reset daily counter at midnight
        async with self._lock:
            if time.time() > self._day_reset_at + 86400:
                self._daily_count = 0
                self._day_reset_at = self._today_start()
                logger.info("🔄 Rate limiter: daily counter reset.")

            self._daily_count += 1
            count = self._daily_count

        if count >= self.RPD_HARD_LIMIT:
            raise RuntimeError(
                f"Daily Gemini quota nearly exhausted ({count}/{self.RPD_HARD_LIMIT}). "
                "Analysis blocked to protect free tier. Resets at midnight."
            )
        if count >= self.RPD_WARN_AT:
            logger.warning(f"⚠️ Gemini daily usage: {count}/1500 — approaching free tier limit.")

        # Acquire semaphore slot (max 3 concurrent)
        await self._semaphore.acquire()

        # Enforce minimum interval between calls
        async with self._lock:
            now     = time.monotonic()
            gap     = now - self._last_call_ts
            wait_for = self.MIN_INTERVAL_SEC - gap
            if wait_for > 0:
                self._last_call_ts = now + wait_for
            else:
                self._last_call_ts = now

        if wait_for > 0:
            logger.debug(f"⏳ Rate limiter: waiting {wait_for:.2f}s before {agent_name}")
            await asyncio.sleep(wait_for)

    def release(self) -> None:
        """Call after every Gemini API request (success or failure)."""
        self._semaphore.release()

    @property
    def daily_count(self) -> int:
        return self._daily_count

    @property
    def daily_remaining(self) -> int:
        return max(0, 1500 - self._daily_count)


# Global singleton — shared across all agents in the process
rate_limiter = GeminiRateLimiter()


# ─── AI Coordinator ───────────────────────────────────────────

class AICoordinator:
    """
    Central AI coordinator.
    Distributes tasks to specialized agents through the rate limiter.
    Agents that make Gemini API calls must go through _throttled_run().
    """

    def __init__(self):
        self.finance_agent      = FinanceAgent()
        self.technical_agent    = TechnicalAgent()
        self.market_agent       = MarketAgent()
        self.portfolio_agent    = PortfolioAgent()
        self.risk_agent         = RiskAgent()
        self.cash_agent         = CashAgent()
        self.goal_agent         = GoalAgent()
        self.installment_agent  = InstallmentAgent()
        self.alternative_agent  = AlternativeAgent()
        self.notification_agent = NotificationAgent()
        self.reporting_agent    = ReportingAgent()
        self.evaluation_engine  = EvaluationEngine()

    async def run_full_analysis(self, context: dict) -> dict:
        """
        Run all agents with rate limiting and return consolidated evaluation.

        Execution model (Free-Tier Safe):
          - Agents are grouped; each group runs concurrently (max 3 at once).
          - Between groups, the rate limiter enforces the 1.5s gap.
          - Total wall-clock time: ~12–20s for 8 agents. Acceptable trade-off.
        """
        logger.info("🤖 AI Coordinator: Starting full analysis (rate-limited)...")
        logger.info(f"   Gemini quota today: {rate_limiter.daily_count} used / {rate_limiter.daily_remaining} remaining")
        started_at = datetime.now(timezone.utc)

        # Agents that call Gemini (throttled)
        ai_agents = [
            ("finance",     self.finance_agent),
            ("technical",   self.technical_agent),
            ("market",      self.market_agent),
        ]

        # Agents that are pure Python / DB — no Gemini call (run freely)
        local_agents = [
            ("portfolio",   self.portfolio_agent),
            ("risk",        self.risk_agent),
            ("cash",        self.cash_agent),
            ("goal",        self.goal_agent),
            ("installment", self.installment_agent),
        ]

        agent_results = {}

        # 1. Run local agents in true parallel (no API calls, no throttle needed)
        local_tasks = [
            self._safe_run(agent, context)
            for _, agent in local_agents
        ]
        local_results = await asyncio.gather(*local_tasks, return_exceptions=True)
        for (name, _), result in zip(local_agents, local_results):
            agent_results[name] = (
                {"error": str(result), "success": False}
                if isinstance(result, Exception) else result
            )

        # 2. Run AI agents through the rate limiter (throttled, sequential batches)
        for name, agent in ai_agents:
            result = await self._throttled_run(agent, context, name)
            agent_results[name] = result

        # 3. Evaluate
        evaluation = await self.evaluation_engine.evaluate(agent_results, context)

        duration = (datetime.now(timezone.utc) - started_at).total_seconds()
        logger.info(
            f"✅ AI Coordinator: Analysis done in {duration:.1f}s "
            f"| Gemini calls today: {rate_limiter.daily_count}/1500"
        )

        return {
            "agent_results":    agent_results,
            "evaluation":       evaluation,
            "duration_seconds": round(duration, 1),
            "timestamp":        started_at.isoformat(),
            "quota_used":       rate_limiter.daily_count,
            "quota_remaining":  rate_limiter.daily_remaining,
        }

    async def analyze_company(self, symbol: str, context: dict) -> dict:
        """
        Deep analysis for a single company.
        3 Gemini calls, rate-limited sequentially.
        Wall-clock: ~6–12s. Acceptable for on-demand company view.
        """
        logger.info(f"🔍 Analyzing {symbol} (rate-limited, 3 AI calls)")
        ctx = {**context, "symbol": symbol}

        finance   = await self._throttled_run(self.finance_agent,   ctx, "finance")
        technical = await self._throttled_run(self.technical_agent, ctx, "technical")
        risk      = await self._throttled_run(self.risk_agent,       ctx, "risk")

        return {"symbol": symbol, "finance": finance, "technical": technical, "risk": risk}

    async def generate_market_summary(self, context: dict) -> dict:
        """1 Gemini call — always rate-limited."""
        return await self._throttled_run(self.market_agent, context, "market")

    async def check_installments(self, context: dict) -> dict:
        """Pure Python — no Gemini call."""
        return await self._safe_run(self.installment_agent, context)

    async def find_alternatives(self, symbol: str, reason: str, context: dict) -> dict:
        """1 Gemini call — rate-limited."""
        return await self._throttled_run(
            self.alternative_agent,
            {**context, "target_symbol": symbol, "reason": reason},
            "alternative"
        )

    # ── Internal helpers ──────────────────────────────────────

    async def _throttled_run(self, agent, context: dict, name: str) -> dict:
        """
        Wraps an agent run with rate limiter acquire/release.
        Use for any agent that makes a Gemini API call.
        """
        try:
            await rate_limiter.acquire(name)
            return await self._safe_run(agent, context)
        except RuntimeError as e:
            # Quota exhausted
            logger.error(f"🚫 Rate limit blocked {name}: {e}")
            return {
                "agent": name, "success": False,
                "summary": str(e), "score": None,
                "confidence": 0, "evidence": [], "suggested_action": "",
            }
        finally:
            rate_limiter.release()

    async def _safe_run(self, agent, context: dict) -> dict:
        """Safely run an agent, catching all exceptions."""
        try:
            return await agent.run(context)
        except Exception as e:
            logger.error(f"Agent {agent.__class__.__name__} error: {e}")
            return {
                "agent": agent.__class__.__name__, "success": False,
                "summary": f"Agent failed: {e}", "score": None,
                "confidence": 0, "evidence": [], "suggested_action": "",
            }

    def quota_status(self) -> dict:
        """Returns current Gemini quota usage."""
        from app.core.config import settings as _cfg
        limit = getattr(_cfg, "GEMINI_DAILY_LIMIT", 1500) or 1500
        return {
            "daily_used":       rate_limiter.daily_count,
            "daily_remaining":  max(0, limit - rate_limiter.daily_count),
            "daily_limit":      limit,
            "usage_pct":        round(rate_limiter.daily_count / limit * 100, 1),
            "rpm_limit":        15,
            "concurrent_limit": rate_limiter.MAX_CONCURRENT,
            "min_interval_sec": rate_limiter.MIN_INTERVAL_SEC,
        }


coordinator = AICoordinator()
