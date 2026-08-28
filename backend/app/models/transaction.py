"""
Financial operation models: Transaction, Installment, Dividend, BonusShare, Cash.
All transactions are immutable history records.
"""

from sqlalchemy import Column, String, Numeric, Enum, DateTime, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class TransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    BONUS = "BONUS"
    SPLIT = "SPLIT"
    CORRECTION = "CORRECTION"
    REINVESTMENT = "REINVESTMENT"


class InstallmentStatus(str, enum.Enum):
    WAITING = "WAITING"
    READY = "READY"
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class DividendAction(str, enum.Enum):
    CASH = "CASH"
    REINVEST = "REINVEST"


class FundingSource(str, enum.Enum):
    """Optional, purely informational tag on a BUY: where the money
    conceptually came from. Never changes the cash/holding math — every BUY
    deducts cash the same way regardless of tag."""
    DIVIDEND = "DIVIDEND"
    PROFIT = "PROFIT"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Numeric(18, 6), nullable=False)
    price = Column(Numeric(18, 6), nullable=False)
    fees = Column(Numeric(18, 6), default=0)
    total_amount = Column(Numeric(18, 6), nullable=False)
    funding_source = Column(String(20))  # BUY only: DIVIDEND / PROFIT / NULL (fresh cash) — informational
    realized_gain = Column(Numeric(18, 6))  # SELL only: proceeds minus cost basis at sale time
    notes = Column(Text)
    executed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="transactions")


class Installment(Base):
    __tablename__ = "installments"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    installment_number = Column(Integer, nullable=False)
    target_price = Column(Numeric(18, 6), nullable=False)
    allocated_amount = Column(Numeric(18, 6), default=0)
    target_quantity = Column(Numeric(18, 6), default=0)
    status = Column(Enum(InstallmentStatus), default=InstallmentStatus.WAITING)
    executed_price = Column(Numeric(18, 6))
    executed_quantity = Column(Numeric(18, 6))
    executed_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    company = relationship("Company", back_populates="installments")


class Dividend(Base):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    announcement_date = Column(DateTime(timezone=True))
    ex_date = Column(DateTime(timezone=True), index=True)
    payment_date = Column(DateTime(timezone=True))
    dividend_per_share = Column(Numeric(18, 6), nullable=False)
    shares_at_time = Column(Numeric(18, 6), default=0)
    received_amount = Column(Numeric(18, 6), default=0)
    action = Column(Enum(DividendAction), default=DividendAction.CASH)
    reinvested_shares = Column(Numeric(18, 6), default=0)
    # Links back to the DIVIDEND/REINVESTMENT Transaction row this came from
    # (NULL for dividends added directly via POST /dividends), so editing or
    # deleting a dividend here can keep that transaction's total_amount in
    # sync instead of leaving a stale figure behind for income reporting.
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="dividends")


class BonusShare(Base):
    __tablename__ = "bonus_shares"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    bonus_ratio = Column(Numeric(10, 4), nullable=False)
    shares_received = Column(Numeric(18, 6), nullable=False)
    shares_before = Column(Numeric(18, 6), default=0)
    market_value_at_time = Column(Numeric(18, 6), default=0)
    granted_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="bonus_shares")


class Cash(Base):
    __tablename__ = "cash"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id"), default=1)
    available_cash = Column(Numeric(18, 6), default=0)
    pending_cash = Column(Numeric(18, 6), default=0)
    reinvestment_cash = Column(Numeric(18, 6), default=0)
    total_cash = Column(Numeric(18, 6), default=0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    portfolio = relationship("Portfolio", back_populates="cash")


class CashLedgerKind(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"


class CashLedger(Base):
    """Manual cash movements not tied to a company (deposits/withdrawals),
    so the liquidity screen can show a real history, not just the balance."""
    __tablename__ = "cash_ledger"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True, index=True)
    kind = Column(Enum(CashLedgerKind), nullable=False)
    amount = Column(Numeric(18, 6), nullable=False)
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
