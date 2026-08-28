"""
Base Agent — Smart Portfolio
==============================
All AI agents inherit from this class.
Enforces the output contract and explainability rules.
"""

from abc import ABC, abstractmethod
from typing import Optional
# ══ استيرادٌ لا يُسقط الخادم ══
# كان `import google.generativeai` صريحاً في أعلى الملف، وهذا الملف يُستورد
# من `coordinator` الذي يستورده مسار `/ai/status`. فغيابُ الحزمة أو عطبٌ في
# تحميلها (ترقيةٌ ناقصة · عجلةٌ لا تطابق المعمارية · تغيّرٌ في SDK المزوّد)
# يُخرج **٥٠٠ بأثرٍ مكدسيّ** لا رسالةً تقول ما الخلل — وقِيس ذلك فعلاً:
# صفحة الذكاء تسقط بـ`ModuleNotFoundError: No module named 'google'`.
# والقاعدة في هذا التطبيق أن العطب يُعلَن ولا يُصمت عنه ولا يُسقط ما حوله:
# فالحزمة تُستورد بحذر، وغيابُها يصير **حالةً تُقال** لا انهياراً.
try:
    import google.generativeai as genai
    GENAI_ERROR: str | None = None
except Exception as _e:                                           # noqa: BLE001
    genai = None                                                  # type: ignore
    GENAI_ERROR = f"{type(_e).__name__}: {_e}"

from loguru import logger
from app.core.config import settings


class BaseAgent(ABC):
    """
    Abstract base class for all Smart Portfolio AI agents.

    Every agent MUST:
    - Have a single clearly defined responsibility.
    - Return a structured, explainable result.
    - Include a confidence score.
    - Never modify portfolio data.
    - Never make autonomous investment decisions.
    """

    name: str = "BaseAgent"
    description: str = ""

    def __init__(self):
        self._setup_ai()

    def _setup_ai(self):
        """Initialize AI provider (Gemini by default)."""
        if genai is None:
            self._model = None
            logger.warning(f"⚠️ {self.name}: مكتبة المزوّد غير متاحة — {GENAI_ERROR}")
        elif settings.AI_API_KEY:
            genai.configure(api_key=settings.AI_API_KEY)
            self._model = genai.GenerativeModel(settings.AI_MODEL)
        else:
            self._model = None
            logger.warning(f"⚠️ {self.name}: No AI API key configured.")

    async def run(self, context: dict) -> dict:
        """
        Main entry point. Validates context, runs analysis, returns result.
        """
        try:
            validated = self._validate_context(context)
            result = await self._analyze(validated)
            return self._format_output(result)
        except Exception as e:
            logger.error(f"❌ {self.name} failed: {e}")
            return self._error_output(str(e))

    @abstractmethod
    async def _analyze(self, context: dict) -> dict:
        """Core analysis logic — implemented by each agent."""
        pass

    def _validate_context(self, context: dict) -> dict:
        """Override to validate required context keys."""
        return context

    def _format_output(self, result: dict) -> dict:
        """Ensure all outputs follow the standard contract."""
        return {
            "agent": self.name,
            "success": True,
            "summary": result.get("summary", ""),
            "score": result.get("score"),
            "confidence": result.get("confidence", 0),
            "evidence": result.get("evidence", []),
            "suggested_action": result.get("suggested_action", ""),
            "data": result.get("data", {}),
        }

    def _error_output(self, error: str) -> dict:
        return {
            "agent": self.name,
            "success": False,
            "summary": f"Analysis failed: {error}",
            "score": None,
            "confidence": 0,
            "evidence": [],
            "suggested_action": "",
            "data": {},
        }

    async def _ask_ai(self, prompt: str, system_prompt: str = "") -> str:
        """
        Send a prompt to the AI model.
        ALL calls pass through the global GeminiRateLimiter to stay
        within the 15 RPM free-tier limit. The coordinator already
        wraps _throttled_run → rate_limiter.acquire() before calling
        agent.run(), so this method does NOT acquire again.
        It is safe to call directly only from within coordinator._throttled_run().
        """
        if not self._model:
            return "AI not configured. Please set AI_API_KEY in settings."
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = await self._model.generate_content_async(full_prompt)
            return response.text
        except Exception as e:
            # Handle 429 explicitly so the coordinator can log it clearly
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                logger.warning(
                    f"⚠️ {self.name}: Gemini 429 — rate limit hit despite throttling. "
                    "Consider reducing MAX_CONCURRENT in GeminiRateLimiter."
                )
                return "Rate limit reached (429). Analysis will retry on next scheduled run."
            logger.error(f"{self.name} AI call failed: {e}")
            return f"AI call failed: {e}"
