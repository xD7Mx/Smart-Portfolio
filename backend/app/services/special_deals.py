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
ARGAAM_ORIGIN = "https://www.argaam.com"
ARGAAM_HOME = ARGAAM_ORIGIN + "/ar"
ARGAAM_MARKET = ("https://www.argaam.com/ar/shareholder/"
                 "shareholders-history-deals?marketid=3&pageno=1")
ARGAAM_EP = ("https://www.argaam.com/ar/shareholder/"
             "shareholders-history-deals")
SHAPE_KEY = "market:special_deals:shape"
DEFAULT_DAYS = 30

# ══ اقرأ كيف ينشر المصدرُ نفسُه، ثمّ اجلبها كما يجلبها ══ (D296)
# قال المالك: «انظر أوّلاً لأرقام كيف يجلبها واجلبها مثله». وكنتُ أطرق
# مسارَ `shareholders-history-deals` بصيغِ نداءٍ مخترَعة — وهو أصلاً
# **صفقاتُ كبار الملّاك**، لا الصفقاتُ الخاصة. و«أرقام» تنشر الصفقاتَ
# الخاصةَ بالطريقة التي تنشر بها كلَّ سجلٍّ مؤرَّخ: **مقالةٌ لكلّ جلسة**
# («تاسي: ٧ صفقات خاصة بقيمة ١٥٧٫٢ مليون ريال») في جدولٍ داخلها، ومجموعُها
# تحت **وسمِ موضوعٍ** واحدٍ مرتَّبٍ بالأحدث. فهذا هو السجلُّ الأسبوعيُّ
# والشهريُّ الذي طلبه — موجودٌ فعلاً، وكنتُ أسأل البابَ الخطأ.
#
# والفهرسُ يُكتشف من قائمة «أرقام» نفسِها (رابطُ «الصفقات الخاصة»)، ولا
# يُثبَّت إلا سقوطاً: مسارٌ مثبَّتٌ يشيخ بلا إنذار — وهي قاعدةُ الطريقة
# المسجَّلة في `docs/FETCH_METHOD.md`.
TAG_INDEX = ("https://www.argaam.com/ar/tags/id/24779/{page}/"
             "%D8%A7%D9%84%D8%B5%D9%81%D9%82%D8%A7%D8%AA-"
             "%D8%A7%D9%84%D8%AE%D8%A7%D8%B5%D8%A9")
NAV_LABEL = re.compile(r"الصفقات\s+الخاصة")
ART_HREF = re.compile(
    r'href="([^"]*?/ar/article/articledetail/id/\d+[^"]*)"[^>]*>(.*?)</a>',
    re.S | re.I)
DEAL_TITLE = re.compile(r"صفق(?:ة|ات|تان|تين|تا)\s*خاص")
_META_DATE = re.compile(
    r'<meta[^>]+(?:article:published_time|datePublished)[^>]*content="([^"]+)"',
    re.I)
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}")
MAX_INDEX_PAGES = 4
MAX_ARTICLES = 30

# ══ سجلٌّ تاريخيٌّ لا لقطةٌ لحظية ══ (D295)
# قال المالك: «ليس شرطاً أن تكون لحظية — سجلُّ عملياتٍ بالتاريخ، أسبوعيٌّ
# وشهريٌّ مثل المفكرة، وهناك حتماً صفقاتٌ خلال هذه المدة». وكلمةُ
# **history** في اسم المسار كانت تقول ذلك ولم أقرأها: كنتُ أطلب الصفحةَ
# بلا **مدى تاريخٍ**، فتعود قشرةً بلا صفوف — لا لأن المصدرَ فارغ.
#
# وشكلُ النداء لا يُخمَّن ولا يُسأل عنه المالك: **التطبيقُ يجرّب الصيغَ
# بنفسه** ويحفظ الناجحةَ في مخزن الحالة فيبدأ بها في المرّة التالية.
# فالقياسُ ينتقل من طرفيّة المالك إلى الخدمة نفسِها.
_XHR = {"X-Requested-With": "XMLHttpRequest",
        "Accept": "text/html, */*; q=0.01"}


def _variants(days: int) -> list[dict]:
    """صيغُ النداء المرشَّحة، بمدى تاريخٍ حقيقيّ."""
    from datetime import date, timedelta
    to_d = date.today()
    from_d = to_d - timedelta(days=max(1, days))
    iso_f, iso_t = from_d.isoformat(), to_d.isoformat()
    dmy_f, dmy_t = from_d.strftime("%d/%m/%Y"), to_d.strftime("%d/%m/%Y")
    base = {"marketid": 3, "pageno": 1}
    return [
        {"name": "POST+XHR·iso", "method": "POST", "headers": _XHR,
         "data": {**base, "fromdate": iso_f, "todate": iso_t}},
        {"name": "POST+XHR·dmy", "method": "POST", "headers": _XHR,
         "data": {**base, "fromdate": dmy_f, "todate": dmy_t}},
        {"name": "POST+XHR·camel", "method": "POST", "headers": _XHR,
         "data": {"marketId": 3, "pageNo": 1,
                  "fromDate": iso_f, "toDate": iso_t}},
        {"name": "GET+XHR·iso", "method": "GET", "headers": _XHR,
         "params": {**base, "fromdate": iso_f, "todate": iso_t}},
        {"name": "GET·iso", "method": "GET", "headers": None,
         "params": {**base, "fromdate": iso_f, "todate": iso_t}},
        {"name": "POST+XHR·بلا تاريخ", "method": "POST", "headers": _XHR,
         "data": base},
        {"name": "GET·صفحة", "method": "GET", "headers": None,
         "params": base},
    ]
_BASE_RE = re.compile(r"<base[^>]+href=[\"']([^\"']+)", re.I)
# اسمُ النداء يُلتقط بنمطه لا بمعرِّفٍ محفوظ: البوّابةُ تُدير المعرِّف،
# ويبقى اسمُ الخدمة. وعدّةُ تسمياتٍ محتملةٍ لأن الاسمَ لم يُقَس بعد.
_EP_RE = re.compile(r"p0/[A-Za-z0-9_=]*=NJ(get[A-Za-z]*(?:Special|Negotiat)[A-Za-z]*)=/")

# مرشّحاتُ الأسماء لكلّ حقل، بالترتيب. وما لم يوجد يغيب.
# ══ الحقولُ كما ردَّها المصدرُ بالحرف ══ (D318)
# قِيس جسمُ `getNegotiatedDetails` على خادم المالك:
#   {"company":"المجموعة السعودية","tradePrice":11.62,"tradeVolume":395000,
#    "turnOver":4589900,"strTime":"14:13:11","strDate":"15-09-2026",
#    "symbol":"2250","companyURL":"…"}
# فتُضاف أسماؤه إلى المرشَّحات — لا تُستبدَل: قارئٌ يقبل أكثرَ من شكلٍ
# يبقى حياً إن غيّر المصدرُ تسميته.
FIELDS = {
    "symbol": ("symbol", "companySymbol", "tradingName", "companyCode"),
    "name": ("company", "companyName", "companyFullName", "issuerName"),
    "price": ("tradePrice", "price", "dealPrice", "executionPrice"),
    "quantity": ("tradeVolume", "quantity", "volume", "dealVolume",
                 "numberOfShares"),
    "value": ("turnOver", "value", "turnover", "dealValue", "totalValue"),
    "at": ("strDate", "date", "dealDate", "tradeDate", "executionDate",
           "dateTime"),
    "time": ("strTime", "time", "tradeTime"),
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
        tm = _pick(r, FIELDS["time"])
        if tm:
            deal["time"] = str(tm).strip()
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


def _abs(href: str) -> str:
    """رابطٌ مطلقٌ **مفكوكُ الترميز** — و`&amp;` ليست `&` (D303).

    ══ عطبٌ قاسه المالكُ على خادمه ══
    قائمةُ «أرقام» تكتب روابطَها بترميز HTML: `?marketid=3&amp;pageno=1`.
    فطُلب الرابطُ بحرفيّته فردّ المصدرُ **403**، وقرأتُ الردَّ حجباً
    وبنيتُ عليه أن المسارَ خطأٌ — وهو مسارُ «الصفقات الخاصة» بعينه كما
    تسمّيه قائمتُهم. والقاعدةُ مكتوبةٌ في `docs/FETCH_METHOD.md` (البند ٤)
    وسقطتُ عنها هنا: **كلُّ رابطٍ يُقرأ من صفحةٍ يُفَكُّ ترميزُه قبل طلبه**.
    """
    import html as _html
    href = _html.unescape(str(href or "").strip())
    if href.startswith("http"):
        return href
    return ARGAAM_ORIGIN + ("" if href.startswith("/") else "/") + href


def _index_from_nav(html: str) -> str | None:
    """رابطُ «الصفقات الخاصة» من قائمة «أرقام» — المصدرُ يقول أين ينشر."""
    from app.services.ownership import _text
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                         html or "", re.S | re.I):
        if NAV_LABEL.search(_text(m.group(2))):
            return _abs(m.group(1))
    return None


def _index_pages(url: str) -> list[str]:
    """صفحاتُ الفهرس بترقيم المصدر نفسِه — وإلا صفحةٌ واحدة."""
    m = re.search(r"(/tags/id/\d+/)(\d+)(/|$)", url)
    if not m:
        return [url]
    return [url[:m.start(2)] + str(p) + url[m.end(2):]
            for p in range(1, MAX_INDEX_PAGES + 1)]


def _index_links(html: str) -> list[tuple[str, str]]:
    """مقالاتُ الصفقات الخاصة من الفهرس — بعنوانها، مرتَّبةً كما نُشرت."""
    from app.services.ownership import _text
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in ART_HREF.finditer(html or ""):
        href, title = _abs(m.group(1)), _text(m.group(2))
        if not DEAL_TITLE.search(title) or href in seen:
            continue
        seen.add(href)
        out.append((href, title))
    return out


def _to_date(raw):
    from datetime import datetime as _dtm
    raw = str(raw or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return _dtm.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def _article_date(html: str):
    """تاريخُ النشر من إفصاح الصفحة نفسِها — لا من ظنٍّ ولا من ساعتنا."""
    m = _META_DATE.search(html or "")
    if m:
        d = _to_date(m.group(1))
        if d:
            return d
    m = _DAY.search(html or "")
    return _to_date(m.group(0)) if m else None


def _argaam_plan(days: int):
    """خطّةُ قراءةٍ في جلسةٍ واحدة: قائمةٌ ← فهرسٌ ← مقالاتٌ مؤرَّخة.

    وتتوقّف عند أوّل مقالةٍ أقدمَ من المدى: الفهرسُ زمنيٌّ بالأحدث، فما
    بعدها أقدمُ منها — فلا تُجلَب صفحاتٌ لا تُعرض.
    """
    from datetime import date, timedelta
    floor = date.today() - timedelta(days=max(1, days))
    log: list[str] = []
    deals: list[dict] = []

    status, body = yield {"url": ARGAAM_HOME}
    index = _index_from_nav(body) if status == 200 else None
    log.append(f"القائمة:{status}/" + ("وُجد" if index else "بالوسم"))
    if not index:
        index = TAG_INDEX.format(page=1)

    fetched = 0
    stop = False
    for page_url in _index_pages(index):
        if stop:
            break
        status, body = yield {"url": page_url, "referer": ARGAAM_HOME}
        if status != 200 or not body:
            log.append(f"فهرس:{status}")
            break
        # فهرسٌ قد ينشر الجدولَ بنفسِه — يُقرأ قبل افتراضِ أنه قائمةُ مقالات.
        direct = rows_from_html(body)
        if direct:
            log.append(f"جدولٌ مباشر:{len(direct)}")
            deals.extend(direct)
            break
        links = _index_links(body)
        log.append(f"مقالات:{len(links)}")
        if not links:
            break
        for href, _title in links:
            if fetched >= MAX_ARTICLES:
                stop = True
                break
            status, art = yield {"url": href, "referer": page_url}
            fetched += 1
            if status != 200 or not art:
                continue
            at = _article_date(art)
            if at and at < floor:
                stop = True
                break
            got = rows_from_html(art, at=at.isoformat() if at else None)
            if got:
                deals.extend(got)
    return deals, log, fetched


def _dedupe(deals: list[dict]) -> list[dict]:
    """صفقةٌ واحدةٌ لا نسختان — والمفتاحُ يشمل التاريخ (مقالتان تتقاطعان)."""
    out: list[dict] = []
    seen: set[tuple] = set()
    for d in deals or []:
        key = (d.get("symbol"), d.get("price"), d.get("quantity"), d.get("at"))
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
        if len(out) >= MAX_ROWS:
            break
    return out


async def argaam_deals(days: int = DEFAULT_DAYS) -> tuple[list[dict], str | None]:
    """صفقاتُ «أرقام» لمدى أيّامٍ — كما تنشرها هي (D296)، ثمّ ما دونها.

    الطبقةُ الأولى نشرُ المصدرِ نفسِه: فهرسُ الوسم ومقالاتُه المؤرَّخة، في
    **جلسةٍ واحدةٍ** منتحِلةٍ تحفظ الكوكيزَ بين الطلبات. وإن لم تُعطِ شيئاً
    بقيت صيغُ النداء المحفوظةُ (D295) ثمّ المتصفّحُ آخرَ الوسائل.
    """
    import functools

    from app.services import lastgood
    from app.services.tadawul_http import smart_fetch, smart_flow

    try:
        deals, log, fetched = await smart_flow(
            functools.partial(_argaam_plan, days), warm=ARGAAM_HOME)
    except Exception as e:                                        # noqa: BLE001
        deals, log, fetched = [], [f"خطّة:{type(e).__name__}"], 0
    deals = _dedupe(deals)
    if deals:
        logger.info("الصفقاتُ الخاصة: {} صفقة من نشر «أرقام» "
                    "({} مقالاً · {})", len(deals), fetched, " · ".join(log))
        return deals, None
    nav = " · ".join(log)

    variants = _variants(days)
    remembered = lastgood.load(SHAPE_KEY)
    if isinstance(remembered, dict) and remembered.get("name"):
        variants.sort(key=lambda v: v["name"] != remembered["name"])

    tried = []
    for v in variants:
        try:
            status, body = await smart_fetch(
                ARGAAM_EP, params=v.get("params"), data=v.get("data"),
                method=v["method"], headers=v.get("headers"),
                warm="https://www.argaam.com/ar", referer=ARGAAM_MARKET)
        except Exception as e:                                    # noqa: BLE001
            tried.append(f"{v['name']}:{type(e).__name__}")
            continue
        got = rows_from_html(body or "") if status == 200 else []
        tried.append(f"{v['name']}:{status}/{len(got)}")
        if got:
            lastgood.save(SHAPE_KEY, {"name": v["name"]})
            logger.info("الصفقاتُ الخاصة: صيغةُ «{}» أعطت {} صفقة",
                        v["name"], len(got))
            return got, None

    # المتصفّحُ آخرَ الوسائل — صفحةٌ واحدةٌ لا أكثر.
    from app.services.browser_fetch import BrowserUnavailable, render
    try:
        pages = await render([ARGAAM_MARKET], settle_ms=9000)
    except BrowserUnavailable as e:
        return [], f"النشرُ: {nav} · الصيغُ: {' · '.join(tried)} · المتصفّح: {e}"
    got = rows_from_html(next(iter(pages.values()), ""))
    if got:
        logger.info("الصفقاتُ الخاصة: بالمتصفّح {} صفقة", len(got))
        return got, None
    return [], (f"النشرُ: {nav} · الصيغُ: " + " · ".join(tried)
                + " · المتصفّح: بلا صفوفٍ مفهومة")


# ══ بابُ «تداول» العامّ — ظهر بتسجيل الشبكة ══ (D310)
# قِيس على خادم المالك: صفحةُ الصفقات الخاصة **تنادي** هذه الخدمةَ وتعود
# بـ٢٩ ألفَ حرف. وهي خدمةُ مساعدٍ ثابتةُ المسار (ليست مسارَ بوّابةٍ
# يُولَّد)، ومصدرٌ عامٌّ غيرُ مدفوع — فتُنادى كما تناديها الصفحة: بجلسةٍ
# واحدةٍ تُسخَّن بالصفحة نفسِها، وبترويسة XHR ومُحيلٍ صحيح.
TD_HELPER = ("https://www.saudiexchange.sa/tadawul.eportal.theme.helper/"
             "RefreshTradeDetailsServlet")


# ══ والمسارُ نفسُه يُكتشف من قائمة «تداول» ══ (D311)
# قِيس على خادم المالك: طُلبت `participants-and-deals/special-deals` فعاد
# ردٌّ **أساسُ صفحته** `…/trading/investing-trading/…` — أي أن البوّابةَ
# صرفتنا إلى صفحةٍ أخرى، فقرأتُ ترويسةَ مؤشّرٍ وحسبتُها «قشرةً بلا
# جدول». فالمسارُ المحفوظُ قديمٌ أو مُحوَّل، والقاعدةُ المسجَّلةُ عندنا
# تقول: **لا يُحفَظ مسار** — يُقرأ من قائمة الموقع نفسِه.
TD_HOME = "https://www.saudiexchange.sa/wps/portal/saudiexchange/home"
TD_LABEL = re.compile(r"الصفقات\s+الخاصة|صفقات\s+متفاوض|Special\s+Deals",
                      re.I)


def td_page_from_nav(html: str) -> str | None:
    """رابطُ صفحةِ الصفقات الخاصة من قائمة «تداول» — بمعرِّفها المولَّد."""
    import html as _h
    from app.services.ownership import _text
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                         html or "", re.S | re.I):
        if not TD_LABEL.search(_text(m.group(2))):
            continue
        href = _h.unescape(m.group(1).strip())
        if href.startswith("http"):
            return href
        # الأصلُ من الصفحة التي قُرئت منها القائمةُ — لا مضيفٌ مثبَّتٌ في
        # الشيفرة: مثبَّتٌ يجعل الدالّةَ غيرَ قابلةٍ للقياس ويشيخ بلا إنذار.
        from urllib.parse import urlsplit
        u = urlsplit(TD_HOME)
        return f"{u.scheme}://{u.netloc}" + ("" if href.startswith("/") else "/") + href
    return None


def td_base(html: str) -> str | None:
    m = _BASE_RE.search(html or "")
    return m.group(1).rstrip("/") if m else None


# ══ الاسمُ الرسميُّ والبابُ المقيس ══ (D318)
# اسمُ الميزة في «تداول»: **«الصفقات المتفاوض عليها»** — وصفحتُها لكلّ
# سوقٍ بالنمط: `ourmarkets/<السوق>-market-watch/issuers-trading-information`.
# وخدمتُها `getNegotiatedDetails` تُنادى بمدى تاريخٍ فتردّ:
#   {"data":[{"company":…,"symbol":"2250","tradePrice":11.62,
#             "tradeVolume":395000,"turnOver":4589900,
#             "strDate":"15-09-2026","strTime":"14:13:11"}]}
# قِيس بمتصفّحٍ حقيقيٍّ على الخادم: ١٨٥ ألفَ حرفٍ لشهرٍ واحد.
NEG_PAGE = ("https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/"
            "{market}-market-watch/issuers-trading-information?locale=ar")
NEG_MARKETS = ("main", "nomu")
_NEG_EP = re.compile(r"p0/[A-Za-z0-9_=]*=NJ(get[A-Za-z]*Negotiat[A-Za-z]*)=/")


async def tadawul_negotiated(days: int = DEFAULT_DAYS,
                             markets: tuple[str, ...] = NEG_MARKETS
                             ) -> tuple[list[dict], str | None]:
    """«الصفقات المتفاوض عليها» من «تداول» — الاسمُ والبابُ كما قِيسا.

    الصفحةُ تُقرأ لاسمِ خدمتها (لا يُثبَّت مسارٌ مولَّد)، ثمّ تُنادى
    الخدمةُ بمدى التاريخ. وكلُّ سوقٍ صفحةٌ، فتُجمَع أسواقُها.
    """
    import functools
    from datetime import date, timedelta

    from app.services.tadawul_http import smart_flow

    to_d = date.today()
    from_d = to_d - timedelta(days=max(1, days))
    params = {"sector": "All", "company": "All",
              "fromDate": from_d.strftime("%d-%m-%Y"),
              "toDate": to_d.strftime("%d-%m-%Y"),
              "requestLocale": "ar"}

    def plan():
        out: list[dict] = []
        log: list[str] = []
        for mk in markets:
            page_url = NEG_PAGE.format(market=mk)
            status, page = yield {"url": page_url}
            if status != 200 or not page:
                log.append(f"{mk}:صفحة {status}")
                continue
            mb = _BASE_RE.search(page)
            me = _NEG_EP.search(page)
            if not (mb and me):
                log.append(f"{mk}:" + ("لا أساس" if not mb else "لا خدمة"))
                continue
            url = mb.group(1).rstrip("/") + "/" + me.group(0)
            status, body = yield {"url": url, "params": params,
                                  "referer": page_url}
            if status != 200 or not body:
                log.append(f"{mk}:{me.group(1)} {status}")
                continue
            try:
                rows = (json.loads(body) or {}).get("data")
            except Exception:                                     # noqa: BLE001
                log.append(f"{mk}:مخرَجٌ غيرُ JSON")
                continue
            got = normalize(rows if isinstance(rows, list) else [])
            log.append(f"{mk}:{len(got)}/"
                       f"{len(rows) if isinstance(rows, list) else 0}")
            out.extend(got)
        return out, log

    try:
        deals, log = await smart_flow(functools.partial(plan))
    except Exception as e:                                        # noqa: BLE001
        return [], f"تداول/متفاوض: {type(e).__name__}: {e}"
    if deals:
        logger.info("الصفقاتُ المتفاوض عليها: {} صفقة ({})",
                    len(deals), " · ".join(log))
        return _dedupe(deals), None
    return [], "تداول/متفاوض: " + (" · ".join(log) or "بلا صفوف")


async def tadawul_trade_details() -> tuple[list[dict], str | None]:
    """صفقاتُ صفحة «تداول» من خدمتها التي قِيس أن الصفحةَ تناديها.

    وشكلُ الجسم لم يُقَس بعد (‏٢٩ ألفَ حرفٍ بلا عيّنةٍ مطبوعة)، فيُقبَل
    **الشكلان**: JSON بصفوفٍ تُسمّى بحقولها، أو HTML يُقرأ بقارئ الصفوف.
    وما لم يُفهَم يُقال سببُه بنصّه — ولا يُخترع صفٌّ واحد.
    """
    import functools

    from app.services.tadawul_http import smart_flow

    def plan():
        # ١ · القائمةُ تدلّ على الصفحة بمعرِّفها المولَّد
        status, home = yield {"url": TD_HOME}
        url = td_page_from_nav(home or "") if status == 200 else None
        log = [f"القائمة:{status}/" + ("وُجد" if url else "لم يوجد")]
        status, page = yield {"url": url or PAGE, "referer": TD_HOME}
        log.append(f"الصفحة:{status}/{len(page or '')}")
        if status != 200 or not page:
            return None, " · ".join(log)
        # ٢ · جدولٌ مرسومٌ من الخادم؟ يُقرأ قبل أيّ نداءٍ ثانٍ
        got = rows_from_html(page)
        if got:
            return {"deals": got}, None
        # ٣ · وإلا: أسماءُ الخدمات في **هذه** الصفحة — ويُختار بمعناه
        names = sorted(set(re.findall(r"=NJ([A-Za-z][A-Za-z0-9_]{3,60})=/", page)))
        log.append("خدمات:" + (",".join(names[:6]) or "لا شيء"))
        base = td_base(page)
        hit = next((n for n in names
                    if re.search(r"deal|negotiat|special", n, re.I)), None)
        if not (base and hit):
            return None, " · ".join(log)
        ep = next(m.group(0) for m in
                  re.finditer(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z0-9_]+)=/", page)
                  if m.group(1) == hit)
        status, body = yield {"url": f"{base}/{ep}",
                              "params": {"requestLocale": "en"},
                              "referer": url or PAGE}
        log.append(f"{hit}:{status}/{len(body or '')}")
        if status != 200 or not body:
            return None, " · ".join(log)
        return body, None

    try:
        body, why = await smart_flow(functools.partial(plan))
    except Exception as e:                                        # noqa: BLE001
        return [], f"تداول/خدمة: {type(e).__name__}: {e}"
    if why or not body:
        return [], why or "تداول: جسمٌ فارغ"
    if isinstance(body, dict) and body.get("deals"):
        return body["deals"], None          # جدولٌ مرسومٌ من الخادم

    # JSON أوّلاً — وأسماءُ الحقول تُطابَق بمرشِّحاتها المكتوبة.
    try:
        data = json.loads(body)
    except Exception:                                             # noqa: BLE001
        data = None
    if data is not None:
        rows = data
        if isinstance(data, dict):
            for k in ("data", "rows", "deals", "result", "items"):
                if isinstance(data.get(k), list):
                    rows = data[k]
                    break
        got = normalize(rows if isinstance(rows, list) else [])
        if got:
            return got, None
        return [], ("خدمةُ التفاصيل: JSON بلا صفوفٍ مفهومة — الحقول: "
                    + ", ".join(sorted((rows[0] if isinstance(rows, list)
                                        and rows and isinstance(rows[0], dict)
                                        else {}).keys()))[:200])
    # وإلا فقارئُ الصفوف: جدولاً كان أو حاويات.
    got = rows_from_html(body)
    if got:
        return got, None
    return [], f"خدمةُ التفاصيل: {len(body)} حرفاً بلا صفوفٍ مفهومة"


async def refresh(days: int = DEFAULT_DAYS) -> dict:
    """يجلب ويحفظ — و«أرقام» **أوّلُ الطبقات** لهذه الشاشة (D288).

    ══ لماذا انقلب الترتيب هنا وحدَه ══
    القاعدةُ العامّة «تداول أوّلاً»، وهي باقيةٌ في كلّ شاشةٍ أخرى. أمّا
    مسارُ الصفقات الخاصة في «تداول» فقد قِيس **محجوباً عند الحافّة**: 200
    بقشرةٍ بلا جدولٍ للجلب المنتحِل، و403 Access Denied لمتصفّحٍ حقيقيّ
    على الخادم. فتقديمُ متعثّرٍ على عاملٍ ليس أمانةً بل تأخيرٌ بلا فائدة،
    وقد أمر المالكُ أن يكون المصدرُ «أرقام». وتبقى «تداول» مكتوبةً تُجرَّب
    بعده: إن فُتح المسارُ يوماً عاد الرسميُّ إلى مقدّمته بلا تعديل.
    """
    # ══ الترتيبُ تغيّر بالقياس ══ (D308 · D310)
    # قِيس أن صفحةَ «أرقام» مغلقةٌ بالاشتراك (تنادي باقاتَها بدل بياناتها)،
    # فلا تُقدَّم على مصدرٍ عامٍّ يعمل. و«تداول» رسميٌّ أصلاً.
    deals, why = await tadawul_negotiated(days)
    src = "تداول"
    if not deals:
        got, why2 = await tadawul_trade_details()
        if got:
            deals, why = got, None
        else:
            why = f"{why} · {why2}"
    if not deals:
        got, why_a = await argaam_deals(days)
        if got:
            deals, src, why = got, "أرقام", None
        else:
            why = f"تداول: {why} · أرقام: {why_a}"
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
           "deals": deals, "source": src, "days": days}
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


def _known_symbols() -> set:
    """رموزُ السوق الرئيسة — حاكمٌ يمنع اختلاق رمزٍ لا وجودَ له (D293)."""
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        return {str(s).replace(".SR", "") for s in main_market(MARKET_UNIVERSE)}
    except Exception:                                             # noqa: BLE001
        return set()


def _norm_ar(s) -> str:
    """اسمٌ عربيٌّ إلى صورةٍ واحدةٍ تُقارَن — لا تشكيلَ ولا همزاتٍ مختلفة."""
    s = re.sub(r"[ً-ْـ]", "", str(s or ""))
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"),
                 ("ة", "ه"), ("ؤ", "و"), ("ئ", "ي")):
        s = s.replace(a, b)
    s = re.sub(r"[^ء-ي ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[2:].strip() if s.startswith("ال") else s


_NAME_INDEX: dict[str, str] | None = None


def _name_index() -> dict[str, str]:
    """اسمُ الشركة ← رمزُها، والمتشابهُ يُسقَط: التباسٌ لا يُحسم بالظنّ."""
    global _NAME_INDEX
    if _NAME_INDEX is not None:
        return _NAME_INDEX
    idx: dict[str, str] = {}
    dupes: set[str] = set()
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        for raw in main_market(MARKET_UNIVERSE):
            sym = str(raw).replace(".SR", "")
            key = _norm_ar((MARKET_UNIVERSE.get(sym) or {}).get("name_ar"))
            if len(key) < 3:
                continue
            if key in idx and idx[key] != sym:
                dupes.add(key)
            idx[key] = sym
    except Exception:                                             # noqa: BLE001
        idx = {}
    for k in dupes:
        idx.pop(k, None)
    _NAME_INDEX = idx
    return idx


def _by_name(cells: list[str]) -> str | None:
    """رمزٌ من اسمِ شركةٍ في الصفّ — ومطابقةٌ واحدةٌ فقط تُقبَل (D296).

    مقالاتُ «أرقام» تكتب الاسمَ القصيرَ وتربطه بصفحة الشركة بمعرِّفها
    الداخليّ، لا برمزِ تاسي. فيُقرأ الاسمُ، وما لم يُطابق اسماً واحداً
    بعينه يُترك الصفّ — فالمطابقةُ المتعدّدةُ اختلاقٌ مؤجَّل.
    """
    idx = _name_index()
    if not idx:
        return None
    for c in cells:
        key = _norm_ar(c)
        if len(key) < 3:
            continue
        if key in idx:
            return idx[key]
        hits = {sym for name, sym in idx.items()
                if len(name) >= 4 and (name in key or key in name)}
        if len(hits) == 1:
            return next(iter(hits))
    return None


def rows_from_html(html: str, at: str | None = None) -> list[dict]:
    """صفقاتٌ من صفحة «أرقام» — جدولاً كانت أو حاويات (D281).

    ══ سمّيتُ المصدرَ ولم أقرأ منه ══
    كتبتُ عنوانَ «أرقام» في الشيفرة وتركتُ القارئ. وهو العطبُ الذي نبّه
    إليه المالك: «تجمع الملاحظات وتجهّز الحلَّ ثمّ تتركه». فهذا هو القارئ.

    والأركانُ ثلاثةٌ لا يُقبل صفٌّ بدونها: **رمزٌ من أربعة أرقام**،
    و**سعرٌ** في حدود المعقول، و**كمّيةٌ** لا تقلّ عن مئة سهم. وما نقص
    أحدُها يُترك — فصفحةُ تنقّلٍ فيها أرقامٌ لا تُقرأ صفقات.
    """
    from app.services.ownership import blocks

    # ══ اختلاقٌ كشفه القياسُ ══ (D293)
    # عاد القارئُ بثلاث «صفقات» من صفحة «أرقام»: «الدخول» (زرُّ تسجيل
    # الدخول!) و«الإعلام والترفيه» و«الطاقة» (أسماءُ قطاعات)، برموزٍ
    # 7759 و9615 **لا وجودَ لها في تاسي**. أي أن قارئَ الحاويات التقط
    # أرقامَ قائمةِ التنقّل وسمّاها صفقات. وهذا أسوأُ من الفراغ: فراغٌ
    # يُقال «لا صفقات»، واختلاقٌ يُقرأ قراراً.
    #
    # فأربعةُ حرّاسٍ لا يُقبل صفٌّ بدونها:
    #   · **الرمزُ من رموز السوق الرئيسة** — لا أيُّ أربعةِ أرقام
    #   · **وتاريخٌ في الصفّ** — الصفقةُ حدثٌ مؤرَّخٌ لا رقمان
    #   · **والسعرُ في حدّ المعقول** (≤ 1000 ﷼ في تاسي)
    #   · **والاسمُ ليس كلمةَ واجهة** (دخول · اشترك · قطاع …)
    KNOWN = _known_symbols()
    NAV = re.compile(r"الدخول|اشترك|تسجيل|القطاع|قطاعات|الرئيسية|المزيد|"
                     r"بحث|تنبيه|حسابي|جميع الحقوق")
    out: list[dict] = []
    seen: set[tuple] = set()
    src = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "",
                 flags=re.S | re.I)
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", src, re.S | re.I)
    # ══ مقالةٌ تُقرأ جدولاً فقط ══ (D296)
    # في وضع المقالة (`at` معلومٌ من إفصاح الصفحة) لا يُلجأ إلى الحاويات:
    # المقالةُ نصٌّ فيه أرقامٌ كثيرةٌ لا صفقات، وقارئُ الحاويات هو نفسُه
    # الذي اختلق «الدخول/7759». فإن لم يكن في المقالة جدولٌ فلا شيء.
    candidates = rows if rows else ([] if at else sorted(blocks(src), key=len))
    for block in candidates:
        cells = _cells(block)
        if len(cells) < 3:
            continue
        joined = " | ".join(cells)
        if NAV.search(joined):
            continue                      # كتلةُ واجهةٍ لا صفَّ صفقة
        # ══ الرمزُ بالرقم أو بالاسم ══
        # «أرقام» تكتب في جداول مقالاتها الاسمَ القصيرَ بلا رمزِ تاسي.
        # فيُقرأ الرقمُ إن كان من رموز السوق، وإلا فالاسمُ — ولا يُقبل
        # صفٌّ لا تُعرَف شركتُه.
        m = _SYM.search(joined)
        code = m.group(1) if m and (not KNOWN or m.group(1) in KNOWN) else None
        sym = code or _by_name(cells)
        if not sym:
            continue
        row_date = _DAY.search(joined)
        if not row_date and not at:
            continue                      # صفقةٌ بلا تاريخٍ ليست صفقة
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
        pool = [v for v in nums if code is None or v != float(code)]
        # السعرُ يُفضَّل كسريّاً: الصفقةُ تُنفَّذ بسعرٍ ذي هللات.
        # وسقفُ السعر في تاسي ألفُ ريالٍ عملياً — وما فوقه رقمُ قائمةٍ لا سعر.
        price = next((v for v in pool if 0.1 <= v <= 1_000 and v != int(v)), None)
        if price is None:
            price = next((v for v in pool if 0.1 <= v <= 1_000), None)
        # ══ الكمّيةُ يُصدّقها عمودُ القيمة ══ (D296)
        # ترتيبُ الأعمدة ليس عهداً: جدولٌ يبدأ بالقيمة يجعل أوّلَ صحيحٍ
        # كبيرٍ «كمّيةً» فتُضاعَف القيمةُ مرّتين. فتُختار الكمّيةُ التي
        # **حاصلُ ضربها في السعر موجودٌ في الصفّ نفسِه** — تصديقٌ داخليٌّ
        # لا ترتيبٌ مفترَض. وإن لم يُصدّقها شيءٌ فأوّلُ صحيحٍ معقول.
        ints = [v for v in pool if v >= 100 and v == int(v) and v != price]
        qty = None
        if price:
            for a in ints:
                if any(abs(b - a * price) <= max(1.0, 0.02 * a * price)
                       for b in ints if b != a):
                    qty = a
                    break
        if qty is None:
            qty = next(iter(ints), None)
        if price is None or qty is None:
            continue
        d = row_date or _DAY.search(joined)
        when = d.group(0) if d else at
        key = (sym, price, qty, when)
        if key in seen:
            continue
        seen.add(key)
        deal = {"symbol": sym, "price": price, "quantity": qty,
                "value": round(price * qty, 2)}
        if when:
            deal["at"] = when
        name = next((c for c in cells
                     if len(c) >= 4 and not _NUMS.fullmatch(c.replace(",", ""))
                     and re.search(r"[ء-ي]{3}", c)), None)
        if name:
            deal["name"] = name
        out.append(deal)
        if len(out) >= MAX_ROWS:
            break
    return out

def _row_date(d: dict):
    """تاريخُ الصفقة تاريخاً — أو None. وقارئُ التواريخ **واحد**."""
    return _to_date(d.get("at"))


def within(deals: list[dict], days: int) -> list[dict]:
    """صفقاتُ المدى — والتي بلا تاريخٍ مقروءٍ تبقى (لا تُحذف بالظنّ)."""
    from datetime import date, timedelta
    if not days or days <= 0:
        return list(deals or [])
    floor = date.today() - timedelta(days=days)
    out = []
    for d in deals or []:
        dd = _row_date(d)
        if dd is None or dd >= floor:
            out.append(d)
    return out
