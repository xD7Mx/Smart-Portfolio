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
    await init_db()
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
    # Record today's portfolio snapshot if missing (uses cached prices only).
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.snapshots import snapshot_if_missing_today
        async with AsyncSessionLocal() as db:
            await snapshot_if_missing_today(db)
            # Auto-analysis: scores fill themselves in — no manual trigger.
            from app.services.scores import refresh_company_scores
            await refresh_company_scores(db)
            # Populate & persist news / events / notifications so no screen is empty.
            from app.services.content_engine import refresh_all
            await refresh_all(db)
            # Self-heal: create the Dividend row for any historical DIVIDEND/
            # REINVESTMENT transaction that predates the dividends table wiring.
            from app.api.v1.endpoints.dividends import backfill_from_transactions
            backfilled = await backfill_from_transactions(db)
            if backfilled:
                logger.info(f"Backfilled {backfilled} dividend record(s) from historical transactions.")
            # Self-heal: reconstruct realized_gain for SELL transactions
            # recorded before that column existed, by replaying the ledger.
            from app.api.v1.endpoints.transactions import backfill_realized_gains
            gains_backfilled = await backfill_realized_gains(db)
            if gains_backfilled:
                logger.info(f"Backfilled realized_gain for {gains_backfilled} historical SELL transaction(s).")
            # Self-heal: remove any directory-only "ghost" Company rows — a
            # past logo-lookup feature (since removed) briefly created a bare
            # Company row for every symbol in the site's market directory
            # just to resolve a logo, without the Holding row every real
            # add-to-portfolio flow always creates alongside it. A Company
            # with NO Holding row at all was never actually added to the
            # portfolio, so this can never touch a real position — runs
            # automatically on every boot, no button needed, and is a no-op
            # once the database is already clean.
            from app.api.v1.endpoints.settings import cleanup_directory_companies
            cleanup_result = await cleanup_directory_companies(db)
            removed = (cleanup_result.get("data") or {}).get("removed_count", 0)
            if removed:
                logger.info(f"Startup self-heal: removed {removed} directory-only ghost compan{'y' if removed == 1 else 'ies'}.")
            # Apply real, committed TradingView logos to portfolio companies
            # that still lack one — automatic, no button, safe (real
            # holdings only, see apply_tradingview_logos docstring).
            from app.api.v1.endpoints.settings import apply_tradingview_logos
            tv_updated = await apply_tradingview_logos(db)
            if tv_updated:
                logger.info(f"Startup: applied {tv_updated} real TradingView logo(s) to portfolio companies.")
    except Exception as e:
        logger.warning(f"Startup snapshot skipped: {e}")
    start_scheduler()
    # Warm the whole-market scan in the BACKGROUND if no snapshot exists yet
    # (fresh deploy / first boot): the market widgets (breadth, sectors,
    # distribution, mood) must never sit on "لم تُحسب بيانات السوق بعد"
    # waiting for the next hourly cron slot. Non-blocking — startup finishes
    # immediately; the ~20s concurrent scan fills in behind the scenes.
    import asyncio as _aio

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
