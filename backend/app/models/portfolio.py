"""
Portfolio, Company, and Holdings database models.
"""

from sqlalchemy import Column, String, Numeric, Enum, DateTime, Date, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class PortfolioMode(str, enum.Enum):
    BUILD = "BUILD"
    MANAGEMENT = "MANAGEMENT"


class CompanyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    WATCHLIST = "WATCHLIST"
    ARCHIVED = "ARCHIVED"
    DELISTED = "DELISTED"


class ShariaStatus(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNDER_REVIEW = "UNDER_REVIEW"
    UNKNOWN = "UNKNOWN"


class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    # account_id: which account owns this portfolio (Phase 2 — accounts layer).
    # Plain column for now (no FK until the accounts table exists); defaults to
    # the single default account on migration.
    account_id = Column(Integer, nullable=True, index=True)
    name = Column(String(100), nullable=False, default="My Portfolio")
    currency = Column(String(10), nullable=False, default="SAR")
    mode = Column(Enum(PortfolioMode), nullable=False, default=PortfolioMode.BUILD)
    target_capital = Column(Numeric(18, 6), default=0)
    target_income = Column(Numeric(18, 6), default=0)
    target_return_pct = Column(Numeric(10, 4), default=0)
    # Multi-portfolio UI: a distinguishing color, whether this is the account's
    # default portfolio, and whether it's summed into the account's combined
    # ("مجمّع") wealth band. Aggregation NEVER crosses accounts — it only ever
    # combines portfolios belonging to the same account.
    color = Column(String(10), default="#3B82F6")
    is_default = Column(Boolean, default=False)
    include_in_aggregate = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    goals = relationship("Goal", back_populates="portfolio")
    cash = relationship("Cash", back_populates="portfolio", uselist=False)


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    exchange = Column(String(50))
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    currency = Column(String(10), default="SAR")
    status = Column(Enum(CompanyStatus), default=CompanyStatus.ACTIVE)
    sharia_status = Column(Enum(ShariaStatus), default=ShariaStatus.UNKNOWN)
    finance_score = Column(Numeric(5, 2), default=0)
    technical_score = Column(Numeric(5, 2), default=0)
    logo_url = Column(String(500))
    color = Column(String(10), default="#3B82F6")
    notes = Column(Text)
    # ── نبذة نشاط الشركة ─────────────────────────────────────────────────
    # المصدر Yahoo وحده (وحدة assetProfile). النصّ الأصلي إنجليزي، فيُترجَم
    # بالذكاء ويُحفَظ هنا كي لا يُعاد جلبه ولا ترجمته لكل عرض.
    # description_source: ai (مترجَمة) · yahoo (إنجليزية كما هي) · manual (نصّك).
    #   يُعرض الوسم في الواجهة كي لا يُقرأ نصٌّ مترجَم آلياً كأنه إفصاح رسمي.
    # ولا يوجد حقلٌ لمجلس الإدارة: Yahoo لا يُوفّر تشكيل المجالس (ما يوفّره هو
    #   الإدارة التنفيذية، وهي جهةٌ أخرى تُعرض باسمها الصحيح)، والاعتماد على
    #   Yahoo وحده يعني إلغاء ما لا يوفّره لا اختلاقه ولا استجداءه من مصدرٍ آخر.
    description = Column(Text)
    description_source = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    holding = relationship("Holding", back_populates="company", uselist=False)
    transactions = relationship("Transaction", back_populates="company")
    installments = relationship("Installment", back_populates="company")
    dividends = relationship("Dividend", back_populates="company")
    bonus_shares = relationship("BonusShare", back_populates="company")
    allocation = relationship("Allocation", back_populates="company", uselist=False)
    ai_results = relationship("AIResult", back_populates="company")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    # ترتيب العرض الذي يختاره المالك في شاشة الحيازات. مصدرٌ واحد لكل
    # البطاقات: التوزيع النسبي والسيولة وأوامر الشراء والتصفية تتبعه، فلا
    # تتنقّل الشركة من موضعٍ إلى آخر بين شاشة وأخرى ولا بعد كل تحديث.
    # والصفر يعني «لم يُرتَّب بعد» فيُذيَّل، فلا تقفز شركةٌ جديدة إلى الصدارة.
    sort_order = Column(Integer, default=0)
    quantity = Column(Numeric(18, 6), default=0)
    average_cost = Column(Numeric(18, 6), default=0)
    invested_amount = Column(Numeric(18, 6), default=0)
    market_value = Column(Numeric(18, 6), default=0)
    last_price = Column(Numeric(18, 6), default=0)
    unrealized_profit = Column(Numeric(18, 6), default=0)
    unrealized_profit_pct = Column(Numeric(10, 4), default=0)
    weight = Column(Numeric(10, 4), default=0)
    installment_progress = Column(Integer, default=0)
    total_dividends_received = Column(Numeric(18, 6), default=0)
    total_bonus_shares = Column(Numeric(18, 6), default=0)
    reinvestment_shares = Column(Numeric(18, 6), default=0)
    profit_reinvested = Column(Numeric(18, 6), default=0)
    # فارق التسوية مع كشف الوسيط: يحفظ تصحيح المالك اليدوي لتكلفته من أن
    # تمحوَه إعادة بناء الحيازة من السجل. سجلّ العمليات قد ينقصه إدخالٌ قديم
    # أو عمولةٌ لم تُسجَّل، والكشف هو المرجع؛ فنخزّن الفرق لا الرقم النهائي،
    # كي تبقى عمليات الشراء والبيع اللاحقة تحرّك التكلفة كما ينبغي.
    cost_basis_adjustment = Column(Numeric(18, 6), default=0)
    # الفوارق المُحقَّقة: عند الخروج الكامل يسقط الفارق عن التكلفة (لا تكلفة بلا
    # أسهم) لكنه لا يسقط عن **رأس المال المدفوع** — فالمالك دفعه فعلاً. يُنقل
    # هنا تراكمياً كي لا يُمحى من المقام، ولا يعود فيُطبَّق على مركزٍ جديد لو
    # عاد المالك إلى السهم لاحقاً.
    paid_in_adjustment_realized = Column(Numeric(18, 6), default=0)
    last_price_update = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    company = relationship("Company", back_populates="holding")


class NoteScope(str, enum.Enum):
    MARKET = "MARKET"
    PORTFOLIO = "PORTFOLIO"


class Note(Base):
    """User notes — MARKET (general) or PORTFOLIO (tied to a company; hidden
    automatically when the company is archived/removed)."""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    scope = Column(Enum(NoteScope), nullable=False, default=NoteScope.MARKET)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company")


class PortfolioSnapshot(Base):
    """Daily portfolio snapshot — one row per day; powers the real
    performance history chart."""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    # One snapshot per portfolio per day (was globally unique on date before
    # multi-portfolio — the composite is applied in the startup migration).
    snapshot_date = Column(Date, nullable=False, index=True)
    market_value = Column(Numeric(18, 6), default=0)
    invested_amount = Column(Numeric(18, 6), default=0)
    cash_balance = Column(Numeric(18, 6), default=0)
    unrealized_profit = Column(Numeric(18, 6), default=0)
    governance_score = Column(Numeric(10, 4))
    # درجة **التقييم العام** — رقمٌ آخر غير `governance_score` أعلاه: ذاك
    # للحوكمة والالتزام الشرعي، وهذا مخرَج محرّك التقييم (تنويع · مخاطر ·
    # بنية · مكافأة أداء · استرداد رأس المال) وهو ما يعرضه شريط التقييم.
    # فُصلا عمودَين لأن رسم تاريخ أحدهما تحت رقم الآخر بيانٌ كاذب: خطٌّ لا
    # ينتهي إلى الرقم المكتوب فوقه، ولا يُكتشف لأنه يبدو صحيحاً.
    evaluation_score = Column(Numeric(10, 4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
