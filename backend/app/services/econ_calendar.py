"""الأحداثُ الاقتصاديةُ الأمريكيةُ وأثرُها (‏D761 · بأمر المالك 2026-11-17).

قال المالك: «لازم يكون أيُّ حدث، أيُّ خبر — مثلاً خبرٌ جللٌ اليوم كالفيدرالي — وما الأثر؟ تفسيرٌ للأثر وتحليل: ماذا أتوقّع؛ إذا رُفعت
الفائدة هل يتضرّر السوق — إلى كول أو بوت».

المصدر: تقويمُ ‏ForexFactory الأسبوعيّ (‏`nfs.faireconomy.media/ff_calendar_thisweek.json`) — قِيس على الخادم 2026-11-17: 125 حدثاً
بالعنوان والبلد والوقت (بتوقيت نيويورك) والأهمية والتوقّع والسابق، **بلا الرقم الفعليّ** — فلا يُقال «صدر كذا»؛ بل يُقال ما يقيسه الحدث
وسيناريواه: إن جاء فوق التوقّع فكذا، ودونه فكذا، وميلُ كلٍّ منهما (عقودُ شراء · عقودُ بيع). والقراءةُ من النموذج على العنوان والتوقّع
والسابق وحدها، بعلاقاتٍ اقتصاديةٍ عامّة لا بأرقامٍ مخترعة؛ وتُخبَّأ ستّ ساعات.

‏D782 (المالك 2026-11-21): «الأحداثُ أبغاها باللغة العربية… وتدعم السوق الأمريكي وتدعم السوق السعودي كمان». فلكلّ حدثٍ اسمُه العربيُّ من
قاموسٍ ثابتٍ لعناوين المصدر (لا ينتظر النموذج ولا يتعطّل بتعطّله)، والنموذجُ لما لم يحوِه القاموس؛ ولا سطرَ إنجليزيٌّ تحته. وللسوق السعودي
أحداثُه من المصدر نفسه بقراءته هو: الريالُ مربوطٌ بالدولار فالبنكُ المركزيُّ السعوديُّ يتبع الفيدرالي (قراراتُه وما يحرّكها: التضخّم
والوظائف)، والنفطُ عصبُ السوق (مخزوناتُ الخام · أوبك)، والصينُ أكبرُ مشترٍ للنفط (بياناتُها العالية الأثر) — وأثرُ كلٍّ على السوق السعودي
وقطاعاته (إيجابيّ · سلبيّ)، ومعها أحداثُ الشركة المفتوحة من مفكرتها («أرقام»).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from loguru import logger

FEED = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
RY = ZoneInfo("Asia/Riyadh")
IMPACT_AR = {"High": "عالٍ", "Medium": "متوسّط", "Low": "منخفض", "Holiday": "عطلة"}

# ‏D782: أسماءُ أحداث المصدر بالعربية — ثابتةٌ لا تنتظر النموذج (والنموذجُ لما ليس هنا)
AR_TITLES = {
    "CPI m/m": "مؤشّرُ أسعار المستهلك (شهرياً)", "CPI y/y": "مؤشّرُ أسعار المستهلك (سنوياً)", "Core CPI m/m": "التضخّمُ الأساسيّ (شهرياً)",
    "Core CPI y/y": "التضخّمُ الأساسيّ (سنوياً)", "PPI m/m": "مؤشّرُ أسعار المنتجين (شهرياً)", "PPI y/y": "مؤشّرُ أسعار المنتجين (سنوياً)",
    "Core PPI m/m": "أسعارُ المنتجين الأساسية (شهرياً)", "Core PCE Price Index m/m": "نفقاتُ الاستهلاك الأساسية (شهرياً)",
    "Core PCE Price Index y/y": "نفقاتُ الاستهلاك الأساسية (سنوياً)", "PCE Price Index m/m": "مؤشّرُ نفقات الاستهلاك (شهرياً)",
    "Non-Farm Employment Change": "الوظائفُ غيرُ الزراعية", "Unemployment Rate": "معدّلُ البطالة",
    "Average Hourly Earnings m/m": "متوسّطُ الأجر بالساعة (شهرياً)", "Unemployment Claims": "طلباتُ إعانة البطالة",
    "ADP Non-Farm Employment Change": "وظائفُ القطاع الخاصّ (ADP)", "JOLTS Job Openings": "الوظائفُ الشاغرة (JOLTS)",
    "Challenger Job Cuts y/y": "تسريحاتُ الوظائف (تشالنجر)", "Employment Cost Index q/q": "مؤشّرُ تكلفة التوظيف (فصلياً)",
    "Federal Funds Rate": "قرارُ الفائدة الأمريكية", "FOMC Statement": "بيانُ الفيدرالي", "FOMC Press Conference": "المؤتمرُ الصحفيُّ للفيدرالي",
    "FOMC Meeting Minutes": "محضرُ اجتماع الفيدرالي", "FOMC Economic Projections": "التوقّعاتُ الاقتصاديةُ للفيدرالي", "Beige Book": "الكتابُ البيج للفيدرالي",
    "Retail Sales m/m": "مبيعاتُ التجزئة (شهرياً)", "Core Retail Sales m/m": "مبيعاتُ التجزئة الأساسية (شهرياً)",
    "ISM Manufacturing PMI": "مديرو المشتريات الصناعيّ (ISM)", "ISM Services PMI": "مديرو المشتريات الخدميّ (ISM)",
    "ISM Manufacturing Prices": "أسعارُ التصنيع (ISM)", "Flash Manufacturing PMI": "مديرو المشتريات الصناعيّ الأوّليّ",
    "Flash Services PMI": "مديرو المشتريات الخدميّ الأوّليّ", "Final Manufacturing PMI": "مديرو المشتريات الصناعيّ النهائيّ",
    "Final Services PMI": "مديرو المشتريات الخدميّ النهائيّ", "Chicago PMI": "مديرو المشتريات في شيكاغو",
    "Empire State Manufacturing Index": "مؤشّرُ إمباير ستيت الصناعيّ", "Philly Fed Manufacturing Index": "مؤشّرُ فيلادلفيا الصناعيّ",
    "Richmond Manufacturing Index": "مؤشّرُ ريتشموند الصناعيّ", "Advance GDP q/q": "الناتجُ المحلّيُّ الأوّليّ (فصلياً)",
    "Prelim GDP q/q": "الناتجُ المحلّيُّ التمهيديّ (فصلياً)", "Final GDP q/q": "الناتجُ المحلّيُّ النهائيّ (فصلياً)",
    "Advance GDP Price Index q/q": "مؤشّرُ أسعار الناتج الأوّليّ", "Durable Goods Orders m/m": "طلبياتُ السلع المعمّرة (شهرياً)",
    "Core Durable Goods Orders m/m": "طلبياتُ السلع المعمّرة الأساسية (شهرياً)", "CB Consumer Confidence": "ثقةُ المستهلك (كونفرنس بورد)",
    "Prelim UoM Consumer Sentiment": "معنوياتُ المستهلك الأوّلية (ميشيغان)", "Revised UoM Consumer Sentiment": "معنوياتُ المستهلك المعدّلة (ميشيغان)",
    "Prelim UoM Inflation Expectations": "توقّعاتُ التضخّم الأوّلية (ميشيغان)", "Revised UoM Inflation Expectations": "توقّعاتُ التضخّم المعدّلة (ميشيغان)",
    "Crude Oil Inventories": "مخزوناتُ النفط الخام الأمريكية", "Natural Gas Storage": "مخزوناتُ الغاز الطبيعيّ",
    "Building Permits": "تصاريحُ البناء", "Housing Starts": "المساكنُ المبدوءة", "New Home Sales": "مبيعاتُ المنازل الجديدة",
    "Existing Home Sales": "مبيعاتُ المنازل القائمة", "Pending Home Sales m/m": "مبيعاتُ المنازل المعلّقة (شهرياً)",
    "Industrial Production m/m": "الإنتاجُ الصناعيّ (شهرياً)", "Trade Balance": "الميزانُ التجاريّ", "Import Prices m/m": "أسعارُ الواردات (شهرياً)",
    "Personal Income m/m": "الدخلُ الشخصيّ (شهرياً)", "Personal Spending m/m": "الإنفاقُ الشخصيّ (شهرياً)",
    "Business Inventories m/m": "مخزوناتُ الشركات (شهرياً)", "Factory Orders m/m": "طلبياتُ المصانع (شهرياً)",
    "Wholesale Inventories m/m": "مخزوناتُ الجملة (شهرياً)", "Federal Budget Balance": "رصيدُ الميزانية الفيدرالية",
    "10-y Bond Auction": "مزادُ سندات العشر سنوات", "30-y Bond Auction": "مزادُ سندات الثلاثين سنة",
    "Prelim Nonfarm Productivity q/q": "إنتاجيةُ العمل الأوّلية (فصلياً)", "Prelim Unit Labor Costs q/q": "تكلفةُ وحدة العمل الأوّلية (فصلياً)",
    "Current Account": "الحسابُ الجاري", "TIC Long-Term Purchases": "صافي المشتريات الأجنبية طويلة الأجل",
    "Consumer Credit m/m": "الائتمانُ الاستهلاكيّ (شهرياً)", "NFIB Small Business Index": "تفاؤلُ الشركات الصغيرة",
    "S&P/CS Composite-20 HPI y/y": "أسعارُ المنازل — كيس شيلر (سنوياً)", "HPI m/m": "مؤشّرُ أسعار المنازل (شهرياً)",
    "Bank Holiday": "عطلةٌ مصرفية",
    # الصين — أكبرُ مشترٍ للنفط (للسوق السعودي)
    "GDP q/y": "الناتجُ المحلّيّ (سنوياً)", "Manufacturing PMI": "مديرو المشتريات الصناعيّ", "Non-Manufacturing PMI": "مديرو المشتريات غيرُ الصناعيّ",
    "Caixin Manufacturing PMI": "مؤشّرُ كايشين الصناعيّ", "Caixin Services PMI": "مؤشّرُ كايشين الخدميّ", "Industrial Production y/y": "الإنتاجُ الصناعيّ (سنوياً)",
    "Retail Sales y/y": "مبيعاتُ التجزئة (سنوياً)", "Fixed Asset Investment ytd/y": "الاستثمارُ في الأصول الثابتة", "New Loans": "القروضُ الجديدة",
    "M2 Money Supply y/y": "المعروضُ النقديّ M2 (سنوياً)", "1-y Loan Prime Rate": "فائدةُ القروض لسنة", "5-y Loan Prime Rate": "فائدةُ القروض لخمس سنوات",
    "USD-Denominated Trade Balance": "الميزانُ التجاريّ بالدولار",
}
AR_PATTERNS = [
    (r"^Fed Chair (\w+) Speaks$", "كلمةُ رئيس الفيدرالي"), (r"^FOMC Member (\w+) Speaks$", "كلمةُ عضوٍ في الفيدرالي"),
    (r"^President (\w+) Speaks$", "كلمةُ الرئيس الأمريكيّ"), (r"^Treasury Sec(retary)? (\w+) Speaks$", "كلمةُ وزير الخزانة الأمريكيّ"),
    (r"^OPEC.*Meetings?$", "اجتماعُ أوبك+"), (r"^OPEC", "أوبك+"),
]
COUNTRY_AR = {"USD": "", "CNY": "الصين — ", "All": ""}


def ar_title(title: str, country: str = "USD") -> str | None:
    """الاسمُ العربيُّ لحدث المصدر من القاموس — و‏None إن لم يكن فيه (فيُسمّيه النموذج)."""
    import re
    t = str(title or "").strip()
    ar = AR_TITLES.get(t)
    if ar is None:
        ar = next((a for p, a in AR_PATTERNS if re.search(p, t)), None)
    return None if ar is None else COUNTRY_AR.get(country, "") + ar


def for_market(it: dict, market: str) -> bool:
    """أحداثُ السوق: الأمريكيُّ أحداثُ الدولار العاليةُ والمتوسّطة؛ والسعوديُّ ما يحرّكه هو — الفيدراليُّ وبياناتُه العالية (الريالُ مربوطٌ
    بالدولار)، والنفطُ (مخزوناتُ الخام · أوبك)، والصينُ العاليةُ الأثر (أكبرُ مشترٍ للنفط)."""
    c, imp, t = it.get("country"), it.get("impact"), str(it.get("title") or "")
    if market == "sa":
        return ((c == "USD" and (imp == "High" or "Crude Oil" in t)) or (c == "CNY" and imp == "High") or "OPEC" in t) and imp in ("High", "Medium")
    return c == "USD" and imp in ("High", "Medium")

READ = """أنت اقتصاديٌّ يشرح لمتداولِ خياراتٍ أمريكيّ أثرَ الأحداث الاقتصادية الأمريكية القادمة. لكلّ حدثٍ أدناه: عنوانُه ووقتُه وأهميّتُه
والتوقّعُ والسابق (إن وُجدا). لا تذكر رقماً غيرَ المعطى، ولا تدّعِ نتيجةً لم تصدر. لكلّ حدثٍ أعطِ:
- ar: اسمُه بالعربية (قصير)
- what: ماذا يقيس ولماذا يهمّ السوق — جملةٌ واحدة
- above: إن جاء أعلى من التوقّع (أو تشدّد المتحدّث): الأثرُ المرجّح على الأسهم الأمريكية والعوائد — جملة
- above_lean: ميلُ الخيارات على مؤشّر الأسهم في هذه الحالة: "call" أو "put" أو "neutral" — ويطابق جملةَ above
- below: إن جاء أدنى من التوقّع (أو تيسّر المتحدّث): الأثرُ المرجّح — جملة
- below_lean: الميلُ في هذه الحالة: "call" أو "put" أو "neutral" — ويطابق جملةَ below
JSON فقط: {"ID": {"ar": "...", "what": "...", "above": "...", "above_lean": "...", "below": "...", "below_lean": "..."}}

"""

READ_SA = """أنت اقتصاديٌّ يشرح لمستثمرٍ في السوق السعودي (تاسي) أثرَ الأحداث الاقتصادية العالمية القادمة عليه. تذكّر: الريالُ مربوطٌ بالدولار
فالبنكُ المركزيُّ السعوديُّ يتبع الفيدراليَّ في الفائدة (فيتأثّر به البنوكُ والعقارُ والسيولة)، والنفطُ عصبُ الاقتصاد (أرامكو والبتروكيماويات
والميزانية)، والصينُ أكبرُ مشترٍ للنفط السعوديّ. لكلّ حدثٍ أدناه: عنوانُه ووقتُه وأهميّتُه والتوقّعُ والسابق (إن وُجدا). لا تذكر رقماً غيرَ المعطى،
ولا تدّعِ نتيجةً لم تصدر. لكلّ حدثٍ أعطِ:
- ar: اسمُه بالعربية (قصير)
- what: ماذا يقيس ولماذا يهمّ السوقَ السعوديّ — جملةٌ واحدة
- above: إن جاء أعلى من التوقّع (أو تشدّد المتحدّث): الأثرُ المرجّح على السوق السعودي وقطاعاته — جملة
- above_lean: "pos" إن كان إيجابياً للسوق السعودي أو "neg" إن كان سلبياً أو "neutral" — ويطابق جملةَ above
- below: إن جاء أدنى من التوقّع (أو تيسّر المتحدّث): الأثرُ المرجّح — جملة
- below_lean: "pos" أو "neg" أو "neutral" — ويطابق جملةَ below
JSON فقط: {"ID": {"ar": "...", "what": "...", "above": "...", "above_lean": "...", "below": "...", "below_lean": "..."}}

"""


def _blocking_get(url: str) -> tuple[int, str]:
    from curl_cffi import requests as cr
    with cr.Session(impersonate="chrome") as s:
        r = s.get(url, timeout=15)
    return r.status_code, r.text or ""


async def raw_week() -> list[dict]:
    """أحداثُ الأسبوع كما هي من المصدر — مخبّأةٌ نصفَ ساعة؛ و[] عند التعذّر."""
    from app.services import cache
    hit = cache.get("econ:ff:week")
    if hit is not None:
        return hit
    try:
        st, txt = await asyncio.to_thread(_blocking_get, FEED)
        items = json.loads(txt) if st == 200 else None
    except Exception as e:                                        # noqa: BLE001
        logger.warning("الأحداثُ الاقتصادية: {}", type(e).__name__)
        items = None
    if not isinstance(items, list):
        return []
    cache.set("econ:ff:week", items, 1800)
    return items


def shape(items: list[dict], now: datetime | None = None, impacts=("High", "Medium"), market: str = "us") -> list[dict]:
    """الأحداثُ المهمّةُ للسوق (الأمريكيّ افتراضاً · السعوديّ ‏D782): وقتُها بالرياض، وحالُها (مضى · اليوم · قادم)، واسمُها العربيّ — مرتّبةً بالوقت."""
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(RY).date()
    out = []
    for it in items or []:
        if it.get("impact") not in impacts or not for_market(it, market):
            continue
        try:
            t = datetime.fromisoformat(str(it.get("date")))
        except ValueError:
            continue
        loc = t.astimezone(RY)
        eid = hashlib.md5(f"{it.get('title')}|{it.get('date')}".encode()).hexdigest()[:10]
        out.append({"id": eid, "title": it.get("title"), "ar": ar_title(it.get("title"), it.get("country") or "USD"), "country": it.get("country"),
                    "impact": it.get("impact"), "impact_ar": IMPACT_AR.get(it.get("impact"), it.get("impact")),
                    "at": t.astimezone(timezone.utc).isoformat(timespec="seconds"), "riyadh": loc.strftime("%Y-%m-%d %H:%M"),
                    "day": "اليوم" if loc.date() == today else "غداً" if loc.date() == today + timedelta(days=1) else "أمس" if loc.date() == today - timedelta(days=1)
                    else loc.strftime("%d/%m"),
                    "past": t < now, "forecast": it.get("forecast") or None, "previous": it.get("previous") or None})
    out.sort(key=lambda e: e["at"])
    return out


async def analysis(events: list[dict], market: str = "us") -> dict:
    """قراءةُ الأثر لكلّ حدثٍ مهمّ (مخبّأةٌ ستّ ساعاتٍ ببصمة القائمة) — و{} إن تعذّر النموذج (فيُعرض الحدثُ بلا قراءة، ويُقال ذلك)."""
    from app.services import cache
    from app.services import research_desk as RD
    todo = [e for e in events if not e["past"] or e["day"] == "اليوم"][:24]
    if not todo:
        return {}
    key = f"econ:read2:{market}:" + hashlib.md5("|".join(e["id"] for e in todo).encode()).hexdigest()[:12]
    hit = cache.get(key)
    if hit is not None:
        return hit
    lines = [f"{e['id']} · {e['title']} · {e['riyadh']} بتوقيت الرياض · أهمية {e['impact']}"
             + (f" · التوقّع {e['forecast']}" if e["forecast"] else "") + (f" · السابق {e['previous']}" if e["previous"] else "") for e in todo]
    try:
        obj = await RD._gemini([{"text": (READ_SA if market == "sa" else READ) + "\n".join(lines)}], max_tokens=5000, temperature=0.2)
    except Exception as e:                                        # noqa: BLE001
        logger.warning("الأحداثُ الاقتصادية/القراءة: {}", type(e).__name__)
        obj = None
    if not isinstance(obj, dict):
        return {}
    L = ("pos", "neg", "neutral") if market == "sa" else ("call", "put", "neutral")
    ok = {k: {f: str(v.get(f) or "")[:260] for f in ("ar", "what", "above", "below")}
          | {"above_lean": v.get("above_lean") if v.get("above_lean") in L else "neutral", "below_lean": v.get("below_lean") if v.get("below_lean") in L else "neutral"}
          for k, v in obj.items() if isinstance(v, dict)}
    cache.set(key, ok, 6 * 3600)
    return ok


async def company_events(symbol: str, name: str = "", now: datetime | None = None) -> list[dict]:
    """أحداثُ الشركة السعودية القادمة من مفكرتها («أرقام» — ‏content_engine.company_calendar): الأحقيّاتُ والتوزيعاتُ والجمعياتُ والنتائج —
    القادمةُ وما كان اليوم، ستّةٌ على الأكثر؛ و[] عند التعذّر (لا يُدّعى حدث)."""
    from app.services.content_engine import company_calendar
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(RY).date().isoformat()
    code = str(symbol or "").upper().replace(".SR", "")              # مفكرةُ الشركة برمزها المجرّد (2222) كما في تبويب «المفكرة»
    try:
        items = await asyncio.wait_for(company_calendar(code, name or code), timeout=12)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("أحداثُ الشركة {}: {}", symbol, type(e).__name__)
        return []
    out = []
    for it in items or []:
        d, t = str(it.get("published") or "")[:10], str(it.get("headline") or it.get("title") or "").strip()
        if len(d) == 10 and d >= today and t:
            out.append({"date": d, "title": t[:160], "kind": str(it.get("kind") or "")[:30]})
    out.sort(key=lambda x: x["date"])
    return out[:6]


async def week(with_reading: bool = True, market: str = "us", symbol: str = "", name: str = "") -> dict:
    market = "sa" if market == "sa" else "us"
    ev = shape(await raw_week(), market=market)
    read = await analysis(ev, market) if with_reading and ev else {}
    for e in ev:
        r = read.get(e["id"])
        if r:
            fixed = e.get("ar")
            e.update(r)
            if fixed:                                             # الاسمُ من القاموس الثابت يتقدّم على تسمية النموذج
                e["ar"] = fixed
    company = await company_events(symbol, name) if market == "sa" and symbol else []
    return {"events": ev, "read_ok": bool(read), "market": market, "company": company, "source": "ForexFactory",
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def before(events: list[dict], until: datetime, impact: str = "High") -> list[dict]:
    """الأحداثُ المهمّةُ القادمةُ قبل وقتٍ (انتهاءُ عقدٍ مثلاً)."""
    lim = until.astimezone(timezone.utc).isoformat()
    return [e for e in events if not e["past"] and e["impact"] == impact and e["at"] <= lim]
