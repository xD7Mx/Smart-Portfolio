"""
Content engine — makes the app never show an empty screen.

Uses Gemini to the fullest and PERSISTS the results to the database so they
stay stable (news/events don't vanish when the cache expires or a new event
happens). Runs on startup (if empty) and daily via the scheduler.

Persisted artefacts:
  • MarketNews    — company + macro economic news
  • MarketEvent   — forward calendar (earnings, dividends, meetings)
  • Notification  — portfolio-derived alerts (movers, target hit, dividends)
"""

import asyncio
import re
from datetime import date, datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import (
    MarketNews, MarketEvent, MarketEventType, Notification,
    NotificationPriority,
)
from app.models.portfolio import Holding, Company
from app.services import cache


async def _portfolio_symbols(db: AsyncSession) -> list[str]:
    rows = await db.execute(select(Company.symbol).where(Company.status != "ARCHIVED"))
    return [r[0] for r in rows.all()]


async def _portfolio_names(db: AsyncSession) -> list[str]:
    rows = await db.execute(select(Company.company_name).where(Company.status != "ARCHIVED"))
    return [r[0] for r in rows.all() if r[0]]


async def _portfolio_symbol_names(db: AsyncSession) -> list[tuple[str, str]]:
    rows = await db.execute(select(Company.symbol, Company.company_name).where(Company.status != "ARCHIVED"))
    return [(r[0], r[1]) for r in rows.all() if r[1]]


async def refresh_news(db: AsyncSession, force: bool = False) -> int:
    """Fetch REAL current headlines from Yahoo (per symbol + macro), store new
    ones and keep the old — the feed stays live and never wipes. Falls back to
    a Gemini digest only if the real fetch returns nothing.

    Runs at most hourly unless forced, so it stays current without churn."""
    last = cache.get("news:refresh:ts")
    if last and not force:
        return 0
    cache.set("news:refresh:ts", datetime.now(timezone.utc).isoformat(), 60 * 60)

    # Retention governance: the feed should read "حديثة" — drop stored
    # headlines older than 14 days so stale items never linger on screen
    # (new ones keep arriving hourly, so the list never empties in practice).
    from sqlalchemy import delete
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    await db.execute(delete(MarketNews).where(MarketNews.published_at < cutoff))

    # 1) real Arabic news (Google News RSS): market-wide + per-company + economic
    from app.services.news_fetcher import fetch_market_news, fetch_economic_news, _story_signature
    pairs = await _portfolio_symbol_names(db)
    names = [n for _, n in pairs]
    real = (await fetch_market_news(names, company_pairs=pairs)) + (await fetch_economic_news())
    # ── الوجه الثالث من مرآة «أرقام»: أخباره من صفحته هو ──────────────────
    # أرقام في سجلّ المصادر أصلاً، لكنه يصلنا **بالواسطة** عبر Google News:
    # عناوينُ منتقاة لا كلُّ ما ينشره، وبتأخير. فتُقرأ صفحته مباشرةً وتُضاف
    # إلى المجموعة نفسها، فيمرّ عليها حارسُ التكرار المتقارب أدناه ولا
    # يتضاعف الخبر الواصل من الطريقين.
    # وفشلُه لا يُسقط الباقي: قائمةٌ فارغة وتحذيرٌ في السجلّ.
    try:
        from app.services.argaam_calendar import fetch_argaam_news
        real += await fetch_argaam_news()
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"Argaam news unavailable: {e}")
    # حارس التكرار المتقارب عبر الدورات: نبني بصمات القصص المخزّنة حديثًا (٧أيام)
    # فلا يُضاف خبرٌ نشرته صحيفة أخرى بصياغة مختلفة كسطر جديد — تُنافس المدفوع.
    recent_cut = datetime.now(timezone.utc) - timedelta(days=7)
    recent_heads = (await db.execute(
        select(MarketNews.headline).where(MarketNews.published_at >= recent_cut)
    )).scalars().all()
    seen_sigs = {_story_signature(h) for h in recent_heads if h}
    added = 0
    for it in real:
        headline = it.get("headline")
        if not headline:
            continue
        dup = (await db.execute(select(MarketNews.id).where(MarketNews.headline == headline))).scalar_one_or_none()
        if dup:
            continue
        sig = _story_signature(headline)
        if sig and sig in seen_sigs:
            continue  # قصّة مطابقة مخزّنة سلفًا بصياغة أخرى → لا تُكرَّر
        seen_sigs.add(sig)
        db.add(MarketNews(
            provider=it.get("source") or "Google News",
            company_symbol=it.get("company"),
            headline=headline[:500],
            summary=(it.get("summary") or None),
            url=(it.get("url") or "")[:1000] or None,
            category=it.get("category"),
            # Real signal, not a guess: was this a recognized, reputable
            # Saudi/regional financial outlet (see news_fetcher.TRUSTED_SOURCES)?
            importance="HIGH" if it.get("trusted") else "MEDIUM",
            published_at=it.get("published"),
        ))
        added += 1

    # 2) Gemini digest only if we still have nothing at all
    have_any = (await db.execute(select(func.count()).select_from(MarketNews))).scalar() or 0
    if not real and (have_any + added) == 0:
        from app.services.ai_content import market_news, economic_news
        symbols = await _portfolio_symbols(db)
        items = (await market_news(symbols)) + (await economic_news())
        for it in items:
            headline = it.get("headline")
            if not headline:
                continue
            dup = (await db.execute(select(MarketNews.id).where(MarketNews.headline == headline))).scalar_one_or_none()
            if dup:
                continue
            db.add(MarketNews(
                provider="AI", company_symbol=it.get("company") or it.get("symbol"),
                headline=headline[:500], category=it.get("category") or it.get("impact") or "أسواق",
                importance="MEDIUM", published_at=datetime.now(timezone.utc),
            ))
            added += 1

    if added:
        await db.commit()
        logger.info(f"Stored {added} news items (Google-News real-first).")
    return added


_EVENT_MAP = {
    "توزيع": MarketEventType.DIVIDEND, "توزيعات": MarketEventType.DIVIDEND,
    "أحقية": MarketEventType.DIVIDEND,
    "زيادة رأس": MarketEventType.RIGHTS_ISSUE, "رفع رأس": MarketEventType.RIGHTS_ISSUE,
    "حقوق أولوية": MarketEventType.RIGHTS_ISSUE, "أسهم حقوق": MarketEventType.RIGHTS_ISSUE,
    "نتائج": MarketEventType.RESULTS, "أرباح": MarketEventType.RESULTS,
    "اندماج": MarketEventType.MERGER, "دمج": MarketEventType.MERGER,
    "استحواذ": MarketEventType.ACQUISITION, "الاستحواذ": MarketEventType.ACQUISITION,
    "جمعية": MarketEventType.AGM, "الجمعية العامة": MarketEventType.AGM,
    "اجتماع": MarketEventType.AGM,
    "منحة": MarketEventType.BONUS, "تجزئة": MarketEventType.SPLIT,
}


def _event_type(text: str) -> MarketEventType:
    for k, v in _EVENT_MAP.items():
        if k in (text or ""):
            return v
    return MarketEventType.OTHER


# ── موعدُ الأحقية نوعٌ قائمٌ بذاته ─────────────────────────────────────
# رأى المالك في مفكرة «أرامكو» صفّاً عنوانه «موعد أحقية» ووسمُه **«صرف
# أرباح»**. وهما قراران مختلفان: الأحقيةُ تاريخُ الاستحقاق — من ملك السهم
# قبله استحقّ التوزيع — والصرفُ تاريخُ وصول النقد إلى الحساب. ومن يقرأ
# «صرف أرباح» على صفّ أحقيةٍ يظنّ المال واصلاً وهو لم يُوزَّع بعد.
# ولا يُضاف النوعُ إلى `MarketEventType` لأنه نوعٌ محفوظٌ في قاعدة
# البيانات بنوع تعداديّ (‏PostgreSQL enum) لا يقبل قيمةً جديدة بلا ترحيل،
# وسلامةُ قاعدة البيانات مقدَّمة. فيُفصل في **مخزن المفكرة** وحده — وهو
# ملفٌّ لا جدول — والواجهةُ تعرف الوسم أصلاً (‏ELIGIBILITY).
_ELIGIBILITY_WORDS = ("أحقية", "احقية")


def _cal_type(text: str):
    """وسمُ صفّ المفكرة — يفصل الأحقية عن الصرف قبل أن يُطابَق الجدول."""
    t = text or ""
    if any(w in t for w in _ELIGIBILITY_WORDS):
        return "ELIGIBILITY"
    return _event_type(t)


# A fixed set of well-known Tadawul blue-chips — used ONLY for the general
# market-wide calendar (Market page), independent of the user's own
# portfolio, so that screen shows real corporate-action news for the market
# at large rather than duplicating the portfolio-only calendar.
_MARKET_BLUE_CHIPS: list[tuple[str, str]] = [
    ("2222", "أرامكو السعودية"), ("1120", "مصرف الراجحي"), ("2010", "سابك"),
    ("7010", "الاتصالات السعودية"), ("1180", "البنك الأهلي السعودي"),
    ("1211", "معادن"), ("2020", "سابك للمغذيات الزراعية"), ("1150", "مصرف الإنماء"),
    ("4001", "أسواق العثيم"), ("2350", "كيان السعودية"), ("4190", "جرير"),
    ("1050", "بنك ساب"), ("2280", "المراعي"), ("4030", "البحري"), ("2380", "بترورابغ"),
    ("1010", "بنك الرياض"), ("1060", "البنك الأول"), ("1140", "بنك البلاد"),
    ("2082", "أكوا باور"), ("5110", "الشركة السعودية للكهرباء"), ("4013", "د. سليمان الحبيب"),
    ("4002", "المواساة للخدمات الطبية"), ("7020", "اتحاد اتصالات"),
    ("4300", "دار الأركان للتطوير العقاري"), ("4321", "سينومي سنترز"),
]


# ── فصل «تاريخ الحدث» عن «تاريخ النشر» ─────────────────────────────────────
# العطل الجذري في المفكرة: عناصر RSS كانت تُؤرَّخ بـ pubDate — وهو تاريخ نشر
# المقال لا تاريخ الحدث. فحين يُعيد موقعٌ نشر إعلانِ توزيعاتٍ قديم، يصل بتاريخ
# اليوم ويهبط في سلّة «اليوم» بالواجهة. النافذة الزمنية لم تكن تحمي لأنها تقيس
# عمر المقال لا عمر الحدث.
#
# القاعدة المعتمدة: المفكرة للأحداث المؤرَّخة حصراً.
#   • عنوان يحمل تاريخاً صريحاً → هذا تاريخ الحدث.
#   • عنوان يحمل فترة ماضية (ربع/سنة سابقة) → إعلان قديم، يُرفض.
#   • عنوان بلا أي علامة زمنية → يُرفض من المفكرة (مكانه قسم الأخبار، حيث
#     تاريخ النشر هو المعنى الصحيح فعلاً).
# النتيجة: مفكرة أصغر وأصدق — ما كان يملؤها جزئياً كان معطوباً.

_AR_MONTHS = {
    "يناير": 1, "كانون الثاني": 1, "فبراير": 2, "شباط": 2, "مارس": 3, "آذار": 3,
    "أبريل": 4, "ابريل": 4, "نيسان": 4, "مايو": 5, "أيار": 5, "يونيو": 6, "يونيه": 6,
    "حزيران": 6, "يوليو": 7, "يوليه": 7, "تموز": 7, "أغسطس": 8, "اغسطس": 8, "آب": 8,
    "سبتمبر": 9, "أيلول": 9, "أكتوبر": 10, "اكتوبر": 10, "تشرين الأول": 10,
    "نوفمبر": 11, "تشرين الثاني": 11, "ديسمبر": 12, "كانون الأول": 12,
}
_QUARTER_WORDS = {"الأول": 1, "الاول": 1, "الثاني": 2, "الثالث": 3, "الرابع": 4}
# نهاية كل ربع تقريباً — تكفي لتصنيف «ماضٍ أم لا»، ولا تُستخدم كتاريخ حدث.
_QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def _headline_event_date(title: str) -> str | None:
    """يستخرج تاريخ الحدث من عنوان الإعلان، أو None إن لم يكن صريحاً.

    يُعيد ISO (YYYY-MM-DD). لا يخمّن: ما لا يحمل تاريخاً كاملاً صريحاً يُعاد
    عنه None ليُرفض العنصر من المفكرة."""
    t = title or ""
    # 1) صيغة رقمية: 2025-06-12 · 12/06/2025 · 12-06-2025
    m = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", t)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b", t)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            # 2) صيغة نصّية عربية: «12 يونيو 2025»
            names = "|".join(sorted(_AR_MONTHS, key=len, reverse=True))
            m = re.search(rf"\b(\d{{1,2}})\s+({names})\s+(20\d{{2}})\b", t)
            if not m:
                return None
            d, mo, y = int(m.group(1)), _AR_MONTHS[m.group(2)], int(m.group(3))
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None                      # تاريخ غير صالح (٣١ فبراير مثلاً)


def _headline_is_stale_period(title: str, today: date | None = None) -> bool:
    """هل يشير العنوان إلى فترة منقضية (ربع أو سنة سابقة)؟ إعلانٌ عن «الربع
    الثاني 2024» في 2026 قديمٌ مهما كان تاريخ نشره."""
    t = title or ""
    today = today or datetime.now(timezone.utc).date()
    m = re.search(r"الربع\s+(\S+)(?:\s+من)?(?:\s+عام)?\s+(20\d{2})", t)
    if m and m.group(1) in _QUARTER_WORDS:
        mo, d = _QUARTER_END[_QUARTER_WORDS[m.group(1)]]
        try:
            return date(int(m.group(2)), mo, d) < today
        except ValueError:
            return False
    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", t)]
    return bool(years) and max(years) < today.year


def calendar_event_date(title: str, published) -> str | None:
    """البوّابة الوحيدة لدخول عنصرٍ نصّي إلى المفكرة. تُعيد تاريخ الحدث (ISO)
    أو None للرفض. `published` لا يُستخدم كتاريخ حدث أبداً — يُقبل فقط للتحقّق
    من التناسق حين يكون العنوان مؤرَّخاً بالفعل."""
    if _headline_is_stale_period(title):
        return None
    return _headline_event_date(title)


def calendar_entry(title: str, published) -> tuple[str | None, str] | None:
    """البوّابة المخفَّفة: تقبل الإعلان حتى بلا تاريخٍ صريح، لكنها **تُصنّف**
    ما تقبله. تُعيد (التاريخ, النوع) أو None للرفض.

    الأنواع الثلاثة، وسببُ الفصل بينها:
      • «event»     — العنوان يحمل تاريخاً صريحاً. هذا وحده يجوز أن يدخل
                      نافذةً زمنية («هذا الأسبوع») لأن موعده معروف.
      • «announced» — لا موعد للحدث، لكن نعرف **متى أُعلن**. حقيقةٌ ماضية
                      تُعرض بوصفها إعلاناً لا موعداً قادماً.
      • «undated»   — إجراءٌ حقيقي بلا أي علامة زمنية. يُقبل ويُعرض في سلّة
                      مستقلّة موسومة، ولا يدخل نافذةً زمنية أبداً.

    هذا هو جواب المخاوف المشروعة من التخفيف: التخفيف يوسّع ما **يُعرض**، ولا
    يمسّ ما **يُؤرَّخ**. لا يمكن لحدثٍ مجهول الموعد أن يظهر تحت «هذا الأسبوع»،
    لأن سلّته لا تُرشَّح زمنياً أصلاً.

    ويبقى المرفوض مرفوضاً: إعلانٌ عن فترةٍ منقضية (ربع/سنة سابقة) لا يدخل
    بأي صفة — قِدَمه معلومٌ لا مجهول."""
    if _headline_is_stale_period(title):
        return None
    exact = _headline_event_date(title)
    if exact:
        return exact, "event"
    pub = str(published)[:10] if published else None
    if pub and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", pub):
        return pub, "announced"
    return None, "undated"


async def company_calendar(symbol: str, name: str) -> list[dict]:
    """مفكرةُ الشركة — **من «أرقام» وحده** (بأمر المالك).

    ══ لماذا مصدرٌ واحد ══
    كانت المفكرة تجمع أربعة مصادر: إعلانات تداول، وأخبار الشركات من RSS،
    وتوزيعات ياهو ومواعيد نتائجه، وأرقام. ثم بُني فوق ذلك منطقُ أسبقيةٍ
    يُسقط صفوف ياهو المتعارضة مع أرقام — أي طبقةُ ترميمٍ فوق خلطٍ لم يُرَد.
    وأمر المالك أن يكون المرجع واحداً: أرقام. وهو المرجع الذي يقيس به،
    فاختلافُ يومين في موعد أحقيةٍ بين مصدرين ليس تفصيلاً — عليه يُبنى قرار.

    ومصدرٌ واحد يُسقط معه منطقُ الأسبقية كلّه: لا تعارضَ يُحسم حين لا
    يتكلّم إلا واحد. فحُذف، ولم يُترك معطَّلاً.

    ══ ما حُذف صراحةً ══
      • `fetch_tadawul_announcements` — تداول يحجب الخادم أصلاً.
      • `fetch_corporate_events` (‏RSS) — أخبارٌ لا مفكرة.
      • `market_service.get_dividends` و`get_earnings_dates` — ياهو.
    وهذه المصادر تبقى حيّةً حيث تخصّ: الأخبار في تبويب الأخبار، وتوزيعات
    ياهو في «ملف التوزيعات». الحذف من **المفكرة** لا من التطبيق.

    ══ الثمن، مصرَّحاً به ══
    سطر «توزيع نقدي X ريال للسهم» كان من ياهو وحده — أرقام يؤرّخ الصرف
    ولا يذكر المبلغ. فيسقط المبلغ من المفكرة. وهو ثمنُ اختيارِ مرجعٍ واحد،
    والمبلغ يبقى في «ملف التوزيعات» و«توزيعاتي المستلمة».

    والشكل الموحَّد كما كان: {headline, url, source, published, kind}.
    """
    items: list[dict] = []

    # ── مرآةُ زرّ «افتح في أرقام» ─────────────────────────────────────────
    # سأل المالك: هل يمكن عكسُ محتوى الزرّ داخل التطبيق؟ والجواب أن القطعة
    # كانت موجودةً وغير موصولة: مفكرة «أرقام» تُجلب وتُخزَّن في
    # `market:calendar:full` وتُعرض في **مفكرة السوق**، ولا يقرؤها تبويب
    # المفكرة للشركة إطلاقاً. ولهذا كان الزرّ ضرورة: يخرج المالك ليرى
    # الجمعيات العمومية وأسهم المنحة والمؤتمرات — وهي ما لا يعرفه ياهو
    # أصلاً، ولا تصل من تداول لأنه يحجب الخادم.
    #
    # فتُقرأ هنا صفوفُ هذا الرمز من المخزن نفسه. ولا نداء شبكةٍ جديد: هو
    # مخزَّنٌ مبنيّ بمهمّةٍ مجدولة، فالقراءة منه مجّانية.
    # والمصدر يبقى موسوماً «أرقام» صراحةً ولا يُنسب إلى تداول — فالفرق بين
    # كشطِ صفحةٍ وتدفّقٍ رسميّ يهمّ المالك أن يعرفه.
    # ── صفحةُ الشركة في «أرقام» — مخزونٌ أسبوعيّ ────────────────────────
    # اقترح المالك مخزناً أسبوعياً، وهو الصواب هنا: جدول مفكرة الشركة
    # (جمعيات · أحقية · صرف) يتغيّر مرّةً كلّ أسابيع، فنداءٌ لكل فتحةِ
    # تبويبٍ إسرافٌ بلا فائدة. والمخزون يجعل التبويب فوريّاً ويُبقي المصدر
    # حيّاً — ويُخدَم القديم إن تعذّر الجلب بدل أن تفرغ الشاشة.
    try:
        from app.services import cache
        ck = f"argaam:company:{symbol}"
        page = cache.get(ck)
        if page is None:
            from app.services.argaam_calendar import fetch_company_page
            page = await fetch_company_page(symbol)
            if page.get("calendar") or page.get("disclosures"):
                cache.set(ck, page, 7 * 24 * 60 * 60)      # أسبوع
        for ev in list(page.get("calendar") or []) + list(page.get("disclosures") or []):
            items.append({
                "headline": ev.get("title") or "",
                "url": ev.get("url"),
                "source": "أرقام",
                "published": ev.get("date"),
                "kind": ev.get("type") or "إعلان",
                "date_kind": ev.get("date_kind") or ("event" if ev.get("date") else "undated"),
            })
    except Exception as e:
        logger.warning(f"company_calendar Argaam page failed for {symbol}: {e}")

    try:
        for ev in _cal_load_store().values():
            if str(ev.get("symbol") or "") != str(symbol):
                continue
            # المخزن مشترك: تكتب فيه بنّاءاتٌ من تداول ومن بيانات السوق
            # أيضاً. والمفكرة من «أرقام» وحده بأمر المالك، فيُرشَّح بالمصدر
            # عند **القراءة** — لا تُعطَّل البنّاءات، فمخرجاتها تُستعمل في
            # مواضع أخرى (مفكرة السوق وسجلّ الأحداث).
            if _src_norm(ev.get("source")) != "أرقام":
                continue
            title = (ev.get("title") or "").strip()
            if not title:
                continue
            items.append({
                "headline": title,
                "url": ev.get("url"),
                "source": ev.get("source") or "أرقام",
                "published": ev.get("date"),
                "kind": ev.get("type") or "إعلان",
                "date_kind": ev.get("date_kind") or ("event" if ev.get("date") else "undated"),
            })
    except Exception as e:
        logger.warning(f"company_calendar Argaam store failed for {symbol}: {e}")

    # منطقُ أسبقية «أرقام» على ياهو كان هنا: يُقارن مفهومَ الحدث بين
    # المصدرين ويُسقط صفَّ ياهو ممّا أرّخه أرقام. وقد سقطت الحاجة إليه
    # مع المصدر الواحد — لا تعارضَ يُحسم حين لا يتكلّم إلا واحد. فحُذف
    # ولم يُترك معطَّلاً: شيفرةٌ ميتة تُقرأ لاحقاً كأنها تعمل.

    # De-dup + newest first (future dates naturally sort to the top).
    seen: set = set()
    uniq = []
    for it in items:
        k = (it["headline"], it.get("published"))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)
    uniq.sort(key=lambda x: x.get("published") or "", reverse=True)
    if not uniq:
        uniq.append({
            "headline": "لا توجد إجراءات شركات معلنة (توزيعات/أحقية/منحة/جمعية) لهذه الشركة حتى الآن.",
            "url": None, "source": None, "published": None, "kind": "معلومة",
        })
    return uniq


# ── مفكرة السوق الكاملة (نِدّ أرقام) — بنّاء تراكمي لكامل السوق ──────────────
# مفكرة السوق لم تعد مقصورة على ٢٥ شركة قيادية: بنّاءٌ مجدوَل يمرّ على كامل كون
# تداول (~٣٩٩ شركة) عبر دفعات دوّارة، ويجمع الأحداث في مخزن ثابت (lastgood)
# فيقرأها الطلب فوراً بلا أي نداء حيّ. مصدران مُهيكلان مجانيان:
#   1) إعلانات الإجراءات (توزيع/أحقية/منحة/زيادة رأس مال/جمعية) عبر RSS المجاني
#      — لا يمسّ حصّة ياهو، فيغطّي كامل السوق بلا حدود.
#   2) تواريخ التوزيعات المُهيكلة (أحقية/صرف قادم + سجل فعلي) من ياهو عبر مسحة
#      دوّارة صغيرة يومياً (محدودة بحصّة آمنة، مُخزَّنة ٢٤ساعة) — الدقّة الزمنية
#      التي تجعلها ندّاً حقيقياً لأرقام.
_CAL_STORE_KEY = "market:calendar:full"      # accumulated event store (lastgood)
_CAL_RSS_CURSOR = "market:calendar:rss_cursor"
_CAL_DIV_CURSOR = "market:calendar:div_cursor"
_CAL_RSS_BATCH = 25                          # RSS hard cap per fetch
_CAL_DIV_BATCH = 20                          # bounded Yahoo pass per daily run
_CAL_MAX_EVENTS = 500
_CAL_PAST_DAYS = 10                          # مفكرة مؤسسية: ماضٍ قصير جدًا (الأحداث القادمة أساسًا)
_CAL_FUTURE_DAYS = 180
_CAL_UNDATED_DAYS = 30       # عمر بقاء الإعلان مجهول الموعد في المخزن


def _universe_pairs() -> list[tuple[str, str]]:
    """Full Tadawul universe as (symbol, arabic_name), stable order."""
    from app.data.market_universe import MARKET_UNIVERSE
    return [(sym, u.get("name_ar") or u.get("name_en") or sym)
            for sym, u in MARKET_UNIVERSE.items()]


def _cal_load_store() -> dict[str, dict]:
    """يُحمَّل المخزن **مطويّاً**: الحدث الواحد مرّةً واحدة.

    تثبيتُ المفتاح يمنع تكراراً جديداً ولا يُصلح ما تراكم قبله — والمخزن
    الموروث ممتلئٌ بنسخٍ وُلدت من المفتاح المتقلّب. فيُطوى عند القراءة
    على (الرمز · التاريخ · العنوان المطبَّع)، ويُرجَّح ما مصدره «أرقام»
    على النسخة العامّة حين يتساويان.
    """
    from app.services import lastgood
    data = lastgood.load(_CAL_STORE_KEY)
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict] = {}
    for k, v in data.items():
        if k.startswith("_") or not isinstance(v, dict):
            continue
        ident = (str(v.get("symbol") or ""), str(v.get("date") or ""),
                 _cal_title_norm(v.get("title") or ""))
        prev = out.get(ident)
        if prev is None or (_src_norm(v.get("source")) == "أرقام"
                            and _src_norm(prev.get("source")) != "أرقام"):
            out[ident] = v
    return {_cal_key(v.get("symbol") or "?", v.get("date") or "بلا-تاريخ",
                     v.get("title") or ""): v for v in out.values()}


def _src_norm(s) -> str:
    """«ارقام» و«أرقام» مصدرٌ واحد بكتابتين — قِيس في المخزن الحيّ: ١٧٠
    تحت الأولى و٥٤ تحت الثانية. وتركُهما يُفسد أيّ عدٍّ أو ترشيحٍ بالمصدر،
    وهو عطبٌ نائم حتى يعتمد عليه شيء."""
    t = (s or "").strip()
    return "أرقام" if t in ("ارقام", "أرقام", "Argaam", "argaam") else t


def _cal_prune_and_save(store: dict[str, dict]) -> None:
    from app.services import lastgood
    today = datetime.now(timezone.utc).date()
    lo = (today - timedelta(days=_CAL_PAST_DAYS)).isoformat()
    hi = (today + timedelta(days=_CAL_FUTURE_DAYS)).isoformat()
    undated_lo = (today - timedelta(days=_CAL_UNDATED_DAYS)).isoformat()
    kept = {}
    for k, ev in store.items():
        d = ev.get("date")
        kind = ev.get("date_kind")
        if not d:
            # مجهول الموعد: يُقاس عمره بأوّل رؤية لا بتاريخ حدثٍ لا يملكه.
            # بلا هذا الفرع كان يُحذف فور كتابته — أي تخفيفٌ بلا أثر.
            if kind != "undated":
                continue                     # صفٌّ قديم بلا تاريخ ولا وسم
            if (ev.get("seen") or "") < undated_lo:
                continue
            kept[k] = ev
            continue
        if d < lo or d > hi:
            continue
        # تطهير رجعيّ: المخزن يحمل عناصر كُتبت قبل فصل «تاريخ الحدث» عن «تاريخ
        # النشر»، فتواريخها تواريخ نشرٍ لا أحداث. نُسقطها الآن بتطبيق البوّابة
        # نفسها على عناوينها. المستثنى: التواريخ المُهيكلة («بيانات السوق»)
        # ومَن وُسم صراحةً بأن تاريخه تاريخ إعلانٍ لا حدث — هذا موصوفٌ بصدق
        # لا مُدَّعى، فلا وجه لإسقاطه.
        if (ev.get("source") != "بيانات السوق" and kind not in ("event", "announced")
                and not calendar_event_date(ev.get("title"), None)):
            continue
        kept[k] = ev
    # Cap: keep the most recent/soonest _CAL_MAX_EVENTS by date desc.
    if len(kept) > _CAL_MAX_EVENTS:
        top = sorted(kept.items(), key=lambda kv: kv[1].get("date") or "", reverse=True)[:_CAL_MAX_EVENTS]
        kept = dict(top)
    lastgood.save(_CAL_STORE_KEY, kept)
    cache.set(_CAL_STORE_KEY, kept, 6 * 60 * 60)


# كلماتٌ عامة ترد في أسماء عشرات الشركات، فمطابقتها وحدها لا تُثبت نسبة.
_NAME_STOP = {"شركة", "الشركة", "مصرف", "بنك", "مجموعة", "السعودية", "القابضة",
              "العربية", "الوطنية", "التعاونية", "للتسويق", "للاستثمار",
              "للتنمية", "الخليج", "المتحدة", "العالمية"}


def _name_matches(name: str, title: str) -> bool:
    """هل يُنسب هذا العنوان إلى هذه الشركة؟ الاسم كاملاً أو كلمةٌ مميّزة منه."""
    n = (name or "").strip()
    t = title or ""
    if not n:
        return False
    if n in t:
        return True
    for tok in n.split():
        if len(tok) >= 4 and tok not in _NAME_STOP and tok in t:
            return True
    return False


def _cal_title_norm(t: str) -> str:
    """تطبيعٌ خفيف للعنوان قبل اشتقاق المفتاح: المسافات المكرّرة والهمزات
    وصيغُ التاء ليست أحداثاً مختلفة. وبدونه يدخل الحدثُ الواحد مرّتين متى
    اختلف مصدراه في حرفٍ واحد."""
    import unicodedata
    t = unicodedata.normalize("NFKC", t or "")
    t = re.sub(r"[\u064B-\u065F\u0640]", "", t)
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")
    return " ".join(t.split())


def _cal_key(symbol: str, date_str: str, title: str) -> str:
    """مفتاحُ الحدث في المخزن — **ثابتٌ عبر العمليات**.

    ══ العطب الذي كان هنا ══
    كان المفتاح `hash(title) % 999983`. و`hash()` على النصّ في بايثون
    **مُملَّحٌ لكل عملية** (‏PYTHONHASHSEED عشوائيّ): الكلمة نفسها تعطي
    ‏226450 ثم 854918 ثم 789174 في ثلاث عمليات. فكلُّ إقلاعٍ للحاوية كان
    يُعيد إضافة كل حدثٍ بمفتاحٍ جديد، فيتراكم المكرَّر بلا حدّ.

    وأثرُه لم يكن تكراراً فحسب: المخزن مسقوف بـ500 حدث، فامتلأ بنسخٍ من
    أحداث «بيانات السوق» و**طرد أحداث «أرقام» الحقيقية**. ولهذا كانت
    مفكرة النهدي تعرض «الموعد المتوقّع» أربع مرّات، ولا تعرض الجمعية
    العمومية ولا صرف الأرباح اللذين يعرضهما أرقام.

    فصار الاشتقاق من `blake2s` — دالّةٌ ثابتة لا تتبدّل بالعملية.
    """
    import hashlib
    h = hashlib.blake2s(_cal_title_norm(title).encode("utf-8"), digest_size=6).hexdigest()
    return f"{symbol}|{date_str}|{h}"


async def build_market_calendar_rss() -> int:
    """One rotating RSS batch of the full universe — free (no Yahoo quota).
    Advances a persistent cursor so consecutive runs sweep the whole market;
    ~399/25 ≈ 16 runs for a full pass. Merges into the accumulated store."""
    from app.services.news_fetcher import fetch_corporate_events
    pairs = _universe_pairs()
    if not pairs:
        return 0
    cursor = int(cache.get(_CAL_RSS_CURSOR) or 0) % len(pairs)
    batch = pairs[cursor:cursor + _CAL_RSS_BATCH]
    if len(batch) < _CAL_RSS_BATCH:
        batch += pairs[:_CAL_RSS_BATCH - len(batch)]   # wrap around
    cache.set(_CAL_RSS_CURSOR, (cursor + _CAL_RSS_BATCH) % len(pairs), 24 * 60 * 60)

    by_symbol = {s: n for s, n in pairs}
    try:
        items = await fetch_corporate_events(batch)
    except Exception as e:
        logger.warning(f"market calendar RSS batch failed: {e}")
        return 0

    store = _cal_load_store()
    added = 0
    for it in items:
        sym = it.get("symbol")
        title = it.get("headline")
        pub = it.get("published")
        if not title:
            continue
        # البوّابة المخفَّفة نفسها في مفكرة السوق الكاملة: يدخل الإعلان حتى
        # بلا تاريخٍ صريح، موسوماً بدقّة تأريخه. الوسم — لا الرفض — هو ما يمنع
        # المجهول من الظهور تحت «هذا الأسبوع».
        got = calendar_entry(title, pub)
        if got is None:                      # فترة منقضية — يبقى مرفوضاً
            continue
        date_str, dkind = got
        k = _cal_key(sym or "?", date_str or "بلا-تاريخ", title)
        if k not in store:
            added += 1
        store[k] = {
            "id": k,
            "type": _cal_type(title),
            "title": title,
            "symbol": sym,
            "company_name": by_symbol.get(sym),
            "date": date_str,
            "date_kind": dkind,
            # المجهول لا تاريخ له يُقاس به عمره، فنُثبّت لحظة أوّل رؤيةٍ له
            # ليُمكن تقليمه لاحقاً بدل أن يسكن المخزن إلى الأبد.
            "seen": (store.get(k) or {}).get("seen") or datetime.now(timezone.utc).date().isoformat(),
            "url": it.get("url"),
            "source": it.get("source"),
        }
    _cal_prune_and_save(store)
    logger.info(f"📅 Market calendar RSS: swept {len(batch)} cos @cursor {cursor}, +{added} new, store={len(store)}.")
    return added


# ── مخزن الأساسيات المتراكم (يخدم فرز الأسهم) ──────────────────────────────
# المشكلة التي يحلّها: كاش ياهو للتوزيعات عمره ٢٤ساعة، والمسحة الدوّارة تغطّي
# ٤٠ شركة/يوم، فلا تكتمل تغطية السوق (٣٩٩) أبداً — ما يُجلب اليوم ينتهي غداً.
# الحلّ: تثبيت كل قيمة تُجلب فعلاً في مخزن دائم يتراكم ويصمد أمام إعادة
# التشغيل، فتكتمل التغطية خلال ~١٠ أيام وتبقى، بلا نداءات إضافية.
_FUND_STORE_KEY = "market:fundamentals"


def _fund_store_put(symbol: str, data: dict) -> None:
    from app.services import lastgood
    store = lastgood.load(_FUND_STORE_KEY)
    store = store if isinstance(store, dict) else {}
    store[symbol] = {**(store.get(symbol) or {}), **data}
    lastgood.save(_FUND_STORE_KEY, store)


def _fund_store_put_many(updates: dict[str, dict]) -> int:
    """كتابة جماعية (قراءة/حفظ مرّة واحدة) — المسحة الليلية تُحدّث مئات الرموز،
    والكتابة رمزاً رمزاً كانت ستُعيد تحميل الملف وحفظه ٣٩٩ مرّة."""
    if not updates:
        return 0
    from app.services import lastgood
    store = lastgood.load(_FUND_STORE_KEY)
    store = store if isinstance(store, dict) else {}
    for sym, data in updates.items():
        store[sym] = {**(store.get(sym) or {}), **data}
    lastgood.save(_FUND_STORE_KEY, store)
    return len(updates)


def fund_store_load() -> dict:
    from app.services import lastgood
    store = lastgood.load(_FUND_STORE_KEY)
    if not isinstance(store, dict):
        return {}
    # lastgood يضيف مفاتيح خدمية (مثل _stale_since) — نستبعدها كما في مخزن المفكرة.
    return {k: v for k, v in store.items() if not k.startswith("_") and isinstance(v, dict)}


_FUND_FULL_CONCURRENCY = 6   # تزامن محدود — رحيمٌ بنقطة ياهو غير الرسمية (تجنّب 429)


async def build_fundamentals_full() -> int:
    """المسحة الليلية الشاملة للأساسيات (٣ فجراً بتوقيت مكة): تجلب توزيعات
    **كامل السوق** دفعةً واحدة فتكتمل تغطية «فرز الأسهم» في ليلة واحدة بدل
    ~٢٠ يوماً من الدفعات الدوّارة.

    لماذا ٣ فجراً تحديداً: عدّاد الحصّة يُصفَّر منتصف ليل مكة، ومسح المحرّكين
    (أكبر مستهلك) لا يبدأ قبل العاشرة صباحاً — فالنافذة فارغة تماماً.

    محكومة بالحصّة ذاتياً: `get_dividends` تُعيد None عند النفاد فتتوقّف
    المسحة بهدوء وتحفظ ما جمعته (لا تُفشل شيئاً ولا تسرق حصّة نهار العمل)."""
    from app.services.market_data import market_service
    from app.services.usage_tracker import can_call

    pairs = _universe_pairs()
    if not pairs:
        return 0
    today = datetime.now(timezone.utc).date().isoformat()
    cutoff12 = (datetime.now(timezone.utc) - timedelta(days=365)).date().isoformat()
    sem = asyncio.Semaphore(_FUND_FULL_CONCURRENCY)
    updates: dict[str, dict] = {}

    async def one(sym: str) -> None:
        if not can_call("yahoo"):
            return                      # نفدت الحصّة — نتوقّف بهدوء
        ysym = f"{sym}.SR" if sym.isdigit() else sym
        async with sem:
            try:
                div = await market_service.get_dividends(ysym)
            except Exception:
                return
            # حقول التقييم في نفس المرور: الجلبة مُكيَّشة ٣٠ يوماً وتُثبَّت في
            # المخزن الدائم من داخل get_company_info، فلا تتكرّر ولا تُستهلك
            # حصّةٌ نهارية. وبها يكتمل «فرز الأسهم» على مستوى السوق.
            if can_call("yahoo"):
                try:
                    await market_service.get_company_info(ysym)
                except Exception:
                    pass
        if not div:
            return
        hist = div.get("history") or []
        paid = sum(h["amount"] for h in hist
                   if h.get("amount") and (h.get("date") or "") >= cutoff12)
        if paid > 0:
            updates[sym] = {"dps_ttm": round(paid, 4), "freq": div.get("frequency"), "asof": today}

    await asyncio.gather(*(one(s) for s, _ in pairs), return_exceptions=True)
    saved = _fund_store_put_many(updates)
    total = len(fund_store_load())
    logger.info(f"💰 Fundamentals full sweep: +{saved} updated · store covers {total}/{len(pairs)} companies.")

    # تسخين القوائم المالية (تُغذّي «الدرجة المالية» في الفرز) — دفعة دوّارة
    # محدودة داخل نفس النافذة الفارغة. القوائم تُحفظ ٣٠ يوماً في الذاكرة
    # **وعلى القرص** (lastgood) فتتراكم وتبقى؛ ٦٠/ليلة تُكمل السوق في ~٥ ليالٍ.
    try:
        await _warm_statements_batch(pairs)
    except Exception as e:
        logger.warning(f"Statements warm batch failed: {e}")
    return saved


_STMT_CURSOR = "market:stmt_cursor"
_STMT_BATCH = 60          # دفعة ليلية محدودة — تُكمل السوق في ~٥ ليالٍ وتبقى
_STMT_RESERVE = 120       # حصّة محجوزة لنهار العمل: لا نلمسها


async def _warm_statements_batch(pairs: list[tuple[str, str]]) -> int:
    """يُسخّن القوائم المالية لدفعة دوّارة فتتوفّر «الدرجة المالية» في الفرز
    بلا نداءات وقت العرض. يحترم احتياطي حصّة لنهار العمل ويتوقّف بهدوء عنده."""
    from app.services.market_data import market_service
    from app.services.usage_tracker import usage as _usage

    def headroom() -> int:
        try:
            u = _usage("yahoo")
            return (u.get("daily_limit") or 0) - (u.get("daily_used") or 0)
        except Exception:
            return 0

    cursor = int(cache.get(_STMT_CURSOR) or 0) % len(pairs)
    batch = pairs[cursor:cursor + _STMT_BATCH]
    if len(batch) < _STMT_BATCH:
        batch += pairs[:_STMT_BATCH - len(batch)]
    cache.set(_STMT_CURSOR, (cursor + _STMT_BATCH) % len(pairs), 24 * 60 * 60)

    sem = asyncio.Semaphore(4)
    done = 0

    async def one(sym: str) -> None:
        nonlocal done
        if headroom() <= _STMT_RESERVE:
            return                       # اقتربنا من الاحتياطي — نتوقّف بهدوء
        async with sem:
            try:
                # الجلب نفسه يحفظ في الذاكرة والقرص؛ لا نحتاج مُخرَجه هنا.
                if await market_service.get_financials(f"{sym}.SR" if sym.isdigit() else sym):
                    done += 1
            except Exception:
                return

    await asyncio.gather(*(one(s) for s, _ in batch), return_exceptions=True)
    logger.info(f"📑 Statements warm: {done}/{len(batch)} @cursor {cursor} (feeds screener finance score).")
    return done


async def build_market_calendar_dividends() -> int:
    """One bounded, rotating Yahoo pass for STRUCTURED dividend dates (exact
    ex/pay + recent paid history) — the precision that matches أرقام. Capped
    at _CAL_DIV_BATCH symbols/run and self-throttled (get_dividends returns
    None once the daily Yahoo quota is spent), so the 100/day ceiling is
    protected. Cached 24h per symbol → whole market refreshed every ~20 days,
    continuously."""
    from app.services.market_data import market_service
    pairs = _universe_pairs()
    if not pairs:
        return 0
    cursor = int(cache.get(_CAL_DIV_CURSOR) or 0) % len(pairs)
    batch = pairs[cursor:cursor + _CAL_DIV_BATCH]
    if len(batch) < _CAL_DIV_BATCH:
        batch += pairs[:_CAL_DIV_BATCH - len(batch)]
    cache.set(_CAL_DIV_CURSOR, (cursor + _CAL_DIV_BATCH) % len(pairs), 24 * 60 * 60)

    store = _cal_load_store()
    today = datetime.now(timezone.utc).date().isoformat()
    added = 0
    for sym, name in batch:
        ysym = f"{sym}.SR" if sym.isdigit() else sym
        try:
            div = await market_service.get_dividends(ysym)
        except Exception:
            div = None
        if not div:
            continue
        # تراكم دائم لعائد التوزيعات (يخدم فرز الأسهم): كاش التوزيعات عمره
        # ٢٤ساعة فينتهي قبل أن تُكمل المسحة الدوّارة السوق (٤٠/يوم × ١٠ أيام)،
        # فتظلّ التغطية ~١٠٪ للأبد. نُثبّت هنا ما جُلب فعلاً في مخزن دائم
        # (lastgood) فتتراكم التغطية حتى تشمل السوق كاملاً وتبقى — بلا أي
        # نداء إضافي (نحن داخل نداءٍ تمّ أصلاً).
        try:
            hist = div.get("history") or []
            cutoff12 = (datetime.now(timezone.utc) - timedelta(days=365)).date().isoformat()
            paid = sum(h["amount"] for h in hist
                       if h.get("amount") and (h.get("date") or "") >= cutoff12)
            if paid > 0:
                _fund_store_put(sym, {"dps_ttm": round(paid, 4),
                                      "freq": div.get("frequency"),
                                      "asof": today})
        except Exception:
            pass

        rows: list[tuple[str, str, str]] = []   # (title, date, kind)
        if div.get("ex_date"):
            lbl = "تاريخ أحقية التوزيعات القادم" if div["ex_date"] >= today else "آخر تاريخ أحقية للتوزيعات"
            rows.append((f"{lbl}: {div['ex_date']}", div["ex_date"], "أحقية"))
        if div.get("pay_date"):
            lbl = "تاريخ صرف التوزيعات القادم" if div["pay_date"] >= today else "آخر تاريخ صرف للتوزيعات"
            rows.append((f"{lbl}: {div['pay_date']}", div["pay_date"], "توزيع"))
        freq = div.get("frequency")
        for h in (div.get("history") or [])[-3:][::-1]:
            rows.append((f"توزيع نقدي {h['amount']:.2f} ريال للسهم" + (f" ({freq})" if freq else ""),
                         h["date"], "توزيع"))
        for title, date_str, kind in rows:
            k = _cal_key(sym, date_str, title)
            if k not in store:
                added += 1
            store[k] = {
                "id": k, "type": _cal_type(kind), "title": title,
                "symbol": sym, "company_name": name, "date": date_str,
                # موعدٌ قادم لا إعلانٌ وقع — انظر D020.
                "date_kind": "event",
                "url": None, "source": "بيانات السوق",
            }
    _cal_prune_and_save(store)
    logger.info(f"📅 Market calendar dividends: {len(batch)} cos @cursor {cursor}, +{added} new, store={len(store)}.")
    return added


_CAL_EARN_CURSOR = "market:calendar:earn_cursor"
_CAL_EARN_BATCH = 20


async def build_market_calendar_earnings() -> int:
    """مسحة ياهو دوّارة لتواريخ إعلان النتائج المالية القادمة — تصنيف أساسي
    مسبق التحديد ترفعه المفكرة لمستوى الخدمات المدفوعة. محدودة الحصّة (تتوقّف
    ذاتيًا عند نفاد حصّة ياهو)، مُخزَّنة ٢٤ساعة، فتغطّي كامل السوق كل ~٢٠ يومًا."""
    from app.services.market_data import market_service
    pairs = _universe_pairs()
    if not pairs:
        return 0
    cursor = int(cache.get(_CAL_EARN_CURSOR) or 0) % len(pairs)
    batch = pairs[cursor:cursor + _CAL_EARN_BATCH]
    if len(batch) < _CAL_EARN_BATCH:
        batch += pairs[:_CAL_EARN_BATCH - len(batch)]
    cache.set(_CAL_EARN_CURSOR, (cursor + _CAL_EARN_BATCH) % len(pairs), 24 * 60 * 60)

    store = _cal_load_store()
    today = datetime.now(timezone.utc).date().isoformat()
    added = 0
    for sym, name in batch:
        ysym = f"{sym}.SR" if sym.isdigit() else sym
        try:
            earn = await market_service.get_earnings_dates(ysym)
        except Exception:
            earn = None
        nd = earn and earn.get("next_date")
        if not nd:
            continue
        # **المؤكَّد وحده يدخل المفكرة** — بأمر المالك. المصدر يقول في
        # `isEarningsDateEstimate` أتقديرٌ هو أم موعدٌ مُعلَن؛ فإن كان تقديراً
        # يُطرح ولا يُعرض بحال. مفكرةٌ ناقصةٌ صادقة خيرٌ من مفكرةٍ ممتلئة
        # بتواريخ تتغيّر — وعليها تُبنى قراراتُ بيعٍ وشراء.
        est = earn.get("is_estimate")
        if est is True:
            continue
        lbl = ("آخر موعد لإعلان النتائج المالية" if nd < today
               else "موعد إعلان النتائج المالية")
        title = f"{lbl}: {nd}"
        k = _cal_key(sym, nd, title)
        if k not in store:
            added += 1
        store[k] = {
            "id": k, "type": _cal_type("النتائج المالية"), "title": title,
            "symbol": sym, "company_name": name, "date": nd,
            "date_kind": "event",
            "url": None, "source": "بيانات السوق",
            "confirmed": True,
        }
        # مكالمة النتائج موعدٌ رسميٌّ مستقلّ — تُضاف حدثاً قائماً بذاته.
        nc = earn.get("next_call")
        if nc and nc >= today:
            k2 = _cal_key(sym, nc, "مكالمة النتائج")
            if k2 not in store:
                added += 1
            store[k2] = {
                "id": k2, "type": _cal_type("النتائج المالية"),
                "title": f"مكالمة إعلان النتائج: {nc}",
                "symbol": sym, "company_name": name, "date": nc,
                "date_kind": "event",
                "url": None, "source": "بيانات السوق", "confirmed": True,
            }
    _cal_prune_and_save(store)
    logger.info(f"📅 Market calendar earnings: {len(batch)} cos @cursor {cursor}, +{added} new, store={len(store)}.")
    return added


async def build_market_calendar_tadawul() -> int:
    """المصدر الأساسي (مؤسسي): إعلانات «تداول» الرسمية → المخزّن الثابت نفسه.
    مجاني ولا يمسّ حصّة ياهو. يُدمج مع دفعات RSS/التوزيعات؛ لكن إعلانات تداول
    هي الأدقّ والأرسم، فتُوسَم مصدرًا «تداول». عند تعذّر الوصول للموقع الرسمي
    يُعيد 0 بهدوء ويبقى RSS احتياطيًا (لا تنكسر المفكرة)."""
    from app.services.tadawul_announcements import fetch_tadawul_announcements
    try:
        items = await fetch_tadawul_announcements()
    except Exception as e:
        logger.warning(f"Tadawul calendar source unavailable: {e}")
        return 0
    if not items:
        return 0
    by_symbol = {s: n for s, n in _universe_pairs()}
    store = _cal_load_store()
    added = 0
    for it in items:
        sym = it.get("symbol")
        title = it.get("title")
        date_str = (it.get("date") or "")[:10]
        if not title or not date_str:
            continue
        k = _cal_key(sym or "?", date_str, title)
        if k not in store:
            added += 1
        store[k] = {
            "id": k,
            "type": _cal_type(it.get("type") or title),
            "title": title,
            "symbol": sym,
            "company_name": it.get("company_name") or by_symbol.get(sym),
            "date": date_str,
            # مصدرها إعلانات تداول — وقعت لا تُنتظر.
            "date_kind": it.get("date_kind") or "announced",
            "url": it.get("url"),
            "source": it.get("source") or "تداول",
        }
    _cal_prune_and_save(store)
    logger.info(f"📅 Market calendar (تداول رسمي): +{added} new, store={len(store)}.")
    return added


async def build_market_calendar_argaam() -> int:
    """الإفصاحات: الجمعيات العمومية · أسهم المنحة · الأحقية · المؤتمرات.

    ياهو — مصدرنا المؤكَّد — لا يعرف من هذه إلا الأحقية والصرف؛ وتداول يحجب
    خادمنا (٤٠٣ حتى على robots.txt). فبقيت هذه القناة وحدها، وهي كشطُ صفحة
    لا تدفّقاً رسمياً. ولذلك تُوسَم مصدراً «أرقام» صراحةً، ولا تُنسب إلى
    «تداول» ولا تُقدَّم كأنها رسمية.

    والأهمّ: **لا تمسّ ما هو مؤكَّد**. إن عادت فارغةً بقي مخزّن ياهو كما هو،
    ولم يُحذف حرف. الكسر هنا يُنقِص المفكرة ولا يُفسدها.
    """
    from app.services.argaam_calendar import fetch_argaam_calendar
    try:
        items = await fetch_argaam_calendar()
    except Exception as e:
        logger.warning(f"Argaam calendar unavailable: {e}")
        return 0
    if not items:
        return 0
    store = _cal_load_store()
    added = 0
    for it in items:
        sym = it.get("symbol")
        title = it.get("title")
        date_str = (it.get("date") or "")[:10]
        if not sym or not title or not date_str:
            continue
        k = _cal_key(sym, date_str, title)
        if k not in store:
            added += 1
        store[k] = {
            "id": k,
            "type": _cal_type(it.get("type") or title),
            "title": title,
            "symbol": sym,
            "company_name": it.get("company_name"),
            "date": date_str,
            "date_kind": it.get("date_kind") or "event",
            "url": it.get("url"),
            "argaam_id": it.get("argaam_id"),
            "detail_id": it.get("detail_id"),
            "source": "أرقام",
        }
    _cal_prune_and_save(store)
    logger.info(f"📅 Market calendar (أرقام — إفصاحات): +{added} new, store={len(store)}.")
    return added


async def build_market_calendar_disclosures() -> int:
    """الإفصاحات المنشورة — ما صدر لحظةَ صدوره، لا ما يُجدوَل.

    المفكرة تقول «جمعية أرامكو يوم ٢١»، والإفصاح يقول «باعظيم وقّعت عقداً
    اليوم». وكلاهما يخصّ المالك.

    وتُوسَم `date_kind="announced"` فتكتب الواجهة «أُعلن: …» — بلا هذا الوسم
    يقرأ المالك تاريخ **صدور** الإعلان على أنه موعدُ حدثٍ اليوم.
    """
    from app.services.argaam_calendar import fetch_argaam_disclosures
    try:
        items = await fetch_argaam_disclosures()
    except Exception as e:
        logger.warning(f"Argaam disclosures unavailable: {e}")
        return 0
    if not items:
        return 0
    by_symbol = {s: n for s, n in _universe_pairs()}
    store = _cal_load_store()
    added = 0
    for it in items:
        sym, title = it.get("symbol"), it.get("title")
        date_str = (it.get("date") or "")[:10]
        if not sym or not title or not date_str:
            continue
        k = _cal_key(sym, date_str, title)
        if k not in store:
            added += 1
        store[k] = {
            "id": k,
            "type": _cal_type(title),
            "title": title,
            "symbol": sym,
            "company_name": by_symbol.get(sym),
            "date": date_str,
            "date_kind": "announced",
            "url": it.get("url"),
            "argaam_id": it.get("argaam_id"),
            "source": "أرقام",
        }
    _cal_prune_and_save(store)
    logger.info(f"📰 Market calendar (أرقام — إفصاحات منشورة): +{added} new, store={len(store)}.")
    return added


async def market_wide_events() -> list[dict]:
    """مفكرة السوق — reads the accumulated full-market store (built by the
    scheduled RSS + dividend passes over the WHOLE universe), newest first.
    Never triggers a live call per view. Falls back to a live blue-chip RSS
    fetch only while the store is still cold (first runs after deploy)."""
    store = _cal_load_store()
    if store:
        # تنقية علاجية للمخزّن (قد يحوي أخبارًا مِن نسبٍ خاطئ قديم): نُبقي الحدث
        # فقط إن ورد اسم شركته في عنوانه، ونُزيل التكرار (رمز + عنوان مُطبَّع).
        sym_to_name = {s: n for s, n in _universe_pairs()}
        out: list[dict] = []
        seen: set = set()
        # المؤرَّخ أولاً (الأحدث فالأقدم)، والمجهول في الذيل — ترتيبٌ تنازلي
        # على سلسلةٍ فارغة كان يقذف المجهول إلى **صدارة** المفكرة.
        for e in sorted(store.values(),
                        key=lambda e: (bool(e.get("date")), e.get("date") or ""),
                        reverse=True):
            sym = e.get("symbol"); title = e.get("title") or ""
            name = sym_to_name.get(sym)
            # منسوب بالرمز من المصدر نفسه — لا يُطبَّق عليه فلتر ورود الاسم في
            # العنوان. وإدراج «أرقام» هنا ضرورة لا تساهل: عناوين الإفصاحات
            # لا تذكر الشركة أصلاً («جمعية عمومية غير عادية»)، والشركة عمودٌ
            # مستقلّ رُبط برمزه من قائمة الصفحة. فلو طُبّق الفلتر لأسقط
            # الإفصاحات كلَّها بلا استثناء.
            official = (e.get("source") in ("تداول", "أرقام"))
            # نسبة الحدث لشركته: كانت تشترط الاسم المسجَّل **كاملاً وحرفياً**
            # داخل العنوان. والعناوين لا تكتب «جرير للتسويق» بل «جرير»، ولا
            # «الشركة السعودية للكهرباء» بل «كهرباء السعودية» — فكان الفلتر
            # يُسقط الأحداث الصحيحة ويترك المفكرة شبه فارغة.
            # صار يقبل ورود **كلمةٍ مميّزة** من الاسم (٤ أحرف فأكثر، وليست من
            # الكلمات العامة التي تشترك فيها عشرات الشركات) — نسبةٌ محفوظة
            # بلا تعقيم.
            if not official and name and not _name_matches(name, title):
                continue
            dk = (sym, " ".join(title.split()))
            if dk in seen:
                continue
            seen.add(dk)
            out.append(e)
        return out[:_CAL_MAX_EVENTS]
    # Cold-start — المصدر الرسمي أولاً (تداول)، ثم RSS احتياطيًا.
    try:
        if await build_market_calendar_tadawul() > 0:
            return await market_wide_events()
    except Exception:
        pass
    from app.services.news_fetcher import fetch_corporate_events
    items = await fetch_corporate_events(_MARKET_BLUE_CHIPS)
    by_symbol = {sym: name for sym, name in _MARKET_BLUE_CHIPS}
    out = []
    for i, it in enumerate(items[:20]):
        # البوّابة المخفَّفة نفسها في مسار الإقلاع البارد — وإلا اختلف ما يراه
        # المالك في أول تشغيلٍ عمّا يراه بعده.
        got = calendar_entry(it.get("headline"), it.get("published"))
        if got is None:
            continue
        edate, dkind = got
        out.append({
            "id": f"mw-{i}",
            "type": _cal_type(it.get("headline")),
            "title": it.get("headline"),
            "symbol": it.get("symbol"),
            "company_name": by_symbol.get(it.get("symbol")),
            "date": edate,
            "date_kind": dkind,
        })
    return out


async def refresh_events(db: AsyncSession, force: bool = False) -> int:
    """Forward calendar of corporate actions. Real-first: free Google News
    RSS announcements (dividends/rights issues/bonus shares/splits/AGMs) per
    portfolio company — never dependent solely on Gemini. Falls back to a
    Gemini-generated calendar only if the real fetch returns nothing."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    existing = (await db.execute(
        select(func.count()).select_from(MarketEvent).where(MarketEvent.created_at >= today_start)
    )).scalar() or 0
    if existing and not force:
        return 0

    # Calendar governance: المفكرة is strictly for key corporate-action dates
    # (توزيعات/أحقية/منحة/زيادة رأس مال/جمعية عمومية) — purge previously
    # stored rows that were admitted before the strict keyword filter existed,
    # plus anything older than 60 days, so the calendar only ever shows
    # relevant, current entries.
    from app.services.news_fetcher import _is_calendar_item
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    all_events = (await db.execute(select(MarketEvent))).scalars().all()
    purged = 0
    for ev in all_events:
        too_old = ev.event_date is not None and ev.event_date < stale_cutoff
        if too_old or not _is_calendar_item(ev.description or ""):
            await db.delete(ev)
            purged += 1
    if purged:
        await db.commit()
        logger.info(f"Calendar governance: purged {purged} non-corporate-action/stale events.")

    added = 0

    # 1) Real announcements via free RSS.
    from app.services.news_fetcher import fetch_corporate_events
    pairs = await _portfolio_symbol_names(db)
    real = await fetch_corporate_events(pairs)
    for it in real:
        headline = it.get("headline")
        if not headline:
            continue
        # البوّابة نفسها قبل الكتابة في قاعدة البيانات — وإلا خُزّن تاريخ النشر
        # كتاريخ حدثٍ دائم يصعب تنظيفه لاحقاً.
        iso = calendar_event_date(headline, it.get("published"))
        if not iso:
            continue
        edate = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
        desc = headline[:300]
        dup = (await db.execute(select(MarketEvent.id).where(MarketEvent.description == desc))).scalar_one_or_none()
        if dup:
            continue
        db.add(MarketEvent(
            company_symbol=it.get("symbol"),
            event_type=_event_type(headline),
            description=desc,
            event_date=edate,
        ))
        added += 1

    # ══ حُذف: تقويمُ Gemini الاستشرافيّ ══
    # كان يُنادى حين لا يوجد حدثٌ حقيقيّ، **ويكتب ما يخترعه في قاعدة
    # البيانات** (`MarketEvent`) — فتصير المواعيد الموهومة بعد ذلك غير
    # مميَّزة عن الحقيقية، وتُخدَم كأنها مخزّنةٌ موثوقة. وهذا أخطر من
    # عرضها مؤقّتاً: الاختلاق يصير دائماً وموثّقاً.
    # فلا بديل عن الصمت حين يغيب المصدر (الخطّ الأحمر الثاني).
    return added


async def generate_notifications(db: AsyncSession) -> int:
    """Derive real alerts from the current portfolio so the bell is never empty:
    big daily movers and analyst-target proximity. One batch per day."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    existing = (await db.execute(
        select(func.count()).select_from(Notification).where(Notification.created_at >= today_start)
    )).scalar() or 0
    if existing:
        return 0

    from sqlalchemy.orm import selectinload
    from app.services.market_data import market_service
    from app.api.v1.endpoints.holdings import yahoo_symbol, refresh_holdings_prices

    result = await db.execute(select(Holding).options(selectinload(Holding.company)))
    holdings = [h for h in result.scalars().all() if h.company and h.company.status != "ARCHIVED" and float(h.quantity or 0) > 0]
    await refresh_holdings_prices(db, holdings)

    added = 0
    for h in holdings:
        pnl_pct = float(h.unrealized_profit_pct or 0)
        name = h.company.company_name
        if pnl_pct >= 10:
            db.add(Notification(category="PORTFOLIO", priority=NotificationPriority.MEDIUM,
                title=f"{name}: مكسب غير محقق قوي",
                message=f"مركزك في {name} ({h.company.symbol}) رابح بنسبة {pnl_pct:.1f}% — قد يستحق مراجعة."))
            added += 1
        elif pnl_pct <= -8:
            db.add(Notification(category="PORTFOLIO", priority=NotificationPriority.HIGH,
                title=f"{name}: تراجع ملحوظ",
                message=f"مركزك في {name} ({h.company.symbol}) متراجع بنسبة {pnl_pct:.1f}% — راجع أطروحتك الاستثمارية."))
            added += 1
        # analyst target proximity
        info = await market_service.get_company_info(yahoo_symbol(h.company.symbol)) or {}
        tgt = info.get("target_mean_price")
        lp = float(h.last_price or 0)
        if tgt and lp:
            upside = (tgt / lp - 1) * 100
            if upside >= 15:
                db.add(Notification(category="MARKET", priority=NotificationPriority.LOW,
                    title=f"{name}: فرصة محتملة",
                    message=f"متوسط تقدير المحللين {tgt:.2f} أعلى من السعر الحالي بنحو {upside:.0f}%."))
                added += 1

    # Governance attention items (sharia, financial safety, debt-service
    # risk, sector concentration) become real notifications too — the same
    # list shown on the Governance page, so the bell never says something
    # the page itself wouldn't also show.
    from app.services.governance import get_portfolio_governance
    gov = await get_portfolio_governance(db)
    for a in gov.get("attention", []):
        priority = NotificationPriority.HIGH if a["severity"] == "high" else NotificationPriority.MEDIUM
        title = f"{a['name']}: تنبيه حوكمة" if a.get("name") else "تنبيه حوكمة المحفظة"
        db.add(Notification(category="GOVERNANCE", priority=priority, title=title, message=a["message"]))
        added += 1

    if added:
        await db.commit()
        logger.info(f"Generated {added} notifications.")
    return added


async def warm_ai(db: AsyncSession) -> None:
    """Proactively generate every Gemini artefact (evaluation, risk, full
    report, market brief) so the AI works automatically — the user never has
    to open a page to trigger it. Each call is internally cached (6-24h), so
    this costs a handful of Gemini requests per day, fully automatic."""
    from app.core.config import settings
    if not settings.AI_API_KEY:
        return
    try:
        from app.api.v1.endpoints.ai import _portfolio_snapshot, _performance_context, _weekly_context
        from app.services.ai_content import (
            portfolio_evaluation, portfolio_risk, portfolio_report, refresh_market_brief,
        )
        holdings, cash = await _portfolio_snapshot(db)
        if holdings:
            # Warm with the SAME weekly context the endpoints use, so the
            # cache key matches and the first page view is an instant hit.
            performance = await _performance_context(db, holdings)
            weekly = await _weekly_context(db, holdings, performance)
            await portfolio_evaluation(holdings, cash, weekly)
            await portfolio_risk(holdings, cash)
            await portfolio_report(holdings, cash, weekly)

        # The live TASI pulse warms via its own scheduled builder (Gemini-first,
        # rule fallback), which also seeds the snapshot the /summary endpoint serves.
        await refresh_market_brief(db)
        logger.info("AI artefacts warmed (evaluation/risk/report/pulse).")
    except Exception as e:
        logger.warning(f"AI warm-up partial failure: {e}")


async def refresh_all(db: AsyncSession) -> None:
    """Run everything — safe to call on startup and daily."""
    try:
        await refresh_news(db)
        # المصدر الرسمي (تداول) أولاً — يملأ المخزّن الثابت قبل القراءة.
        await build_market_calendar_tadawul()
        # ثمّ الإفصاحات (جمعيات · منح · مؤتمرات) — ما لا يعرفه ياهو ولا يصلنا
        # من تداول المحجوب. تأتي بعده فلا تُزاحم مصدراً رسمياً.
        await build_market_calendar_argaam()
        # ثمّ ما صدر فعلاً — الإفصاحات المنشورة، موسومةً «أُعلن».
        await build_market_calendar_disclosures()
        # خريطة معرّفات أرقام: تُبنى أسبوعياً وتُحفظ، فزرّ «افتح في أرقام»
        # يعمل لكل شركة — والمُدرَج حديثاً يدخل وحده بلا صيانة يدوية.
        try:
            from app.services.argaam_ids import build as _build_argaam_ids
            await _build_argaam_ids()
        except Exception as e:
            logger.warning(f"argaam ids skipped: {e}")
        await refresh_events(db)
        # Pre-warms market_wide_events()'s own 2h cache (see news_fetcher.
        # fetch_corporate_events) so the Market page's calendar — and the
        # news ticker, which also reads this endpoint — never has to pay a
        # live RSS fetch on the first real page view after a restart.
        await market_wide_events()
        await generate_notifications(db)
        await warm_ai(db)
    except Exception as e:
        logger.warning(f"content refresh partial failure: {e}")
