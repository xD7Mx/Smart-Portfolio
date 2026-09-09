"""
محتوى الذكاء — **صياغةٌ وتفسير، لا توليدُ وقائع**.

الحدّ الفاصل الذي تعمل عليه هذه الوحدة:
  • مسموح: ترجمة، تعريب مسمّى، صياغة نبذة، سرد تحليليّ فوق أرقامٍ موجودة.
  • ممنوع: اختراع واقعةٍ لا مصدر لها — تاريخُ حدث، رقمٌ ماليّ، توزيعٌ
    قادم، اسمُ شركةٍ في مفكرة. وهو الخطّ الأحمر الثاني في الميثاق.

وقد كانت هنا `upcoming_events` تفعل الممنوع: تسأل النموذج أن «يكتب ستّة
مواعيد متوقعة»، فتُعرض في مفكرة المالك وتُكتب في قاعدة البيانات. حُذفت،
ويحرس موضعَها فحصُ `S-AIFACT`.

والموجز الإخباري (`market_news`) يبقى موسوماً `source="AI"` فتُظهر الواجهة
أنه مولَّد — فالوسم هو الفارق بين رأيٍ معلَن واختلاقٍ صامت.
"""

import json
import hashlib
import httpx
from datetime import date
from loguru import logger
from app.core.config import settings
from app.services import cache

def _stable(text: str) -> str:
    """بصمةٌ ثابتة للنصّ — لمفاتيح الذاكرة المؤقّتة.

    كانت `hash(text)`، و`hash()` على النصّ مُملَّحةٌ لكل عملية. وأثرُه هنا
    ليس تكراراً بل **إهدار حصّة**: مفتاحُ الذاكرة يتبدّل مع كل إقلاعٍ
    للحاوية، فلا يُصيب المخزون أبداً بعد إعادة التشغيل ويُدفع نداءُ
    جيمناي من جديد لنفس المدخَل تماماً. والحصّة اليومية محدودة.
    وهو العطب نفسه الذي أفسد مفتاح مخزن المفكرة (D017) في ملفٍّ آخر.
    """
    import hashlib
    return hashlib.blake2s((text or "").encode("utf-8"), digest_size=6).hexdigest()


NEWS_TTL = 12 * 60 * 60     # twice a day is plenty for a digest
EVENTS_TTL = 24 * 60 * 60   # calendar changes slowly


def _extract_json(text: str):
    """Gemini often wraps JSON in ```json fences — strip them robustly."""
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("```")
        t = parts[1] if len(parts) > 1 else t
        if t.lstrip().startswith("json"):
            t = t.lstrip()[4:]
    start = t.find("[")
    end = t.rfind("]")
    if start != -1 and end != -1:
        t = t[start:end + 1]
    return json.loads(t)


async def _generate(prompt: str, cache_key: str, ttl: int) -> list:
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    if not settings.AI_API_KEY:
        return []
    from app.services.usage_tracker import can_call, record
    if not can_call("gemini"):
        logger.warning("Gemini: daily quota reached — skipping call to stay within free tier.")
        return []
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
    }
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=body)
        if r.status_code != 200:
            logger.warning(f"AI content: HTTP {r.status_code} — {r.text[:150]}")
            return []
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        items = _extract_json(text)
        if isinstance(items, list) and items:
            for i, it in enumerate(items):
                it.setdefault("id", i + 1)
                it["source"] = "AI"
            cache.set(cache_key, items, ttl)
            return items
    except Exception as e:
        logger.warning(f"AI content generation failed: {e}")
    return []


async def market_news(symbols: list[str]) -> list:
    today = date.today().isoformat()
    focus = "، مع تركيز خاص على: " + "، ".join(symbols[:10]) if symbols else ""
    prompt = f"""أنت محرر مالي سعودي. التاريخ اليوم {today}.
اكتب موجزاً من 6 عناوين إخبارية واقعية النبرة عن سوق الأسهم السعودية (تداول){focus}.
غطِّ: أداء مؤشر تاسي، قطاع الطاقة، قطاع البنوك، وأخبار شركات كبرى.
أعد النتيجة بصيغة JSON فقط بدون أي شرح، مصفوفة من عناصر بهذا الشكل:
[{{"headline": "العنوان بالعربية", "company": "رمز الشركة أو TASI", "published": "{today}"}}]"""
    return await _generate(prompt, f"ai:news:{today}", NEWS_TTL)


# ── Live TASI market pulse ──────────────────────────────────────────────────
# The market brief is no longer computed on-demand per page view (which made
# every visitor pay a Gemini call and, being cached per-day, never actually
# refreshed intraday). It's now a SCHEDULED pulse: fired half an hour before
# the open (pre-open outlook), then at the top of every trading hour through
# the close — reading the session live and continuously. Gemini writes the
# narrative; a deterministic rule-based text is the always-available fallback.
# The endpoint just serves this cached snapshot, so the page is interactive
# and cheap no matter how many people are watching.

BRIEF_SNAPSHOT_KEY = "market:brief:latest"


def _market_phase(now=None) -> str:
    """Trading phase from the container-local (Riyadh) clock — the same clock
    the movers/snapshot jobs already trust. Tadawul trades 10:00–15:00."""
    from datetime import datetime
    now = now or datetime.now()
    hm = now.hour * 60 + now.minute
    if hm < 10 * 60:
        return "pre_open"     # e.g. the 09:30 pre-open outlook
    if hm < 15 * 60:
        return "intraday"     # live session
    return "post_close"       # wrap-up after the bell


_PHASE_AR = {
    "pre_open": "قبل الافتتاح بنصف ساعة",
    "intraday": "أثناء الجلسة المتداولة",
    "post_close": "بعد إغلاق الجلسة",
}


def _tasi_verb(d: float, phase: str) -> str:
    """وصفٌ متدرّج لحركة المؤشر بحسب حجمها — يتنوّع فلا يبقى نمطاً واحداً."""
    a = abs(d)
    if phase == "pre_open":
        if d > 0.5:  return "تُرجّح المعطيات افتتاحاً إيجابياً بقوة"
        if d > 0.15: return "تميل المؤشرات إلى افتتاحٍ أخضر"
        if d < -0.5: return "تشير المعطيات إلى افتتاحٍ تحت ضغطٍ واضح"
        if d < -0.15:return "تميل المؤشرات إلى افتتاحٍ حذر"
        return "تُرجّح المعطيات افتتاحاً متوازناً قرب التعادل"
    strong = "بقوة" if a > 1.0 else "بوضوح" if a > 0.5 else ""
    if d > 0.15:  return f"يصعد المؤشر {strong}".strip()
    if d < -0.15: return f"يتراجع المؤشر {strong}".strip()
    return "يتحرّك المؤشر متعادلاً قرب خط الافتتاح"


def _rule_brief(tasi: dict | None, brent: dict | None, flow: dict | None,
                phase: str = "intraday", movers: dict | None = None) -> str:
    """قراءة رقمية حيّة للسوق — احتياطي دائم التوفّر حتى لو تعذّر Gemini. يصف
    أحداثاً فعلية: اتساع السوق (صاعد/هابط)، أبرز الرابحين والخاسرين بالاسم،
    القطاعات القائدة والمتراجعة، وأثر النفط والسيولة الأجنبية — بصياغةٍ تتغيّر
    مع الأرقام فلا تبقى نمطاً جامداً."""
    prefix = {
        "pre_open": "قراءة ما قبل الافتتاح — ",
        "intraday": "نبض الجلسة الآن — ",
        "post_close": "حصيلة الإغلاق — ",
    }.get(phase, "")
    sentences: list[str] = []

    # 1) المؤشر + وصف حركته
    if tasi and tasi.get("price") is not None:
        d = tasi.get("change_pct", 0) or 0
        sentences.append(f"{_tasi_verb(d, phase)} عند {tasi['price']:,.2f} نقطة ({d:+.2f}%)")
    else:
        sentences.append("بيانات المؤشر غير متاحة حالياً")

    # 2) اتساع السوق (breadth) — قلب «النبض»
    if movers and movers.get("total"):
        up, dn = movers.get("advancers", 0), movers.get("decliners", 0)
        tot = movers.get("total", 0)
        senti = (movers.get("sentiment") or {}).get("label")
        dom = "بأفضلية واضحة للصاعدة" if up >= dn * 1.5 else \
              "بأفضلية واضحة للهابطة" if dn >= up * 1.5 else "بتوازنٍ بين الطرفين"
        s = f"اتساع السوق {dom}: {up} سهماً صاعداً مقابل {dn} هابطاً من أصل {tot}"
        if senti:
            s += f" (المزاج العام: {senti})"
        sentences.append(s)

        # 3) أبرز رابح وخاسر بالاسم
        g = (movers.get("gainers") or [])[:1]
        l = (movers.get("losers") or [])[:1]
        tops = []
        if g and g[0].get("change_pct") is not None:
            tops.append(f"تصدّر {g[0]['name']} الرابحين ({g[0]['change_pct']:+.2f}%)")
        if l and l[0].get("change_pct") is not None:
            tops.append(f"وتصدّر {l[0]['name']} التراجعات ({l[0]['change_pct']:+.2f}%)")
        if tops:
            sentences.append(" ".join(tops))

        # 4) القطاع الأقوى والأضعف
        secs = [s for s in (movers.get("sectors") or []) if s.get("avg_change_pct") is not None]
        if secs:
            best = max(secs, key=lambda x: x["avg_change_pct"])
            worst = min(secs, key=lambda x: x["avg_change_pct"])
            if best["sector"] != worst["sector"]:
                sentences.append(
                    f"قطاعياً قاد {best['sector']} ({best['avg_change_pct']:+.2f}%) بينما ضغط {worst['sector']} ({worst['avg_change_pct']:+.2f}%)"
                )

    # 5) النفط
    if brent and brent.get("price") is not None:
        bd = brent.get("change_pct", 0) or 0
        oil = "يدعم الطاقة" if bd > 0.3 else "يضغط على الطاقة" if bd < -0.3 else "مستقر"
        sentences.append(f"برنت عند {brent['price']:,.2f}$ ({bd:+.2f}%) {oil}")

    # 6) السيولة الأجنبية
    if flow:
        sentences.append(
            f"وصافي تداول الأجانب الأسبوعي {'تدفقٌ داخل' if flow['direction'] == 'in' else 'تدفقٌ خارج'} بقيمة {flow['amount']:,.0f} ريال"
        )

    return prefix + ("، ".join(sentences) + ".")


def _movers_context(movers: dict | None) -> str:
    """صياغة معطيات اتساع السوق وأبرز حركاته لتغذية Gemini بأحداثٍ حقيقية."""
    if not movers or not movers.get("total"):
        return "اتساع السوق: غير متاح بعد"
    lines = [f"اتساع السوق: {movers.get('advancers',0)} صاعد · {movers.get('decliners',0)} هابط · {movers.get('unchanged',0)} ثابت (من {movers.get('total',0)} سهماً)"]
    senti = movers.get("sentiment") or {}
    if senti.get("label"):
        lines.append(f"مزاج السوق (من الاتساع): {senti['label']} ({senti.get('score','')}٪ صاعد)")
    g = ", ".join(f"{x['name']} {x['change_pct']:+.2f}%" for x in (movers.get("gainers") or [])[:3] if x.get("change_pct") is not None)
    l = ", ".join(f"{x['name']} {x['change_pct']:+.2f}%" for x in (movers.get("losers") or [])[:3] if x.get("change_pct") is not None)
    if g: lines.append(f"أبرز الرابحين: {g}")
    if l: lines.append(f"أبرز الخاسرين: {l}")
    secs = [s for s in (movers.get("sectors") or []) if s.get("avg_change_pct") is not None]
    if secs:
        secs_sorted = sorted(secs, key=lambda x: x["avg_change_pct"], reverse=True)
        top = ", ".join(f"{s['sector']} {s['avg_change_pct']:+.2f}%" for s in secs_sorted[:2])
        bot = ", ".join(f"{s['sector']} {s['avg_change_pct']:+.2f}%" for s in secs_sorted[-2:])
        lines.append(f"أقوى القطاعات: {top} · أضعفها: {bot}")
    if movers.get("market_liquidity"):
        lines.append(f"سيولة السوق (قيمة التداول): {movers['market_liquidity']:,.0f} ريال")
    return "\n".join(lines)


async def market_brief(tasi: dict | None, brent: dict | None, flow: dict | None,
                       headlines: list[str], phase: str = "intraday", slot: str | None = None,
                       movers: dict | None = None) -> str | None:
    """A short, professional Arabic brief about the Saudi market (TASI). Phase-
    aware (pre-open outlook / live session read / post-close wrap-up) and cached
    per hourly SLOT so each scheduled run through the session produces a fresh
    reading instead of one frozen daily text."""
    from datetime import datetime
    slot = slot or f"{datetime.now():%Y-%m-%d:%H}"
    key = f"ai:brief:{slot}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    if not settings.AI_API_KEY:
        return None
    def line(name, d):
        if not d:
            return f"{name}: غير متاح"
        return f"{name}: {d.get('price')} ({d.get('change_pct', 0):+.2f}%)"
    flow_line = (
        f"صافي تداول الأجانب الأسبوعي: {'تدفق داخل' if flow['direction'] == 'in' else 'تدفق خارج'} {flow['amount']:,.0f} ريال"
        if flow else "صافي تداول الأجانب: غير متاح"
    )
    ctx = "؛ ".join([line("مؤشر تاسي", tasi), line("برنت", brent), flow_line])
    breadth = _movers_context(movers)
    news = ("\nأبرز العناوين:\n- " + "\n- ".join(headlines[:6])) if headlines else ""
    phase_ar = _PHASE_AR.get(phase, "أثناء الجلسة")
    phase_task = {
        "pre_open": "الوقت الآن قبل افتتاح تداول بنحو نصف ساعة. اكتب استشرافاً مهنياً موجزاً للجلسة المقبلة استناداً إلى إغلاق الأمس واتساع السوق وسعر برنت وصافي تدفقات الأجانب — دون الجزم بنتيجة الجلسة.",
        "intraday": "الجلسة مفتوحة الآن ونسبة تغيّر المؤشر أدناه هي حركته الحيّة منذ الافتتاح. اكتب قراءة لحظية حيّة تصف ما يجري فعلاً: هل السوق واسع الصعود أم الهبوط، مَن يقود ومَن يضغط.",
        "post_close": "أُغلقت الجلسة للتو. اكتب حصيلة مهنية تصف كيف انتهت الجلسة واتساعها وأبرز محرّكاتها.",
    }.get(phase, "")
    prompt = f"""أنت كبير محللي الأسواق في غرفة تداول سعودية — نبرتك مهنية رصينة وواثقة، موضوعية بلا مبالغة، حيّة تصف أحداث السوق الفعلية لا عبارات عامة.
التاريخ {date.today().isoformat()}. الحالة: {phase_ar}. {phase_task}
اعتمد حصرياً على هذه المعطيات الحقيقية:
• المؤشرات: {ctx}
• {breadth}{news}
اكتب تحليلاً موجزاً **في حدود خمسين كلمة** (٤٠–٥٠ كلمة، لا تتجاوزها). والأرقام معروضةٌ للمالك في البطاقة نفسها، فلا تُعِد سردها: مهمّتك أن تقول **سببَ** ما حدث ومعناه — خبرٌ أو نتائج أو قرار أو حركة نفط أو سيولة أجنبية تفسّر اتجاه المؤشر واتساع السوق وقيادة القطاعات. اذكر الرقم فقط حين يكون هو الحجّة. لا تذكر محفظة المستخدم ولا توصيات شراء/بيع. أعد نصاً عربياً واحداً بلا عناوين ولا تعداد."""
    from app.services.usage_tracker import can_call, record
    if not can_call("gemini"):
        logger.warning("Gemini: daily quota reached — skipping call to stay within free tier.")
        return None
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.4, "maxOutputTokens": 512}}
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}")
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=body)
        if r.status_code == 200:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                cache.set(key, text, 90 * 60)  # one slot's lifetime — next run writes a fresh read
                return text
    except Exception as e:
        logger.warning(f"market_brief failed: {e}")
    return None


def get_market_brief_snapshot() -> dict | None:
    """The last computed pulse snapshot — served instantly by the /summary
    endpoint (no live Gemini call per view). Survives restarts via lastgood."""
    snap = cache.get(BRIEF_SNAPSHOT_KEY)
    if snap is not None:
        return snap
    try:
        from app.services import lastgood
        return lastgood.load("market:brief", max_age_seconds=24 * 3600)
    except Exception:
        return None


async def refresh_market_brief(db=None) -> dict:
    """Compute & cache one TASI pulse. Scheduled pre-open (09:30) and at the top
    of every trading hour (10:00–15:00) so the market is read continuously from
    open to close. Gemini writes the narrative; rule-based text is the fallback.
    Also runs as the endpoint's first-view fallback before any scheduled run."""
    import asyncio as _aio
    from datetime import datetime
    from app.services.market_data import market_service
    from app.services.news_fetcher import fetch_weekly_foreign_flow
    from app.services import lastgood

    tasi, brent, flow = await _aio.gather(
        market_service.get_price("^TASI.SR"),
        market_service.get_price("BZ=F"),
        fetch_weekly_foreign_flow(),
    )
    tasi = tasi or lastgood.load("market:tasi", max_age_seconds=7 * 24 * 3600)
    brent = brent or lastgood.load("market:brent", max_age_seconds=7 * 24 * 3600)
    flow = flow or lastgood.load("market:flow", max_age_seconds=21 * 24 * 3600)

    headlines: list[str] = []
    if db is not None:
        try:
            from sqlalchemy import select
            from app.models.market import MarketNews
            rows = (await db.execute(
                select(MarketNews).order_by(MarketNews.published_at.desc().nullslast()).limit(6)
            )).scalars().all()
            headlines = [n.headline for n in rows]
        except Exception:
            pass

    # اتساع السوق وأبرز حركاته — قلب «النبض». من نفس مسح السوق المجدول
    # (لا استدعاءات إضافية)، مع احتياطٍ من آخر إغلاق محفوظ على القرص.
    movers = None
    try:
        from app.services.market_movers import get_cached_market_movers
        movers = get_cached_market_movers() or lastgood.load("market:movers", max_age_seconds=4 * 24 * 3600)
    except Exception:
        pass

    now = datetime.now()
    phase = _market_phase(now)
    slot = f"{now:%Y-%m-%d}:{now.hour:02d}"
    summary, source = _rule_brief(tasi, brent, flow, phase, movers), "rule"
    try:
        ai = await market_brief(tasi, brent, flow, headlines, phase, slot, movers)
        if ai:
            summary, source = ai, "AI"
    except Exception as e:
        logger.warning(f"refresh_market_brief AI step failed: {e}")

    snap = {
        "summary": summary, "source": source, "phase": phase,
        "tasi": tasi, "brent": brent, "flow": flow, "headlines": headlines,
        "generated_at": now.isoformat(),
    }
    cache.set(BRIEF_SNAPSHOT_KEY, snap, 12 * 60 * 60)
    try:
        lastgood.save("market:brief", snap)
    except Exception:
        pass
    logger.info(f"Market pulse refreshed ({phase}, source={source}).")
    return snap


async def governance_narrative(overall_score: int, label: str, holdings: list[dict],
                               sectors: list[dict], all_compliant: bool) -> str | None:
    """A short, POSITIVE-leaning Arabic paragraph describing the portfolio's
    overall governance — leads with strengths, mentions balance/compliance,
    and closes with at most one constructive improvement lever. Cached by a
    fingerprint of the scores so it only calls Gemini when the picture
    actually changed. Returns None on any failure so the caller falls back
    to the deterministic rule-based narrative."""
    scored = [h for h in holdings if h.get("finance_score") is not None]
    fp = "|".join(f"{h['symbol']}:{round(h['finance_score'])}" for h in sorted(scored, key=lambda x: x['symbol']))
    key = f"ai:gov_narrative:{overall_score}:{hashlib.sha1(fp.encode()).hexdigest()[:10]}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    if not settings.AI_API_KEY or not scored:
        return None
    top = sorted(scored, key=lambda h: -h["finance_score"])[:5]
    holds_txt = "، ".join(f"{h['name']} {round(h['finance_score'])}/100 (وزن {h['weight_pct']}%)" for h in top)
    sect_txt = "، ".join(f"{s['sector']} {s['weight_pct']}%" for s in sectors[:4])
    prompt = f"""أنت مستشار حوكمة محافظ استثمارية سعودي محترف. صِف الحالة العامة لحوكمة هذه المحفظة في **سطر واحد فقط** (جملة أو جملتين قصيرتين، لا أكثر) بنبرة إيجابية بنّاءة تُبرز القوة والاستقرار.
الدرجة الكلية: {overall_score}/100 ({label}).
أقوى المراكز: {holds_txt}.
التوزيع القطاعي: {sect_txt}.
التوافق الشرعي: {"جميع المراكز المُقيَّمة متوافقة شرعياً" if all_compliant else "توجد مراكز غير متوافقة شرعياً"}.
سطر واحد موجز فقط — لا قائمة، لا عناوين، لا تعداد أرقام، ولا أكثر من جملتين قصيرتين."""
    from app.services.usage_tracker import can_call, record
    if not can_call("gemini"):
        logger.warning("Gemini: daily quota reached — governance narrative skipped.")
        return None
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.5, "maxOutputTokens": 160}}
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}")
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=body)
        if r.status_code == 200:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                cache.set(key, text, 12 * 60 * 60)
                return text
    except Exception as e:
        logger.warning(f"governance_narrative failed: {e}")
    return None


async def evaluation_narrative(overall_score: int, div_score: int, risk_score: int,
                               perf_score: int, weekly: dict | None = None) -> str | None:
    """One-line evaluation narrative for تقييم الذكاء — the SAME pattern as the
    governance score's narrative (governance_narrative): a single positive,
    professional Arabic line from Gemini, cached by a fingerprint of the scores,
    None on failure so the caller falls back to the deterministic rule text."""
    wk = ""
    if weekly:
        bits = []
        if weekly.get("portfolio_week_pct") is not None:
            bits.append(f"تغيّر الأسبوع {weekly['portfolio_week_pct']:+.2f}%")
        if weekly.get("outperformance_pct") is not None:
            bits.append(f"فارق الأداء عن تاسي {weekly['outperformance_pct']:+.2f} نقطة")
        if weekly.get("total_return_pct") is not None:
            bits.append(f"العائد المحقّق من رأس المال المدفوع منذ التأسيس {weekly['total_return_pct']:+.2f}%")
        wk = " · ".join(bits)
    key = f"ai:eval_line:{overall_score}:{div_score}:{risk_score}:{perf_score}:{hashlib.sha1(wk.encode()).hexdigest()[:8]}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    if not settings.AI_API_KEY:
        return None
    prompt = f"""أنت مستشار محافظ استثمارية سعودي محترف. صِف الحالة العامة لهذه المحفظة في **سطر واحد فقط** (جملة أو جملتين قصيرتين، لا أكثر) بنبرة إيجابية بنّاءة تُبرز القوة والاستقرار.
التقييم العام: {overall_score}/100. التوازن: {div_score}/100. إدارة المخاطر: {risk_score}/100. الأداء: {perf_score}/100.{(' مؤشرات حقيقية: ' + wk + '.') if wk else ''}
سطر واحد موجز فقط — لا قائمة، لا عناوين، لا تعداد أرقام، ولا أكثر من جملتين قصيرتين."""
    from app.services.usage_tracker import can_call, record
    if not can_call("gemini"):
        logger.warning("Gemini: daily quota reached — evaluation narrative skipped.")
        return None
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.5, "maxOutputTokens": 160}}
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}")
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=body)
        if r.status_code == 200:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                cache.set(key, text, 12 * 60 * 60)
                return text
    except Exception as e:
        logger.warning(f"evaluation_narrative failed: {e}")
    return None


async def economic_news() -> list:
    """Macro news moving the Saudi market — rates, Fed, OPEC, foreign flows,
    IPOs, key indicators. Cached 12h (a few Gemini calls a day, not per view)."""
    today = date.today().isoformat()
    prompt = f"""أنت محرر اقتصادي متخصص في السوق السعودي. التاريخ اليوم {today}.
اكتب 6 عناوين إخبارية اقتصادية كلية مؤثرة على سوق الأسهم السعودية، تغطي:
قرارات الفائدة، اجتماعات الفيدرالي، أخبار أوبك والنفط، تدفقات الصناديق الأجنبية،
تغيّر نسب الملكية الأجنبية، الاكتتابات الجديدة، والمؤشرات الاقتصادية المهمة.
أعد النتيجة بصيغة JSON فقط بدون شرح، مصفوفة بهذا الشكل:
[{{"headline": "العنوان بالعربية", "category": "الفئة (فائدة/نفط/صناديق/اكتتاب/مؤشرات)", "impact": "إيجابي أو سلبي أو محايد", "published": "{today}"}}]"""
    return await _generate(prompt, f"ai:econ:{today}", NEWS_TTL)


# ══ حُذفت `upcoming_events` ══
# كانت تسأل النموذج: «اكتب 6 مواعيد **متوقعة** للأسابيع الأربعة القادمة»
# فيخترع أسماء شركاتٍ ورموزاً وتواريخ لا مصدر لها، ثم تُعرض في مفكرة
# المالك وتُكتب في قاعدة البيانات — فتصير بعد ذلك غير مميَّزة عن الحقيقيّ.
#
# والذكاء في هذا التطبيق يُستعمل للصياغة والترجمة والتفسير — أي على
# **بيانات موجودة**. أمّا توليد الوقائع نفسها (تواريخ، أرقام، أحداث) فهو
# الخطّ الأحمر الثاني في الميثاق: «ما لا مصدر له يُقال عنه غير متوفّر».
# ويحرسه الآن فحصُ S-AIFACT.


ANALYSIS_TTL = 24 * 60 * 60  # portfolio analysis refreshes daily


def _extract_json_obj(text: str):
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


async def _generate_obj(prompt: str, cache_key: str, ttl: int) -> dict | None:
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    if not settings.AI_API_KEY:
        return None
    from app.services.usage_tracker import can_call, record
    if not can_call("gemini"):
        logger.warning("Gemini: daily quota reached — skipping call to stay within free tier.")
        return None
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        # Was hardcoded to 2048 regardless of AI_MAX_TOKENS — too small for
        # stock_opinion's 5-section response (sentiment + technical +
        # valuation + fundamentals + dividends + summary), which reliably
        # got truncated mid-JSON and failed to parse every single time,
        # while portfolio_evaluation's much shorter 5-field response fit
        # fine in the same limit — that's why only this one call looked
        # "broken" while other AI features worked.
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": settings.AI_MAX_TOKENS},
    }
    try:
        record("gemini")
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=body)
        if r.status_code != 200:
            logger.warning(f"AI analysis: HTTP {r.status_code} — {r.text[:150]}")
            return None
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        obj = _extract_json_obj(text)
        if isinstance(obj, dict) and obj:
            obj["source"] = "AI"
            cache.set(cache_key, obj, ttl)
            return obj
    except Exception as e:
        logger.warning(f"AI analysis generation failed: {e}")
    return None


def _portfolio_fingerprint(holdings: list[dict]) -> str:
    """A short hash of the portfolio's actual composition (which symbols,
    how many shares of each) — NOT just len(holdings). Two different
    portfolios can easily have the same holding COUNT (sell one company,
    buy another; or swap positions) while being completely different in
    substance, and a count-only cache key would then serve a stale Gemini
    narrative that still names a company no longer held. Rounding qty
    avoids busting the cache on trivial live-price refreshes that don't
    change the actual position."""
    import hashlib
    sig = "|".join(sorted(f"{h['symbol']}:{h['qty']:.2f}" for h in holdings))
    return hashlib.md5(sig.encode()).hexdigest()[:10]


def _portfolio_context(holdings: list[dict], cash: float) -> str:
    total_mv = sum(h["mv"] for h in holdings) + cash
    lines = [
        f"- {h['name']} ({h['symbol']}): {h['qty']:.0f} سهم، متوسط تكلفة {h['avg']:.2f}، "
        f"قيمة سوقية {h['mv']:.0f} ({(h['mv'] / total_mv * 100) if total_mv else 0:.1f}% من المحفظة)، "
        f"ربح/خسارة {h['pnl']:+.0f}، قطاع {h['sector'] or 'غير محدد'}"
        for h in holdings
    ]
    sectors: dict = {}
    for h in holdings:
        s = h.get("sector") or "غير محدد"
        sectors[s] = sectors.get(s, 0) + h["mv"]
    sector_lines = [f"- {s}: {(v / total_mv * 100) if total_mv else 0:.1f}%" for s, v in sorted(sectors.items(), key=lambda x: -x[1])]
    return (
        "مكونات المحفظة:\n" + "\n".join(lines)
        + f"\nالسيولة النقدية المتاحة: {cash:.0f} ({(cash / total_mv * 100) if total_mv else 0:.1f}% من المحفظة)"
        + "\n\nالوزن القطاعي:\n" + "\n".join(sector_lines)
    )


def _weekly_story(weekly: dict | None) -> str:
    """Render the real weekly-momentum numbers into a compact Arabic context
    block for the prompts — only the fields we actually computed, never a blank
    placeholder that invites the model to invent one."""
    if not weekly:
        return ""
    lines = []
    if weekly.get("portfolio_week_pct") is not None:
        lines.append(f"تغيّر عائد المحفظة خلال الأسبوع الماضي: {weekly['portfolio_week_pct']:+.2f} نقطة مئوية (مقياس أداء صافٍ لا يتأثر بالإيداع أو البيع)")
    if weekly.get("tasi_week_pct") is not None:
        lines.append(f"تغيّر مؤشر تاسي خلال الأسبوع نفسه: {weekly['tasi_week_pct']:+.2f}%")
    if weekly.get("outperformance_pct") is not None:
        d = weekly["outperformance_pct"]
        lines.append(f"فارق أداء المحفظة عن السوق هذا الأسبوع: {d:+.2f} نقطة مئوية ({'تفوّق على المؤشر' if d >= 0 else 'دون المؤشر'})")
    if weekly.get("total_return_pct") is not None:
        lines.append(f"المحصول التراكمي للمحفظة (توزيعات + حصيلة البيع الرابحة + منحة) من رأس المال المدفوع منذ التأسيس: {weekly['total_return_pct']:+.2f}%")
    return ("\n\nمؤشرات الأداء الأسبوعية الحقيقية:\n- " + "\n- ".join(lines)) if lines else ""


async def portfolio_evaluation(holdings: list[dict], cash: float, weekly: dict | None = None) -> dict | None:
    """Diversification/risk/performance scores + a concise, professional,
    honestly-optimistic Arabic summary. Cached 24h (keyed on composition +
    weekly momentum so it refreshes when the week's story changes)."""
    if not holdings:
        return None
    ctx = _portfolio_context(holdings, cash)
    week = _weekly_story(weekly)
    wk_fp = str(weekly.get("portfolio_week_pct")) if weekly else "-"
    key = f"ai:eval:{date.today().isoformat()}:{_portfolio_fingerprint(holdings)}:{wk_fp}"
    prompt = f"""أنت مستشار محافظ استثمارية سعودي محترف — نبرتك أنيقة واثقة وإيجابية بصدق (تُبرز القوة والتقدّم دون مبالغة أو تجميل، وتذكر الضعف بلباقة عند وجوده).
حلّل المحفظة التالية اعتماداً حصرياً على الأرقام المعطاة أدناه، بدون افتراضات خارجية:
{ctx}{week}

قيّم كل بُعد بناءً على معيار واضح:
- diversification_score: يُخفَض إذا تجاوز أي قطاع واحد 30% من المحفظة، أو تركزت في أقل من 5 شركات.
- risk_score: يعكس التركّز القطاعي + نسبة السيولة (سيولة أقل من 5% ترفع المخاطر، أكثر من 30% تدل على تردد استثماري).
- performance_score: يعكس الربح/الخسارة الفعلي الحالي فقط، وليس توقعات مستقبلية.
- overall_score: متوسط موزون للثلاثة أعلاه.

أعد النتيجة بصيغة JSON فقط بدون أي شرح خارج الكائن، كائن بهذا الشكل بالضبط:
{{"diversification_score": 0-100, "risk_score": 0-100, "performance_score": 0-100, "overall_score": 0-100,
"summary": "ملخص عربي مختصر (جملتان إلى ثلاث) بنبرة احترافية إيجابية صادقة، يفتتح بأبرز نقطة قوة أو تقدّم أسبوعي حقيقي (ارتفاع العائد أو التفوّق على المؤشر إن وُجد)، ويذكر أرقاماً محددة من المعطيات — لا عبارات عامة بلا دليل رقمي"}}"""
    return await _generate_obj(prompt, key, ANALYSIS_TTL)


async def portfolio_risk(holdings: list[dict], cash: float) -> dict | None:
    """Risk level + concrete Arabic risk items. Cached 24h."""
    if not holdings:
        return None
    ctx = _portfolio_context(holdings, cash)
    key = f"ai:risk:{date.today().isoformat()}:{_portfolio_fingerprint(holdings)}"
    prompt = f"""أنت محلل مخاطر مالية للسوق السعودي. حلّل مخاطر هذه المحفظة:
{ctx}
أعد النتيجة بصيغة JSON فقط بدون أي شرح، كائن بهذا الشكل بالضبط:
{{"overall_risk_level": "LOW أو MEDIUM أو HIGH",
"summary": "ملخص عربي من جملتين",
"risks": [{{"description": "وصف الخطر بالعربية"}}]}}
اذكر 3 إلى 5 مخاطر ملموسة (تركّز، قطاع واحد، سيولة، تقلب...)."""
    return await _generate_obj(prompt, key, ANALYSIS_TTL)


async def stock_opinion(symbol: str, name: str, analysis: dict,
                        headlines: list[str] | None = None,
                        evidence_lines_ar: list[str] | None = None) -> dict | None:
    """One-click "رأي الذكاء" card for a single stock — a fixed-template
    prompt (only symbol/data/headlines change) grounded ONLY in our own real,
    already-computed numbers (price, technical indicators, fundamentals,
    dividend yield) plus real stored headlines for that company. Never
    invents figures we don't actually have (e.g. no fake "17 analysts"
    count) — explicitly instructed to omit anything not given. Cached 24h
    per symbol."""
    # نسخةُ التوجيه في المفتاح: تغييرُ التوجيه يُبطل رأياً مخزَّناً كُتب
    # قبله — وإلّا بقي رأيُ اليوم يناقض القرارَ رغم إصلاح التوجيه.
    # نسخةُ التوجيه ‎v3: دخلت شواهدُ «أرقام»، فرأيٌ مخزَّنٌ كُتب قبلها لا
    # يعرفها — والمفتاحُ القديم كان سيُبقيه يوماً كاملاً.
    key = f"ai:opinion:v3:{date.today().isoformat()}:{symbol}"
    f = analysis.get("fundamentals") or {}
    t = analysis.get("technical") or {}
    lines = [
        f"السعر الحالي: {analysis.get('price')} ({analysis.get('change_pct', 0):+.2f}% اليوم)",
        f"نطاق اليوم: {analysis.get('day_low')} - {analysis.get('day_high')}" if analysis.get("day_low") else "",
        f"RSI: {t.get('rsi')}" if t.get("rsi") is not None else "",
        f"الدعم/المقاومة (60 جلسة): {t.get('support')} / {t.get('resistance')}" if t.get("support") else "",
        f"الاتجاه الفني: {t.get('trend') or t.get('verdict') or '—'}",
        # كان هذا السطر يقول للنموذج «متوسط تقدير المحللين» ويُمرّر إليه
        # **متوسطاً متحرّكاً للسعر**. فيبني رأيه على وصفٍ كاذب للرقم —
        # ويخرج التناقض الذي رآه المالك بين الشاشات. صار كلٌّ باسمه:
        f"متوسط السعر المتحرّك (SMA200): {t.get('mean_basis')} ({t.get('pct_from_avg')}%)" if t.get("mean_basis") else "",
        # ══ السعرُ العادل = متوسّطُ تقديرات بيوت الخبرة ══ (بأمر المالك)
        # ويُقرأ من `analysis` لا من `fundamentals`، فيكون الرقمُ الذي
        # يكتبه النموذجُ هو عينَ الرقم المعروض في بطاقة صفحة الشركة.
        f"هدف المحللين (متوسط تقديرات بيوت الخبرة): "
        f"{analysis.get('fair_value')}"
        + (f" · الفجوة {analysis.get('fair_value_upside_pct')}%"
           if analysis.get("fair_value_upside_pct") is not None else "")
        if analysis.get("fair_value") is not None else "",
        f"مكرر الربحية P/E: {f.get('pe_ratio')}" if f.get("pe_ratio") else "",
        f"نمو ربحية السهم EPS: {f.get('earnings_growth')}%" if f.get("earnings_growth") is not None else "",
        f"العائد على حقوق المساهمين ROE: {f.get('roe')}%" if f.get("roe") is not None else "",
        f"هامش الربح: {f.get('profit_margin')}%" if f.get("profit_margin") is not None else "",
        f"عائد التوزيعات: {f.get('dividend_yield')}%" if f.get("dividend_yield") is not None else "",
    ]
    ctx = "\n".join(l for l in lines if l)
    news_ctx = ("\n\nأحدث الأخبار الحقيقية المتوفرة عن السهم:\n- " + "\n- ".join(headlines[:5])) if headlines else ""
    # ══ شواهدُ «أرقام» — بيّنةٌ لا حَكَم ══ (D218)
    # مصدرٌ محدَّثٌ صار متاحاً (توصياتُ بيوت الخبرة · نِسَبٌ رقابية · مفكرة).
    # يدخل مادّةً يُستشهد بها، ولا يُعطى صلاحيةَ تغيير القرار: المُقرِّرُ
    # واحدٌ والشهودُ كُثر.
    argaam_ctx = (("\n\nشواهدُ من «أرقام» (بيانات منشورة، لا أحكام):\n- "
                   + "\n- ".join(evidence_lines_ar))
                  if evidence_lines_ar else "")

    # ══ العقلُ الثالثُ يُخبَر بالقرار ولا يخترعه ══ (D166)
    # كان التوجيهُ يسأل النموذجَ «هل أنت متفائل أم متشائم؟» ولا يذكر له
    # قرارَ التطبيق ولا مرّةً واحدة — فيجتهد اجتهاداً مستقلّاً بجوار
    # محرّكٍ حاسم، ولو وافقه فبالمصادفة. فخرج للمالك «شراء» وأسبابُه
    # كلُّها هبوطٌ فنّيٌّ وماليّ.
    # فيُعطى القرارَ وسببَه ويُلزَم بشرحهما: يفسّر ولا يحكم، ونبرتُه تتبع
    # الحكم. والقرارُ يبقى مُنتَجاً في محرّك القواعد — النموذجُ لا يملك
    # تغييرَه ولا مناقضتَه.
    _dec = (analysis.get("decision") or {})
    _dlabel = _dec.get("label") or _dec.get("raw")
    _dreason = _dec.get("reason")
    decision_ctx = ""
    tone_rule = ""
    if _dlabel:
        decision_ctx = (f"\n\nقرارُ التطبيق النهائيّ لهذه الورقة: **{_dlabel}**"
                        + (f"\nسببُه: {_dreason}" if _dreason else ""))
        tone_rule = (
            f"\n- **القرارُ أعلاه نهائيّ وصادرٌ عن محرّك قواعد التطبيق — لا "
            f"تناقضه ولا تقترح قراراً غيره ولا تعيد تقييمه.** مهمّتك أن "
            f"تشرحه بالأرقام المعطاة.\n"
            f"- ويجب أن يتّسق `sentiment_label` وكلُّ نقطةٍ تكتبها مع «{_dlabel}»: "
            f"فلا يكون الحكمُ شراءً وأسبابُك كلُّها هبوطٌ فنّيٌّ وماليّ، ولا العكس. "
            f"وإن كانت الأرقامُ مختلطةً فقُل ذلك صراحةً واذكر أيَّها رجّح الكفّة.")

    prompt = f"""أنت محلل مالي سعودي متزن وموضوعي.
اشرح لقارئٍ غيرِ متخصّص **لماذا** خرج التطبيقُ بهذا القرار عن {name}:{symbol}: حلل أساسياته (مكرر الربحية P/E، نمو ربحية السهم EPS) باستخدام المقاييس الرئيسية أدناه، وراجع إجماع هدف المحللين، ولاحظ أي إشارات فنية مهمة من المؤشرات الفنية.{decision_ctx}

المعطيات الحقيقية المتاحة فقط (لا تستخدم أي رقم من خارجها):
{ctx}{news_ctx}{argaam_ctx}

قواعد صارمة:
- لا تخترع أي رقم أو إحصائية غير موجودة أعلاه (مثل عدد المحللين أو أهداف أسعار غير مذكورة) — إن لم تُعطَ معلومة فاحذف القسم الخاص بها أو اذكر "غير متاح".
- اربط كل نقطة برقم فعلي من المعطيات أعلاه.
- كن متزناً: اذكر نقاط القوة والضعف معاً، لا تصاغة تسويقية.
- شواهدُ «أرقام» **بيّنةٌ لا حكم**: استشهد بها بأسمائها وتواريخها، ولا تجعلها قراراً ثانياً. وإن خالفت توصياتُ بيوت الخبرة قرارَ التطبيق فقُل ذلك صراحةً بوصفه واقعة — «توصياتٌ حديثةٌ بالشراء بينما قرارُنا كذا لأنّ كذا» — ولا تُخفِ أحدهما ولا تُطاوع الأعلى صوتاً.{tone_rule}

أعد النتيجة بصيغة JSON فقط بدون أي شرح خارج الكائن، بهذا الشكل بالضبط:
{{
  "sentiment_label": "متفائل بحذر / متفائل / متشائم / محايد (اختر الأقرب لقرار التطبيق أعلاه، ولا تناقضه)",
  "sentiment_bullets": ["2-4 نقاط قصيرة تبرر هذا الرأي بالأرقام"],
  "technical_headline": "عنوان قصير للحالة الفنية",
  "technical_bullets": ["2-3 نقاط عن RSI/الدعم والمقاومة/الاتجاه، فقط مما هو معطى"],
  "valuation_headline": "عنوان قصير عن التقييم",
  "valuation_bullets": ["1-2 نقطة عن السعر العادل والفجوة السعرية، فقط إن كانت البيانات متاحة"],
  "fundamentals_headline": "عنوان قصير عن الأساسيات المالية",
  "fundamentals_bullets": ["2-3 نقاط عن P/E وROE وهامش الربح ونمو الأرباح، فقط مما هو معطى"],
  "dividends_headline": "عنوان قصير عن التوزيعات (احذف الحقل بالكامل إن لم يوجد عائد توزيعات)",
  "dividends_bullets": ["1-2 نقطة عن عائد التوزيعات فقط إن كان معطى"],
  "summary": "ملخص من جملتين يجمع الرأي العام"
}}"""
    return await _generate_obj(prompt, key, ANALYSIS_TTL)


async def portfolio_report(holdings: list[dict], cash: float, weekly: dict | None = None) -> dict | None:
    """Comprehensive Arabic portfolio report — kept full-length, but written in
    an elegant, professional, honestly-optimistic tone that tracks the week's
    real momentum (return growth, outperformance vs. TASI, positive events).
    Cached 24h (keyed on composition + weekly momentum)."""
    if not holdings:
        return None
    ctx = _portfolio_context(holdings, cash)
    week = _weekly_story(weekly)
    wk_fp = str(weekly.get("portfolio_week_pct")) if weekly else "-"
    key = f"ai:report:{date.today().isoformat()}:{_portfolio_fingerprint(holdings)}:{wk_fp}"
    prompt = f"""أنت كاتب تقارير استثمارية سعودي رفيع المستوى، تكتب لقارئ غير متخصص يريد أن يفهم حال محفظته ويطمئن إليها.
أسلوبك: نثر عربي رزين متوازن مترابط، يقرأ كتقرير مؤسسة محترمة دون تكلّف ودون لغة تسويقية. **قلّل الأرقام إلى أدنى حد** — رقمان أو ثلاثة مرساةً فقط (كالعائد المحقّق)، والباقي وصف نوعي بكلمات واضحة (وزن معتبر، حضور قوي، نمو مطّرد).
مبدأ المرآة الصادق: التقرير انعكاس للنتائج الفعلية —
• إن كانت المحفظة قوية ونتائجها إيجابية: اكتب تقريراً إيجابياً واثقاً يعزّز هذا الأداء ويُبرز جودة البناء والاختيار، **ولا تذكر عيوباً أو مخاطر أو تحفّظات إطلاقاً** ولا عبارات استدراك.
• وإن كانت النتائج سلبية فعلاً: اكتب بصدق هادئ متّزن دون تهويل.
لا تخترع أي معلومة أو رقم غير موجود في المعطيات.

المعطيات (لاستخدامك أنت — لا تسردها كقوائم):
{ctx}{week}

أعد النتيجة بصيغة JSON فقط بدون أي شرح خارج الكائن:
{{"content": "تقرير عربي من 4 فقرات نثرية مترابطة يفصل بينها سطر فارغ، بلا عناوين وبلا تعداد نقطي:
(1) افتتاحية تضع القارئ في صورة الحال العام للمحفظة وما تعكسه من نهج.
(2) قراءة نوعية لبنائها وتنوّعها وجودة شركاتها بكلمات لا بأرقام.
(3) مسيرة الأداء وثمرته، برقم مرساة واحد أو اثنين على الأكثر، مع الإشارة إلى التقدّم مقارنة بالسوق إن كان متحققاً.
(4) خاتمة رزينة تُجمل الصورة وتختم بأن القرار الاستثماري يظل بيد صاحب المحفظة."}}"""
    return await _generate_obj(prompt, key, ANALYSIS_TTL)


async def company_brief_ar(name: str, summary_en: str, sector: str | None = None) -> str | None:
    """نبذة عربية عن نشاط الشركة، مُشتقّة من الوصف الإنجليزي الرسمي للمصدر.

    تُستدعى فقط حين لا يُوفّر «سهمك» وصفاً عربياً جاهزاً. النصّ الناتج يُوسَم في
    الواجهة صراحةً بأنه مُترجَم آلياً، فلا يُقرأ كإفصاحٍ رسمي.

    القيد الحاكم: الترجمة لا الإنشاء. الوصف الإنجليزي هو المعطى الوحيد، ويُمنع
    إضافة أرقام أو أحكام أو تقييمات لا ترد فيه — وإلا صارت «نبذة» مصدرها الذكاء
    لا الشركة، وهو ما يخالف قاعدة «لا بيانات وهمية» في هذا التطبيق.
    """
    text = (summary_en or "").strip()
    if not text:
        return None
    key = f"ai:brief:{name}:{_stable(text)}"
    prompt = f"""أنت مترجم مالي سعودي محترف. أمامك الوصف الرسمي الإنجليزي لنشاط شركة مدرجة في تداول.

الشركة: {name}{f" — قطاع {sector}" if sector else ""}

الوصف الإنجليزي:
{text[:2500]}

مهمتك: صُغْ نبذة عربية عن **نشاط الشركة** في فقرة أو فقرتين (٤٠ إلى ٩٠ كلمة).
قيود ملزمة:
• تَرجِم ولا تُنشئ. لا تُضف أي معلومة أو رقم أو تاريخ أو حكم لا يرد في النصّ أعلاه.
• لا تقييم ولا توصية ولا رأي في السهم — وصف نشاطٍ فقط.
• عربية فصيحة رزينة بلا لغة تسويقية وبلا مبالغة.
• إن كان الوصف الإنجليزي ركيكاً أو ناقصاً فاكتفِ بما فيه ولا تكمله من عندك.

أعد النتيجة بصيغة JSON فقط: {{"brief": "النبذة العربية هنا"}}"""
    # شهرٌ لا يوم: وصف نشاط شركةٍ لا يتغيّر أسبوعياً، وإعادة توليده يومياً تستهلك
    # حصّة الذكاء المجانية بلا فائدة. وتُحفظ النبذة في قاعدة البيانات عند أول
    # توليد على أي حال، فلا يُنادى الذكاء إلا مرّة واحدة لكل شركة عملياً.
    obj = await _generate_obj(prompt, key, 30 * 24 * 60 * 60)
    if isinstance(obj, dict):
        brief = (obj.get("brief") or "").strip()
        return brief or None
    return None


async def exec_titles_ar(titles_en: list[str]) -> dict[str, str]:
    """تعريب **مسمّيات** الإدارة التنفيذية — لا الأسماء.

    الأسماء أعلامٌ تبقى بحروفها الأصلية: تعريبها نقلٌ صوتي يُنتج صيغاً متعدّدة
    للاسم الواحد ويصعّب البحث عنه، بخلاف المسمّى الوظيفي فهو مصطلحٌ له مقابلٌ
    عربي مستقرّ («الرئيس التنفيذي»، «المدير المالي»).

    ونفس قيد النبذة يحكمها: تَرجِم ولا تُنشئ. ما لا مقابل له يُترك كما هو بدل
    أن يُخترع له مسمّى.

    تُعاد خريطة {المسمّى الإنجليزي: العربي}، ويُخزَّن الناتج شهراً — المسمّيات
    لا تتغيّر إلا نادراً، فلا يُنادى الذكاء إلا مرّة لكل مجموعة.
    """
    items = [t.strip() for t in (titles_en or []) if t and t.strip()]
    if not items:
        return {}
    uniq = sorted(set(items))
    key = f"ai:exectitles:{_stable('|'.join(uniq))}"
    listing = "\n".join(f"- {t}" for t in uniq[:25])
    prompt = f"""أنت مترجم مالي سعودي محترف. أمامك مسمّيات وظيفية تنفيذية بالإنجليزية.

{listing}

مهمتك: أعطِ لكل مسمّى مقابله العربي المتعارف عليه في الشركات المدرجة.
قيود ملزمة:
• تَرجِم ولا تُنشئ. لا تُضف رتبةً ولا قسماً لا يرد في المسمّى.
• استعمل المصطلح المستقرّ: Chief Executive Officer ⇐ الرئيس التنفيذي،
  Chief Financial Officer ⇐ المدير المالي، Chairman ⇐ رئيس مجلس الإدارة.
• ما لا تجد له مقابلاً عربياً واضحاً، أعده كما هو بالإنجليزية.
• بلا ألقاب مضافة (سعادة/الأستاذ) وبلا شرح.

أعد النتيجة بصيغة JSON فقط: {{"titles": {{"English title": "المقابل العربي"}}}}"""
    obj = await _generate_obj(prompt, key, 30 * 24 * 60 * 60)
    if isinstance(obj, dict) and isinstance(obj.get("titles"), dict):
        return {str(k): str(v).strip() for k, v in obj["titles"].items() if str(v).strip()}
    return {}


async def exec_names_ar(names_en: list[str]) -> dict[str, str]:
    """كتابة أسماء الإدارة التنفيذية بالحروف العربية — بأمر المالك.

    وهذا **نقلٌ صوتيّ لا ترجمة**: الاسم عَلَمٌ لا معنى يُترجَم، فـ`Yasir` يُكتب
    «ياسر» ولا يُفسَّر. وأكثر هؤلاء سعوديّون أسماؤهم عربيةٌ أصلاً كُتبت
    بالحروف اللاتينية في مصدرٍ إنجليزي — فما يجري هنا **ردُّها إلى أصلها** لا
    اختراعُ صيغةٍ لها، ولذلك أُمر النموذج بالصيغة السعودية المتعارفة تحديداً
    (‏`Abdulaziz` ⇐ «عبدالعزيز» موصولةً كما تُكتب في السجلّات، لا «عبد العزيز»).

    وقد كان القرار السابق إبقاءَ الأسماء لاتينيةً خشية تعدّد الصيغ، ونقضه
    المالكُ صراحةً. فبقي من الحذر أثرٌ واحد: الاسم الأصلي يُرسَل مع العربي
    (`name_en`) وتعرضه الواجهة عند المرور، فيُمكن البحث به دائماً. وما يتعذّر
    نقله يبقى لاتينياً كما هو — ولا يُخمَّن.

    والناتج يُخزَّن شهراً: الأسماء لا تتغيّر، فلا يُنادى الذكاء إلا مرّةً
    واحدة لكلّ مجموعة.
    """
    items = [n.strip() for n in (names_en or []) if n and n.strip()]
    if not items:
        return {}
    uniq = sorted(set(items))
    key = f"ai:execnames:{_stable('|'.join(uniq))}"
    listing = "\n".join(f"- {n}" for n in uniq[:25])
    prompt = f"""أنت متخصص في كتابة أسماء الأعلام السعودية بالحروف العربية.
أمامك أسماء تنفيذيين في شركات مدرجة، مكتوبة بحروف لاتينية:

{listing}

مهمتك: اكتب كل اسم بالحروف العربية كما يُكتب في السجلات السعودية.
قيود ملزمة:
• هذا نقل صوتي للاسم، وليس ترجمة لمعناه. Nasser ⇐ ناصر، ولا تكتب «الناصر» ولا تشرح.
• الأسماء المركبة بـ«عبد» تُوصل كما هو المتعارف: Abdulaziz ⇐ عبدالعزيز، Abdullah ⇐ عبدالله.
• أبقِ «بن» و«آل» كما ترد في الاسم اللاتيني، ولا تُضف نسباً غير موجود.
• لا تُضف لقباً (الأستاذ/المهندس/الدكتور) ولا رتبةً ولا أي كلمة زائدة.
• الاسم غير العربي (أجنبي) اكتبه بالعربية نطقاً كما يُلفظ.
• ما تعذّر عليك نقله بثقة، أعده كما هو بالحروف اللاتينية.

أعد النتيجة بصيغة JSON فقط: {{"names": {{"Latin Name": "الاسم بالعربية"}}}}"""
    obj = await _generate_obj(prompt, key, 30 * 24 * 60 * 60)
    if isinstance(obj, dict) and isinstance(obj.get("names"), dict):
        return {str(k): str(v).strip() for k, v in obj["names"].items() if str(v).strip()}
    return {}
