"""الصفقاتُ الخاصة — من «تداول»، باكتشافِ النداء لا بتثبيته (D273).

## لماذا

طلبها المالكُ صراحةً ولم تُبنَ — سهوٌ منّي، لا قرارٌ. وهي معنًى لا يُقاس
من شريط الأسعار: صفقةٌ متفاوَضٌ عليها خارج دفتر الأوامر، بحجمٍ كبيرٍ وسعرٍ
قد يخالف سعرَ السوق، وكثيراً ما تسبق تغيّرَ ملكيةٍ مؤثّرة.

## كيف تُقرأ

«تداول» بوّابةٌ تُولّد معرِّفاتٍ في المسار، وتثبيتُ المسار يجعله يشيخ بلا
إنذار. فتُقرأ النقطةُ من الصفحة نفسِها: `<base href>` ثمّ نداءُ الجدول
بالاسم — وهي الطريقةُ التي فتحت الصكوكَ ومراقبةَ السوق (‏D249 · D251).

وأسماءُ الحقول **لم تُقَس بعد**: «تداول» محجوبةٌ عن حاويتي اليوم. فالقارئُ
يقبل عدّةَ أسماءٍ محتملةٍ لكلّ حقل، ولا يخترع حقلاً غائباً — وصفٌّ بلا
رمزٍ أو سعرٍ أو كمّيةٍ **يُترك**، ولا يُعرض نصفُ صفقة. والقياسُ بالمسبار
على الخادم، وحتى يُقاس يقول التطبيقُ «غير متوفّر».
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from loguru import logger

STORE_KEY = "market:special_deals"
MAX_AGE_SECONDS = 15 * 60
MAX_ROWS = 200

PAGE = ("https://www.saudiexchange.sa/wps/portal/saudiexchange/trading/"
        "participants-and-deals/special-deals")

# ══ «تداول» مغلقةٌ عند الحافّة لهذا المسار — قِيس، لا رُجّح ══ (D275)
# الصفحةُ تعود 200 للجلب المنتحِل وفيها **صفرُ جداول** (قشرةٌ بلا محتوى)،
# وتعود **403 Access Denied** من أكامايّ حين تُفتح بمتصفّحٍ حقيقيّ على
# الخادم. فليست مسألةَ سكربتٍ يُنفَّذ: المسارُ نفسُه محجوب.
#
# و«أرقام» تنشرها بمسارين قِيسا في صفحة الشركة بأسمائهما:
#   · السوقُ كلُّه: /ar/shareholder/shareholders-history-deals
#   · وللشركة:     /ar/shareholder/major-shareholders/company-deals/...
# فتُقرأ منها. والطبقةُ الأولى تبقى مكتوبةً: إن فُتحت «تداول» يوماً عادت
# أوّلاً — الترتيبُ لا يتغيّر لأن مصدراً تعثّر، ولكنّ المتعثّرَ لا يُنتظَر.
ARGAAM_MARKET = ("https://www.argaam.com/ar/shareholder/"
                 "shareholders-history-deals?marketid=3&pageno=1")
_BASE_RE = re.compile(r"<base[^>]+href=[\"']([^\"']+)", re.I)
# اسمُ النداء يُلتقط بنمطه لا بمعرِّفٍ محفوظ: البوّابةُ تُدير المعرِّف،
# ويبقى اسمُ الخدمة. وعدّةُ تسمياتٍ محتملةٍ لأن الاسمَ لم يُقَس بعد.
_EP_RE = re.compile(r"p0/[A-Za-z0-9_=]*=NJ(get[A-Za-z]*(?:Special|Negotiat)[A-Za-z]*)=/")

# مرشّحاتُ الأسماء لكلّ حقل، بالترتيب. وما لم يوجد يغيب.
FIELDS = {
    "symbol": ("symbol", "companySymbol", "tradingName", "companyCode"),
    "name": ("companyName", "companyFullName", "issuerName"),
    "price": ("price", "dealPrice", "executionPrice", "tradePrice"),
    "quantity": ("quantity", "volume", "dealVolume", "numberOfShares"),
    "value": ("value", "turnover", "dealValue", "totalValue"),
    "at": ("date", "dealDate", "tradeDate", "executionDate", "dateTime"),
}


def _num(x) -> float | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = re.sub(r"[,\s]", "", str(x or ""))
    try:
        return float(s)
    except ValueError:
        return None


def _pick(row: dict, names: tuple[str, ...]):
    for n in names:
        for k, v in row.items():
            if str(k).lower() == n.lower() and v not in (None, "", "-"):
                return v
    return None


def normalize(rows: list) -> list[dict]:
    """صفوفُ المصدر ← صفقاتٌ مفهومة. وناقصُ الأركان يُترك لا يُرمَّم."""
    out: list[dict] = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        sym = _pick(r, FIELDS["symbol"])
        m = re.search(r"\b(\d{4})\b", str(sym or ""))
        price = _num(_pick(r, FIELDS["price"]))
        qty = _num(_pick(r, FIELDS["quantity"]))
        # الأركانُ الثلاثة: رمزٌ وسعرٌ وكمّية. وبلا أحدها ليست صفقةً تُعرض.
        if not m or price is None or price <= 0 or qty is None or qty <= 0:
            continue
        val = _num(_pick(r, FIELDS["value"]))
        deal = {"symbol": m.group(1), "price": price, "quantity": qty,
                "value": val if val is not None else round(price * qty, 2)}
        name = _pick(r, FIELDS["name"])
        if name:
            deal["name"] = str(name).strip()
        at = _pick(r, FIELDS["at"])
        if at:
            deal["at"] = str(at).strip()
        out.append(deal)
        if len(out) >= MAX_ROWS:
            break
    return out


async def fetch_rows() -> tuple[list, str | None]:
    """صفوفُ الصفقات الخاصة من «تداول» — أو (فارغ، سببُ التعذّر) بنصِّه.

    وهي اليومَ **محجوبةٌ عند الحافّة** (‏403 لمتصفّحٍ حقيقيّ على الخادم).
    تبقى مكتوبةً لأن المصدرَ الرسميَّ أوّلُ الطبقات إن فُتح، ولا يُنتظَر
    وهو مغلق — القارئُ الثاني («أرقام») يعمل بعده.
    """
    from app.services.tadawul_http import fetch
    status, body = await fetch(PAGE)
    if status != 200 or not body:
        return [], f"HTTP {status} من صفحة الصفقات الخاصة"
    mb, me = _BASE_RE.search(body), _EP_RE.search(body)
    if not (mb and me):
        return [], ("لم يُعثر على "
                    + ("أساسِ الصفحة" if not mb else "نداءِ جدول الصفقات")
                    + " — تُقاس البنيةُ بالمسبار على الخادم")
    status, body = await fetch(mb.group(1).rstrip("/") + "/" + me.group(0),
                               params={"requestLocale": "en"}, referer=PAGE)
    if status != 200:
        return [], f"HTTP {status} من نقطة الصفقات الخاصة"
    try:
        data = json.loads(body)
    except Exception:                                             # noqa: BLE001
        return [], "مخرَجٌ غيرُ JSON من نقطة الصفقات"
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return [], "لا صفوفَ في مخرَج نقطة الصفقات"
    return rows, None


async def refresh() -> dict:
    """يجلب ويحفظ — و«أرقام» **أوّلُ الطبقات** لهذه الشاشة (D288).

    ══ لماذا انقلب الترتيب هنا وحدَه ══
    القاعدةُ العامّة «تداول أوّلاً»، وهي باقيةٌ في كلّ شاشةٍ أخرى. أمّا
    مسارُ الصفقات الخاصة في «تداول» فقد قِيس **محجوباً عند الحافّة**: 200
    بقشرةٍ بلا جدولٍ للجلب المنتحِل، و403 Access Denied لمتصفّحٍ حقيقيّ
    على الخادم. فتقديمُ متعثّرٍ على عاملٍ ليس أمانةً بل تأخيرٌ بلا فائدة،
    وقد أمر المالكُ أن يكون المصدرُ «أرقام». وتبقى «تداول» مكتوبةً تُجرَّب
    بعده: إن فُتح المسارُ يوماً عاد الرسميُّ إلى مقدّمته بلا تعديل.
    """
    deals, why = await argaam_deals()
    src = "أرقام"
    if not deals:
        rows, why_t = await fetch_rows()
        got = normalize(rows) if not why_t else []
        if got:
            deals, src, why = got, "تداول", None
        else:
            why = f"أرقام: {why} · تداول: {why_t or 'لا صفوف'}"
    if not deals:
        # يومٌ بلا صفقاتٍ خاصّةٍ **وارد** — لكنّه لا يُميَّز عن أسماءِ حقولٍ
        # لم تُطابَق. فلا يُمحى المحفوظُ، ويُقال سببُ الطبقتين بنصِّه.
        logger.warning("الصفقاتُ الخاصة لم تُقرأ: {}", why)
        return {"count": 0, "error": why}
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "deals": deals, "source": src}
    from app.services import cache, lastgood
    lastgood.save(STORE_KEY, rec)
    cache.set(STORE_KEY, rec, MAX_AGE_SECONDS)
    logger.info("الصفقاتُ الخاصة: {} صفقة من «{}»", len(deals), src)
    return {"count": len(deals), "at": rec["at"], "source": src}


def reading() -> dict | None:
    """المحفوظُ — أو None إن غاب أو شاخ."""
    from app.services import cache, lastgood
    rec = cache.get(STORE_KEY)
    if not isinstance(rec, dict):
        rec = lastgood.load(STORE_KEY, max_age_seconds=MAX_AGE_SECONDS)
    return rec if isinstance(rec, dict) and rec.get("deals") else None


def for_symbol(symbol) -> list[dict]:
    """صفقاتُ شركةٍ بعينها — أو قائمةٌ فارغة."""
    m = re.search(r"\b(\d{4})\b", str(symbol or ""))
    if not m:
        return []
    return [d for d in ((reading() or {}).get("deals") or [])
            if d.get("symbol") == m.group(1)]

# ── الطبقةُ الثانية: «أرقام» ─────────────────────────────────────────────
_SYM = re.compile(r"\b(\d{4})\b")
_NUMS = re.compile(r"\d[\d,]*(?:\.\d+)?")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}:\d{2}(?::\d{2})?")


def _cells(block: str) -> list[str]:
    from app.services.ownership import _text
    parts = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", block, re.S | re.I)
    if not parts:
        parts = re.findall(r"<(?:span|div|b|strong)\b[^>]*>(.*?)</(?:span|div|b|strong)>",
                           block, re.S | re.I)
    return [t for t in (_text(x) for x in parts) if t]


def rows_from_html(html: str) -> list[dict]:
    """صفقاتٌ من صفحة «أرقام» — جدولاً كانت أو حاويات (D281).

    ══ سمّيتُ المصدرَ ولم أقرأ منه ══
    كتبتُ عنوانَ «أرقام» في الشيفرة وتركتُ القارئ. وهو العطبُ الذي نبّه
    إليه المالك: «تجمع الملاحظات وتجهّز الحلَّ ثمّ تتركه». فهذا هو القارئ.

    والأركانُ ثلاثةٌ لا يُقبل صفٌّ بدونها: **رمزٌ من أربعة أرقام**،
    و**سعرٌ** في حدود المعقول، و**كمّيةٌ** لا تقلّ عن مئة سهم. وما نقص
    أحدُها يُترك — فصفحةُ تنقّلٍ فيها أرقامٌ لا تُقرأ صفقات.
    """
    from app.services.ownership import blocks

    out: list[dict] = []
    seen: set[tuple] = set()
    src = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "",
                 flags=re.S | re.I)
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", src, re.S | re.I)
    candidates = rows if rows else sorted(blocks(src), key=len)
    for block in candidates:
        cells = _cells(block if rows else block)
        if len(cells) < 3:
            continue
        joined = " | ".join(cells)
        m = _SYM.search(joined)
        if not m:
            continue
        # ══ التاريخُ ليس كمّية ══
        # «2026-09-11» أعطت كمّيةً قدرُها 2026 في أوّل قياس. فتُنزَع
        # التواريخُ من النصّ قبل استخراج الأرقام — والتاريخُ يُقرأ وحدَه.
        nums = []
        for c in cells:
            c = _DATE.sub(" ", c)
            for t in _NUMS.findall(c):
                v = _num(t)
                if v is not None:
                    nums.append(v)
        # ══ الرمزُ ليس سعراً ══
        # أوّلُ صيغةٍ قرأت «1010» سعراً: استبعدتُه بمقارنة نصٍّ برقمٍ
        # (`str(1010.0) != "1010"`) فلم تستبعد شيئاً. والمقارنةُ بالقيمة.
        sym_val = float(m.group(1))
        pool = [v for v in nums if v != sym_val]
        # السعرُ يُفضَّل كسريّاً: الصفقةُ تُنفَّذ بسعرٍ ذي هللات.
        price = next((v for v in pool if 0.1 <= v <= 10_000 and v != int(v)), None)
        if price is None:
            price = next((v for v in pool if 0.1 <= v <= 10_000), None)
        qty = next((v for v in pool if v >= 100 and v == int(v) and v != price), None)
        if price is None or qty is None:
            continue
        key = (m.group(1), price, qty)
        if key in seen:
            continue
        seen.add(key)
        deal = {"symbol": m.group(1), "price": price, "quantity": qty,
                "value": round(price * qty, 2)}
        d = re.search(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}", joined)
        if d:
            deal["at"] = d.group(0)
        name = next((c for c in cells
                     if len(c) >= 4 and not _NUMS.fullmatch(c.replace(",", ""))
                     and re.search(r"[ء-ي]{3}", c)), None)
        if name:
            deal["name"] = name
        out.append(deal)
        if len(out) >= MAX_ROWS:
            break
    return out


async def argaam_deals() -> tuple[list[dict], str | None]:
    """صفقاتُ «أرقام» — قراءةٌ خفيفةٌ أوّلاً، ثمّ المتصفّحُ إن لزم (D288).

    ══ الأرخصُ أوّلاً ══
    بأمر المالك صار **«أرقام» مصدرَ هذه الشاشة**. وفتحُ متصفّحٍ كلَّ نصف
    ساعةٍ ثقيلٌ إن كانت الصفحةُ تُقرأ بلا سكربت — فتُجرَّب القراءةُ
    العادية، وما لم تُفهَم صفوفُها يُفتح المتصفّح. والفرقُ يُقاس لا
    يُفترَض: إن كفت الخفيفةُ لم يُشغَّل كروميوم أصلاً.
    """
    import httpx

    from app.services.argaam_calendar import UA

    # ١ · قراءةٌ عادية
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                     headers={"User-Agent": UA,
                                              "Accept-Language": "ar,en;q=0.8"}) as c:
            r = await c.get(ARGAAM_MARKET)
        if r.status_code == 200 and r.text:
            got = rows_from_html(r.text)
            if got:
                return got, None
    except Exception as e:                                        # noqa: BLE001
        logger.debug("أرقام (خفيف): {}: {}", type(e).__name__, e)

    # ٢ · المتصفّح — للمرسوم بجافاسكربت
    from app.services.browser_fetch import BrowserUnavailable, render
    try:
        pages = await render([ARGAAM_MARKET], settle_ms=8000)
    except BrowserUnavailable as e:
        return [], f"المتصفّحُ غيرُ متاح: {e}"
    html = pages.get(ARGAAM_MARKET, "")
    if not html:
        return [], "لم تُرسَم صفحةُ «أرقام»"
    got = rows_from_html(html)
    return got, None if got else "لم يُفهَم صفٌّ في صفحة «أرقام»"
