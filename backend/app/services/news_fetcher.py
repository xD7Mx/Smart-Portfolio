"""
Real market news via Google News RSS — free, keyless, returns actual current
Arabic headlines for any query with a real article link, publisher and time.
Far more reliable for the Saudi market than English financial APIs.

Used by content_engine to fetch + persist news that stays live (new items
appended, old kept). A 1h cache avoids hammering the feed.
"""

import asyncio
import html
import re
import httpx
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET
from loguru import logger
from app.services import cache

NEWS_CACHE_TTL = 60 * 60  # 1h
# حوكمة الحداثة (مؤسسية): الأخبار طازجة فقط — نافذة قصيرة صارمة، فلا يظهر
# خبر قديم يوتّر المستخدم. الإعلانات المؤسسية (المفكرة) نافذتها أوسع لأن
# بعضها يُعلَن مسبقًا لأحداث قادمة، لكنها تُرتَّب بالأحدث وتُنقّى بتاريخ الحدث.
NEWS_MAX_AGE_DAYS = 3
CORPORATE_MAX_AGE_DAYS = 30

# Google News RSS aggregates from any site that publishes matching text —
# some are low-quality reposts. We keep it as our only free, keyless source
# for real-time Arabic market headlines, but rank known, reputable Saudi/
# regional financial outlets first so the reader sees trustworthy names.
# Derived from the injected canonical registry (app/data/news_sources.py) —
# ONE policy file governs both admission/ranking here and the outlet logos
# shown in the UI, so the approved-outlets list can never drift between layers.
from app.data.news_sources import TRUSTED_SOURCE_ALIASES as TRUSTED_SOURCES

# Market-wide Arabic queries — broadened across the WHOLE Tadawul so the
# Market tab (and the ticker that mirrors it) can carry a large, real feed
# covering every major sector, not just the index. Each is a separate Google
# News RSS round-trip (run concurrently in _collect).
MARKET_QUERIES = [
    "مؤشر تاسي", "السوق السعودي تداول", "إغلاق تاسي اليوم", "تحليل السوق السعودي",
    "نتائج الشركات السعودية", "توزيعات أرباح الشركات السعودية",
    "أسهم البنوك السعودية", "قطاع البتروكيماويات السعودي", "سهم أرامكو", "سابك",
    "قطاع العقار السعودي", "شركات الاتصالات السعودية", "قطاع التأمين السعودي",
    "صناديق الريت السعودية", "قطاع الطاقة السعودي", "قطاع التجزئة السعودي",
    "الاكتتابات السعودية", "السوق الموازية نمو",
]
ECONOMIC_QUERIES = ["أوبك النفط أسعار", "الفيدرالي الأمريكي الفائدة", "الاقتصاد السعودي", "الاكتتابات السعودية"]

# أخبار إنجليزية حقيقية عن السوق السعودي (لوضع English في الواجهة) —
# تُجلب مباشرة من مصادر إنجليزية عبر Google News، لا تُترجم ولا تُخزَّن
# في قاعدة البيانات (ذاكرة مؤقتة فقط) حفاظاً على بيانات المحفظة.
EN_MARKET_QUERIES = [
    "Tadawul TASI index", "Saudi stock market", "Saudi stocks earnings",
    "Saudi Aramco stock", "Saudi banks shares", "Saudi petrochemicals SABIC",
    "Saudi IPO Tadawul", "Saudi dividends companies", "Saudi REIT funds",
    "Saudi economy market", "Nomu parallel market Saudi",
]


_TAG_RE = re.compile(r"<[^>]+>")


def _clean_description(desc: str, title: str, source: str | None) -> str | None:
    """Google News RSS wraps <description> in an <a> tag around the same
    title, sometimes followed by other same-story source links. Strip the
    HTML and drop it if it's just the headline repeated — we only want a
    real, additional snippet, never a duplicate of the title masquerading
    as a summary."""
    if not desc:
        return None
    text = html.unescape(_TAG_RE.sub(" ", desc)).strip()
    text = re.sub(r"\s+", " ", text)
    if not text or text == title or text.startswith(title[:40]):
        return None
    if source and text == source:
        return None
    return text


async def _fetch_google_news(client: httpx.AsyncClient, query: str, count: int = 6, lang: str = "ar") -> list:
    """Parse one Google News RSS query into normalized items."""
    url = "https://news.google.com/rss/search"
    params = {"q": query, "hl": "ar", "gl": "SA", "ceid": "SA:ar"} if lang == "ar" \
        else {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    try:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        items = []
        for it in list(root.iterfind(".//item"))[:count]:
            title = it.findtext("title") or ""
            link = it.findtext("link") or ""
            pub = it.findtext("pubDate")
            desc = it.findtext("description")
            source_el = it.find("{*}source")
            source = source_el.text if source_el is not None else None
            # Google appends " - Source" to titles; strip it.
            if title and source and title.endswith(f" - {source}"):
                title = title[: -(len(source) + 3)]
            # لا نُلفّق تاريخًا: خبر بلا pubDate صالح يبقى بلا تاريخ (None) —
            # فلا يظهر بتاريخ اليوم كذبًا (خبر قديم كان يُعرض كأنه اليوم)،
            # ويُسقطه فلتر الحداثة لأنه غير قابل للتحقّق.
            try:
                published = parsedate_to_datetime(pub) if pub else None
                if published and published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
            except Exception:
                published = None
            clean_title = html.unescape(title).strip()
            items.append({
                "headline": clean_title,
                "url": link.strip() or None,
                "source": source,
                "published": published,
                "summary": _clean_description(desc or "", clean_title, source),
            })
        return items
    except Exception as e:
        logger.debug(f"Google News '{query}' failed: {e}")
        return []


# ── تطبيع عربي + طيّ القصص المتقاربة (جودة تُنافس المدفوع) ──────────────────
_AR_DIACRITICS = re.compile(r"[ؗ-ًؚ-ْٰـ]")  # تشكيل + تطويل
_NON_WORD = re.compile(r"[^\w؀-ۿ]+")
# كلمات وقف شائعة لا تحمل هوية القصّة — تُستبعَد من بصمة التطابق.
_AR_STOP = {"في", "من", "على", "عن", "إلى", "الى", "مع", "أن", "ان", "و", "ال",
            "خلال", "بعد", "قبل", "اليوم", "سهم", "شركة", "بنسبة", "ريال", "السعودي",
            "السعودية", "خبر", "عاجل", "بورصة", "سوق"}


def _normalize_ar(text: str) -> str:
    """تطبيع عربي: إزالة التشكيل/التطويل، توحيد الألف/الهمزة/الياء/التاء المربوطة،
    وتصغير اللاتيني — حتى تتطابق الصيغ الكتابية المختلفة لنفس الاسم/القصّة."""
    t = _AR_DIACRITICS.sub("", text or "")
    t = (t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
         .replace("ى", "ي").replace("ئ", "ي").replace("ؤ", "و")
         .replace("ة", "ه"))
    return t.lower().strip()


# بادئات/لواحق عربية شائعة تُقشَّر لتقريب صيغ الكلمة الواحدة (توزيع/توزيعات،
# أرباح/أرباحاً) — تخفيف صرفيّ بسيط يكفي لكشف تكرار القصّة دون دمج قصص مختلفة.
_AR_PREFIXES = ("وال", "بال", "كال", "فال", "لل", "ال", "و", "ف", "ب", "ك", "ل")
_AR_SUFFIXES = ("اتها", "اتهم", "يتها", "ات", "ون", "ين", "ان", "ها", "هم",
                "يه", "يا", "ي", "ه", "ا")


def _stem_token(w: str) -> str:
    for p in _AR_PREFIXES:
        if len(w) - len(p) >= 3 and w.startswith(p):
            w = w[len(p):]
            break
    for s in _AR_SUFFIXES:
        if len(w) - len(s) >= 3 and w.endswith(s):
            w = w[: -len(s)]
            break
    return w


def _sig_tokens(headline: str) -> frozenset:
    """مجموعة الجذور الدلاليّة للعنوان (بلا وقف، بعد التطبيع والتخفيف الصرفي)
    — أساس قياس تشابه القصّتين."""
    norm = _normalize_ar(headline)
    toks = set()
    for w in _NON_WORD.sub(" ", norm).split():
        if not w or w in _AR_STOP or len(w) < 2:
            continue
        st = _stem_token(w)
        if len(st) >= 2 and st not in _AR_STOP:
            toks.add(st)
    return frozenset(toks)


def _story_signature(headline: str) -> str:
    """بصمة نصّية مستقرّة (للتخزين عبر الدورات): الجذور مرتّبة."""
    return " ".join(sorted(_sig_tokens(headline)))


_DUP_SIM = 0.62   # عتبة تشابه محافِظة: تطوي المكرّر الواضح دون إخفاء خبر مختلف


def _dedup_stories(items: list[dict]) -> list[dict]:
    """يطوي القصص المتكرّرة/المتقاربة (نفس الخبر من عدّة صحف بصياغات مختلفة)
    والروابط المكرّرة، مُبقيًا أفضل ممثّل: الموسوم لشركة أولاً (تغطية محفظة)، ثم
    المصدر الموثوق، ثم الأحدث. القياس بتشابه Jaccard للجذور بعتبة محافِظة، فلا
    يظهر الخبر الواحد مكرّرًا — ولا يُدمَج خبران مختلفان خطأً."""
    def rank(it: dict) -> tuple:
        return (
            0 if it.get("company") else 1,          # الموسوم أولاً
            0 if it.get("trusted") else 1,           # ثم الموثوق
            -(it["published"].timestamp() if it.get("published") else 0),  # ثم الأحدث
        )
    clusters: list[dict] = []   # {tokens, rep, urls}
    for it in items:
        toks = _sig_tokens(it.get("headline") or "")
        url = (it.get("url") or "").strip()
        match = None
        for cl in clusters:
            # رابط مطابق = نفس القصّة قطعًا؛ وإلا قياس تشابه الجذور.
            if url and url in cl["urls"]:
                match = cl
                break
            if toks and cl["tokens"]:
                inter = len(toks & cl["tokens"])
                union = len(toks | cl["tokens"])
                if union and inter / union >= _DUP_SIM:
                    match = cl
                    break
        if match is None:
            clusters.append({"tokens": toks, "rep": it, "urls": {url} if url else set()})
        else:
            if url:
                match["urls"].add(url)
            if rank(it) < rank(match["rep"]):
                match["rep"] = it
    out = [cl["rep"] for cl in clusters]
    out.sort(key=lambda x: (not x.get("trusted"),
                            -(x["published"].timestamp() if x.get("published") else 0)))
    return out


async def _collect(queries: list[str], category: str, max_age_days: int | None = None,
                   tags: list[str | None] | None = None, count: int = 6, lang: str = "ar") -> list[dict]:
    """`tags`, when given, aligns 1:1 with `queries`: every headline returned
    by query i is stamped with tags[i] as its company symbol. This is the
    RELIABLE way to attribute a headline to the company it was queried for —
    the old approach (name-substring matching after merging all results)
    silently dropped most attributions because headlines rarely contain the
    exact directory spelling of a company name."""
    seen: set = set()
    out: list[dict] = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    cutoff = (datetime.now(timezone.utc).timestamp() - max_age_days * 86400) if max_age_days else None
    async with httpx.AsyncClient(timeout=12, headers=headers, follow_redirects=True) as client:
        # Each query is an independent RSS round-trip — fetching them
        # sequentially could take 10 x several-hundred-ms on a cold cache
        # (this endpoint blocks the top news ticker on page load), so they
        # run concurrently instead.
        results = await asyncio.gather(*(_fetch_google_news(client, q, count, lang) for q in queries))
        for qi, items in enumerate(results):
            tag = tags[qi] if tags and qi < len(tags) else None
            for it in items:
                h = it["headline"]
                if not h or h in seen:
                    continue
                # حوكمة الحداثة: نُسقط ما هو أقدم من نافذة المستدعي، وكذلك ما
                # لا تاريخ له (لا يمكن التحقّق من حداثته) عندما تُطلَب نافذة —
                # فلا يتسرّب خبر قديم بلا تاريخ ويظهر كأنه اليوم.
                if cutoff is not None:
                    if it["published"] is None or it["published"].timestamp() < cutoff:
                        continue
                seen.add(h)
                it["category"] = category
                it["trusted"] = (it.get("source") or "").strip() in TRUSTED_SOURCES
                if tag:
                    it["company"] = tag
                out.append(it)
    # Trusted outlets first, most recent within each group next (undated last).
    out.sort(key=lambda x: (not x["trusted"], -(x["published"].timestamp() if x["published"] else 0)))
    return out


def _prefer_trusted(items: list[dict], min_trusted: int = 5) -> list[dict]:
    """Source governance: professional/official outlets only, as long as
    they give us enough material. Unknown aggregator/repost sites are only
    admitted (after the trusted ones, capped) when the trusted feed alone
    is too thin to fill the screen — so the list never goes empty, but
    never turns into a random-blogs wall either."""
    trusted = [it for it in items if it["trusted"]]
    if len(trusted) >= min_trusted:
        return trusted
    untrusted = [it for it in items if not it["trusted"]]
    return trusted + untrusted[: max(0, min_trusted - len(trusted))]


async def fetch_market_news_en() -> list[dict]:
    """أخبار السوق السعودي بالإنجليزية — لوضع English. مخزّنة مؤقتاً ساعة،
    ولا تُكتب في قاعدة البيانات (بيانات المحفظة لا تُمَس)."""
    key = "news:gnews:market:en"
    cached = cache.get(key)
    if cached is not None:
        return cached
    items = await _collect(EN_MARKET_QUERIES, "Markets", max_age_days=NEWS_MAX_AGE_DAYS, count=8, lang="en")
    items = _dedup_stories(items)[:120]
    if items:
        cache.set(key, items, NEWS_CACHE_TTL)
    return items


async def fetch_market_news(company_names: list[str] | None = None, company_pairs: list[tuple[str, str]] | None = None) -> list[dict]:
    """Market-wide + per-company real Arabic news. Cached 1h.
    `company_pairs` (symbol, name), when given, tags each item with the
    company it's actually about (matched by name substring in the headline —
    Google News doesn't echo the query back) so the UI can show that
    company's real logo instead of a generic icon."""
    key = "news:gnews:market"
    cached = cache.get(key)
    if cached is not None:
        return cached
    # Market-wide queries (untagged) + one DEDICATED, directly-tagged query
    # per portfolio company — ALL of them, not a truncated [:8] slice that
    # silently left some companies with zero coverage. Direct per-query
    # tagging (see _collect) is what actually attributes headlines reliably;
    # the old substring match missed most, leaving "أخبار المحفظة" nearly
    # empty even when plenty of real per-company headlines existed.
    queries: list[str] = list(MARKET_QUERIES)
    tags: list[str | None] = [None] * len(queries)
    if company_pairs:
        for sym, name in company_pairs[:20]:
            if name:
                queries.append(f'"{name}" سهم')
                tags.append(sym)
    elif company_names:
        for name in company_names[:20]:
            if name:
                queries.append(f'"{name}" سهم')
                tags.append(None)
    # Deep fetch (up to ~80 items/query) so the whole-market feed is large —
    # the Market tab and the ticker that mirrors it can then carry hundreds of
    # real headlines, not a couple dozen.
    collected = await _collect(queries, "أسواق", max_age_days=NEWS_MAX_AGE_DAYS, tags=tags, count=80)
    # Source governance applies to the GENERAL market feed; company-tagged
    # headlines are portfolio coverage and always kept — their visual
    # identity is the company's own logo, and dropping a company's only
    # headline because its outlet isn't in the registry is exactly what
    # left "أخبار المحفظة" at 3 items for 10 companies.
    tagged = [it for it in collected if it.get("company")]
    general = _prefer_trusted([it for it in collected if not it.get("company")])
    items = tagged + general
    items.sort(key=lambda x: (not x["trusted"], -(x["published"].timestamp() if x["published"] else 0)))
    if company_pairs:
        # نسبة آمنة للعناصر غير الموسومة: الاسم الأطول أولاً حتى لا يُطابق اسمٌ
        # قصير جزءًا من اسم شركة أخرى («الأهلي» ضمن «البنك الأهلي» و«الأهلي
        # المالية») فيُعلَّق شعار خطأ — مصدرُ إحراج نسبة الخبر لغير صاحبه.
        by_name = sorted([(name, sym) for sym, name in company_pairs if name],
                         key=lambda x: len(x[0]), reverse=True)
        for it in items:
            if not it.get("company"):
                it["company"] = next((sym for name, sym in by_name if name in it["headline"]), None)
    # طيّ القصص المتقاربة/المكرّرة → لا يظهر الخبر الواحد أكثر من مرّة.
    items = _dedup_stories(items)
    if items:
        cache.set(key, items, NEWS_CACHE_TTL)
    return items


async def fetch_economic_news() -> list[dict]:
    """Macro economic real Arabic news. Cached 1h."""
    key = "news:gnews:econ"
    cached = cache.get(key)
    if cached is not None:
        return cached
    items = _dedup_stories(_prefer_trusted(await _collect(ECONOMIC_QUERIES, "اقتصاد", max_age_days=NEWS_MAX_AGE_DAYS)))
    if items:
        cache.set(key, items, NEWS_CACHE_TTL)
    return items


# المفكرة governance: a calendar entry must actually BE a corporate-action
# announcement — dividend distribution, entitlement/eligibility date, bonus
# shares, capital increase / rights issue, or a general assembly. Google's
# OR-query matches loosely (results coverage, opinion pieces, price-move
# stories all slip through), so every headline is re-verified against these
# keywords before it's allowed into the calendar. Anything else belongs in
# الأخبار, not المفكرة — each tab strictly its own content.
CALENDAR_KEYWORDS = [
    "توزيع", "توزيعات",                      # dividend distribution
    "أحقية", "الأحقية",                       # entitlement/eligibility date
    "منحة",                                   # bonus shares
    "زيادة رأس", "رفع رأس", "أسهم حقوق", "حقوق أولوية",  # capital increase / rights
    "جمعية عمومية", "الجمعية العامة", "جمعيتها العمومية", "الجمعية العمومية",  # general assembly
    "تجزئة",                                  # split
]


def _is_calendar_item(headline: str) -> bool:
    return any(k in (headline or "") for k in CALENDAR_KEYWORDS)


async def fetch_corporate_events(companies: list[tuple[str, str]]) -> list[dict]:
    """Real corporate-action announcements (dividends/entitlements/bonus
    shares/capital increases/AGMs) per portfolio company via the same free
    Google News RSS — a free source that supports the Saudi market, so the
    calendar is never solely dependent on Gemini. Each item is the real
    announcement headline + link + publish date; `companies` is a list of
    (symbol, name). Cached 2h per symbol set. Governed strictly: only
    headlines that actually contain a corporate-action keyword survive
    (see CALENDAR_KEYWORDS), and only from the last 45 days — old chatter
    and generic company news never reach the calendar."""
    # Keyed by the actual symbols, not just how many there are — this used to
    # be `len(companies)`, so EVERY single-company call (i.e. every "المفكرة"
    # tab, which always queries exactly one company) shared one cache slot:
    # whichever company was fetched first got served to every other company
    # viewed within the 2h window, showing real-but-wrong-company news.
    key = "events:gnews:" + ",".join(sorted(symbol for symbol, _ in companies))
    cached = cache.get(key)
    if cached is not None:
        return cached
    # One dedicated, directly-tagged query per company — ALL of them (the old
    # [:10] slice silently dropped companies from the market calendar, which
    # is how a 15-company scan showed a single event). Direct per-query
    # tagging attributes every announcement to its company reliably.
    queries: list[str] = []
    tags: list[str | None] = []
    for symbol, name in companies[:25]:
        if name:
            queries.append(f"{name} توزيعات أرباح OR أحقية OR منحة أسهم OR زيادة رأس المال OR الجمعية العامة")
            tags.append(symbol)
    if not queries:
        return []
    items = [it for it in await _collect(queries, "شركات", max_age_days=CORPORATE_MAX_AGE_DAYS, tags=tags)
             if _is_calendar_item(it["headline"])]
    # التحقّق من نسبة الخبر لشركته: بحث جوجل نيوز يعيد نتائج فضفاضة، فقد يرجع
    # خبر شركة أخرى ضمن استعلام شركة ما. لا نثق بوسم الاستعلام إطلاقًا — نُثبت
    # النسبة فقط إذا ورد اسم الشركة فعلاً في العنوان؛ وإلا نُعيد نسبته للشركة
    # المذكورة صراحةً، وإن لم تُذكر أيّ شركة معروفة نُسقط الخبر (تجنّب الإحراج).
    sym_to_name = {symbol: name for symbol, name in companies if name}
    name_to_sym = sorted(
        [(name, symbol) for symbol, name in companies if name],
        key=lambda x: len(x[0]), reverse=True)  # الأطول أولاً لتفادي مطابقة جزئية
    validated: list[dict] = []
    seen: set = set()
    for it in items:
        hl = it.get("headline") or ""
        tag = it.get("company")
        tag_name = sym_to_name.get(tag)
        real_sym = tag if (tag_name and tag_name in hl) else next(
            (s for nm, s in name_to_sym if nm in hl), None)
        if not real_sym:
            continue  # لا شركة معروفة في العنوان → لا نعرضه منسوبًا لأحد
        it["symbol"] = real_sym
        dk = (real_sym, " ".join(hl.split()))  # مفتاح إزالة التكرار (رمز+عنوان مُطبَّع)
        if dk in seen:
            continue
        seen.add(dk)
        validated.append(it)
    if validated:
        cache.set(key, validated, 2 * 60 * 60)
    return validated


_FLOW_AMOUNT_RE = re.compile(r"(\d[\d,\.]*)\s*(مليار|مليون)\s*ريال")
_FLOW_BUY_WORDS = ["شراء", "شرا", "تدفق"]
_FLOW_SELL_WORDS = ["بيع", "خروج", "تسييل"]

FOREIGN_FLOW_QUERIES = ["صافي تداول الأجانب تاسي", "المستثمر الأجنبي صافي تداول الأسبوعي تاسي"]


async def fetch_weekly_foreign_flow() -> dict | None:
    """CMA only publishes foreign-ownership/trading-activity figures weekly
    (every Thursday), not as a live daily feed — there is no free real-time
    source for this. Best-effort: pull the most recent real Arabic headline
    reporting it (Argaam/Al-Eqtisadiah routinely publish the SAR figure in
    the headline itself) and parse the amount + direction out of the text.
    Returns None (never a guessed number) if no headline actually states a
    parseable amount. Cached 6h — this changes at most once a week anyway."""
    key = "flow:foreign:weekly"
    cached = cache.get(key)
    if cached is not None:
        return cached
    items = await _collect(FOREIGN_FLOW_QUERIES, "أسواق")
    result = None
    for it in items:
        text = it["headline"]
        m = _FLOW_AMOUNT_RE.search(text)
        if not m:
            continue
        amount = float(m.group(1).replace(",", ""))
        if m.group(2) == "مليار":
            amount *= 1_000_000_000
        else:
            amount *= 1_000_000
        direction = (
            "in" if any(w in text for w in _FLOW_BUY_WORDS)
            else "out" if any(w in text for w in _FLOW_SELL_WORDS)
            else None
        )
        if direction is None:
            continue
        result = {
            "amount": amount, "direction": direction,
            "headline": text, "url": it["url"], "source": it["source"],
            "published": it["published"].isoformat() if it["published"] else None,
        }
        break
    if result:
        cache.set(key, result, 6 * 60 * 60)
    return result
