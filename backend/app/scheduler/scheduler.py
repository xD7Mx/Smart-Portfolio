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


async def job_argaam_results():
    """نتائجُ الشركات ربعياً وسنوياً من «أرقام» — يومياً بعد الإغلاق (D253).

    الإفصاحاتُ تصل تباعاً في موسم النتائج، وجدولٌ واحدٌ يحمل السوقَ كلَّه —
    فلا نداءَ لكلّ شركة. والرمزُ يُقرأ من معرِّف الرابط لا من اسمٍ مقارَب.
    """
    try:
        from app.services.argaam_results import refresh
        rec = await refresh()
        if rec.get("error"):
            logger.warning(f"Argaam results unread: {rec.get('error')}")
    except Exception as e:
        logger.error(f"Argaam results failed: {e}")


async def job_tadawul_snapshot():
    """لقطةُ السوق من «تداول» — نداءٌ واحدٌ لكلّ الشركات (D251).

    فيها منشوراً: السعرُ والقيمةُ السوقية والمكرّرُ ومضاعفُ الدفترية
    وحدّا العام. تحلّ محلّ الاشتقاق من المزوّد، وتُقرأ بلا حصّةٍ ولا
    نداءٍ لكلّ شركة.
    """
    try:
        from app.services.tadawul_market import refresh
        rec = await refresh()
        if not rec.get("count"):
            logger.warning(f"Tadawul snapshot unread: {rec.get('error')}")
    except Exception as e:
        logger.error(f"Tadawul snapshot failed: {e}")


async def job_ownership():
    """هيكلُ الملكية — دفعةٌ دوّارةٌ أسبوعية بالمتصفّح (D276).

    ══ التطبيقُ يقيس نفسَه ══
    دُرتُ ثلاثَ جولاتِ مسبارٍ لأعرف شكلَ الصفحة، وكلُّ جولةٍ تكلّف المالكَ
    وقتاً ولا تُوصل ميزة. فالقياسُ ينتقل إلى التطبيق: الوظيفةُ تقرأ دفعةً
    صغيرةً كلَّ أسبوع، وتسجّل في السجلّ **كم شركةً قُرئت وكم بنداً** —
    فتُعرَف التغطيةُ من السجلّ بلا مسبارٍ رابع. وما قُرئ يظهر في البطاقة،
    وما لم يُقرأ يبقى غائباً ولا يُختلق.

    وثقيلةٌ عمداً على مهلها: عشرُ شركاتٍ في الأسبوع، والمتصفّحُ صفحةً
    صفحةً، وبعد الإغلاق في عطلة نهاية الأسبوع.
    """
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        from app.services import lastgood
        from app.services.ownership import reading, refresh

        # ══ الرسميُّ أوّلاً ══ (D277)
        # «تداول» تنشر الملكيةَ الأجنبيةَ وأعضاءَ المجلس في صفحة الشركة،
        # وتُقرأ بنداءٍ واحدٍ بلا متصفّح. فتُجرَّب لكلّ شركةٍ أوّلاً، ولا
        # يُفتح المتصفّحُ على «أرقام» إلا لمن لم تُقرأ منه.
        from app.services.tadawul_ownership import reading as t_reading
        from app.services.tadawul_ownership import refresh as t_refresh

        syms = [s for s in main_market(MARKET_UNIVERSE)
                if not t_reading(s) and not reading(s)]
        if not syms:
            return
        done = fresh = 0
        for sym in syms[:25]:
            res = await t_refresh(sym)
            if not res.get("ok"):
                res = await refresh(sym)          # الطبقةُ الثانية بالمتصفّح
            done += 1
            if res.get("ok"):
                fresh += 1
            else:
                logger.warning("هيكلُ الملكية {}: {}", sym, res.get("error"))
        covered = sum(1 for s in main_market(MARKET_UNIVERSE)
                      if t_reading(s) or reading(s))
        logger.info("هيكلُ الملكية: قُرئت {} من {} محاولةً · التغطيةُ {} شركة",
                    fresh, done, covered)
        lastgood.save("ownership:coverage",
                      {"covered": covered, "last_batch": done, "ok": fresh})
    except Exception as e:
        logger.error(f"Ownership refresh failed: {e}")


async def job_special_deals():
    """الصفقاتُ الخاصة — كلَّ ربع ساعةٍ في وقت التداول (D273).

    تُنشَر أثناء الجلسة وبعدها، وهي بطيئةُ التغيّر مقارنةً بالسعر — فربعُ
    ساعةٍ يكفي، ولا تُجلب في مسار طلبِ المستخدم أبداً.
    """
    try:
        from app.services.special_deals import refresh
        rec = await refresh()
        if not rec.get("count"):
            logger.warning(f"Special deals unread: {rec.get('error')}")
    except Exception as e:
        logger.error(f"Special deals failed: {e}")


async def job_xbrl_statements():
    """قوائمُ XBRL الرسمية — دفعةٌ دوّارةٌ يومية (D263).

    الملفُّ الواحد ميجاباتٌ عدّة، والسوقُ ‎273 شركة — فلا تُقرأ دفعةً
    واحدة. تُقرأ دفعةٌ صغيرةٌ كلَّ ليلةٍ فتكتمل التغطيةُ في أسابيعَ وتبقى،
    ويُعاد من شاخ إيداعُه وحدَه. والإفصاحاتُ الجديدةُ تُلتقط بالدورة
    نفسِها — لا انتظارَ موسمٍ ولا نداءَ لكلّ شركةٍ كلَّ يوم.
    """
    # ══ التغطيةُ جِدٌّ لا شعار ══ (D280)
    # كانت الدفعةُ اثنتَي عشرةَ شركةً في الليلة: ‎273 شركةً تحتاج ثلاثةً
    # وعشرين ليلة — وفي هذه المدّة تبقى الدرجةُ والسعرُ العادل بلا قوائمَ
    # رسميةٍ لأكثر السوق. وقال المالك: «أيُّ عجزٍ لإظهار نتيجة شركةٍ خذلان».
    # فصارت أربعين في الدفعة، ودفعتين في الليلة — فتكتمل في أربع ليالٍ.
    #
    # وكانت القائمةُ تُؤخذ من لقطة السوق وحدَها: لقطةٌ لم تصل ⇒ **صفرُ
    # قراءةٍ تلك الليلة**، بلا سببٍ ظاهر. فالنطاقُ من السوق الرئيسة، واللقطةُ
    # تُستعمل إن وُجدت — ولا تُرتهَن التغطيةُ بمصدرٍ آخرَ قد يتأخّر.
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        from app.services.tadawul_market import snapshot
        from app.services.tadawul_xbrl import for_symbol, refresh, stale_symbols

        universe = list(snapshot() or {}) or list(main_market(MARKET_UNIVERSE))
        missing = [s for s in universe if not for_symbol(s)]
        logger.info("XBRL: {} مقروءةٌ من {} — الباقي {}",
                    len(universe) - len(missing), len(universe), len(missing))
        # ‏D579: ومن قُرئ يُعاد إن شاخت قراءتُه — كانت الدفعةُ للفارغ وحدَه، فلا تصل شركةً قُرئت مرّةً
        # نتائجُ ربعٍ جديد أبداً (قِيس: «9 أشهر» لثلاثين شركةً نشرت نتائجَ يونيو)
        due = stale_symbols(universe, 45)
        batch = (missing + [s for s in due if s not in missing])[:40]
        if not batch:
            return
        rec = await refresh(batch)
        logger.info(f"XBRL batch: {rec}")
    except Exception as e:
        logger.error(f"XBRL batch failed: {e}")


async def job_stock_warm():
    """‏D581: صفحاتُ أسهم المحافظ والمراقبة تُحسب مسبقاً — فلا ينتظر المالكُ أوّلَ فتحٍ (حتى 56 ثانية)."""
    try:
        from app.services.stock_warm import warm
        await warm()
    except Exception as e:
        logger.error(f"تجهيزُ صفحات الأسهم: {e}")


async def job_market_warm():
    """‏D583: صفحاتُ أسهم السوق كلِّه — قبل الفجر، بعد القارئ البصريّ الأثقل."""
    try:
        from app.services.stock_warm import warm_market
        await warm_market()
    except Exception as e:
        logger.error(f"تجهيزُ السوق: {e}")


async def job_autopilot():
    """‏D587: رأيُ الطيار الآليّ لكلّ محفظةٍ بالوضعين، بعد الإغلاق — جاهزٌ حين يُفتح."""
    try:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.core.portfolio_scope import set_scope, reset_scope
        from app.models.portfolio import Portfolio
        from app.services.autopilot import opinion
        async with AsyncSessionLocal() as db:
            pids = [p.id for p in (await db.execute(select(Portfolio).execution_options(skip_portfolio_scope=True))).scalars().all()
                    if not p.is_archived]
        for pid in pids:
            set_scope(pid, False)
            try:
                async with AsyncSessionLocal() as db:
                    await opinion(db, force=True)
            finally:
                reset_scope()
        logger.info(f"الطيار الآليّ: {len(pids)} محفظة")
    except Exception as e:
        logger.error(f"الطيار الآليّ: {e}")


async def job_library_wisdom():
    """‏D586: دراسةُ ما لم يُدرَس من كتب المكتبة — ليلاً، كتابٌ مرّةً ويبقى."""
    try:
        from app.services.library_wisdom import digest_all
        await digest_all()
    except Exception as e:
        logger.error(f"المكتبة — المبادئ: {e}")


async def job_results_announcements():
    """‏D580: نتائجُ الشركات من إعلانات «تداول» — من لا نتيجةَ حديثةَ له، الأقدمُ أوّلاً، ثمانون في الجولة."""
    try:
        from app.services.results_announcements import refresh
        logger.info(f"نتائجُ الإعلانات: {await refresh()}")
    except Exception as e:
        logger.error(f"نتائجُ الإعلانات: {e}")


async def job_tadawul_financials():
    """‏D596: جدولُ «المعلومات المالية» لكلّ السوق — الطبقةُ المعتمدة للقوائم (أحدثُ من XBRL في أكثر الأوراق)."""
    try:
        from app.services.tadawul_financials import refresh
        logger.info(f"المعلوماتُ المالية: {await refresh()}")
    except Exception as e:
        logger.error(f"المعلوماتُ المالية: {e}")
    # ‏D622: بعد قراءة الصفحات — أحداثُ رأس المال من الأسهم المصدرة
    try:
        from app.services.split_watch import issued_watch
        logger.info(f"الأسهمُ المصدرة: {issued_watch()}")
    except Exception as e:
        logger.error(f"الأسهمُ المصدرة: {e}")


async def job_close_digest():
    """‏D604: ملخّصُ الإغلاق على تلغرام — المؤشرُ والقطاعاتُ ومحفظتُك وأهمُّ الأخبار، بلا حشو."""
    try:
        from app.services.market_close_digest import send
        logger.info(f"ملخّصُ الإغلاق: {await send()}")
    except Exception as e:
        logger.error(f"ملخّصُ الإغلاق: {e}")


async def job_analyst_opinions():
    """‏D664: آراءُ بيوت الخبرة لكلّ شركات السوق الرئيسيّ من «أرقام» — ليلاً، ثمّ يُعاد بناءُ «التوقعات»."""
    try:
        from app.services.analyst_opinions import refresh
        from app.services.forecasts import build
        got = await refresh()
        logger.info(f"آراءُ بيوت الخبرة: {len(got)} شركةً · التوقعات {len(await build())} بنداً")
    except Exception as e:
        logger.error(f"آراءُ بيوت الخبرة: {e}")


async def job_forecasts():
    """‏D662: تقاريرُ الجهات المرخّصة تُجمع مسبقاً — فلا ينتظر من يفتح «التوقعات» قراءةَ ثلاث جهات."""
    try:
        from app.services.forecasts import build
        logger.info(f"التوقعات: {len(await build())} بنداً")
    except Exception as e:
        logger.error(f"التوقعات: {e}")


async def job_tasi_session():
    """‏D661: جلسةُ «تداول» لتاسي تُحفظ ساعاتُها بعد الإغلاق — فيطول سجلُّ الساعة الرسميُّ وإن لم يفتح أحدٌ الرسم."""
    try:
        from app.services.tasi_history import capture
        logger.info(f"جلسةُ تاسي: {len(await capture())} جلسةً محفوظة")
    except Exception as e:
        logger.error(f"جلسةُ تاسي: {e}")


async def job_split_watch():
    """‏D614: كاشفُ التجزئة — صباحاً بعد الافتتاح يُنبِّه، وبعد الإغلاق يُنبِّه ويحفظ أسعار اليوم مرجعاً للغد."""
    try:
        from app.services.split_watch import job
        logger.info(f"كاشفُ التجزئة: {await job()}")
    except Exception as e:
        logger.error(f"كاشفُ التجزئة: {e}")


async def job_advisor_watch():
    """متابعةُ نصائح صقر (D569): ما نُفّذ، وما تحقّق شرطُه، وما يوقفها — ويُبلَّغ الجديدُ وحده."""
    try:
        from app.services.advisor_memory import watch
        await watch()
    except Exception as e:
        logger.error(f"متابعة المستشار: {e}")


async def job_advisor_weekly():
    """المراجعةُ الأسبوعية (D571): كلَّ خميسٍ مساءً، ورقةٌ لكلّ محفظة في التطبيق وتلغرام."""
    try:
        from app.services.advisor_weekly import weekly
        await weekly()
    except Exception as e:
        logger.error(f"المراجعة الأسبوعية: {e}")


async def job_file_reader():
    """القارئُ البصريّ (D557): ملفّاتٌ قليلةٌ ليلاً بالتتابع — المحفظةُ أوّلاً.

    في **عمليةٍ منفصلة**: قِيس أنّ ملفّين يحجزان ~90MB في الكومة، وعلى خادمٍ بذاكرة 1GB
    لا يُترك ذلك في عملية الخادم — فتُعاد الذاكرةُ كاملةً بانتهائها، ولها مهلةٌ قصوى."""
    import asyncio, sys
    try:
        p = await asyncio.create_subprocess_exec(
            sys.executable, "-c",
            "import asyncio, sys; sys.path.insert(0, '/app'); "
            "from app.services.file_reader import nightly; asyncio.run(nightly())")
        try:
            await asyncio.wait_for(p.wait(), timeout=6 * 60 * 60)   # ‏D560: ينتهي قبل السادسة والنصف
        except asyncio.TimeoutError:
            p.kill()
            logger.warning("القارئ البصري: جاوز ستَّ ساعاتٍ فأُوقف")
    except Exception as e:
        logger.error(f"القارئ البصري: {e}")


async def job_sector_betas():
    """بيتا قطاعيةٌ مقيسةٌ من سوقنا — شهرياً (D257).

    بيتا «أرقام» لكلّ شركةٍ تُنزَع رافعتُها بهامادا ويُؤخذ وسيطُ القطاع.
    والبيتا خاصيّةٌ بطيئةُ التغيّر — فشهرياً يكفي، وحصادُها رحيمٌ بالمصدر.
    """
    try:
        from app.services.sector_betas import refresh
        rec = await refresh()
        if rec.get("error"):
            logger.warning(f"Sector betas unread: {rec.get('error')}")
    except Exception as e:
        logger.error(f"Sector betas failed: {e}")


async def job_valuation_sweep():
    """درجةُ جودةٍ وسعرٌ عادلٌ لكلّ ورقةٍ في السوق — ليلياً (D387).

    بأمر المالك: «جميعُ شركات السوق اجعل لها درجةً للجودة ودرجةً للسعر
    العادل». ولا نداءَ خارجيّ: تُقرأ القوائمُ من الباب الواحد المخزَّن
    واللقطةُ للسعر، فتكتمل أعمدةُ الفرز من عملنا لا من رقمٍ مستعار.
    """
    logger.info("🧮 Scheduler: market-wide quality + fair value sweep...")
    try:
        from app.services import cache
        from app.services.market_valuation_sweep import sweep
        # ‏D653: مسحةُ الإقفال تقيس الآن — لا تقرأ ما حسبته مسحةُ نشرٍ في منتصف الجلسة اليوم (مفتاحُها بيومها لا بساعتها)
        n_old = cache.expire_containing(":fresh:")
        rep = await sweep()
        logger.info(f"🧮 مسحةُ التقييم (أُبطل قبلها {n_old} حساباً سابقاً): {rep}")
    except Exception as e:                                        # noqa: BLE001
        logger.error(f"Valuation sweep failed: {e}")


async def job_engine_ledger():
    """سجلُّ التحقّق — تقديرُ كلِّ شركةٍ يُسجَّل يومياً ليُقاس بالزمن لا بالرأي (‏D638)."""
    try:
        from app.services.engine_ledger import snapshot
        n = snapshot()
        logger.info(f"📒 سجلُّ التحقّق: {n} صفّاً")
    except Exception as e:                                        # noqa: BLE001
        logger.error(f"Engine ledger failed: {e}")


async def job_engine_outcomes():
    """تقريرُ التحقّق الشهريّ — ما قدّره المحرّكُ قبل 90 و180 و365 يوماً مقابل ما حدث (‏D638).
    يُحفظ دائماً، ويُرسَل للمالك متى وُجد أفقٌ مكتمل — ولا رسالةَ فارغةً قبل ذلك."""
    try:
        from app.services import lastgood
        from app.services.engine_ledger import outcomes
        res = outcomes()
        lastgood.save("engine:outcomes", {"at": __import__("datetime").date.today().isoformat(), "res": res})
        if not res:
            return
        lines = ["📒 تقريرُ التحقّق الشهريّ — المحرّكُ مقابل ما حدث فعلاً"]
        for h, v in res.items():
            a = v.get("all") or {}
            lines.append(f"بعد {h} يوماً: {a.get('n')} تقديراً · إصابةُ الاتجاه {a.get('hit')} · "
                         f"ارتباطُ الرتبة {a.get('rank_corr')} · الفجوةُ المُغلَقة {a.get('gap_closed')}")
            for c, b in (v.get("by_conf") or {}).items():
                lines.append(f"   ثقة {c}: {b.get('n')} · إصابة {b.get('hit')} · ارتباط {b.get('rank_corr')}")
            for fp, b in (v.get("by_fp") or {}).items():               # ‏D647: كلُّ إصدارٍ بأيّامه
                lines.append(f"   بصمة {fp}: {b.get('n')} · إصابة {b.get('hit')} · ارتباط {b.get('rank_corr')}")
        from app.services.advisor_memory import notify
        await notify("", lines, raw=True)
    except Exception as e:                                        # noqa: BLE001
        logger.error(f"Engine outcomes failed: {e}")


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

# ══ أسبوعُ التداول السعوديّ — مكتوبٌ مرّةً (D274) ══
# كانت وظائفُ السوق مجدوَلةً «mon-fri»: أسبوعُ عملٍ غربيٌّ في تطبيقٍ سوقُه
# **الأحدُ إلى الخميس**. فأثرُه مرّتان في كلّ أسبوع: يومَ الأحد يفتح السوقُ
# ولا تعمل الوظائف (فيرى المالكُ أرقامَ الخميس)، ويومَ الجمعة تعمل والسوقُ
# مغلق. ويُكتب المدى مرّةً واحدةً لا في ثلاثةَ عشرَ موضعاً — فما تكرّر نصّاً
# يختلف يوماً بلا أن يلاحظه أحد.
# (والأيامُ تُعدّ ولا تُمدّ: APScheduler ‏mon=0…sun=6، فـ«sun-thu» مدًى
#  مقلوبٌ يرفع ValueError في الإقلاع — وهو عطبُ D258 الذي أسقط التطبيق.)
TRADING_DAYS = "sun,mon,tue,wed,thu"


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
        CronTrigger(minute=0, hour="10-15", day_of_week=TRADING_DAYS),
        id="market_movers_hourly",
        replace_existing=True,
    )

    # Live TASI market pulse — pre-open outlook at 09:30, then a fresh read at
    # the top of every trading hour (10:00–15:00), so the Market page's summary
    # card follows the session continuously from open to close. Gemini-first,
    # rule-based fallback; the endpoint only serves the cached snapshot.
    _scheduler.add_job(
        job_market_pulse,
        CronTrigger(minute=30, hour=9, day_of_week=TRADING_DAYS),
        id="market_pulse_preopen",
        replace_existing=True,
    )
    _scheduler.add_job(
        job_market_pulse,
        CronTrigger(minute=0, hour="10-15", day_of_week=TRADING_DAYS),
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

    # لقطةُ «تداول» — كلَّ دقيقةٍ في أيّام التداول وساعاتِه (D260). نداءٌ
    # واحدٌ يغطّي السوق كلَّه، فلا حصّةَ تُستهلك ولا سعرَ يشيخ في شاشة.
    _scheduler.add_job(
        job_tadawul_snapshot,
        # ══ «sun-thu» مدًى مقلوب ══ (عطبٌ أسقط التطبيق · D258)
        # ترتيبُ الأيام في APScheduler ‏mon=0…sun=6، فـ«sun-thu» يعني
        # ‏6 ← 3 فيرفع ValueError **في الإقلاع** — فلا تسقط الجدولةُ
        # وحدَها بل الخلفيةُ كلُّها. والأيامُ تُعدّ ولا تُمدّ.
        CronTrigger(day_of_week=TRADING_DAYS, hour="9-16",
                    minute="*"),
        id="tadawul_snapshot",
        replace_existing=True,
    )

    # هيكلُ الملكية — الجمعةَ فجراً: بطيءُ التغيّر (شهريّ)، والمتصفّحُ
    # ثقيلٌ فلا يُشغَّل في وقت التداول.
    _scheduler.add_job(
        job_ownership,
        CronTrigger(day_of_week="fri", hour=5, minute=0),
        id="ownership_weekly",
        replace_existing=True,
    )

    # الصفقاتُ الخاصة — كلَّ ربع ساعةٍ في أيّام التداول وساعاتِه، وساعةً
    # بعد الإغلاق: كثيرٌ منها يُنشَر بعد الجلسة. (والأيامُ تُعدّ لا تُمدّ.)
    _scheduler.add_job(
        job_special_deals,
        # ══ سجلٌّ تاريخيٌّ لا لقطةٌ لحظية ══ (D295)
        # صار البندُ سجلَّ عملياتٍ شهريّ/أسبوعيّ بأمر المالك، فلا معنى
        # لقراءةٍ كلَّ نصف ساعة: مرّتان في يوم التداول تكفيان — بعد
        # الإغلاق حين تُنشَر صفقاتُ اليوم، وفي الصباح لِما استُدرك.
        CronTrigger(day_of_week=TRADING_DAYS, hour="9,16", minute=20),
        id="special_deals",
        replace_existing=True,
    )

    # نتائجُ الشركات — يومياً ‎17:30 بعد إغلاق السوق ونشر الإفصاحات.
    _scheduler.add_job(
        job_argaam_results,
        CronTrigger(hour=17, minute=30),
        id="argaam_results_daily",
        replace_existing=True,
    )

    # قوائمُ XBRL — دفعةٌ صغيرةٌ كلَّ ليلةٍ بعد الإغلاق بساعات.
    _scheduler.add_job(
        job_xbrl_statements,
        CronTrigger(hour=22, minute=15),
        id="xbrl_statements_daily",
        replace_existing=True,
    )

    # ودفعةٌ ثانيةٌ بعد منتصف الليل: السوقُ مغلقٌ والمضيفُ فارغ — فتكتمل
    # التغطيةُ في أربع ليالٍ بدل ثلاثٍ وعشرين.
    _scheduler.add_job(
        job_xbrl_statements,
        CronTrigger(hour=1, minute=30),
        id="xbrl_statements_night",
        replace_existing=True,
    )
    # ‏D571: المراجعةُ الأسبوعية — الخميسَ بعد آخر جلسة، وقبل مؤتمرات المساء
    _scheduler.add_job(job_advisor_weekly, CronTrigger(day_of_week="thu", hour=19, minute=15),
                       id="advisor_weekly_thu", replace_existing=True)
    # ‏D581: قبل الافتتاح وبعد الإغلاق — والمخزَّنُ يعيش يوماً فيبقى جاهزاً بينهما
    _scheduler.add_job(job_stock_warm, CronTrigger(hour=8, minute=40), id="stock_warm_morning", replace_existing=True)
    _scheduler.add_job(job_stock_warm, CronTrigger(hour=16, minute=10), id="stock_warm_close", replace_existing=True)
    _scheduler.add_job(job_stock_warm, CronTrigger(hour=21, minute=30), id="stock_warm_evening", replace_existing=True)
    _scheduler.add_job(job_market_warm, CronTrigger(hour=6, minute=50), id="market_warm_dawn", replace_existing=True)
    _scheduler.add_job(job_autopilot, CronTrigger(hour=16, minute=35), id="autopilot_close", replace_existing=True)
    _scheduler.add_job(job_library_wisdom, CronTrigger(hour=6, minute=40), id="library_wisdom_dawn", replace_existing=True)
    _scheduler.add_job(job_tadawul_financials, CronTrigger(hour=19, minute=50), id="tadawul_financials_night", replace_existing=True)
    _scheduler.add_job(job_close_digest, CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=15, minute=35), id="close_digest", replace_existing=True)
    _scheduler.add_job(job_split_watch, CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=10, minute=20), id="split_watch_am", replace_existing=True)
    _scheduler.add_job(job_split_watch, CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=15, minute=40), id="split_watch_pm", replace_existing=True)
    _scheduler.add_job(job_tasi_session, CronTrigger(day_of_week=TRADING_DAYS, hour=15, minute=25), id="tasi_session_close", replace_existing=True)
    _scheduler.add_job(job_forecasts, CronTrigger(minute=50), id="forecasts_hourly", replace_existing=True)
    _scheduler.add_job(job_analyst_opinions, CronTrigger(hour=20, minute=40), id="analyst_opinions_night", replace_existing=True)
    try:                                                      # وبعد الإقلاع إن لم يُجمع بعد — لا ينتظر التبويبُ ليلةً كاملة
        from datetime import datetime as _dt
        from apscheduler.triggers.date import DateTrigger
        from app.services.analyst_opinions import stored as _ops_stored
        if not _ops_stored():
            _scheduler.add_job(job_analyst_opinions, DateTrigger(run_date=_dt.now(_RIYADH_TZ) + timedelta(minutes=6), timezone=_RIYADH_TZ),
                               id="analyst_opinions_boot", replace_existing=True)
    except Exception as e:
        logger.error(f"آراءُ بيوت الخبرة/الإقلاع: {e}")
    # وبعد كلِّ إقلاعٍ بأربع دقائق: الإعادةُ تمحو ذاكرةَ الخادم، والمخزَّنُ في القرص لا يقرؤه خادمٌ يعمل —
    # قِيس أنّ تجهيزاً من عمليةٍ أخرى لا يصل الخادمَ الحيّ؛ فالخادمُ يُجهّز نفسَه
    from datetime import datetime as _dt
    from apscheduler.triggers.date import DateTrigger
    _scheduler.add_job(job_stock_warm, DateTrigger(run_date=_dt.now(_RIYADH_TZ) + timedelta(minutes=4), timezone=_RIYADH_TZ),
                       id="stock_warm_boot", replace_existing=True)
    # ‏D580: مساءً بعد إغلاق السوق — إعلاناتُ النتائج تنزل نهاراً
    _scheduler.add_job(job_results_announcements, CronTrigger(hour=20, minute=20), id="results_announcements_evening",
                       replace_existing=True)
    # ‏D569: متابعةُ نصائح المستشار — بعد الإغلاق، ومساءً بعد إعلانات النتائج
    _scheduler.add_job(job_advisor_watch, CronTrigger(hour=15, minute=40), id="advisor_watch_close", replace_existing=True)
    _scheduler.add_job(job_advisor_watch, CronTrigger(hour=21, minute=10), id="advisor_watch_evening", replace_existing=True)
    # ‏D557 · D560: من منتصف الليل حتى السادسة والنصف كحدٍّ أقصى — والسوقُ مغلقٌ والخادمُ هادئ؛
    # وإن ضاقت الذاكرةُ لحظةَ حصاد XBRL انتظر ولم يتوقّف
    _scheduler.add_job(
        job_file_reader,
        CronTrigger(hour=0, minute=20),
        id="file_reader_night",
        replace_existing=True,
    )

    # البيتا القطاعية — أوّلَ جمعةٍ من كلّ شهرٍ فجراً (خاصيّةٌ بطيئةُ التغيّر).
    _scheduler.add_job(
        job_sector_betas,
        CronTrigger(day="1-7", day_of_week="fri", hour=3, minute=0),
        id="sector_betas_weekly",
        replace_existing=True,
    )

    # المعدَّلُ الخالي من المخاطر — الجمعةَ بعد مزامنة الدليل بنصف ساعة:
    # نفسُ المضيفِ ونفسُ الجلسةِ المسخَّنة، وعائدُ صكٍّ عشريٍّ لا يتحرّك
    # في اليوم حركةً تُغيّر تقييماً.
    # مسحةُ التقييم — بعد الإغلاق بساعةٍ ونصف في أيام التداول: القوائمُ
    # والأسعارُ مستقرّةٌ، ولا تُزاحم نبضَ السوق أثناء الجلسة (D387).
    _scheduler.add_job(
        job_valuation_sweep,
        CronTrigger(hour=17, minute=30, day_of_week=TRADING_DAYS),
        id="valuation_sweep_daily",
        replace_existing=True,
    )

    # ‏D638: سجلُّ التحقّق بعد المسحة بساعة وعشر دقائق، وتقريرُه أوّلَ كلّ شهر
    _scheduler.add_job(
        job_engine_ledger,
        CronTrigger(hour=18, minute=40, day_of_week=TRADING_DAYS),
        id="engine_ledger_daily",
        replace_existing=True,
    )
    _scheduler.add_job(
        job_engine_outcomes,
        CronTrigger(day=1, hour=9, minute=10),
        id="engine_outcomes_monthly",
        replace_existing=True,
    )

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
        CronTrigger(hour=16, minute=0, day_of_week=TRADING_DAYS),
        id="market_screener_daily",
        replace_existing=True,
    )
    # التحليل القطاعي — بعد الفرز بنصف ساعة (يقرأ نفس التواريخ المجلوبة).
    _scheduler.add_job(
        job_sector_analysis,
        CronTrigger(hour=16, minute=30, day_of_week=TRADING_DAYS),
        id="sector_analysis_daily",
        replace_existing=True,
    )

    # توزيعُ الأقران — بعد التحليل القطاعيّ، على المخزون لا على المصدر.
    _scheduler.add_job(
        job_peer_distribution,
        CronTrigger(hour=17, minute=0, day_of_week=TRADING_DAYS),
        id="peer_distribution_daily",
        replace_existing=True,
    )

    # AI analysis — weekdays at 18:00
    _scheduler.add_job(
        job_run_ai_analysis,
        CronTrigger(hour=18, day_of_week=TRADING_DAYS),
        id="ai_analysis",
        replace_existing=True,
    )

    # Daily report — weekdays at 20:00
    _scheduler.add_job(
        job_generate_daily_report,
        CronTrigger(hour=20, day_of_week=TRADING_DAYS),
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
        CronTrigger(hour=9, minute=20, day_of_week=TRADING_DAYS),
        id="portfolio_content_preopen",
        replace_existing=True,
    )
    _scheduler.add_job(
        job_daily_portfolio_refresh,
        CronTrigger(hour=15, minute=40, day_of_week=TRADING_DAYS),
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
