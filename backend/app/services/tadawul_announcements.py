"""
المصدر الرسمي المؤسسي للمفكرة — إعلانات «تداول / Saudi Exchange».

يقرأ صفحة/واجهة الإفصاحات الرسمية في السوق مباشرةً (توزيعات · أحقية · منحة ·
زيادة رأس مال · الجمعية العامة · النتائج) ويحوّلها إلى عناصر مفكرة مُهيكلة
بالرمز والاسم والتاريخ والرابط الرسمي. هذا هو **المصدر الأساسي**؛ يظلّ Google
News RSS احتياطيًا عند تعذّر الوصول (`content_engine` يدمج المصدرين).

تصميم دفاعي بالكامل:
  • يجرّب JSON أولاً ثم تحليل HTML — يتكيّف مع أي من الشكلين.
  • عند أي فشل (حظر/شبكة/تغيير هيكل) يُعيد [] ويُسجّل تحذيرًا فقط — لا يكسر
    المفكرة، فتُخدَم من الاحتياطي بلا انقطاع.
  • نقطة النهاية قابلة للضبط عبر متغيّر البيئة TADAWUL_ANNOUNCEMENTS_URL دون
    إعادة بناء الصورة.

ملاحظة تشغيلية: يتعذّر الوصول لهذا المضيف من بيئة التطوير (محجوب)، لكنه يعمل من
السيرفر. لذا يوجد probe في market.py يعرض الاستجابة الخام لضبط المُحلِّل على
البنية الحقيقية عند أول تشغيل على السيرفر.
"""

import os
import re
import html
import json
import httpx
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from loguru import logger

from app.services import cache

# نقطة النهاية الرسمية الافتراضية (قابلة للتجاوز بمتغيّر بيئة). واجهة الإعلانات
# المؤسسية في موقع «Saudi Exchange». إن تغيّر مسارها مستقبلاً يضبطه المالك عبر
# المتغيّر دون لمس الكود.
DEFAULT_TADAWUL_URL = os.getenv(
    "TADAWUL_ANNOUNCEMENTS_URL",
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/"
    "issuer-news/company-announcements",
)
# واجهة JSON محتملة (أسرع وأدقّ إن توفّرت) — تُجرّب أولاً.
TADAWUL_JSON_URL = os.getenv("TADAWUL_ANNOUNCEMENTS_JSON_URL", "")

_CACHE_KEY = "tadawul:announcements"
_CACHE_TTL = 60 * 60  # ساعة

# رؤوس متصفح كاملة وحديثة — Akamai يفحص اتّساق سلسلة الوكيل مع sec-ch-ua/
# sec-fetch. رؤوس ناقصة = 403 فوري.
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
_ORIGIN = "https://www.saudiexchange.sa"
_HEADERS = {
    "User-Agent": _UA,
    "Accept": "application/json, text/html, application/xhtml+xml, */*",
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1",
}

# تصنيف نوع الإعلان من نصّه العربي/الإنجليزي → نفس مفردات المفكرة.
_TYPE_KEYWORDS = [
    ("توزيع", "توزيعات"),
    ("أحقية", "أحقية"),
    ("منحة", "منحة"),
    ("زيادة رأس", "زيادة رأس المال"),
    ("رأس المال", "زيادة رأس المال"),
    ("حقوق", "أسهم حقوق أولوية"),
    ("جمعية", "الجمعية العامة"),
    ("النتائج المالية", "النتائج المالية"),
    ("نتائج", "النتائج المالية"),
    ("dividend", "توزيعات"),
    ("bonus", "منحة"),
    ("capital increase", "زيادة رأس المال"),
    ("rights", "أسهم حقوق أولوية"),
    ("general assembly", "الجمعية العامة"),
    ("agm", "الجمعية العامة"),
    ("results", "النتائج المالية"),
]


def _classify(text: str) -> str:
    t = (text or "").lower()
    for kw, label in _TYPE_KEYWORDS:
        if kw.lower() in t:
            return label
    return "إعلان"


_DATE_RES = [
    re.compile(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})"),          # 2026-07-26
    re.compile(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})"),          # 26/07/2026
]


def _norm_date(raw) -> str | None:
    """يُطبِّع أي تمثيل تاريخ شائع إلى ISO (YYYY-MM-DD). لا يُلفّق تاريخًا:
    ما لا يُحلَّل يبقى None فيُسقطه فلتر النافذة لاحقًا."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):  # epoch ms/seconds
        try:
            ts = raw / 1000 if raw > 1e11 else raw
            return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        except Exception:
            return None
    s = str(raw).strip()
    if not s:
        return None
    # ══ «Sep 14, 2026» تاريخٌ أيضاً ══ (D313)
    # قِيس أن خدمةَ «تداول» تردّ `PR_DATE: "Sep 14, 2026"` — وصيغُ قارئي
    # كانت أرقاماً فقط، فعاد التاريخُ None فأسقط الفلترُ الإفصاحَ كلَّه.
    # وشهرٌ بالحرف يُقرأ بجدولٍ صريحٍ لا بلغةِ النظام (‏locale) — فالخادمُ
    # قد يكون بأيّ لغة.
    _MON = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    m = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2})\s*,?\s*(\d{4})", s)
    if m and m.group(1)[:3].lower() in _MON:
        try:
            return datetime(int(m.group(3)), _MON[m.group(1)[:3].lower()],
                            int(m.group(2)), tzinfo=timezone.utc).date().isoformat()
        except Exception:                                         # noqa: BLE001
            pass
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})", s)
    if m and m.group(2)[:3].lower() in _MON:
        try:
            return datetime(int(m.group(3)), _MON[m.group(2)[:3].lower()],
                            int(m.group(1)), tzinfo=timezone.utc).date().isoformat()
        except Exception:                                         # noqa: BLE001
            pass
    for rx in _DATE_RES:
        m = rx.search(s)
        if not m:
            continue
        g = m.groups()
        try:
            if len(g[0]) == 4:
                y, mo, d = int(g[0]), int(g[1]), int(g[2])
            else:
                d, mo, y = int(g[0]), int(g[1]), int(g[2])
            return datetime(y, mo, d, tzinfo=timezone.utc).date().isoformat()
        except Exception:
            continue
    return None


_SYMBOL_RE = re.compile(r"\b(\d{4})\b")


def _extract_symbol(*texts: str) -> str | None:
    for t in texts:
        if not t:
            continue
        m = _SYMBOL_RE.search(str(t))
        if m:
            return m.group(1)
    return None


def _row_to_item(symbol, name, title, date_str, url) -> dict | None:
    title = (title or "").strip()
    date_str = _norm_date(date_str)
    if not title:
        return None
    return {
        "symbol": symbol,
        "company_name": name,
        "title": title,
        "type": _classify(title),
        "date": date_str,
        # إعلانٌ وقع لا موعدٌ يُنتظر — ومن يفرز به يقارن بالعدم إن غاب (D020).
        "date_kind": "announced",
        "url": url or None,
        "source": "تداول",
    }


def _parse_json(payload) -> list[dict]:
    """يتكيّف مع أشكال JSON الشائعة: قائمة مباشرة أو مغلّفة في مفتاح data/
    items/announcements/list. لكل صفّ يبحث عن مفاتيح شائعة للرمز/الاسم/العنوان/
    التاريخ/الرابط بأسماء عربية أو إنجليزية."""
    # ══ المفتاحُ يُقاس لا يُحفَظ ══ (D313)
    # قِيس على خادم المالك: خدمةُ الصفحة (`getNewsListData`) تردّ
    # `{"announcementList":[{"PR_DATE":…,"TITLE":…}]}` — ومفتاحُ القائمة
    # ليس في قائمتي، وأسماءُ الحقول **كبيرةٌ بشُرَط سفلية**. فالقارئُ صار
    # يبحث عن **أوّل قائمةٍ من قواميس** في أيّ مفتاح، ويطابق أسماءَ الحقول
    # بالمعنى لا بالنصّ الحرفيّ (بعد توحيد الحالة وحذف الشُرَط).
    rows = payload
    if isinstance(payload, dict):
        named = ("data", "items", "announcements", "announcementList", "list",
                 "result", "results", "records", "newsList")
        for k in named:
            v = payload.get(k)
            if isinstance(v, list) and v:
                rows = v
                break
        else:
            rows = next((v for v in payload.values()
                         if isinstance(v, list) and v
                         and isinstance(v[0], dict)), [payload])
    if not isinstance(rows, list):
        return []

    def pick(d, *keys):
        # مطابقةٌ بالمعنى: `PR_DATE` و`pr-date` و`prDate` شيءٌ واحد.
        flat = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v
                for k, v in d.items()}
        for k in keys:
            kk = re.sub(r"[^a-z0-9]", "", str(k).lower())
            if kk in flat and flat[kk] not in (None, ""):
                return flat[kk]
            if str(k) in d and d[str(k)] not in (None, ""):
                return d[str(k)]
        return None

    out: list[dict] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        symbol = pick(r, "symbol", "companySymbol", "symbolCode", "code", "tickerSymbol", "الرمز")
        name = pick(r, "companyName", "company", "name", "issuerName", "companyNameAr", "اسم الشركة")
        title = pick(r, "title", "subject", "headline", "announcementTitle",
                     "titleAr", "prTitle", "newsTitle", "العنوان", "الموضوع")
        date_str = pick(r, "date", "prDate", "publishDate", "announcementDate",
                        "createdDate", "dateTime", "publishedDate", "newsDate",
                        "التاريخ")
        url = pick(r, "url", "link", "detailsUrl", "announcementUrl", "href",
                   "prUrl", "newsUrl")
        symbol = str(symbol).strip() if symbol else _extract_symbol(str(title or ""), str(name or ""))
        item = _row_to_item(symbol, str(name).strip() if name else None,
                            str(title) if title else None, date_str, url)
        if item:
            out.append(item)
    return out


_TAG_RE = re.compile(r"<[^>]+>")


def _parse_html(text: str) -> list[dict]:
    """محلّل HTML دفاعي بلا اعتماد على مكتبة خارجية: يمرّ على صفوف الجدول
    (<tr>…</tr>) ويلتقط الخلايا (<td>). يفترض ترتيبًا شائعًا (رمز/شركة/عنوان/
    تاريخ) لكنه يتحمّل الاختلاف: يستخرج الرمز والتاريخ من أي خلية. يعتمد على
    probe لضبط الترتيب الحقيقي عند اللزوم."""
    out: list[dict] = []
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", text, re.I | re.S)
    for row in rows:
        cells = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, re.I | re.S)
        if len(cells) < 2:
            continue
        # رابط إن وُجد داخل الصفّ
        href = None
        hm = re.search(r'href=["\']([^"\']+)["\']', row, re.I)
        if hm:
            href = hm.group(1)
        vals = [html.unescape(_TAG_RE.sub(" ", c)).strip() for c in cells]
        vals = [re.sub(r"\s+", " ", v) for v in vals]
        joined = " | ".join(vals)
        symbol = _extract_symbol(*vals)
        date_str = next((v for v in vals if _norm_date(v)), None)
        # العنوان: أطول خليّة نصيّة ليست الرمز ولا التاريخ
        candidates = [v for v in vals if v and v != symbol and _norm_date(v) is None]
        title = max(candidates, key=len) if candidates else joined
        name = None
        # اسم الشركة: خليّة قصيرة نسبيًا تحوي حروفًا عربية وليست العنوان
        for v in candidates:
            if v != title and re.search(r"[؀-ۿ]", v) and len(v) < 40:
                name = v
                break
        item = _row_to_item(symbol, name, title, date_str, href)
        if item and item["date"]:  # في HTML نشترط تاريخًا لتفادي صفوف الترويسة
            out.append(item)
    return out


def _parse_rss(text: str) -> list[dict]:
    """بعض بوابات الإفصاح تقدّم RSS/XML — نحاول تحليلها إن بدت XML."""
    try:
        root = ET.fromstring(text)
    except Exception:
        return []
    out: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        it = _row_to_item(_extract_symbol(title), None,
                         html.unescape(title), pub, link)
        if it:
            out.append(it)
    return out


async def _raw_fetch(url: str) -> tuple[int, str]:
    """إفصاحاتُ «تداول» عبر **المَعبر المنتحِل** — لا httpx مباشرةً (D312).

    ══ كانت الخدمةُ تصدّق ما أبطله القياس ══
    كُتب هنا أن «كثيراً من إعدادات Akamai تُمرّر الطلبَ متى وُجدت الكوكيزُ
    والرؤوس»، وبُني عليه جلبٌ بـ`httpx` برؤوسٍ كاملةٍ وجلسةٍ مسخَّنة. ثمّ
    قِيس في D250 نقيضُه بالحرف: **الرؤوسُ الكاملةُ مع httpx تردّ 403،
    ونفسُها مع انتحال بصمة TLS تردّ 200** — فالحجبُ بالمصافحة لا بالرؤوس.
    وبقيت هذه الخدمةُ وحدَها خارج المَعبر، فصارت تردّ «Access Denied»
    (475 حرفاً) في كلّ نداء: لا إفصاحَ واحدٌ يصل، والمفكرةُ والأخبارُ
    وبحثُ الصفقات كلُّها تُبنى على الفراغ **بصمت**.

    فمعبرٌ واحدٌ لكلّ «تداول»: `tadawul_http.fetch` ينتحل البصمةَ ويُسخّن
    ويسقط إلى httpx وحدَه إن غابت المكتبة — ولا تُكرَّر جلسةٌ في كلّ ملفّ.
    """
    from app.services.tadawul_http import fetch
    return await fetch(url, referer=_ORIGIN + "/wps/portal/saudiexchange/"
                                              "newsandreports/issuer-news/"
                                              "company-announcements")


async def probe_tadawul() -> dict:
    """أداة فحص (للمالك): تجلب الاستجابة الخام وتُظهر عيّنة + عدد ما فُهم، حتى
    يُضبط المُحلِّل على البنية الحقيقية على السيرفر (المضيف محجوب عن التطوير)."""
    report: dict = {"urls": {}}
    for label, url in (("json", TADAWUL_JSON_URL), ("page", DEFAULT_TADAWUL_URL)):
        if not url:
            continue
        entry: dict = {"url": url}
        try:
            status, body = await _raw_fetch(url)
            entry["status"] = status
            entry["length"] = len(body)
            entry["content_head"] = body[:2000]
            parsed = []
            try:
                parsed = _parse_json(json.loads(body))
                entry["shape"] = "json"
            except Exception:
                if body.lstrip().startswith("<") and "<item" in body.lower():
                    parsed = _parse_rss(body)
                    entry["shape"] = "rss"
                else:
                    parsed = _parse_html(body)
                    entry["shape"] = "html"
            entry["parsed_count"] = len(parsed)
            entry["parsed_sample"] = parsed[:5]
        except Exception as e:
            entry["error"] = repr(e)
        report["urls"][label] = entry
    return report


# ══ القشرةُ تُسمّي خدمتَها — فتُنادى ══ (D313)
# قِيس على خادم المالك بعد فتح الحجب: الصفحةُ ٢٠٠ بـ٥٧٢ ألفَ حرفٍ و**صفرُ
# جداول** — فهي قشرةٌ يُملأ جدولُها بنداءِ خدمةٍ اسمُها في الصفحة:
# `getNewsListData`، وردُّها `{"announcementList":[{"PR_DATE":…,"TITLE":…}]}`.
# وهي الطريقةُ المسجَّلةُ عندنا (‏D251) ولم تكن مطبَّقةً في هذه الخدمة.
_SVC_RE = re.compile(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z][A-Za-z0-9_]{3,60})=/")
_SVC_WANT = re.compile(r"news|announc|disclos|issuer", re.I)


async def _from_page_service(page_url: str) -> list[dict]:
    """يقرأ أساسَ الصفحة واسمَ خدمتها ثمّ يناديها — أو قائمةٌ فارغة."""
    from app.services.tadawul_http import fetch

    status, page = await _raw_fetch(page_url)
    if status != 200 or not page:
        return []
    mb = re.search(r"<base[^>]+href=[\"']([^\"']+)", page, re.I)
    if not mb:
        return []
    base = mb.group(1).rstrip("/")
    eps: dict[str, str] = {}
    for m in _SVC_RE.finditer(page):
        eps.setdefault(m.group(1), m.group(0))
    for name in [n for n in eps if _SVC_WANT.search(n)][:3]:
        try:
            st, body = await fetch(f"{base}/{eps[name]}",
                                   params={"requestLocale": "ar"},
                                   referer=page_url)
        except Exception as e:                                     # noqa: BLE001
            logger.debug("خدمةُ الإفصاحات {}: {}", name, e)
            continue
        if st != 200 or not body:
            continue
        try:
            got = _parse_json(json.loads(body))
        except Exception:                                          # noqa: BLE001
            got = []
        if got:
            logger.info("إفصاحاتُ «تداول»: {} عنصراً من خدمة «{}»",
                        len(got), name)
            return got
    return []


async def fetch_tadawul_announcements(force: bool = False) -> list[dict]:
    """المصدر الأساسي: إعلانات تداول الرسمية. يُعيد قائمة عناصر مفكرة مُهيكلة
    [{symbol, company_name, title, type, date, url, source}]. مُخزَّن ساعة.
    عند أي تعذّر يُعيد [] بهدوء (يتكفّل الاحتياطي في content_engine)."""
    if not force:
        cached = cache.get(_CACHE_KEY)
        if cached is not None:
            return cached

    items: list[dict] = []
    # 1) واجهة JSON إن ضُبطت (الأدقّ).
    if TADAWUL_JSON_URL:
        try:
            status, body = await _raw_fetch(TADAWUL_JSON_URL)
            if status == 200:
                items = _parse_json(json.loads(body))
        except Exception as e:
            logger.warning(f"Tadawul JSON fetch failed: {e}")

    # 2ب) خدمةُ الصفحة المسمّاةُ فيها — القشرةُ لا تحمل الجدول (D313).
    if not items:
        try:
            items = await _from_page_service(DEFAULT_TADAWUL_URL)
        except Exception as e:                                     # noqa: BLE001
            logger.warning("خدمةُ صفحة الإفصاحات تعذّرت: {}", e)

    # 2) الصفحة الرسمية (HTML/RSS) — إن لم تُنتج JSON عناصر.
    if not items:
        try:
            status, body = await _raw_fetch(DEFAULT_TADAWUL_URL)
            if status == 200 and body:
                stripped = body.lstrip()
                if stripped.startswith("{") or stripped.startswith("["):
                    items = _parse_json(json.loads(body))
                elif "<item" in body.lower() and stripped.startswith("<"):
                    items = _parse_rss(body)
                else:
                    items = _parse_html(body)
            elif status in (401, 403, 429):
                # حجب Akamai معروف/متوقّع — ليس خطأً تشغيليًا. نُسجّله بمستوى
                # debug فقط حتى لا يملأ السجلّات، فالمصادر المُهيكلة تغطّي مكانه.
                logger.debug(f"Tadawul official page blocked (status {status}) — using structured sources.")
            else:
                logger.warning(f"Tadawul page returned status {status}.")
        except Exception as e:
            logger.warning(f"Tadawul announcements fetch failed (will fall back to RSS): {e}")

    # إزالة التكرار (رمز + عنوان مُطبَّع).
    seen: set = set()
    uniq: list[dict] = []
    for it in items:
        dk = (it.get("symbol"), " ".join((it.get("title") or "").split()))
        if dk in seen:
            continue
        seen.add(dk)
        uniq.append(it)

    if uniq:
        cache.set(_CACHE_KEY, uniq, _CACHE_TTL)
        logger.info(f"📢 Tadawul official announcements: {len(uniq)} items.")
    return uniq
