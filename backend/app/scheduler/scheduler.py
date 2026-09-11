"""
Smart Portfolio Scheduler
===========================
Manages all background jobs:
- Market price updates
- AI analysis
- Daily/weekly reports
- Backup
- Log cleanup
"""

from datetime import timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from app.core.config import settings

# توقيت مكة/الرياض صراحةً للجدولة (UTC+3، بلا توقيت صيفي فالإزاحة ثابتة) — كل
# ساعات المهام (`hour=…`) تُفسَّر بتوقيت مكة لا UTC، فتنضبط أطوار السوق (١٠ص–٣م)
# والتدوير اليومي (منتصف الليل) على مكة مهما كان توقيت الحاوية.
_RIYADH_TZ = timezone(timedelta(hours=3))
_scheduler = AsyncIOScheduler(timezone=_RIYADH_TZ)


# ─── Job Functions ────────────────────────────────────────────

async def job_update_market_prices():
    """Full-market movers scan (gainers/losers/advancer-decliner counts) —
    runs hourly during trading hours, not on a tight 15-min interval, since
    Yahoo (the shared price source for the whole site) is an unofficial
    endpoint that can rate-limit/block a server hitting it too often — that
    block would stop prices working everywhere on the site, not just here.
    See app/services/market_movers.py."""
    logger.info("📊 Scheduler: Computing market-wide movers...")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.market_movers import compute_market_movers
        async with AsyncSessionLocal() as db:
            await compute_market_movers(db)
    except Exception as e:
        logger.error(f"Market movers scan failed: {e}")


async def job_directory_sync():
    """مزامنةُ دليل السوق مع «تداول» — أسبوعياً (D242).

    الكونُ كان ساكناً: اكتتابٌ جديدٌ لا يظهر حتى يُضاف بيدٍ وتُبنى حزمة،
    وشركةٌ موقوفةٌ تبقى بسعرها الأخير بلا أن يُقال إنها موقوفة. والمزامنةُ
    لا تحذف أحداً أبداً: تُضيف الجديدَ وتوسم الغائبَ «موقوفاً» وترفع
    الوسمَ إن عاد، وترفض قائمةً قصيرةً لأنها جلبٌ فشل لا سوقٌ تقلّص.
    """
    logger.info("🗂️ Scheduler: syncing market directory with Tadawul...")
    try:
        from app.services.tadawul_sync import sync
        await sync()
    except Exception as e:
        logger.error(f"Directory sync failed: {e}")


async def job_risk_free():
    """المعدَّلُ الخالي من المخاطر بالريال — أسبوعياً (D249).

    محرّكُ القيمة العادلة يرفض العملَ بمعدَّلٍ مفترَض، والقيمةُ في ملفّ
    المعايير فارغةٌ عمداً. فتُقرأ من صكٍّ سياديٍّ عشريٍّ في «تداول» بتاريخها
    وأجلِها؛ وما لم يُفهم لا يُكتب شيءٌ ويبقى المحرّكُ ممتنعاً.
    """
    logger.info("📉 Scheduler: reading SAR risk-free rate from Tadawul sukuk...")
    try:
        from app.services.risk_free import refresh
        rec = await refresh()
        if rec.get("value") is None:
            logger.warning(f"Risk-free unread: {rec.get('error')}")
    except Exception as e:
        logger.error(f"Risk-free refresh failed: {e}")


async def job_compute_screener():
    """Whole-market technical screener scan — one Yahoo history call per
    company, so it runs once daily after the close, never on-demand. Feeds the
    فرز الأسهم page (SMA50/200, RSI, 52w range). See market_screener.py."""
    logger.info("🔎 Scheduler: Computing whole-market technical screener...")
    try:
        from app.services.market_screener import compute_screener
        await compute_screener()
    except Exception as e:
        logger.error(f"Screener scan failed: {e}")


async def job_peer_distribution():
    """توزيعُ الأقران — العتبةُ تُشتقّ من السوق لا تُخترَع.

    يقرأ قوائمَ كل شركةٍ من مخزوننا (بلا نداءاتٍ جديدة) ويحسب نقاطَ القطع
    لكل مؤشّرٍ داخل نمطه، فيصير تقييمُ الشركة بحثاً في جدولٍ لا حساباً.
    يعمل بعد التحليل القطاعيّ لأن مخزونَ القوائم يكون قد امتلأ.
    """
    logger.info("📐 Scheduler: Building peer distribution...")
    try:
        from app.services.peer_distribution import build
        await build()
    except Exception as e:
        logger.error(f"Peer distribution build failed: {e}")


async def job_sector_analysis():
    """التحليل القطاعي — يعمل بعد حساب الفرز (٤:٣٠ عصراً) على نفس البيانات."""
    try:
        from app.services.sector_analysis import compute_sector_analysis
        await compute_sector_analysis()
    except Exception as e:
        logger.error(f"Sector analysis failed: {e}")


async def job_market_pulse():
    """Live TASI market pulse — fired half an hour before the open (pre-open
    outlook) and at the top of every trading hour through the close, so the
    market is read continuously from open to close. Gemini writes the brief;
    a rule-based text is the always-available fallback. The Market page's
    summary card just serves the cached snapshot this produces."""
    logger.info("🛎️ Scheduler: Refreshing live TASI market pulse...")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.ai_content import refresh_market_brief
        async with AsyncSessionLocal() as db:
            await refresh_market_brief(db)
    except Exception as e:
        logger.error(f"Market pulse refresh failed: {e}")


async def job_run_ai_analysis():
    """Daily automatic analysis — company scores + sharia, no button needed."""
    logger.info("🤖 Scheduler: Running automatic company analysis...")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.scores import refresh_company_scores
        from app.services.content_engine import warm_ai
        async with AsyncSessionLocal() as db:
            await refresh_company_scores(db)
            await warm_ai(db)  # Gemini artefacts regenerate automatically
    except Exception as e:
        logger.error(f"Automatic analysis failed: {e}")


async def job_market_calendar_rss():
    """مفكرة السوق الكاملة — دفعة RSS دوّارة على كامل كون تداول (مجانية، لا تمسّ
    حصّة ياهو). تُشغَّل كل ١٥ دقيقة فتُكمل مسحة كاملة للسوق كل ~٤ ساعات."""
    try:
        from app.services.content_engine import build_market_calendar_rss
        await build_market_calendar_rss()
    except Exception as e:
        logger.error(f"Market calendar RSS batch failed: {e}")


async def job_market_calendar_tadawul():
    """المصدر الرسمي (تداول) للمفكرة — يُشغَّل كل ٣٠ دقيقة (٧ص–١١م). أدقّ وأرسم
    من RSS؛ عند تعذّر الوصول يبقى RSS احتياطيًا بلا انقطاع."""
    try:
        from app.services.content_engine import build_market_calendar_tadawul
        await build_market_calendar_tadawul()
    except Exception as e:
        logger.error(f"Market calendar Tadawul batch failed: {e}")


async def job_market_calendar_dividends():
    """مفكرة السوق — مسحة ياهو دوّارة محدودة لتواريخ التوزيعات المُهيكلة (أحقية/
    صرف). محدودة الحصّة وذاتية الكبح، تُشغَّل مرّتين يومياً فتغطّي السوق تدريجياً."""
    try:
        from app.services.content_engine import build_market_calendar_dividends
        await build_market_calendar_dividends()
    except Exception as e:
        logger.error(f"Market calendar dividends batch failed: {e}")


async def job_fundamentals_full():
    """المسحة الليلية الشاملة للأساسيات (٣ فجراً بتوقيت مكة) — تُكمل تغطية
    «فرز الأسهم» (توزيعات كامل السوق) في ليلة واحدة بدل ~٢٠ يوماً. النافذة
    فارغة: الحصّة صُفّرت منتصف الليل، ومسح المحرّكين لا يبدأ قبل العاشرة."""
    try:
        from app.services.content_engine import build_fundamentals_full
        await build_fundamentals_full()
    except Exception as e:
        logger.error(f"Fundamentals full sweep failed: {e}")


async def job_market_calendar_earnings():
    """مفكرة السوق — مسحة ياهو دوّارة لتواريخ إعلان النتائج المالية القادمة
    (تصنيف مسبق التحديد بجودة مدفوعة). محدودة الحصّة وذاتية الكبح، مرّتين يومياً."""
    try:
        from app.services.content_engine import build_market_calendar_earnings
        await build_market_calendar_earnings()
    except Exception as e:
        logger.error(f"Market calendar earnings batch failed: {e}")


async def job_generate_daily_report():
    """Refresh & persist market content (news/events/notifications) daily."""
    logger.info("📋 Scheduler: Refreshing market content...")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.content_engine import refresh_all
        async with AsyncSessionLocal() as db:
            await refresh_all(db)
    except Exception as e:
        logger.error(f"Content refresh failed: {e}")


async def job_backup():
    """Nightly REAL backup: writes a full JSON snapshot of every portfolio
    table to /app/data/backups/ (a compose volume outside the DB container,
    so it survives restarts, rebuilds, and even a total DB-volume loss) and
    keeps the newest 14 copies. Same engine as the manual backup endpoints."""
    logger.info("💾 Scheduler: Running nightly backup...")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.backup_service import write_backup_file
        async with AsyncSessionLocal() as db:
            info = await write_backup_file(db)
            logger.info(f"💾 Nightly backup done: {info['name']} ({info['size']} bytes).")
    except Exception as e:
        logger.error(f"Nightly backup failed: {e}")


async def job_cleanup():
    """Weekly housekeeping: prune old Backup metadata rows so the list can't
    grow forever (backup FILES are already pruned to 14 by the backup job
    itself — this trims the DB-side history to the last 60 entries)."""
    logger.info("🧹 Scheduler: Housekeeping old backup records...")
    try:
        from sqlalchemy import select, delete
        from app.core.database import AsyncSessionLocal
        from app.models.market import Backup
        async with AsyncSessionLocal() as db:
            ids = (await db.execute(
                select(Backup.id).order_by(Backup.created_at.desc()).offset(60)
            )).scalars().all()
            if ids:
                await db.execute(delete(Backup).where(Backup.id.in_(ids)))
                await db.commit()
                logger.info(f"🧹 Pruned {len(ids)} old backup records.")
    except Exception as e:
        logger.error(f"Housekeeping failed: {e}")


async def job_cache_purge():
    """تنظيف يومي خفيف (٠٠:٠٥): يزيل مفاتيح الكاش المنتهية فقط — لا مسح جماعي،
    فلا يُبطِل كاشًا حيًّا ولا يستهلك حصّة مزوّد. يمنع تراكم مفاتيح الأمس المؤرّخة."""
    try:
        from app.services import cache
        removed = cache.purge_expired()
        logger.info(f"🧽 Cache purge: removed {removed} expired keys.")
    except Exception as e:
        logger.error(f"Cache purge failed: {e}")


async def job_daily_snapshot():
    """Record the daily portfolio snapshot after Tadawul close."""
    logger.info("📸 Scheduler: Taking daily portfolio snapshot...")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.snapshots import take_snapshot
        async with AsyncSessionLocal() as db:
            await take_snapshot(db)
    except Exception as e:
        logger.error(f"Daily snapshot failed: {e}")


async def job_daily_portfolio_refresh():
    """Precautionary safeguard, every day at 00:01: proactively refresh every
    holding's live price/market-value/P&L instead of waiting on the first
    real page view of the day to trigger it — so the portfolio never briefly
    shows blank/stale figures the moment the site opens each morning.
    Also runs the same full batch as the manual "تحديث بيانات المحفظة"
    button (رأي الذكاء per company + المفكرة + تحليل الذكاء + الحوكمة):
    the AI opinion/evaluation caches are keyed per-day, so the first minute
    of the new day is exactly when they're cold — warming them here means
    the owner never opens the site to yesterday's opinions."""
    logger.info("🌙 Scheduler: Midnight portfolio data refresh...")
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.core.database import AsyncSessionLocal
        from app.models.portfolio import Holding
        from app.api.v1.endpoints.holdings import refresh_holdings_prices
        async with AsyncSessionLocal() as db:
            holdings = (await db.execute(select(Holding).options(selectinload(Holding.company)))).scalars().all()
            await refresh_holdings_prices(db, holdings)
    except Exception as e:
        logger.error(f"Midnight portfolio refresh failed: {e}")
    try:
        from app.core.database import AsyncSessionLocal
        from app.api.v1.endpoints.settings import refresh_portfolio_data
        async with AsyncSessionLocal() as db:
            await refresh_portfolio_data(db)
        logger.info("🌙 Midnight AI opinions/governance refresh done.")
    except Exception as e:
        logger.error(f"Midnight AI/governance refresh failed: {e}")


# ─── Scheduler Control ────────────────────────────────────────

def start_scheduler():
    if not settings.SCHEDULER_ENABLED:
        logger.info("⚠️ Scheduler is disabled.")
        return

    # Market-wide movers scan — hourly during trading hours (10:00-15:00),
    # not every 15 min: Yahoo is the site's one shared, unofficial price
    # source with no published quota, but tightening the request rate too
    # far risks it rate-limiting/blocking the server outright — which would
    # break prices everywhere on the site at once, not just here. Hourly is
    # meaningfully fresher than the original 2-runs/day without pushing into
    # that risk zone (6 runs/day vs. 28 at a 15-min interval).
    _scheduler.add_job(
        job_update_market_prices,
        CronTrigger(minute=0, hour="10-15", day_of_week="mon-fri"),
        id="market_movers_hourly",
        replace_existing=True,
    )

    # Live TASI market pulse — pre-open outlook at 09:30, then a fresh read at
    # the top of every trading hour (10:00–15:00), so the Market page's summary
    # card follows the session continuously from open to close. Gemini-first,
    # rule-based fallback; the endpoint only serves the cached snapshot.
    _scheduler.add_job(
        job_market_pulse,
        CronTrigger(minute=30, hour=9, day_of_week="mon-fri"),
        id="market_pulse_preopen",
        replace_existing=True,
    )
    _scheduler.add_job(
        job_market_pulse,
        CronTrigger(minute=0, hour="10-15", day_of_week="mon-fri"),
        id="market_pulse_hourly",
        replace_existing=True,
    )

    # مزامنةُ الدليل — الجمعةَ فجراً: السوقُ مغلقٌ والحصّةُ فارغة، وقائمةُ
    # المدرَجين لا تتغيّر أكثرَ من مرّةٍ في الأسبوع عملياً.
    _scheduler.add_job(
        job_directory_sync,
        CronTrigger(day_of_week="fri", hour=4, minute=0),
        id="directory_sync_weekly",
        replace_existing=True,
    )

    # المعدَّلُ الخالي من المخاطر — الجمعةَ بعد مزامنة الدليل بنصف ساعة:
    # نفسُ المضيفِ ونفسُ الجلسةِ المسخَّنة، وعائدُ صكٍّ عشريٍّ لا يتحرّك
    # في اليوم حركةً تُغيّر تقييماً.
    _scheduler.add_job(
        job_risk_free,
        CronTrigger(day_of_week="fri", hour=4, minute=30),
        id="risk_free_weekly",
        replace_existing=True,
    )

    # Whole-market technical screener — weekdays at 16:00, after the movers
    # scan's last run and the Tadawul close, so SMA/RSI reflect the day's
    # final closes. One history call per company → daily, not intraday.
    _scheduler.add_job(
        job_compute_screener,
        CronTrigger(hour=16, minute=0, day_of_week="mon-fri"),
        id="market_screener_daily",
        replace_existing=True,
    )
    # التحليل القطاعي — بعد الفرز بنصف ساعة (يقرأ نفس التواريخ المجلوبة).
    _scheduler.add_job(
        job_sector_analysis,
        CronTrigger(hour=16, minute=30, day_of_week="mon-fri"),
        id="sector_analysis_daily",
        replace_existing=True,
    )

    # توزيعُ الأقران — بعد التحليل القطاعيّ، على المخزون لا على المصدر.
    _scheduler.add_job(
        job_peer_distribution,
        CronTrigger(hour=17, minute=0, day_of_week="mon-fri"),
        id="peer_distribution_daily",
        replace_existing=True,
    )

    # AI analysis — weekdays at 18:00
    _scheduler.add_job(
        job_run_ai_analysis,
        CronTrigger(hour=18, day_of_week="mon-fri"),
        id="ai_analysis",
        replace_existing=True,
    )

    # Daily report — weekdays at 20:00
    _scheduler.add_job(
        job_generate_daily_report,
        CronTrigger(hour=20, day_of_week="mon-fri"),
        id="daily_report",
        replace_existing=True,
    )

    # Backup — daily at 02:00
    _scheduler.add_job(
        job_backup,
        CronTrigger(hour=2),
        id="backup",
        replace_existing=True,
    )

    # Housekeeping — weekly on Sunday at 03:00
    _scheduler.add_job(
        job_cleanup,
        CronTrigger(hour=3, day_of_week="sun"),
        id="log_cleanup",
        replace_existing=True,
    )

    # Daily portfolio snapshot — 15:30 (after Tadawul close, container-local time)
    _scheduler.add_job(
        job_daily_snapshot,
        CronTrigger(hour=15, minute=30),
        id="daily_snapshot",
        replace_existing=True,
    )

    # Precautionary portfolio data refresh — every day at 00:01, so prices/
    # market values are never left blank/stale waiting for the day's first
    # visitor to trigger the refresh.
    _scheduler.add_job(
        job_daily_portfolio_refresh,
        CronTrigger(hour=0, minute=1),
        id="daily_portfolio_refresh",
        replace_existing=True,
    )
    # تنظيف كاش خفيف يومي (٠٠:٠٥) — يزيل المفاتيح المنتهية فقط، بعد تدوير مفاتيح
    # منتصف الليل المؤرّخة، فلا تتراكم في الذاكرة. لا مسح جماعي.
    _scheduler.add_job(
        job_cache_purge,
        CronTrigger(hour=0, minute=5),
        id="cache_purge",
        replace_existing=True,
    )

    # التحديث التلقائي الكامل بديل زر «تحديث بيانات المحفظة» اليدوي (أُزيل من
    # الإعدادات): نفس الدفعة (أسعار الحيازات + رأي الذكاء + المفكرة + تحليل
    # الذكاء + الحوكمة) تعمل ذاتياً قبل الافتتاح وبعد الإغلاق أيام التداول.
    # آمنة ضد الاستخدام الخاطئ بطبيعتها: كل طبقات الذكاء تُخزَّن 24 ساعة
    # والمفكرة ساعتين، فالتشغيل المتكرر في نفس النافذة لا يستهلك حصة إضافية.
    _scheduler.add_job(
        job_daily_portfolio_refresh,
        CronTrigger(hour=9, minute=20, day_of_week="mon-fri"),
        id="portfolio_content_preopen",
        replace_existing=True,
    )
    _scheduler.add_job(
        job_daily_portfolio_refresh,
        CronTrigger(hour=15, minute=40, day_of_week="mon-fri"),
        id="portfolio_content_postclose",
        replace_existing=True,
    )

    # مفكرة السوق الكاملة — دفعة RSS دوّارة كل ١٥ دقيقة (٧ص–١١م) تُغطّي كامل
    # السوق (~٣٩٩ شركة) كل ~٤ ساعات؛ مصدر مجاني لا يمسّ حصّة ياهو.
    _scheduler.add_job(
        job_market_calendar_rss,
        CronTrigger(minute="*/15", hour="7-23"),
        id="market_calendar_rss",
        replace_existing=True,
    )
    # المصدر الرسمي (تداول) — كل ٣٠ دقيقة (٧ص–١١م)، المصدر الأساسي للمفكرة.
    _scheduler.add_job(
        job_market_calendar_tadawul,
        CronTrigger(minute="*/30", hour="7-23"),
        id="market_calendar_tadawul",
        replace_existing=True,
    )
    # مسحة تواريخ التوزيعات المُهيكلة — مرّتان يومياً (محدودة الحصّة، دوّارة).
    _scheduler.add_job(
        job_market_calendar_dividends,
        CronTrigger(hour="8,16", minute=10),
        id="market_calendar_dividends",
        replace_existing=True,
    )
    # المسحة الليلية الشاملة للأساسيات (٣ فجراً) — تُكمل تغطية الفرز في ليلة.
    # قبل مسح المحرّكين (١٠ص) وقبل حساب الفرز (٤م) من اليوم نفسه.
    _scheduler.add_job(
        job_fundamentals_full,
        CronTrigger(hour=3, minute=0),
        id="fundamentals_full",
        replace_existing=True,
    )
    # مسحة تواريخ النتائج المالية القادمة — مرّتان يومياً (محدودة الحصّة، دوّارة).
    _scheduler.add_job(
        job_market_calendar_earnings,
        CronTrigger(hour="9,17", minute=20),
        id="market_calendar_earnings",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("✅ Scheduler started with 16 jobs.")


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("🛑 Scheduler stopped.")


def get_scheduler():
    return _scheduler
