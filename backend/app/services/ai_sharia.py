"""
AI-based Sharia-compliance lookup.

The AI (Gemini) is the primary source of truth for a stock's Sharia
status. It is asked to answer strictly from well-established public
Sharia-screening standards (AAOIFI-style criteria used by known Saudi
screening sources such as "المقاصد" / Maqasid), and must return UNKNOWN
rather than guess when unsure. The result is cached on the company row
forever once resolved — this runs once per company, ever, never
fabricated, never re-fetched.
"""

import json
import httpx
from loguru import logger
from app.core.config import settings


def _extract_json_object(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("```")
        t = parts[1] if len(parts) > 1 else t
        if t.lstrip().startswith("json"):
            t = t.lstrip()[4:]
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1:
        t = t[start:end + 1]
    return json.loads(t)


async def ai_lookup_sharia_status(symbol: str, company_name: str) -> str | None:
    """Returns 'COMPLIANT' / 'NON_COMPLIANT' / None (unknown — never guessed)."""
    if not settings.AI_API_KEY:
        return None
    from app.services.usage_tracker import record, can_call
    if not can_call("gemini"):
        logger.warning("Gemini: daily quota reached — skipping Sharia lookup.")
        return None

    prompt = f"""أنت باحث متخصص في الفرز الشرعي للأسهم السعودية (تداول)، وفق معايير معروفة
ومنشورة من جهات فرز شرعي مثل هيئة المقاصد وشركات الفرز الشرعي الأخرى (نسبة الدين إلى
القيمة السوقية أقل من 30%، الودائع والاستثمارات الربوية أقل من 30%، الإيرادات غير
المتوافقة أقل من 5% من إجمالي الإيرادات).

الشركة: {company_name} — الرمز: {symbol} في تداول (السوق السعودي).

بناءً على معرفتك الفعلية بحالة الفرز الشرعي المنشورة لهذه الشركة تحديداً، أجب بصيغة
JSON فقط بدون أي شرح إضافي:
{{"status": "COMPLIANT" أو "NON_COMPLIANT" أو "UNKNOWN", "confidence": "high" أو "medium" أو "low"}}

مهم جداً: إذا لم تكن متأكداً تماماً من الحالة المنشورة الفعلية لهذه الشركة تحديداً،
أجب "UNKNOWN" — لا تخمّن أبداً."""

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 256},
    }
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=body)
        if r.status_code != 200:
            logger.warning(f"AI Sharia lookup: HTTP {r.status_code} — {r.text[:150]}")
            return None
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = _extract_json_object(text)
        status = result.get("status")
        confidence = result.get("confidence", "low")
        if status in ("COMPLIANT", "NON_COMPLIANT") and confidence in ("high", "medium"):
            return status
        return None
    except Exception as e:
        logger.warning(f"AI Sharia lookup failed for {symbol}: {e}")
        return None
