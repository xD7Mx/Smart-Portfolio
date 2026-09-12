"""خلاصةُ القوائم — جيمناي أوّلاً، ومحلّلٌ قاعديٌّ تحته (D278).

## ما طلبه المالك

«الخلاصةُ الماليةُ يجب أن تعتمد على ذكاء جيمناي ثمّ ذكاءٍ قاعديٍّ يحلّل
الأرقامَ بشكلٍ واقعيٍّ وليس ديكوراً، وللسنويّ وللربع سنويّ أيضاً.»

## ثلاثُ طبقاتٍ لا واحدة

  ١· **القياسُ أوّلاً**: تُحسب الإشاراتُ من القوائم نفسِها — النموّ،
     وتحويلُ الربح إلى نقد، والهامش، والمديونية، والتغطية، والتدفّق الحرّ.
     هذه أرقامٌ لا رأيٌ فيها، وهي مادّةُ الطبقتين فوقها.
  ٢· **جيمناي يصوغ** من هذه الإشارات سطراً واحداً.
  ٣· **والقاعديُّ يكتب** حين يغيب جيمناي أو يُردّ كلامُه.

## ولماذا يُردّ كلامُ جيمناي

لأنّ نموذجاً لغوياً قد يكتب رقماً لم يُقَس. فكلُّ رقمٍ في سطره **يُطابَق**
بما حُسب، وما لم يُطابِق **يُرَدّ السطرُ كلُّه** ويُكتب القاعديّ. ولا
يُصحَّح نصفُه: جملةٌ نصفُها مقيسٌ ونصفُها مُختلَقٌ أخطرُ من جملةٍ مردودة.

والقاعديُّ ليس ديكوراً: يذكر **الإشارةَ الحاكمة** (أقواها انحرافاً) ويسمّي
ما يخالفها — لا «أداءٌ جيّد» ولا «يُنصح بالمتابعة».
"""
from __future__ import annotations

import re

from loguru import logger

CACHE_TTL = 12 * 60 * 60
MAX_LEN = 190


def _yoy(cur: dict, prev: dict | None, field: str) -> float | None:
    if not prev:
        return None
    a, b = cur.get(field), prev.get(field)
    if a is None or not b:
        return None
    return (a - b) / abs(b) * 100


def signals(periods: list[dict]) -> dict:
    """الإشاراتُ المقيسةُ من القوائم — أرقامٌ لا رأي. وما لا يُحسب يغيب."""
    periods = [p for p in (periods or []) if isinstance(p, dict)]
    if not periods:
        return {}
    cur = periods[-1]
    prev = periods[-2] if len(periods) >= 2 else None
    out: dict = {}

    for key, field in (("نمو_الإيراد", "revenue"),
                       ("نمو_صافي_الربح", "net_income"),
                       ("نمو_التشغيلي", "operating_cash_flow")):
        v = _yoy(cur, prev, field)
        if v is not None:
            out[key] = round(v, 1)

    rev, ni = cur.get("revenue"), cur.get("net_income")
    if rev and ni is not None and rev > 0:
        out["هامش_صافي"] = round(ni / rev * 100, 1)
        if prev and prev.get("revenue") and prev.get("net_income") is not None \
                and prev["revenue"] > 0:
            out["تغير_الهامش"] = round(
                out["هامش_صافي"] - prev["net_income"] / prev["revenue"] * 100, 1)

    ocf = cur.get("operating_cash_flow")
    if ocf is not None and ni:
        out["تحويل_النقد"] = round(ocf / abs(ni) * 100, 1)   # نقدٌ لكلّ ريال ربح
    for key, field in (("التدفق_الحر", "free_cash_flow"),
                       ("المديونية", "debt_ratio"),
                       ("تغطية_الفائدة", "interest_coverage")):
        v = cur.get(field)
        if isinstance(v, (int, float)):
            out[key] = round(float(v), 2)
    if prev and cur.get("debt_ratio") is not None \
            and prev.get("debt_ratio") is not None:
        out["تغير_المديونية"] = round(cur["debt_ratio"] - prev["debt_ratio"], 2)
    return out


# ── الطبقةُ القاعدية ─────────────────────────────────────────────────────
def rule_line(sig: dict, kind: str = "annual") -> str:
    """سطرُ محلّلٍ من الأرقام: الإشارةُ الحاكمةُ وما يخالفها.

    ولا يُقال «أداءٌ جيّد»: تُذكر الحركةُ ومقدارُها وما يناقضها — فيقرأ
    المالكُ **سبباً** لا صفة.
    """
    if not sig:
        return "لا تكفي البنودُ المقروءة لحكمٍ على هذه الفترة."
    per = "الربع" if kind == "quarterly" else "العام"
    bits: list[str] = []

    rev, ni = sig.get("نمو_الإيراد"), sig.get("نمو_صافي_الربح")
    if rev is not None and ni is not None:
        if ni >= 0 and rev >= 0 and ni > rev + 2:
            bits.append(f"ربحٌ ينمو {ni:g}٪ أسرعَ من إيرادٍ {rev:g}٪")
        elif ni < 0 <= rev:
            bits.append(f"إيرادٌ يرتفع {rev:g}٪ وربحٌ يتراجع {abs(ni):g}٪")
        elif ni >= 0 and rev < 0:
            bits.append(f"ربحٌ يرتفع {ni:g}٪ على إيرادٍ منكمشٍ {abs(rev):g}٪")
        else:
            bits.append(f"إيرادٌ {rev:+g}٪ وربحٌ {ni:+g}٪")
    elif ni is not None:
        bits.append(f"صافي الربح {ni:+g}٪")
    elif rev is not None:
        bits.append(f"الإيراد {rev:+g}٪")

    conv = sig.get("تحويل_النقد")
    if conv is not None:
        if conv < 60:
            bits.append(f"والنقدُ التشغيليُّ {conv:g}٪ من الربح — الربحُ ورقيٌّ أكثرَ منه نقداً")
        elif conv > 140:
            bits.append(f"ونقدٌ تشغيليٌّ {conv:g}٪ من الربح")

    fcf = sig.get("التدفق_الحر")
    if isinstance(fcf, (int, float)) and fcf < 0:
        bits.append("والتدفّقُ الحرُّ سالب")

    dch, dr = sig.get("تغير_المديونية"), sig.get("المديونية")
    if dch is not None and abs(dch) >= 2:
        bits.append(f"والمديونيةُ {'ترتفع' if dch > 0 else 'تنخفض'} "
                    f"{abs(dch):g} نقطةً إلى {dr:g}٪")
    cov = sig.get("تغطية_الفائدة")
    if isinstance(cov, (int, float)) and 0 < cov < 3:
        bits.append(f"وتغطيةُ الفائدة {cov:g}× فقط")

    if not bits:
        return f"بنودُ {per} مقروءةٌ بلا حركةٍ تُذكر."
    line = "، ".join(bits[:3]) + "."
    return line[:MAX_LEN]


# ── الطبقةُ الأولى: جيمناي ───────────────────────────────────────────────
_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


def verify(line: str, sig: dict) -> tuple[bool, str]:
    """(أيُقبَل السطر؟، السبب) — كلُّ رقمٍ فيه يُطابَق بما قِيس.

    لا يُصحَّح نصفُ جملة: ما لم يُطابِق يُرَدُّ السطرُ كلُّه.
    """
    if not line or len(line) > MAX_LEN * 1.4:
        return False, "فارغٌ أو أطولُ من سطر"
    if "\n" in line.strip():
        return False, "أكثرُ من سطر"
    known = set()
    for v in sig.values():
        if isinstance(v, (int, float)):
            known.add(round(abs(float(v)), 1))
            known.add(round(abs(float(v))))
    for m in _NUM.finditer(line):
        try:
            v = abs(float(m.group(0).replace(",", ".")))
        except ValueError:
            return False, "رقمٌ غيرُ مقروء"
        if round(v, 1) in known or round(v) in known:
            continue
        return False, f"رقمٌ لم يُقَس: {m.group(0)}"
    return True, "مطابق"


def _prompt(sig: dict, kind: str, name: str | None) -> str:
    facts = "\n".join(f"- {k.replace('_', ' ')}: {v}" for k, v in sig.items())
    per = "الربع الأخير" if kind == "quarterly" else "آخر سنة مالية"
    return (
        "أنت محلّلٌ ماليٌّ مؤسسيّ. اكتب **سطراً واحداً** بالعربية الفصيحة "
        f"يلخّص حالَ {('شركة ' + name) if name else 'الشركة'} في {per}.\n\n"
        "الأرقامُ المقيسة (النِّسَبُ مئويةٌ ما لم يُذكر غيرُها):\n" + facts +
        "\n\nالقواعد الملزمة:\n"
        "- لا تذكر أيَّ رقمٍ غيرِ موجودٍ في القائمة أعلاه، ولا تُقرّبه.\n"
        "- اذكر الإشارةَ الأقوى وما يناقضها إن وُجد.\n"
        "- لا توصيةَ بيعٍ أو شراء، ولا عباراتِ مجاملةٍ أو تحفيز.\n"
        "- سطرٌ واحدٌ لا يتجاوز 25 كلمة، بلا مقدّمةٍ ولا عناوين."
    )


async def ai_line(sig: dict, kind: str, name: str | None) -> str | None:
    """سطرُ جيمناي — أو None (بلا مفتاحٍ · بلا حصّةٍ · تعذُّرٍ · رَدٍّ)."""
    import httpx

    from app.core.config import settings
    if not settings.AI_API_KEY or not sig:
        return None
    from app.services.usage_tracker import can_call, record
    if not can_call("gemini"):
        return None
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}")
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(url, json={
                "contents": [{"parts": [{"text": _prompt(sig, kind, name)}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 160}})
        if r.status_code != 200:
            return None
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:                                        # noqa: BLE001
        logger.debug("خلاصةُ جيمناي تعذّرت: {}: {}", type(e).__name__, e)
        return None
    line = " ".join(str(text or "").split()).strip(" .·-—\"'`*")
    if not line:
        return None
    ok, why = verify(line, sig)
    if not ok:
        logger.info("خلاصةُ جيمناي رُدّت ({}) — يُكتب القاعديّ", why)
        return None
    return line + ("" if line.endswith(".") else ".")


async def brief(periods: list[dict], *, kind: str = "annual",
                name: str | None = None, symbol: str | None = None) -> dict:
    """خلاصةٌ للفترة: جيمناي إن صحّ، وإلّا القاعديّ. ولا تُترك فارغةً."""
    from app.services import cache

    sig = signals(periods)
    if not sig:
        return {"line": rule_line({}, kind), "by": "قاعدي", "signals": {}}
    # مُعرِّفٌ ثابتٌ عبر الإقلاع: `hash()` مملَّحةٌ لكلّ عملية، فمفتاحُها
    # يتغيّر مع كلّ إعادة تشغيلٍ فيُعاد نداءُ جيمناي بلا سبب.
    import hashlib
    fp = hashlib.sha1(repr(sorted(sig.items())).encode()).hexdigest()[:12]
    ck = f"finbrief:{symbol or ''}:{kind}:{fp}"
    hit = cache.get(ck)
    if isinstance(hit, dict):
        return hit
    line = await ai_line(sig, kind, name)
    out = {"line": line or rule_line(sig, kind),
           "by": "جيمناي" if line else "قاعدي", "signals": sig}
    cache.set(ck, out, CACHE_TTL)
    return out
