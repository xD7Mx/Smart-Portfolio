"""قراءةُ الرسم بالذكاء — زرُّ «تحليل الرسم» (‏D782 · بأمر المالك 2026-11-21).

قال المالك: «داخل الرسم البيانيّ ضع زرّاً: تحليلُ الرسم — لما أضغط عليه يقرأ هو: الذكاءُ يقرأ الرسمَ فين متوجّه، ويتعرّف على المؤشّرات
الموجودة ويعرف يقرأها نيابةً عنّي… يفهم المستويات ويعرف متى يقرّر البيع ومتى الشراء: عندما يفهم أنّ هذه منطقةُ مقاومة يبدأ يلاحظ البيع
مع رؤية ستوكاستيك RSI في منطقة تشبّعٍ شرائيّ ووصولِ السهم إلى مستوى مقاومة… استنتاجاتٌ واقعية».

فالواجهةُ ترسل لقطةَ ما على الرسم نفسه — صورتَه كما يراها المالك، ومعها أرقامُه: آخرُ الشموع، وقيمُ كلّ مؤشّرٍ ظاهر، والمستوياتُ المرسومة
(فيبوناتشي · خطوطُ الاتجاه والقناة · ‏VWAP · المتوسّطات · القممُ والقيعان)، ولوحتا قوّة الاتجاه والسيولة — لإطارٍ واحدٍ أو لكلّ شاشةٍ في
الشاشات المتعدّدة. ويقرؤها النموذجُ قراءةَ محلّلٍ محترف، وتُحرس القراءةُ قبل العرض:
  · المستوى الذي يعيده يُطابَق بمستوىً مرسومٍ في اللقطة أو بالأسعار المفتاحية (السعرُ الحاليّ · الشمعةُ الأخيرة · أعلى الفترة وأدناها) ±0.35%،
    ويُكتب برقم اللقطة نفسِه — وإلّا أُسقط. ولا يكفي أن يكون السعرُ قد مرّ في شمعةٍ ما: الشموعُ تملأ المدى كلَّه فلا تحرس شيئاً.
  · وكلُّ رقمٍ في نصّه يُطابَق بتلك الأسعار وبقيم المؤشّرات وإعداداتها ونسبِ فيبوناتشي؛ والجملةُ برقمٍ لا أصلَ له تُسقط كلُّها — لا يُعرض اختلاق.
  · ولا مؤشّرَ يُقرأ إلّا ما ظهر على الرسم.
  · وتُخبَّأ القراءةُ ثلاثَ دقائق ببصمة اللقطة (الرمز · الأطر · آخرُ شمعة · السعر) فإعادةُ الضغط لا تكلّف نداءً جديداً.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

from loguru import logger

TTL = 180
# ‏D797 (المالك 2026-11-24: «تحليلُ الرسم لا يستجيب»): قِيس — النموذجُ يجيب البرومبتَ نفسَه في 8–10 ثوانٍ، لكنه يردّ «503 UNAVAILABLE — high demand»
# مرّاتٍ في الدقيقة، وكان الانتظارُ بين المحاولات 15 ثمّ 30 ثانية (قراءةُ إطارين 68.8 ثانية) — وفي الشاشات المتعدّدة أربعةُ أطرٍ بصورها تتجاوز مهلةَ
# الواجهة (120 ثانية) فيبدو الزرُّ ميّتاً. فللقراءة مهلةٌ كلّيةٌ دون مهلة الواجهة، ومحاولاتٌ قصيرةٌ متقاربة، ثمّ النموذجُ الاحتياطيّ إن ضُبط —
# وإن تعذّر قيل لماذا: «مزدحم» أو «أطولُ من المعتاد» — لا «تعذّر» مبهمة.
DEADLINE = 90.0
TOL = 0.0035
BIAS = ("صاعد", "هابط", "عرضي")
KINDS = ("مقاومة", "دعم")
FIELDS = ("headline", "buy", "sell", "invalid", "risk")

PROMPT = """أنت محلّلٌ فنّيٌّ محترفٌ يقرأ رسماً بيانياً لمتداولٍ عربيّ، كما يقرؤه هو على الشاشة. أمامك {what}: صورةُ الرسم كما يراه، ولقطةٌ دقيقةٌ
بأرقامه — الشموعُ الأخيرة [زمن، افتتاح، أعلى، أدنى، إغلاق، حجم]، وقيمُ المؤشّرات الظاهرة على الرسم، والمستوياتُ المرسومة عليه، ولوحتا قوّة
الاتجاه والسيولة.

اقرأ كما يقرأ المحترف: أين يتّجه السعر؟ أين أقربُ مقاومةٍ وأقربُ دعم؟ ماذا تقول المؤشّراتُ عند هذه المستويات (تشبّعٌ شرائيٌّ أو بيعيٌّ في
Stoch RSI، تقاطعاتُ MACD، اتجاهُ CVD، الحجمُ النسبيّ)؟ وإن اجتمع وصولُ السعر إلى مقاومةٍ مع تشبّعٍ شرائيٍّ فذلك منطقةُ حذرٍ وجني ربح، وإن
اجتمع وصولُه إلى دعمٍ مع تشبّعٍ بيعيٍّ وسيولةٍ داخلةٍ فذلك منطقةُ شراءٍ محتملة — بشرط تأكيدٍ تذكره.

القواعدُ الصارمة:
١) لا تذكر رقماً ليس في اللقطة. كلُّ سعرٍ تذكره مستوىً من قائمة «levels» أو من «key_prices» (السعرُ الحاليّ · الشمعةُ الأخيرة · أعلى الفترة
   وأدناها) — لا سعرٌ آخرُ من الشموع ولا هدفٌ تحسبه. ولا تحسب نِسَباً أو مسافاتٍ جديدة.
٢) لا تقرأ إلّا المؤشّراتِ المذكورةَ في «shown».
٣) الاستنتاجاتُ مشروطةٌ واقعية («إن أغلق فوق… فـ…»)، لا وعودَ ولا يقين.
٤) إن تعدّدت الأطرُ وتعارضت فقل ذلك صراحةً ورجّح بالأكبر.
٥) عربيةٌ فصحى موجزة، وأسماءُ المؤشّرات كما هي (Stoch RSI · MACD · CVD · VWAP · EMA).

أعِد JSON فقط بهذا الشكل:
{{"bias": "صاعد" أو "هابط" أو "عرضي",
 "headline": "جملةٌ واحدة: أين يتّجه السعرُ الآن ولماذا",
 "frames": [{{"tf": "الإطار كما في اللقطة", "reading": "جملةٌ عن هذا الإطار"}}],
 "levels": [{{"kind": "مقاومة" أو "دعم", "price": رقمٌ من levels أو key_prices, "from": "اسمُ المستوى كما في اللقطة", "note": "جملةٌ قصيرة"}}],
 "indicators": [{{"name": "اسمُ المؤشّر", "reading": "جملةٌ واحدة"}}],
 "buy": "متى يُنظر في الشراء — شرطٌ بمستوىً من اللقطة",
 "sell": "متى يُنظر في البيع أو جني الربح — شرطٌ بمستوىً من اللقطة",
 "invalid": "ما يُبطل هذه القراءة",
 "risk": "أهمُّ مخاطرةٍ الآن"}}
— والمستوياتُ ستةٌ على الأكثر، الأقربُ إلى السعر أوّلاً.

اللقطة:
"""


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def key_prices(fr: dict) -> dict:
    """الأسعارُ المفتاحيةُ للإطار: السعرُ الحاليّ والشمعةُ الأخيرة وأعلى الفترة وأدناها — وحدها من الشموع ما يُذكر."""
    bars = [b for b in fr.get("bars") or [] if isinstance(b, (list, tuple)) and len(b) >= 5]
    if not bars:
        return {}
    last = bars[-1]
    hi = max((_num(b[2]) for b in bars if _num(b[2]) is not None), default=None)
    lo = min((_num(b[3]) for b in bars if _num(b[3]) is not None), default=None)
    return {"price": _num(fr.get("price")) or _num(last[4]), "last_open": _num(last[1]), "last_high": _num(last[2]), "last_low": _num(last[3]),
            "last_close": _num(last[4]), "period_high": hi, "period_low": lo}


def known_numbers(snap: dict) -> list[float]:
    """أرقامُ اللقطة المسموحُ ذكرُها: الأسعارُ المفتاحية، والمستويات، وقيمُ المؤشّرات وإعداداتُها، ونسبُ فيبوناتشي، وقوّةُ اللوحتين — لا كلُّ الشموع."""
    out: list[float] = []

    def walk(x):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            f = _num(x)
            if f is not None:
                out.append(f)
        elif isinstance(x, str):
            for m in re.findall(r"-?\d+(?:\.\d+)?", x):
                f = _num(m)
                if f is not None:
                    out.append(f)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
    for fr in snap.get("frames") or []:
        walk({k: v for k, v in fr.items() if k not in ("img", "bars")})
        walk(key_prices(fr))
    return out


def _matches(v: float, pool: list[float]) -> float | None:
    for p in pool:
        if p == v or (abs(p) > 1e-9 and abs(v - p) / abs(p) <= TOL) or abs(v - p) <= 0.011:
            return p
    return None


NUM_RE = re.compile(r"(?<![\w.])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])-?\d+(?:\.\d+)?")


def clean_text(s, pool: list[float]) -> str | None:
    """النصُّ إن كان كلُّ رقمٍ فيه من اللقطة — وإلّا ‏None (يُسقط ولا يُعرض)."""
    if not isinstance(s, str):
        return None
    t = " ".join(s.split())[:320]
    if not t:
        return None
    for m in NUM_RE.findall(t):
        v = _num(m.replace(",", ""))
        if v is None:
            continue
        if abs(v) < 10 and float(v).is_integer():          # الأعدادُ الصغيرة (إطارُ «4 ساعات» · «شمعتان») ليست أسعاراً
            continue
        if _matches(v, pool) is None:
            return None
    return t


def level_pool(snap: dict) -> list[float]:
    """أسعارُ المستويات المسموحُ ذكرُها: المستوياتُ المرسومةُ في اللقطة والأسعارُ المفتاحية."""
    pool: list[float] = []
    for fr in snap.get("frames") or []:
        for lv in fr.get("levels") or []:
            f = _num((lv or {}).get("price"))
            if f is not None:
                pool.append(f)
        pool.extend(v for v in key_prices(fr).values() if v is not None)
    return pool


def validate(obj: dict, snap: dict) -> dict:
    """قراءةُ النموذج بعد الحراسة: المستوياتُ برقم اللقطة، والنصوصُ بلا رقمٍ مختلَق، والمؤشّراتُ مما ظهر."""
    pool, lv_pool = known_numbers(snap), level_pool(snap)
    shown = {str(x).lower() for fr in snap.get("frames") or [] for x in (fr.get("shown") or [])}
    if "volume" in shown:                 # ‏D784: الواجهةُ تسمّي الحجمَ «volume» ومفتاحُه هنا «vol» — فكانت قراءةُ الحجم تُسقط دائماً
        shown.add("vol")
    tfs =[str(fr.get("tf_ar") or fr.get("tf") or "") for fr in snap.get("frames") or []]
    out: dict = {"bias": obj.get("bias") if obj.get("bias") in BIAS else "عرضي", "dropped": 0}
    for f in FIELDS:
        t = clean_text(obj.get(f), pool)
        if obj.get(f) and t is None:
            out["dropped"] += 1
        out[f] = t
    frames = []
    for fr in obj.get("frames") or []:
        if not isinstance(fr, dict):
            continue
        t = clean_text(fr.get("reading"), pool)
        if t is None:
            out["dropped"] += 1 if fr.get("reading") else 0
            continue
        tf = str(fr.get("tf") or "")[:24]
        frames.append({"tf": tf if tf in tfs else (tfs[len(frames)] if len(frames) < len(tfs) else tf), "reading": t})
    out["frames"] = frames[:4]
    levels, seen = [], set()
    for lv in obj.get("levels") or []:
        if not isinstance(lv, dict) or lv.get("kind") not in KINDS:
            continue
        v = _num(lv.get("price"))
        m = _matches(v, lv_pool) if v is not None else None
        if m is None or (lv["kind"], round(m, 4)) in seen:
            out["dropped"] += 1
            continue
        seen.add((lv["kind"], round(m, 4)))
        note = clean_text(lv.get("note"), pool)
        if lv.get("note") and note is None:
            out["dropped"] += 1
        levels.append({"kind": lv["kind"], "price": m, "from": str(lv.get("from") or "")[:60], "note": note or ""})
    out["levels"] = levels[:6]
    NAMES = {"stochrsi": ("stoch",), "macd": ("macd",), "cvd": ("cvd",), "vol": ("حجم", "volume", "vol"), "d7m": ("d7m", "vwap", "ema", "فيبو", "fib", "قناة", "اتجاه"),
             "rsi": ("rsi",)}
    inds = []
    for it in obj.get("indicators") or []:
        if not isinstance(it, dict):
            continue
        nm = str(it.get("name") or "")[:40]
        low = nm.lower()
        key = next((k for k, keys in NAMES.items() if any(x in low for x in keys)), None)
        # ‏Stoch RSI يحمل «rsi» فيُقدَّم عليه
        if "stoch" in low:
            key = "stochrsi"
        if key is None or (key != "rsi" and key not in shown):
            continue
        t = clean_text(it.get("reading"), pool)
        if t is None:
            out["dropped"] += 1
            continue
        inds.append({"name": nm, "reading": t})
    out["indicators"] = inds[:8]
    return out


def fingerprint(snap: dict) -> str:
    parts = [str(snap.get("symbol") or "")]
    for fr in snap.get("frames") or []:
        bars = fr.get("bars") or []
        last = bars[-1] if bars else []
        parts.append(f"{fr.get('tf')}|{last[0] if last else ''}|{fr.get('price')}|{','.join(sorted(map(str, fr.get('shown') or [])))}")
    return hashlib.md5("§".join(parts).encode()).hexdigest()[:16]


async def read(snap: dict) -> dict:
    """{ok, reading?, at} — القراءةُ المحروسة، أو ‏ok=False إن تعذّر النموذج (فيُقال «تعذّر»، ولا قراءةَ بديلةٌ مختلَقة)."""
    from datetime import datetime, timezone
    from app.services import cache
    key = "chartread:" + fingerprint(snap)
    hit = cache.get(key)
    if hit is not None:
        return {**hit, "cached": True}
    frames = snap.get("frames") or []
    parts: list = []
    for fr in frames:
        img = fr.get("img")
        if isinstance(img, str) and img.startswith("data:image/jpeg;base64,"):
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img.split(",", 1)[1]}})
    lean = {"symbol": snap.get("symbol"), "name": snap.get("name"), "market": snap.get("market"),
            "frames": [{**{k: v for k, v in fr.items() if k != "img"}, "key_prices": key_prices(fr)} for fr in frames]}
    what = "رسمَ سهمٍ واحدٍ على إطارٍ واحد" if len(frames) == 1 else f"رسمَ سهمٍ واحدٍ على {len(frames)} أطر (شاشاتٌ متعدّدة)"
    parts.append({"text": PROMPT.format(what=what) + json.dumps(lean, ensure_ascii=False, separators=(",", ":"))})
    obj, why = await _ask(parts)
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not isinstance(obj, dict):
        return {"ok": False, "at": at, "reason": why}
    out = {"ok": True, "reading": validate(obj, snap), "at": at}
    cache.set(key, out, TTL)
    return out


async def _ask(parts: list) -> tuple[dict | None, str]:
    """(القراءة، السبب) — النموذجُ الأساسيُّ ثمّ الاحتياطيّ، بمحاولاتٍ قصيرةٍ متقاربة داخل مهلةٍ كلّية (‏DEADLINE).
    السببُ: ‏ok · ‏busy (ازدحامٌ أو حصّة) · ‏timeout (تجاوزت المهلة) · ‏error (غيرُ ذلك) · ‏nokey."""
    import asyncio
    import time
    import httpx
    from app.core.config import settings
    from app.services.ai_content import _extract_json_obj
    from app.services.usage_tracker import can_call, record
    if not settings.AI_API_KEY:
        return None, "nokey"
    models = [settings.AI_MODEL] + [m.strip() for m in (settings.AI_MODEL_FALLBACKS or "").split(",") if m.strip() and m.strip() != settings.AI_MODEL]
    body = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 3000}}
    end = time.monotonic() + DEADLINE
    why = "error"
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(3):
            left = end - time.monotonic()
            if left < 5:
                return None, "timeout"
            if not can_call("gemini"):
                return None, "busy"
            try:
                record("gemini")
                status, data = await _post(url, settings.AI_API_KEY, body, min(60.0, left))
            except httpx.TimeoutException:
                why = "timeout"
                break                                                   # نموذجٌ بطيءٌ الآن ⇒ التالي
            except Exception as e:                                      # noqa: BLE001
                logger.warning("قراءةُ الرسم ({}): {}", model, type(e).__name__)
                why = "error"
                break
            if status in (429, 500, 503):
                why = "busy"
                if attempt < 2:
                    await asyncio.sleep(min(2.0 * (attempt + 1), max(0.0, end - time.monotonic() - 5)))
                    continue
                break                                                   # مزدحمٌ بعد ثلاث ⇒ الاحتياطيّ
            if status != 200:
                logger.warning("قراءةُ الرسم ({}): HTTP {}", model, status)
                why = "error"
                break
            try:
                obj = _extract_json_obj(data["candidates"][0]["content"]["parts"][0]["text"])
            except Exception:                                           # noqa: BLE001
                obj = None
            if isinstance(obj, dict):
                return obj, "ok"
            why = "error"
            break
    return None, why


async def _post(url: str, key: str, body: dict, timeout: float) -> tuple[int, dict]:
    """نداءُ النموذج الواحد — (الحالة، الجسم). منفصلٌ ليُستبدل في الحارس بلا شبكة."""
    import httpx
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(url, params={"key": key}, json=body)
    try:
        data = r.json() if r.status_code == 200 else {}
    except ValueError:
        data = {}
    return r.status_code, data
