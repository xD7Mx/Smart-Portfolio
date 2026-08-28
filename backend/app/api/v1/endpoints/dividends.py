from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.response import success_response
from app.models.transaction import Dividend, DividendAction, Cash
from app.models.portfolio import Holding
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

router = APIRouter()

class DividendCreate(BaseModel):
    company_id: int
    dividend_per_share: float
    shares_at_time: float
    action: str = "CASH"
    ex_date: Optional[datetime] = None
    payment_date: Optional[datetime] = None

class DividendUpdate(BaseModel):
    """Editing a recorded dividend re-derives its cash/holding effect from the
    delta between the old and new amount, so the portfolio stays consistent."""
    dividend_per_share: Optional[float] = None
    shares_at_time: Optional[float] = None
    payment_date: Optional[datetime] = None


def _recalc_holding(h: Holding):
    qty = float(h.quantity or 0)
    inv = float(h.invested_amount or 0)
    lp = float(h.last_price or 0)
    h.average_cost = (inv / qty) if qty else 0
    h.market_value = qty * lp if lp else inv
    mv = float(h.market_value or 0)
    h.unrealized_profit = mv - inv
    h.unrealized_profit_pct = ((mv - inv) / inv * 100) if inv else 0


async def _get_holding(db: AsyncSession, company_id: int) -> Holding | None:
    return (await db.execute(select(Holding).where(Holding.company_id == company_id).with_for_update())).scalar_one_or_none()


async def _get_cash(db: AsyncSession) -> Cash | None:
    return (await db.execute(select(Cash).limit(1).with_for_update())).scalar_one_or_none()


async def backfill_from_transactions(db: AsyncSession) -> int:
    """Self-heal for installs that recorded dividends before the dividends
    table was wired up: those DIVIDEND/REINVESTMENT transactions only ever
    mutated Cash/Holding, so they never got a row here — making them
    invisible and impossible to edit on the dividends screen. This scans
    historical transactions and creates the missing Dividend row for any
    that don't already have a matching one, WITHOUT re-applying any cash or
    holding effect (that already happened when the transaction first ran).
    Safe to call on every startup — it only ever adds rows that are missing."""
    from app.models.transaction import Transaction, TransactionType

    txs = (await db.execute(
        select(Transaction).where(Transaction.transaction_type.in_(
            [TransactionType.DIVIDEND, TransactionType.REINVESTMENT]
        ))
    )).scalars().all()

    added = 0
    for t in txs:
        amount = float(t.total_amount or 0)
        if amount <= 0:
            continue
        exists = (await db.execute(select(Dividend.id).where(
            Dividend.transaction_id == t.id,
        ))).scalar_one_or_none()
        if exists:
            continue
        exists_legacy = (await db.execute(select(Dividend.id).where(
            Dividend.company_id == t.company_id,
            Dividend.received_amount == amount,
            Dividend.payment_date == t.executed_at,
            Dividend.transaction_id.is_(None),
        ))).scalar_one_or_none()
        if exists_legacy:
            continue
        h = await _get_holding(db, t.company_id)
        shares = float(h.quantity or 0) if h else 0
        dps = (amount / shares) if shares else float(t.price or 0)
        action = DividendAction.REINVEST if t.transaction_type == TransactionType.REINVESTMENT else DividendAction.CASH
        db.add(Dividend(
            company_id=t.company_id, dividend_per_share=dps, shares_at_time=shares,
            received_amount=amount, action=action, payment_date=t.executed_at,
            transaction_id=t.id,
        ))
        added += 1
    if added:
        await db.commit()
    return added


@router.get("")
async def get_dividends(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dividend).order_by(Dividend.payment_date.desc().nulls_last(), Dividend.created_at.desc()))
    items = result.scalars().all()
    return success_response(data=[{
        "id": d.id,
        "company_id": d.company_id,
        "dividend_per_share": float(d.dividend_per_share or 0),
        "shares_at_time": float(d.shares_at_time or 0),
        "received": float(d.received_amount or 0),
        "received_amount": float(d.received_amount or 0),
        "action": d.action,
        "payment_date": d.payment_date.isoformat() if d.payment_date else None,
        "ex_date": d.ex_date.isoformat() if d.ex_date else None,
    } for d in items])

@router.post("")
async def add_dividend(data: DividendCreate, db: AsyncSession = Depends(get_db)):
    if data.dividend_per_share <= 0 or data.shares_at_time <= 0:
        raise HTTPException(422, "dividend_per_share and shares_at_time must be positive")
    if data.action == "REINVEST":
        # This endpoint has no price field to compute purchased shares —
        # recording REINVEST here would silently add dividend income
        # without ever buying shares. Use POST /transactions (REINVESTMENT) instead.
        raise HTTPException(422, "Use /transactions with type REINVESTMENT to record a reinvested dividend")
    amount = data.dividend_per_share * data.shares_at_time
    div = Dividend(company_id=data.company_id, dividend_per_share=data.dividend_per_share, shares_at_time=data.shares_at_time, received_amount=amount, action=data.action, ex_date=data.ex_date, payment_date=data.payment_date)
    db.add(div)

    # Keep cash/holding in sync with manually-recorded dividends too.
    h = await _get_holding(db, data.company_id)
    if h:
        h.total_dividends_received = float(h.total_dividends_received or 0) + amount
    if data.action == "CASH":
        cash = await _get_cash(db)
        if cash:
            cash.available_cash = float(cash.available_cash or 0) + amount
            cash.total_cash = float(cash.total_cash or 0) + amount

    await db.commit()
    await db.refresh(div)
    return success_response(data={"id": div.id, "received_amount": float(amount)}, message="Dividend recorded.")


@router.patch("/{dividend_id}")
async def update_dividend(dividend_id: int, data: DividendUpdate, db: AsyncSession = Depends(get_db)):
    div = (await db.execute(select(Dividend).where(Dividend.id == dividend_id))).scalar_one_or_none()
    if not div:
        raise HTTPException(404, "Dividend not found")

    old_amount = float(div.received_amount or 0)
    new_dps = data.dividend_per_share if data.dividend_per_share is not None else float(div.dividend_per_share or 0)
    new_shares = data.shares_at_time if data.shares_at_time is not None else float(div.shares_at_time or 0)
    if new_dps <= 0 or new_shares <= 0:
        raise HTTPException(422, "dividend_per_share and shares_at_time must be positive")
    new_amount = new_dps * new_shares
    delta = new_amount - old_amount

    if delta != 0:
        h = await _get_holding(db, div.company_id)
        if h:
            h.total_dividends_received = max(0, float(h.total_dividends_received or 0) + delta)
            if div.action == DividendAction.REINVEST:
                # Reinvested dividends bought shares — adjust the position too.
                old_shares_bought = float(div.reinvested_shares or 0)
                new_shares_bought = (new_amount / new_dps) if new_dps else old_shares_bought
                share_delta = new_shares_bought - old_shares_bought
                h.quantity = max(0, float(h.quantity or 0) + share_delta)
                h.invested_amount = max(0, float(h.invested_amount or 0) + delta)
                h.reinvestment_shares = max(0, float(h.reinvestment_shares or 0) + share_delta)
                div.reinvested_shares = new_shares_bought
                _recalc_holding(h)
        if div.action == DividendAction.CASH:
            cash = await _get_cash(db)
            if cash:
                cash.available_cash = float(cash.available_cash or 0) + delta
                cash.total_cash = float(cash.total_cash or 0) + delta

    div.dividend_per_share = new_dps
    div.shares_at_time = new_shares
    div.received_amount = new_amount
    if data.payment_date is not None:
        div.payment_date = data.payment_date

    if div.transaction_id:
        # Keep the source Transaction row in sync — goals.py's yearly income
        # reads total_amount from Transaction, not from Dividend, so leaving
        # this stale would silently desync the income figure from an edit.
        from app.models.transaction import Transaction
        tx = (await db.execute(select(Transaction).where(Transaction.id == div.transaction_id))).scalar_one_or_none()
        if tx:
            tx.total_amount = new_amount

    await db.commit()
    return success_response(data={"id": div.id, "received_amount": float(new_amount)}, message="Dividend updated.")


@router.delete("/{dividend_id}")
async def delete_dividend(dividend_id: int, db: AsyncSession = Depends(get_db)):
    div = (await db.execute(select(Dividend).where(Dividend.id == dividend_id))).scalar_one_or_none()
    if not div:
        raise HTTPException(404, "Dividend not found")

    amount = float(div.received_amount or 0)
    h = await _get_holding(db, div.company_id)
    if h:
        h.total_dividends_received = max(0, float(h.total_dividends_received or 0) - amount)
        if div.action == DividendAction.REINVEST:
            shares = float(div.reinvested_shares or 0)
            h.quantity = max(0, float(h.quantity or 0) - shares)
            h.invested_amount = max(0, float(h.invested_amount or 0) - amount)
            h.reinvestment_shares = max(0, float(h.reinvestment_shares or 0) - shares)
            _recalc_holding(h)
    if div.action == DividendAction.CASH:
        cash = await _get_cash(db)
        if cash:
            cash.available_cash = max(0, float(cash.available_cash or 0) - amount)
            cash.total_cash = max(0, float(cash.total_cash or 0) - amount)

    if div.transaction_id:
        # Remove the source Transaction row too — otherwise it survives as
        # a phantom income entry that goals.py would keep counting forever
        # even though its cash/holding effect was just reversed above.
        from app.models.transaction import Transaction
        tx = (await db.execute(select(Transaction).where(Transaction.id == div.transaction_id))).scalar_one_or_none()
        if tx:
            await db.delete(tx)

    await db.delete(div)
    await db.commit()
    return success_response(message="Dividend deleted.")
