"""
Database engine, session factory, and initialization.
Single Source of Truth for all DB access.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
from loguru import logger

from app.core.config import settings


# Convert sync URL to async
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: provides an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables on startup."""
    import app.models  # noqa: F401 — ensure all models are registered
    # عزل بيانات المحافظ على مستوى الجلسة (مُرشِّح القراءة + ختم الإدخال)
    from app.core.portfolio_scope import install_scope_listeners
    install_scope_listeners()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all only creates brand-new tables — it never alters an
        # existing one, so a new column on an already-deployed table (like
        # portfolio_snapshots.governance_score) needs an explicit, idempotent
        # ALTER here. Safe to run every startup; a no-op once applied.
        from sqlalchemy import text

        # كل جملة ترحيل في نقطة حفظ مستقلّة.
        #
        # العلّة التي يعالجها: الترحيلات كلّها تجري في معاملةٍ واحدة، وفشلُ جملةٍ
        # في Postgres يُبطل المعاملة كلّها — فتفشل بعدها **كل** جملة بـ
        # InFailedSqlTransaction، ويُلغى ما نجح قبلها. فجملةٌ واحدة لا تنطبق على
        # هذه القاعدة (عمودٌ قديم غير موجود، أو قيمةُ enum لا تُضاف داخل معاملة)
        # كانت تُسقط كل الأعمدة الجديدة بصمت — فتبدو الميزة كأنها «لا تحفظ»
        # بلا خطأ ظاهر في السجل ولا في الواجهة.
        async def _safe(sql: str) -> bool:
            try:
                async with conn.begin_nested():
                    await conn.execute(text(sql))
                return True
            except Exception as e:
                logger.warning(f"Skipped migration [{sql[:70]}…]: {e}")
                return False

        async def _safe_p(sql: str, params: dict) -> bool:
            try:
                async with conn.begin_nested():
                    await conn.execute(text(sql), params)
                return True
            except Exception as e:
                logger.warning(f"Skipped migration [{sql[:70]}…]: {e}")
                return False

        await _safe("ALTER TABLE portfolio_snapshots ADD COLUMN IF NOT EXISTS governance_score NUMERIC(10,4)")
        # درجة التقييم العام — عمودٌ مستقلّ عن درجة الحوكمة أعلاه. يبدأ فارغاً
        # للقطات القديمة، ويمتلئ من أول لقطةٍ بعد التحديث؛ والواجهة لا ترسم
        # خطّاً حتى تجتمع نقطتان، وتقول ذلك صراحةً بدل أن تعرض فراغاً.
        await _safe("ALTER TABLE portfolio_snapshots ADD COLUMN IF NOT EXISTS evaluation_score NUMERIC(10,4)")
        # قوائم مراقبة متعدّدة: عمود group_id + إسقاط قيد التفرّد العالمي على
        # الرمز (صار الرمز فريدًا داخل مجموعته لا عالميًا).
        await _safe("ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS group_id INTEGER REFERENCES watchlist_groups(id)")
        await _safe("ALTER TABLE watchlist DROP CONSTRAINT IF EXISTS watchlist_symbol_key")
        await _safe("ALTER TABLE goals ADD COLUMN IF NOT EXISTS target_type VARCHAR(20) DEFAULT 'AMOUNT'")
        await _safe("ALTER TABLE holdings ADD COLUMN IF NOT EXISTS profit_reinvested NUMERIC(18,6) DEFAULT 0")
        await _safe("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS realized_gain NUMERIC(18,6)")
        # الكتب المرفوعة قبل نظام المعالجة الخلفية تُعتبَر جاهزة (DEFAULT TRUE)
        # كي لا تظهر عالقة في «جارٍ التحضير»؛ الرفع الجديد يضبطها False ثم True.
        await _safe("ALTER TABLE library_books ADD COLUMN IF NOT EXISTS ready BOOLEAN DEFAULT TRUE")
        await _safe("ALTER TABLE library_books ADD COLUMN IF NOT EXISTS position INTEGER DEFAULT 0")
        await _safe("ALTER TABLE dividends ADD COLUMN IF NOT EXISTS transaction_id INTEGER REFERENCES transactions(id)")
        # REINVESTMENT was a distinct transaction type with special
        # skip-cash/deduct-cash rules per source — simplified away in favor
        # of: every purchase is just a BUY, optionally tagged funding_source
        # for reporting, always deducting cash the same way. Migrate in
        # order: rename the old column (preserving its data) if this deploy
        # still has it, add funding_source fresh if not, recover the real
        # share count for old REINVESTMENT rows (their `quantity` was never
        # populated — only `total_amount`/`price` were), then relabel the
        # type. Each step is idempotent — a no-op once applied.
        try:
            # RENAME COLUMN بلا حارس IF EXISTS — يُفحص المخطّط أوّلاً.
            cols = {row[0] for row in (await conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='transactions'"
            ))).all()}
        except Exception:
            cols = set()
        if "reinvestment_source" in cols and "funding_source" not in cols:
            await _safe("ALTER TABLE transactions RENAME COLUMN reinvestment_source TO funding_source")
        await _safe("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS funding_source VARCHAR(20)")
        # نبذة نشاط الشركة — إضافةٌ آمنة (IF NOT EXISTS) بلا أي مساس ببيانات
        # قائمة، على نفس نمط الترحيلات أعلاه.
        await _safe("ALTER TABLE companies ADD COLUMN IF NOT EXISTS description TEXT")
        await _safe("ALTER TABLE companies ADD COLUMN IF NOT EXISTS description_source VARCHAR(20)")
        await _safe("UPDATE transactions SET quantity = total_amount / price "
                    "WHERE transaction_type = 'REINVESTMENT' AND price > 0 AND (quantity IS NULL OR quantity = 0)")
        await _safe("UPDATE transactions SET transaction_type = 'BUY' WHERE transaction_type = 'REINVESTMENT'")

        # ── Multi-portfolio migration (Phase 1) ───────────────────────────
        # Non-destructive: adds portfolio_id to every per-portfolio table and
        # assigns ALL existing data to the owner's current/default portfolio,
        # so the app behaves EXACTLY as before (one portfolio) until new ones
        # are created. Every statement is idempotent (a no-op once applied).
        try:
            # New Portfolio columns for the multi-portfolio UI.
            for col_sql in (
                "ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS account_id INTEGER",
                "ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS color VARCHAR(10) DEFAULT '#3B82F6'",
                "ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT FALSE",
                "ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS include_in_aggregate BOOLEAN DEFAULT TRUE",
                "ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE",
                "ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0",
                "ALTER TABLE holdings ADD COLUMN IF NOT EXISTS cost_basis_adjustment NUMERIC(18,6) DEFAULT 0",
                "ALTER TABLE holdings ADD COLUMN IF NOT EXISTS paid_in_adjustment_realized NUMERIC(18,6) DEFAULT 0",
                # إدارة السيولة: الجدول يُنشئه create_all، والفهرس يُضاف هنا
                # لأن create_all لا يُعدّل جدولاً قائماً.
                "CREATE INDEX IF NOT EXISTS ix_liquidity_plan_company ON liquidity_plan (company_id)",
                # قلبُ النموذج: مبلغٌ محجوز لكل شركة ← نسبةٌ من دفعةٍ واحدة.
                # العمود القديم يُترك ولا يُحذف: حذفُ عمودٍ فيه بيانات المالك
                # لا رجعة فيه، وتركه لا يضرّ إذ لم يعد يُقرأ.
                "ALTER TABLE liquidity_plan ADD COLUMN IF NOT EXISTS share_pct NUMERIC(10,4)",
                "ALTER TABLE allocation ADD COLUMN IF NOT EXISTS liquidation_threshold_pct NUMERIC(10,4)",
                "ALTER TABLE liquidity_plan ADD COLUMN IF NOT EXISTS exec_tranches INTEGER",
                "ALTER TABLE holdings ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0",
                # العمود القديم قد لا يوجد أصلاً على قاعدةٍ أُنشئت بعد تغيير
                # النموذج — تُترك الجملة تفشل وحدها بلا أثرٍ على غيرها.
                "ALTER TABLE liquidity_plan ALTER COLUMN reserved_amount DROP NOT NULL",
            ):
                await _safe(col_sql)
        except Exception as e:
            logger.warning(f"Skipped portfolio column migration: {e}")

        # New calendar category «جمعية عمومية» (AGM) — add the value to the
        # native Postgres enum so MarketEvent rows can carry it. IF NOT EXISTS
        # makes it a safe no-op once applied. Must be its own transaction:
        # ADD VALUE cannot run inside a block that later uses the new value.
        # ADD VALUE لا يُقبل داخل معاملةٍ في بعض إصدارات Postgres، فيُبطلها
        # ومعها كل ما بعدها — نقطة الحفظ تحصر أثره في نفسه.
        await _safe("ALTER TYPE marketeventtype ADD VALUE IF NOT EXISTS 'AGM'")

        # Ensure exactly one default portfolio exists, and capture its id.
        default_pid = None
        try:
          # نقطة حفظ حول التمهيد كلّه: فشلُ إدخالٍ هنا كان يُبطل المعاملة فتسقط
          # معه كل ترحيلات تعدّد المحافظ التي تليه.
          async with conn.begin_nested():
              row = (await conn.execute(text(
                  "SELECT id FROM portfolio ORDER BY id LIMIT 1"
              ))).first()
              if row is None:
                  await conn.execute(text(
                      "INSERT INTO portfolio (name, currency, mode, is_default, include_in_aggregate) "
                      "VALUES ('المحفظة الرئيسية', 'SAR', 'BUILD', TRUE, TRUE)"
                  ))
                  row = (await conn.execute(text("SELECT id FROM portfolio ORDER BY id LIMIT 1"))).first()
              default_pid = row[0]
              # Mark it default if none is flagged yet.
              await conn.execute(text(
                  "UPDATE portfolio SET is_default = TRUE WHERE id = :pid "
                  "AND NOT EXISTS (SELECT 1 FROM portfolio WHERE is_default = TRUE)"
              ), {"pid": default_pid})
        except Exception as e:
            logger.warning(f"Skipped default-portfolio bootstrap: {e}")

        # Add portfolio_id to every per-portfolio table + backfill to default.
        if default_pid is not None:
            per_portfolio_tables = [
                "holdings", "transactions", "installments", "dividends",
                "bonus_shares", "cash_ledger", "notes", "portfolio_snapshots",
            ]
            for tbl in per_portfolio_tables:
                try:
                    await _safe(
                        f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS portfolio_id INTEGER "
                        f"REFERENCES portfolio(id) ON DELETE CASCADE")
                    await _safe_p(
                        f"UPDATE {tbl} SET portfolio_id = :pid WHERE portfolio_id IS NULL",
                        {"pid": default_pid})
                except Exception as e:
                    logger.warning(f"Skipped {tbl}.portfolio_id migration: {e}")
            # cash + goals already have portfolio_id — just backfill any NULLs.
            for tbl in ("cash", "goals"):
                try:
                    await _safe_p(
                        f"UPDATE {tbl} SET portfolio_id = :pid WHERE portfolio_id IS NULL",
                        {"pid": default_pid})
                except Exception as e:
                    logger.warning(f"Skipped {tbl}.portfolio_id backfill: {e}")
            # reports + allocation: عزلهما بالمحفظة أيضًا (تقرير كل محفظة، وأوزان
            # التوزيع النسبي الخاصة بها). allocation كان company_id فريدًا عالميًا
            # → نُسقط القيد ونجعله فريدًا لكل (محفظة، شركة).
            for tbl in ("reports", "allocation"):
                try:
                    await _safe(
                        f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS portfolio_id INTEGER "
                        f"REFERENCES portfolio(id) ON DELETE CASCADE")
                    await _safe_p(
                        f"UPDATE {tbl} SET portfolio_id = :pid WHERE portfolio_id IS NULL",
                        {"pid": default_pid})
                except Exception as e:
                    logger.warning(f"Skipped {tbl}.portfolio_id migration: {e}")
            await _safe("ALTER TABLE allocation DROP CONSTRAINT IF EXISTS allocation_company_id_key")
            await _safe("CREATE UNIQUE INDEX IF NOT EXISTS ux_allocation_portfolio_company "
                        "ON allocation (portfolio_id, company_id)")
            # Snapshots: replace the old global-unique-on-date constraint with a
            # per-portfolio composite one (one snapshot per portfolio per day).
            await _safe("ALTER TABLE portfolio_snapshots DROP CONSTRAINT IF EXISTS portfolio_snapshots_snapshot_date_key")
            await _safe("DROP INDEX IF EXISTS ix_portfolio_snapshots_snapshot_date")
            await _safe("CREATE UNIQUE INDEX IF NOT EXISTS ux_snapshot_portfolio_date "
                        "ON portfolio_snapshots (portfolio_id, snapshot_date)")
            logger.info(f"✅ Multi-portfolio migration applied (default portfolio id={default_pid}).")
    logger.info("✅ Database tables verified / created.")
