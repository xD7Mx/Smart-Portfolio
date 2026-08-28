"""
Goal, Allocation, Market events, AI results, Notifications,
Reports, Settings, Audit logs, Scheduler, API usage, Backup models.
"""

from sqlalchemy import (
    Column, String, Numeric, Enum, DateTime, Text,
    Integer, ForeignKey, Boolean, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


# ─── Goals ────────────────────────────────────────────────────

class GoalStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACHIEVED = "ACHIEVED"
    PAUSED = "PAUSED"


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id"), default=1)
    goal_name = Column(String(200), nullable=False)
    target_value = Column(Numeric(18, 6), nullable=False)
    # "AMOUNT" — a SAR value (e.g. reach 1,000,000 ﷼ portfolio value).
    # "PERCENT" — a return/growth percentage (e.g. +25% unrealized gain).
    target_type = Column(String(20), default="AMOUNT")
    current_value = Column(Numeric(18, 6), default=0)
    completion_percentage = Column(Numeric(10, 4), default=0)
    deadline = Column(DateTime(timezone=True))
    status = Column(Enum(GoalStatus), default=GoalStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    portfolio = relationship("Portfolio", back_populates="goals")


# ─── Allocation ────────────────────────────────────────────────

class Allocation(Base):
    __tablename__ = "allocation"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    target_weight = Column(Numeric(10, 4), default=0)
    # عتبة التصفية لهذه الشركة (٪ فوق متوسط التكلفة). NULL ⇒ ترث العتبة العامة.
    # ولماذا لكل شركة: سهمٌ يُحمَل للحصاد يُصفّى عند ١٠٪، وسهمٌ يُؤمَن بنموّه
    # لا يُقصّ إلا عند ٥٠ — وعتبةٌ واحدة تُعامِلهما سواءً فتقصّ الرابح مبكّراً.
    liquidation_threshold_pct = Column(Numeric(10, 4))
    current_weight = Column(Numeric(10, 4), default=0)
    deviation = Column(Numeric(10, 4), default=0)
    rebalance_required = Column(Boolean, default=False)
    last_reviewed = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    company = relationship("Company", back_populates="allocation")


# ─── Market ────────────────────────────────────────────────────

class MarketEventType(str, enum.Enum):
    DIVIDEND = "DIVIDEND"
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    SPLIT = "SPLIT"
    BONUS = "BONUS"
    RESULTS = "RESULTS"
    MERGER = "MERGER"
    ACQUISITION = "ACQUISITION"
    AGM = "AGM"
    OTHER = "OTHER"


class MarketNews(Base):
    __tablename__ = "market_news"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50))
    company_symbol = Column(String(20), index=True)
    headline = Column(String(500), nullable=False)
    summary = Column(Text)
    url = Column(String(1000))
    category = Column(String(50))
    importance = Column(String(20), default="MEDIUM")
    published_at = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MarketEvent(Base):
    __tablename__ = "market_events"

    id = Column(Integer, primary_key=True, index=True)
    company_symbol = Column(String(20), index=True)
    event_type = Column(Enum(MarketEventType), nullable=False)
    description = Column(Text)
    event_date = Column(DateTime(timezone=True), index=True)
    value = Column(Numeric(18, 6))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── AI Results ───────────────────────────────────────────────

class AIResult(Base):
    __tablename__ = "ai_results"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    agent_name = Column(String(100), nullable=False, index=True)
    target_module = Column(String(100))
    confidence = Column(Numeric(5, 2), default=0)
    summary = Column(Text)
    recommendation = Column(Text)
    evidence = Column(JSON)
    score = Column(Numeric(5, 2))
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    company = relationship("Company", back_populates="ai_results")


# ─── Notifications ─────────────────────────────────────────────

class NotificationPriority(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class NotificationStatus(str, enum.Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    ARCHIVED = "ARCHIVED"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.INFO)
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(50), default="IN_APP")
    status = Column(Enum(NotificationStatus), default=NotificationStatus.UNREAD, index=True)
    extra_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    read_at = Column(DateTime(timezone=True))


# ─── Reports ──────────────────────────────────────────────────

class ReportType(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"
    CUSTOM = "CUSTOM"


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    report_type = Column(Enum(ReportType), nullable=False, index=True)
    report_period = Column(String(50))
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    file_path = Column(String(500))
    checksum = Column(String(64))
    summary = Column(JSON)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ─── Settings ─────────────────────────────────────────────────

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(200), unique=True, nullable=False, index=True)
    value = Column(Text)
    category = Column(String(100), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


# ─── Watchlist (قائمة المراقبة) ───────────────────────────────
# شركات يتابعها المستخدم دون امتلاكها — رمز تداول + اسم عربي، مستقلّة عن
# الحيازات، وتُضمَّن في النسخة الاحتياطية.
class WatchlistGroup(Base):
    __tablename__ = "watchlist_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(20), default="#3B82F6")
    is_default = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(200))
    group_id = Column(Integer, ForeignKey("watchlist_groups.id"), index=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── Audit Log ────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    module = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    entity = Column(String(100))
    entity_id = Column(Integer)
    old_value = Column(JSON)
    new_value = Column(JSON)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ─── Scheduler ────────────────────────────────────────────────

class SchedulerJob(Base):
    __tablename__ = "scheduler_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(100), unique=True, nullable=False)
    frequency = Column(String(100))
    last_run = Column(DateTime(timezone=True))
    next_run = Column(DateTime(timezone=True))
    status = Column(String(50), default="ACTIVE")
    last_error = Column(Text)


# ─── API Usage ────────────────────────────────────────────────

class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(100), nullable=False, index=True)
    endpoint = Column(String(200))
    requests_today = Column(Integer, default=0)
    daily_limit = Column(Integer, default=500)
    remaining = Column(Integer, default=500)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


# ─── Backup ───────────────────────────────────────────────────

class Backup(Base):
    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, index=True)
    backup_name = Column(String(200), nullable=False)
    backup_type = Column(String(50), default="FULL")
    file_size = Column(Integer)
    location = Column(String(500))
    checksum = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ─── Library (المكتبة) ────────────────────────────────────────
# كتب PDF جاهزة للمعاينة/التحميل، مع «نبذة اليوم» يستقيها الذكاء من نصّ الكتاب
# نفسه (استُخرج مرة واحدة عند الرفع) — لا اختلاق: كل نبذة مستشهَدة بصفحة فعلية.
# ملفات الـPDF ونصّها تُخزَّن في مجلد data (خارج git/الحزمة، على فوليوم يبقى).
class LibraryBook(Base):
    __tablename__ = "library_books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    author = Column(String(200))
    filename = Column(String(300), nullable=False)  # اسم ملف PDF على القرص
    file_size = Column(Integer)
    page_count = Column(Integer)
    has_text = Column(Boolean, default=False)  # نجح استخراج النصّ (لازم للذكاء)
    # False أثناء المعالجة في الخلفية (استخراج/OCR)، True عند الجهوزية — كي
    # يعود الرفع فوراً بلا انتظار الـOCR (يتجاوز مهلة الوسيط)، والواجهة تعرض حالة.
    ready = Column(Boolean, default=False)
    # ترتيب يدويّ يحدّده المالك (الأصغر أولاً)؛ الافتراضي 0 والفرز الثانوي بالأحدث.
    position = Column(Integer, default=0, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ─── إدارة السيولة (خطّة الدفعات) ──────────────────────────────
# نموذج المالك: لكل شركةٍ **مبلغٌ محجوز لكل دفعة**، وعددُ دفعاتٍ منفَّذة من أصل
# خمس. فالمبلغ المرصود لها = المحجوز × عدد الدفعات، وعددُ الأسهم = المبلغ ÷ السعر.
# ومجموع المحجوز عبر الشركات = «قيمة الدفعة» الكاملة.
#
# ولماذا جدولٌ لا حسابٌ مشتقّ: هذه **خطّةٌ مستقبلية** لا واقعةٌ ماضية — لا
# تُستنتج من سجلّ العمليات لأنها لم تقع بعد. وحفظها يجعلها تصمد عبر إعادة
# التشغيل وتُقرأ من أي جهاز، بخلاف ملفٍّ على حاسوبٍ واحد.
class LiquidityPlan(Base):
    __tablename__ = "liquidity_plan"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    # نسبة الشركة من قيمة الدفعة (٪). المالك يُدخل رقماً واحداً لقيمة الدفعة،
    # وهذه النسبة تقسّمه — بدل إدخال مبلغٍ لكل شركة على حدة. فتعديل قيمة
    # الدفعة يُعيد توزيع الجميع بضربةٍ واحدة، وهو ما يُتَّخذ عليه القرار فعلاً.
    # NULL ⇒ لم يُحرَّر بعد، فيُستعمل الوزن الحالي في التوزيع النسبي تلقائياً.
    # وهذا فرقٌ جوهري عن الصفر: الصفر قرارٌ صريح بعدم التخصيص، والفراغ ليس
    # قراراً — فلا يجوز أن يُقرأ كأنه هو.
    share_pct = Column(Numeric(10, 4))
    # الدفعات المنفَّذة: خمس رايات مستقلّة لا عدّاد — كي يبقى معلوماً **أيّ**
    # دفعةٍ نُفِّذت لا كم عددها، فتُقرأ الشبكة كما في ملف المالك حرفياً.
    t1 = Column(Boolean, default=False)
    t2 = Column(Boolean, default=False)
    t3 = Column(Boolean, default=False)
    t4 = Column(Boolean, default=False)
    t5 = Column(Boolean, default=False)
    # سعرٌ يدويّ يتقدّم على سعر السوق حين يُحدَّد — المالك قد يخطّط على سعر
    # أمرٍ معلَّق لا على السعر اللحظي. NULL ⇒ يُستعمل السعر الحيّ.
    price_override = Column(Numeric(18, 6))
    # عدد دفعات بطاقة «أوامر الشراء» — مستقلٌّ عن مربّعات بطاقة إدارة السيولة.
    # الأولى خطّة توزيع، والثانية أمر تنفيذ، وقد يختلفان عمداً.
    exec_tranches = Column(Integer)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
