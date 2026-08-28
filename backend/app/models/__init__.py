"""
Import all models to ensure SQLAlchemy registers them
before creating tables.
"""

from app.models.portfolio import Portfolio, Company, Holding, PortfolioMode, CompanyStatus, Note, NoteScope, PortfolioSnapshot
from app.models.transaction import (
    Transaction, Installment, Dividend, BonusShare, Cash, CashLedger,
    TransactionType, InstallmentStatus, DividendAction, CashLedgerKind
)
from app.models.market import (
    Goal, Allocation, MarketNews, MarketEvent, AIResult,
    Notification, Report, Settings, AuditLog, SchedulerJob,
    APIUsage, Backup,
    NotificationPriority, NotificationStatus, ReportType, MarketEventType
)

__all__ = [
    "Portfolio", "Company", "Holding", "Note", "PortfolioSnapshot",
    "Transaction", "Installment", "Dividend", "BonusShare", "Cash", "CashLedger",
    "Goal", "Allocation", "MarketNews", "MarketEvent", "AIResult",
    "Notification", "Report", "Settings", "AuditLog",
    "SchedulerJob", "APIUsage", "Backup",
]
