"""
Financial narrative — a fluent Arabic analytical SENTENCE about a company's
financial statements, for the governance/financials view.

Deliberately NOT a "buy/avoid" verdict: that call already lives next to the
score (the Decision Engine / تقييم الأداء) and repeating it here is noise.
What belongs here is an *analyst's read* of the numbers — what the
statements say about the business.

Two layers, in the order the owner asked for:
  1. Gemini (primary) when an API key is configured and the daily quota
     allows — a natural, well-phrased sentence grounded in the real
     scores/strengths we pass it (never free-invented).
  2. A deterministic rule-based sentence (permanent backup) composed from
     the same explainability output — always available, no key, no quota,
     every clause traceable to a real signal.
"""

from __future__ import annotations

from typing import Optional

from app.services import cache
from app.services.four_scores import FourScores
from app.services.explainability import Explanation

NARRATIVE_TTL = 24 * 60 * 60


def _health_lead(quality: Optional[float]) -> str:
    if quality is None:
        return "بيانات مالية محدودة"
    if quality >= 85:
        return "مركز مالي قوي جداً"
    if quality >= 70:
        return "مركز مالي قوي"
    if quality >= 55:
        return "مركز مالي مقبول"
    if quality >= 40:
        return "مركز مالي متوسط مع نقاط تحتاج متابعة"
    return "مركز مالي ضعيف يتطلب حذراً"


def rule_based_narrative(scores: FourScores, explanation: Explanation) -> str:
    """Fluent analytical sentence from the real scores + top strengths/
    weaknesses — the permanent, quota-free backup."""
    if scores.rejected:
        return f"استُبعدت الشركة من التقييم: {scores.hard_filter_message}."

    lead = _health_lead(scores.quality.score)
    parts: list[str] = [lead]

    strengths = [_strip_bonus_prefix(s) for s in explanation.strengths[:2]]
    weaknesses = [_strip_bonus_prefix(w) for w in explanation.weaknesses[:2]]
    is_strong = (scores.quality.score or 0) >= 55

    if is_strong:
        # Lead with what drives the strength, then any caveat.
        if strengths:
            parts.append("يدعمه " + " و".join(strengths))
        if weaknesses:
            parts.append("مع تحفّظ على " + " و".join(weaknesses))
        elif strengths:
            parts.append("دون نقاط ضعف جوهرية في القوائم")
    else:
        # Lead with the real problems, then note any bright spot honestly.
        if weaknesses:
            parts.append("أبرز ما يثقله " + " و".join(weaknesses))
        if strengths:
            parts.append("رغم " + " و".join(strengths))

    return "؛ ".join(parts) + "."


def _strip_bonus_prefix(msg: str) -> str:
    """The explainability messages already read naturally ("عائد ممتاز على
    حقوق الملكية (22%)"); just trim a trailing parenthetical if it makes the
    concatenated sentence cleaner. Kept conservative — only drops an empty
    tail, never real content."""
    return msg.strip()


def _gemini_prompt(scores: FourScores, explanation: Explanation) -> str:
    s = scores
    lines = [
        "أنت محلل مالي محترف. اكتب جملة تحليلية عربية واحدة فقط (لا أكثر من ٣٠ كلمة)",
        "تلخّص قراءة القوائم المالية لهذه الشركة. لا تذكر توصية شراء أو بيع أو تجنب إطلاقاً",
        "— فقط تحليل الوضع المالي. اعتمد حصراً على المعطيات التالية دون اختلاق أرقام:",
        f"- درجة الجودة: {s.quality.score}/100",
        f"- درجة السلامة المالية: {s.safety.score}/100",
        "- أبرز نقاط القوة: " + "؛ ".join(explanation.strengths[:3] or ["لا يوجد"]),
        "- أبرز نقاط الضعف: " + "؛ ".join(explanation.weaknesses[:3] or ["لا يوجد"]),
        "أخرج الجملة فقط بلا مقدمات ولا رموز.",
    ]
    return "\n".join(lines)


async def _gemini_narrative(scores: FourScores, explanation: Explanation) -> Optional[str]:
    from app.core.config import settings
    if not settings.AI_API_KEY:
        return None
    from app.services.usage_tracker import can_call, record
    if not can_call("gemini"):
        return None
    import httpx
    from loguru import logger
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
    )
    body = {
        "contents": [{"parts": [{"text": _gemini_prompt(scores, explanation)}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 120},
    }
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=body)
        if r.status_code != 200:
            logger.debug(f"narrative Gemini HTTP {r.status_code}: {r.text[:120]}")
            return None
        cand = (r.json().get("candidates") or [{}])[0]
        text = ((cand.get("content") or {}).get("parts") or [{}])[0].get("text", "").strip()
        # Guard: reject if the model slipped a buy/sell word in despite the
        # instruction — fall back to the rule-based sentence rather than
        # duplicating the decision the user explicitly didn't want here.
        if not text or any(w in text for w in ("شراء", "بيع", "تجنب", "احتفظ", "توصي")):
            return None
        return text.split("\n")[0].strip()
    except Exception as e:
        logger.debug(f"narrative Gemini failed: {e}")
        return None


async def financial_narrative(symbol: str, scores: FourScores, explanation: Explanation) -> str:
    """Analytical sentence for `symbol` — Gemini when available, else the
    deterministic rule-based sentence. Cached 24h per symbol so it costs at
    most one Gemini call per company per day."""
    ck = f"fin_narrative:{symbol}"
    cached = cache.get(ck)
    if cached is not None:
        return cached
    text = await _gemini_narrative(scores, explanation)
    if not text:
        text = rule_based_narrative(scores, explanation)
    cache.set(ck, text, NARRATIVE_TTL)
    return text
