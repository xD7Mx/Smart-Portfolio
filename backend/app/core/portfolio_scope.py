"""
عزل بيانات المحافظ على مستوى الجلسة (Row-Level Scoping).

بدل تعديل عشرات مواضع الاستعلام يدويًا، نُركّب مُرشِّحًا عامًّا:
  • مستمع do_orm_execute يُضيف with_loader_criteria لكل نموذج يملك
    portfolio_id، فيُقصر كل SELECT على المحفظة النشطة تلقائيًا.
  • مستمع before_flush يُختم كل صفٍّ جديد بمعرّف المحفظة النشطة.

وضعان عبر متغيّرات سياق (ContextVar) تُضبط لكل طلب:
  • _active_pid: المحفظة المختارة — يُختم بها الإدخال دائمًا.
  • _read_all: عند التشغيل (توحيد الثروة) يُلغى ترشيح القراءة فيُجمَع الكل؛
    الإدخال يبقى للمحفظة النشطة.

المهام الخلفية (المجدول/النسخ الاحتياطي) لا تمرّ بالسياق، فتعمل بلا ترشيح
(عبر كل المحافظ) كما كانت.
"""
from contextvars import ContextVar

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

_active_pid: ContextVar[int | None] = ContextVar("active_pid", default=None)
_read_all: ContextVar[bool] = ContextVar("read_all", default=False)


def set_scope(active_pid: int | None, read_all: bool) -> None:
    _active_pid.set(active_pid)
    _read_all.set(read_all)


def reset_scope() -> None:
    _active_pid.set(None)
    _read_all.set(False)


def is_aggregate() -> bool:
    """وضع التوحيد فعّال (قراءة مُجمَّعة عبر كل المحافظ)."""
    return _read_all.get()


def _scoped_models():
    from app.models.portfolio import Holding, Note, PortfolioSnapshot
    from app.models.transaction import Transaction, Installment, Dividend, BonusShare, Cash, CashLedger
    from app.models.market import Goal, Allocation, Report
    return [Holding, Note, PortfolioSnapshot, Transaction, Installment, Dividend, BonusShare, Cash, CashLedger, Goal, Allocation, Report]


_installed = False


def install_scope_listeners() -> None:
    """يُركّب المستمعَين مرّة واحدة. يُستدعى عند الإقلاع."""
    global _installed
    if _installed:
        return
    _installed = True
    models = _scoped_models()

    @event.listens_for(Session, "do_orm_execute")
    def _filter_reads(state):
        if not state.is_select:
            return
        # فرصة للتعطيل الصريح (استعلامات داخلية عابرة للمحافظ)
        if state.execution_options.get("skip_portfolio_scope"):
            return
        if _read_all.get():
            return  # وضع التوحيد: بلا ترشيح
        pid = _active_pid.get()
        if pid is None:
            return  # لا سياق (مهمة خلفية) → بلا ترشيح
        for m in models:
            state.statement = state.statement.options(
                with_loader_criteria(m, m.portfolio_id == pid, include_aliases=True)
            )

    @event.listens_for(Session, "before_flush")
    def _stamp_inserts(session, flush_context, instances):
        pid = _active_pid.get()
        if pid is None:
            return
        for obj in session.new:
            if hasattr(obj, "portfolio_id") and getattr(obj, "portfolio_id", None) is None:
                obj.portfolio_id = pid
