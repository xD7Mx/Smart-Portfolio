"""شواهدُ «أرقام» لرأي الذكاء — **بيّنةٌ لا حَكَم**.

## القاعدة التي لا تُخرَق

القرارُ يخرج من محرّك القواعد وحدَه (‏D166)، ورأيُ الذكاء **يشرحه ولا
يحكم**. فهذه الشواهدُ تدخل التوجيهَ مادّةً يُستشهد بها، ولا تُعطى صلاحيةَ
تغيير الحكم ولا مناقضته.

## وماذا لو خالفت «أرقام» قرارَنا؟

بيوتُ الخبرة قد تُوصي بالشراء ودرجتُنا تقول غيرَ ذلك. والحلُّ ليس إخفاءَ
أحدهما ولا مطاوعةَ الأقوى صوتاً، بل **إعلانُ الخلاف بوصفه واقعة**: «أربعُ
توصياتٍ حديثةٍ بالشراء، ودرجتُنا كذا لأنّ كذا». فالمستخدم يرى المشهدَ
كاملاً ويبقى للتطبيق حكمٌ واحد. هذا هو «العقل الواحد»: مُقرِّرٌ واحدٌ
وشهودٌ كُثر، والخلافُ يُقال لا يُطمس.

## ولا يُبطئ الرأي

كلُّ ما هنا يُقرأ من مخزن «أرقام» المبنيّ سلفاً؛ وما لم يكن مخزَّناً
يُترك. ونداءٌ متعذّرٌ يعني شاهداً غائباً لا رأياً متعذّراً.
"""
from __future__ import annotations

import asyncio
from loguru import logger

# مهلةٌ قصيرةٌ عن قصد: الشاهدُ الذي يتأخّر لا يُنتظَر — الرأيُ يخرج بدونه.
_BUDGET_SECONDS = 6.0
_MAX_RECS = 4


async def argaam_evidence(symbol: str) -> dict:
    """{recommendations: [...], ratios: {...}, calendar: [...]} — ما توفّر منها.

    لا ترفع استثناءً أبداً: الغيابُ حالةٌ عادية، ورأيُ الذكاء يعمل بدونها.
    """
    base = str(symbol or "").replace(".SR", "").strip()
    out: dict = {"recommendations": [], "ratios": {}, "calendar": [], "url": None}
    if not base:
        return out

    async def _recs() -> None:
        from app.services.argaam_calendar import fetch_company_recommendations
        r = await fetch_company_recommendations(base)
        rows = [x for x in (r.get("rows") or []) if x.get("verdict")]
        out["recommendations"] = rows[:_MAX_RECS]
        out["url"] = r.get("url") or out["url"]

    async def _ratios() -> None:
        from app.services.argaam_calendar import fetch_company_ratios
        r = await fetch_company_ratios(base)
        out["ratios"] = r.get("ratios") or {}

    async def _cal() -> None:
        from app.services.argaam_calendar import fetch_company_page
        r = await fetch_company_page(base)
        out["calendar"] = (r.get("calendar") or [])[:3]

    try:
        await asyncio.wait_for(
            asyncio.gather(_recs(), _ratios(), _cal(), return_exceptions=True),
            timeout=_BUDGET_SECONDS)
    except asyncio.TimeoutError:
        logger.info(f"أرقام/شواهد {base}: انتهت المهلة — يخرج الرأيُ بما توفّر.")
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"أرقام/شواهد {base}: {type(e).__name__}: {e}")
    return out


_AR_RATIO_LABELS = {
    "car": "كفاية رأس المال", "car_tier1": "كفاية رأس المال الأساسي",
    "npl": "القروض المتعثّرة", "npl_coverage": "تغطية المتعثّرات",
    "combined_ratio": "النسبة المجمّعة", "loss_ratio": "نسبة الخسائر",
    "solvency_margin": "هامش الملاءة",
}


def evidence_lines(ev: dict) -> list[str]:
    """الشواهدُ أسطراً عربيةً تدخل التوجيه — كلُّ سطرٍ حقيقةٌ بمصدرها.

    ولا يُلخَّص حكمُ بيوت الخبرة في كلمةٍ واحدة: تُذكر التوصياتُ كما هي
    بأسمائها وتواريخها. تلخيصُها «إيجابيّ» يصنع حكماً ثانياً في التطبيق،
    وذلك بعينه ما مُنع.
    """
    lines: list[str] = []
    recs = ev.get("recommendations") or []
    if recs:
        parts = []
        for r in recs:
            house = r.get("house") or "بيت خبرة"
            tgt = f" · هدف {r['target']}" if r.get("target") is not None else ""
            when = f" ({r['date']})" if r.get("date") else ""
            parts.append(f"{house}: {r.get('verdict')}{tgt}{when}")
        lines.append("توصياتُ بيوت الخبرة من «أرقام» — بيّنةٌ لا حكم: "
                     + " | ".join(parts))
    ratios = ev.get("ratios") or {}
    known = [f"{_AR_RATIO_LABELS.get(k, k)}: {v}" for k, v in ratios.items()
             if isinstance(v, (int, float))]
    if known:
        lines.append("نِسَبٌ رقابيةٌ منشورةٌ في «أرقام»: " + " · ".join(known[:6]))
    cal = ev.get("calendar") or []
    if cal:
        ev_txt = " | ".join(
            f"{c.get('date') or ''} {c.get('title') or c.get('kind') or ''}".strip()
            for c in cal if c)
        if ev_txt.strip():
            lines.append("مواعيدُ قادمةٌ من مفكرة «أرقام»: " + ev_txt)
    return lines
