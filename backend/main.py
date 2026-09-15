"""
Smart Portfolio — Backend Entry Point
=====================================
Version: 1.0.0
Philosophy: AI Assists. Human Decides.
"""

import os
import time as _time

# توقيت الرياض مثبّت صراحةً وقسريًّا: كل datetime.now()/date.today() في
# الجدولة وأطوار السوق والتدوير اليومي يفترضه. نفرضه (لا setdefault، حتى لا
# يهزمه TZ موروث)، ثم نتحقّق فعليًّا: إن غابت حزمة tzdata من الصورة فلن تُحَلّ
# «Asia/Riyadh» وتسقط صامتةً إلى UTC (سبب انزياح ٣ ساعات) — عندها نُثبّت إزاحة
# POSIX ثابتة (UTC-3 تعني +3، بلا حاجة لملفات المناطق؛ السعودية بلا توقيت صيفي).
os.environ["TZ"] = "Asia/Riyadh"
if hasattr(_time, "tzset"):
    _time.tzset()
    # time.timezone = ثوانٍ غرب UTC؛ الرياض = -10800. صفرٌ ⇒ فشل الحلّ وسقط لـUTC.
    if _time.timezone != -3 * 3600:
        os.environ["TZ"] = "UTC-3"
        _time.tzset()

import asyncio as _aio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
from loguru import logger

from app.core.config import settings
from app.core.database import init_db
from app.scheduler.scheduler import start_scheduler, stop_scheduler
from app.api.v1.router import api_router


# حالُ إقلاع القاعدة — تُقرأ في `/api/health` فيُعرف العجزُ بلا تخمين.
DB_BOOT_TRIES = 5
DB_BOOT: dict = {"ok": None, "error": None}
SCHED_BOOT: dict = {"ok": None, "error": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    # إثبات توقيت عملية الخادم فعليًّا (لا يُرى عبر exec لأنه عملية منفصلة) —
    # يجب أن تكون الإزاحة +3 (مكة). لو ظهرت +0 فالإصلاح لم يُطبَّق على الخادم.
    from datetime import datetime as _dt, timezone as _tz
    _off = -_time.timezone // 3600
    logger.info(f"🕒 توقيت الخادم: محليًا {_dt.now():%Y-%m-%d %H:%M} (إزاحة {_off:+d}س) · UTC {_dt.now(_tz.utc):%H:%M} — {'مكة ✓' if _off == 3 else '⚠️ ليس مكة'}")
    # Belt-and-suspenders: wipe the in-memory cache on every boot and log the
    # active governance-rules version, so a deploy's scores can NEVER be
    # masked by a warm cache — and the log proves which rules are live.
    try:
        from app.services import cache
        from app.services.governance_rules import rules_version
        cache.clear()
        logger.info(f"🧹 Cache cleared on boot · governance rules version = {rules_version()}")
    except Exception as e:
        logger.warning(f"Boot cache clear failed: {e}")
    # ══ الإقلاعُ لا يموت (D271) ══
    # `init_db` كان مكشوفاً: قاعدةٌ متأخّرةٌ لحظةً عن قبول الاتّصالات —
    # وهو المعتادُ في `docker compose up -d --build` حين تُبنى الحاويتان
    # معاً — ترفع استثناءً في دورة الحياة، فيسقط **التطبيقُ كلُّه** ويراه
    # المالك فارغاً. وهو صنفُ D258 بعينه: عطبٌ في خطوةٍ واحدةٍ يُسقط كلَّ
    # الشاشات، بما فيها ما لا يمسّ القاعدة أصلاً (السوقُ والأسعارُ
    # والقوائم). فيُنتظَر بتراجعٍ محدود، وما بقي بعده **يُعلَن ولا يَقتل**:
    # الخادمُ يقوم، وكلُّ نداءٍ يحتاج القاعدةَ يقول عجزَه بنفسه.
    for _try in range(1, DB_BOOT_TRIES + 1):
        try:
            await init_db()
            DB_BOOT["ok"], DB_BOOT["error"] = True, None
            break
        except Exception as _e:                                   # noqa: BLE001
            DB_BOOT["ok"], DB_BOOT["error"] = False, f"{type(_e).__name__}: {_e}"
            if _try == DB_BOOT_TRIES:
                logger.error("❌ قاعدةُ البيانات لم تستجب بعد {} محاولة — "
                             "الخادمُ يقوم ويُعلن العجزَ في كلّ نداءٍ يحتاجها: {}",
                             DB_BOOT_TRIES, DB_BOOT["error"])
                break
            logger.warning("قاعدةُ البيانات لم تستجب (محاولة {}/{}) — إعادةٌ بعد {}ث: {}",
                           _try, DB_BOOT_TRIES, _try * 2, DB_BOOT["error"])
            await _aio.sleep(_try * 2)
    # استرداد كتب المكتبة العالقة: أي كتاب لم يكتمل تحضيره (ready=False) أو لم
    # يُستخرَج نصّه (has_text=False) — مثلاً أُعيد تشغيل الخادم أثناء معالجته —
    # يُعاد جدولته في الخلفية كي لا يبقى عالقاً في «جارٍ التحضير» للأبد.
    try:
        import asyncio as _asyncio
        from app.core.database import AsyncSessionLocal as _ASL
        from app.models.market import LibraryBook as _LB
        from app.api.v1.endpoints.library import _process_book as _pb
        from sqlalchemy import select as _sel, or_ as _or
        async with _ASL() as _db:
            _stuck = (await _db.execute(
                _sel(_LB.id).where(_or(_LB.ready == False, _LB.has_text == False))  # noqa: E712
            )).scalars().all()
        for _bid in _stuck:
            _asyncio.create_task(_pb(_bid))
        if _stuck:
            logger.info(f"استرداد {len(_stuck)} كتاباً عالقاً في المكتبة.")
    except Exception as _e:
        logger.warning(f"استرداد كتب المكتبة تخطّى: {_e}")
    # قناة «صقر» على تلغرام — تُشغَّل مع الخادم وتسقط وحدها إن تعثّرت.
    # لا تُنتظر: `create_task` داخلها، فلا يتأخّر إقلاع التطبيق لأجل شبكةٍ
    # خارجية. وإن كانت متوقّفة في الإعدادات فلا شيء يحدث أصلاً.
    try:
        from app.services.saqr_bot import start_bot as _start_saqr
        await _start_saqr()
    except Exception as _e:
        logger.warning(f"قناة صقر لم تبدأ: {_e}")
    # تبنّي التكلفة المخزَّنة كمرجع، مرّةً واحدة: بعض الحيازات صُحّحت يدوياً في
    # الماضي مقابل كشف الوسيط، وقيمتها المخزَّنة لا تطابق إعادة تشغيل السجل
    # (نقصٌ في العمليات القديمة أو عمولاتٌ لم تُسجَّل). أُدخِل عمود الفارق بعد
    # ذلك التصحيح، فلو بقي صفراً لمحا أوّلُ تعديلٍ لاحقٍ تصحيحَ المالك بصمت.
    # نقيس الفارق مرّةً ونثبّته؛ ومن يطابق سجلَّه فارقُه صفرٌ ولا يتأثّر.
    try:
        from app.core.database import AsyncSessionLocal as _ASL2
        from app.models.portfolio import Holding as _H
        from app.api.v1.endpoints.transactions import replay_holding as _replay
        from sqlalchemy import select as _sel2
        async with _ASL2() as _db:
            _rows = (await _db.execute(_sel2(_H))).scalars().all()
            _adopted = 0
            for _h in _rows:
                if float(_h.cost_basis_adjustment or 0) != 0 or float(_h.quantity or 0) <= 0:
                    continue
                _delta = float(_h.invested_amount or 0) - float((await _replay(_db, _h.company_id))["invested"])
                if abs(_delta) > 0.01:
                    _h.cost_basis_adjustment = round(_delta, 6)
                    _adopted += 1
            if _adopted:
                await _db.commit()
                logger.info(f"تثبيت تصحيح التكلفة اليدوي لـ {_adopted} حيازة.")
    except Exception as _e:
        logger.warning(f"تثبيت فارق التكلفة تخطّى: {_e}")
    # ══ خطواتُ الإقلاع سبعٌ لا واحدة ══ (D323)
    # كانت في `try` واحدةٍ وجلسةٍ واحدة: فخطأُ خطوةٍ يردّ المعاملةَ ويُسقط
    # **كلَّ ما بعدها** بسطرٍ واحدٍ لا يسمّي الساقط. قِيس على خادم المالك
    # مرّتين في يومٍ واحد: مرّةً من تاريخِ خبرٍ نصٍّ (D320)، ومرّةً من حذف
    # شركةٍ وهميةٍ يتعلّق بها وزنٌ مستهدف — وفي المرّتين سقطت لقطةُ
    # المحفظة والدرجاتُ والأخبارُ والترميماتُ معاً وهي لا تمسّ بعضها.
    #
    # فصارت كلُّ خطوةٍ **بجلستها وبحراستها**: الساقطُ يُسمّى باسمه، وما
    # بعده يعمل. وهو صنفُ D271 نفسُه نُقل من دورة الحياة إلى داخلها.
    async def _boot_step(label: str, fn) -> None:
        from app.core.database import AsyncSessionLocal
        try:
            async with AsyncSessionLocal() as db:
                note = await fn(db)
            if note:
                logger.info("إقلاع · {}: {}", label, note)
        except Exception as e:                                    # noqa: BLE001
            logger.warning("إقلاع · {} تعذّرت — وما بعدها يعمل: {}: {}",
                           label, type(e).__name__, e)

    async def _step_snapshot(db):
        from app.services.snapshots import snapshot_if_missing_today
        await snapshot_if_missing_today(db)
        return None

    async def _step_scores(db):
        from app.services.scores import refresh_company_scores
        await refresh_company_scores(db)
        return None

    async def _step_content(db):
        from app.services.content_engine import refresh_all
        await refresh_all(db)
        return None

    async def _step_dividends(db):
        from app.api.v1.endpoints.dividends import backfill_from_transactions
        n = await backfill_from_transactions(db)
        return f"{n} توزيعاً مُرمَّماً" if n else None

    async def _step_gains(db):
        from app.api.v1.endpoints.transactions import backfill_realized_gains
        n = await backfill_realized_gains(db)
        return f"{n} ربحاً محقَّقاً مُرمَّماً" if n else None

    async def _step_ghosts(db):
        # شركاتٌ وهميةٌ من ميزةِ شعاراتٍ سابقة: بلا أيّ عمليةٍ قطُّ. وما
        # يتعلّق به صفٌّ للمالك يُستثنى ويُسمّى (settings.py · D323).
        from app.api.v1.endpoints.settings import cleanup_directory_companies
        res = (await cleanup_directory_companies(db)).get("data") or {}
        n = res.get("removed_count", 0)
        return f"{n} شركةً وهميةً أُزيلت" if n else None

    async def _step_logos(db):
        from app.api.v1.endpoints.settings import apply_tradingview_logos
        n = await apply_tradingview_logos(db)
        return f"{n} شعاراً" if n else None

    for _label, _fn in (("لقطةُ المحفظة", _step_snapshot),
                        ("درجاتُ الشركات", _step_scores),
                        ("الأخبارُ والأحداث", _step_content),
                        ("ترميمُ التوزيعات", _step_dividends),
                        ("ترميمُ الأرباح المحقَّقة", _step_gains),
                        ("تنظيفُ الشركات الوهمية", _step_ghosts),
                        ("شعاراتُ الشركات", _step_logos)):
        await _boot_step(_label, _fn)
    # والجدولةُ كذلك لا تُسقط الخادم (D271): في D258 أسقطَ خطأُ تعبيرٍ في
    # `CronTrigger` التطبيقَ كلَّه فرآه المالك فارغاً. أُصلح التعبيرُ يومَها،
    # ولم يُصلَح **الصنف**: خطوةٌ واحدةٌ ما زالت قادرةً على قتل كلّ الشاشات.
    # فيُعلَن العجزُ بصوتٍ عالٍ ويبقى الخادمُ قائماً — وحارسُ `scheduler_boot`
    # هو الذي يمنع أن يصير هذا الصمتُ عادةً: يثبت أن الجدولةَ تقوم فعلاً.
    try:
        start_scheduler()
        SCHED_BOOT["ok"], SCHED_BOOT["error"] = True, None
    except Exception as _e:                                       # noqa: BLE001
        SCHED_BOOT["ok"], SCHED_BOOT["error"] = False, f"{type(_e).__name__}: {_e}"
        logger.error("❌ الجدولةُ لم تبدأ — التطبيقُ يعمل والتحديثُ الدوريُّ "
                     "متوقّف: {}", SCHED_BOOT["error"])
    # Warm the whole-market scan in the BACKGROUND if no snapshot exists yet
    # (fresh deploy / first boot): the market widgets (breadth, sectors,
    # distribution, mood) must never sit on "لم تُحسب بيانات السوق بعد"
    # waiting for the next hourly cron slot. Non-blocking — startup finishes
    # immediately; the ~20s concurrent scan fills in behind the scenes.
    # (‏`_aio` مستورَدٌ على مستوى الوحدة — واستيرادُه هنا ثانيةً كان يجعله
    # متغيّراً محلّياً فيسقط الإقلاعُ قبل بلوغه بـ`UnboundLocalError`.)

    async def _warm_movers():
        try:
            from app.services import lastgood
            from app.services.market_movers import get_cached_market_movers, compute_market_movers
            if get_cached_market_movers() is None and lastgood.load("market:movers") is None:
                logger.info("🔥 First-boot market scan warming in background...")
                await compute_market_movers()
        except Exception as e:
            logger.warning(f"Background market-scan warmup failed: {e}")

    _aio.create_task(_warm_movers())

    async def _warm_tadawul():
        """لقطةُ «تداول» عند الإقلاع إن كان المخزنُ فارغاً (D286).

        ══ عقدةٌ واحدةٌ أطفأت كلَّ شيء ══
        قِيس على الخادم: «لقطةُ السوق 0 رمزاً» — ومنها انهار ما بعدها:
        رابطُ صفحة الشركة يُقرأ من اللقطة، وقارئُ XBRL يبني عليه فردَّ
        «بلا ملفّات» لكلّ شركة، فبقيت القوائمُ صفراً فامتنع السعرُ العادل.
        صفرٌ واحدٌ في الأصل أنتج أربعةَ أصفارٍ في الفروع، وكنتُ أطاردها
        فرعاً فرعاً.

        والسببُ أن اللقطةَ مجدوَلةٌ في **ساعات التداول وحدَها**: حاويةٌ
        تُعاد مساءَ الخميس تبقى بلا لقطةٍ إلى الأحد. و«تداول» تخدم آخرَ
        إغلاقٍ في كلّ وقت — فلا عذرَ لفراغٍ يومين.

        فتُقرأ مرّةً عند الإقلاع **إن كانت فارغة**، في الخلفية، ولا تُعاد
        إن كانت عامرة — لا نداءَ بلا حاجة.
        """
        try:
            from app.services.tadawul_market import refresh, usable_rows
            rows, _live, _at = usable_rows()
            if rows:
                return
            logger.info("🔥 لقطةُ «تداول» فارغةٌ عند الإقلاع — تُقرأ مرّةً…")
            rec = await refresh()
            if not rec.get("count"):
                logger.warning(f"لقطةُ الإقلاع لم تُقرأ: {rec.get('error')}")
        except Exception as e:
            logger.warning(f"Boot Tadawul snapshot failed: {e}")

    _aio.create_task(_warm_tadawul())

    async def _warm_deals():
        """سجلُّ الصفقات الخاصة عند الإقلاع إن كان فارغاً (D322).

        جلبُه مرّتان في يوم التداول (‎09:20 و‎16:20). فحاويةٌ تُعاد بعد
        الإغلاق — أو في يوم عطلة — تبقى بلا سجلٍّ إلى الغد، والتبويبُ
        فارغٌ وقد كانت الصفقاتُ مقروءةً مجلوبة. والمصدرُ يخدم مدى شهرٍ
        في كلّ وقت، فلا عذرَ للفراغ. يُقرأ مرّةً **إن غاب**، ولا يُعاد
        إن حضر.
        """
        try:
            from app.services.special_deals import reading, refresh
            if reading():
                return
            await _aio.sleep(20)          # بعد اللقطة، ورحمةً بالمصدر
            logger.info("🔥 سجلُّ الصفقات الخاصة فارغٌ عند الإقلاع — يُقرأ…")
            rec = await refresh()
            if not rec.get("count"):
                logger.warning("صفقاتُ الإقلاع لم تُقرأ: {}", rec.get("error"))
        except Exception as e:                                    # noqa: BLE001
            logger.warning(f"Boot special deals failed: {e}")

    _aio.create_task(_warm_deals())

    async def _warm_betas():
        """بيتا القطاعات إن غابت — بعد اللقطة بمهلة، ومرّةً واحدة (D286).

        كانت شهريةً فقط: مخزنٌ فارغٌ يعني شهراً بلا بيتا مقيسة، وثقةً
        مخصومةً في كلّ شركة. وقِيس على الخادم أنها تُبنى في ثوانٍ حين
        تُطلب — فلا معنى لانتظارٍ شهريّ.
        """
        try:
            from app.services.sector_betas import reading, refresh
            if reading():
                return
            await _aio.sleep(90)          # بعد اللقطة، ورحمةً بالمصدر
            logger.info("🔥 بيتا القطاعات غائبةٌ عند الإقلاع — تُبنى مرّةً…")
            logger.info(f"بيتا الإقلاع: {await refresh()}")
        except Exception as e:
            logger.warning(f"Boot sector betas failed: {e}")

    _aio.create_task(_warm_betas())



    async def _warm_market_calendar():
        # مفكرة السوق الكاملة: عند أول إقلاع (المخزن بارد) شغّل عدّة دفعات RSS
        # متتالية لملء جزء محسوس من السوق فوراً بدل انتظار جدولة الـ١٥ دقيقة.
        try:
            from app.services import lastgood
            from app.services.content_engine import (
                build_market_calendar_rss, build_market_calendar_dividends,
            )
            if lastgood.load("market:calendar:full") is None:
                logger.info("🔥 First-boot market calendar warming in background...")
                for _ in range(4):            # ~100 companies immediately
                    await build_market_calendar_rss()
                await build_market_calendar_dividends()
        except Exception as e:
            logger.warning(f"Background market-calendar warmup failed: {e}")

    _aio.create_task(_warm_market_calendar())
    logger.info("✅ Smart Portfolio is ready.")
    yield
    stop_scheduler()
    logger.info("👋 Smart Portfolio shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Personal Investment Management Platform",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────
# allow_origins="*" + allow_credentials=True is an invalid combination
# (browsers reject it) and unnecessary here anyway — auth is a Bearer
# token in the Authorization header, not a cookie, so no credentials
# need to be shared across origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── API Router ────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/api", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "motto": "حلّل أكثر... قرّر بنفسك.",
        "docs": "/api/docs",
    }

# ── Serve frontend (single-process deployment, no nginx) ───────
FRONTEND_BUILD = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
if os.path.isdir(FRONTEND_BUILD):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_BUILD, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # مسار API غير معروف يجب أن يردّ 404 صريحاً لا صفحة التطبيق.
        # كان يردّ index.html بحالة 200، فيتلقّى العميل HTML حيث ينتظر JSON
        # ويفشل التحليل برسالةٍ غامضة بدل «غير موجود». والأسوأ: مراقبةٌ تفحص
        # «200» تبقى خضراء بعد اختفاء نقطة النهاية كلّها.
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return FileResponse(os.path.join(FRONTEND_BUILD, "index.html"))
