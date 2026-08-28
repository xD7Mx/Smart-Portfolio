from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.response import success_response
from app.models.transaction import Cash, CashLedger, CashLedgerKind, Transaction, TransactionType
from pydantic import BaseModel, field_validator

router = APIRouter()

class CashDeposit(BaseModel):
    amount: float
    source: str = "DEPOSIT"

    @field_validator("amount")
    @classmethod
    def _positive(cls, v: float) -> float:
        # حارسٌ غائب: المبلغ كان يُقبل سالباً، فإيداعُ (−٥٠٠٠) يعمل عمل السحب
        # ويتجاوز حارس «السيولة لا تكفي» تماماً، ويُقيَّد في السجل «إيداعاً»
        # فيُقرأ عكس ما فعل. والصفر يُنشئ قيداً بلا أثر يزحم السجل.
        if v is None or v <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر.")
        # سقفٌ للمبالغ: رقمٌ فوق التريليون خطأُ إدخالٍ لا إيداع. وقبوله كان
        # يكسر مطابقة النقد فعلياً — الفروق العشرية في الأعداد الضخمة تجعل
        # الرصيد المخزَّن يخالف مجموع حركاته بقروش، فيسقط أقوى فحصٍ في
        # المنظومة على رقمٍ لم يقصده أحد.
        if v > 1e12:
            raise ValueError("المبلغ أكبر من الحدّ المعقول (تريليون).")
        return v

@router.get("")
async def get_cash(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cash).limit(1))
    cash = result.scalar_one_or_none()
    if not cash:
        return success_response(data={"available_cash": 0, "pending_cash": 0, "reinvestment_cash": 0, "total_cash": 0})
    return success_response(data={
        "available_cash": float(cash.available_cash or 0),
        "pending_cash": float(cash.pending_cash or 0),
        # reinvestment_cash عمودٌ ميت: لا يكتبه أي مسار في التطبيق. كان يُعرض
        # في المحفظة باسم «سيولة إعادة الاستثمار» فيقرأ المالك رقماً جامداً من
        # نسخةٍ قديمة يناقض الحوض المحسوب زمنياً. المصدر الوحيد للحوض هو
        # compute_reinvestment_pool، ويُعرض في بطاقة التوزيع النسبي.
        "reinvestment_cash": 0.0,
        "total_cash": float(cash.total_cash or 0),
    })

@router.get("/history")
async def get_cash_history(limit: int = 30, db: AsyncSession = Depends(get_db)):
    """Everything that has moved the liquidity balance: manual deposits/
    withdrawals plus BUY/SELL/DIVIDEND transactions — so the liquidity
    screen shows real detail, not just a number."""
    items = []

    ledger = (await db.execute(
        select(CashLedger).order_by(CashLedger.created_at.desc()).limit(limit)
    )).scalars().all()
    for l in ledger:
        amt = float(l.amount or 0)
        items.append({
            "id": l.id,
            "kind": "ledger",
            "date": l.created_at.isoformat() if l.created_at else None,
            "type": l.kind,
            "label": "إيداع" if l.kind == CashLedgerKind.DEPOSIT else "سحب",
            "amount": amt if l.kind == CashLedgerKind.DEPOSIT else -amt,
            "company": None,
        })

    txs = (await db.execute(
        select(Transaction).options(selectinload(Transaction.company))
        .where(Transaction.transaction_type.in_([TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND]))
        .order_by(Transaction.executed_at.desc()).limit(limit)
    )).scalars().all()
    # الوسم الموحّد، والقديمان يُعرضان بنفس الصياغة فلا يبدو السجلّ نصفين.
    source_suffix = {"REINVEST": " (إعادة استثمار)",
                     "DIVIDEND": " (إعادة استثمار)",
                     "PROFIT": " (إعادة استثمار)"}
    labels = {"BUY": "شراء", "SELL": "بيع", "DIVIDEND": "توزيع نقدي"}
    for t in txs:
        amt = float(t.total_amount or 0)
        signed = -amt if t.transaction_type == TransactionType.BUY else amt
        label = labels.get(t.transaction_type, t.transaction_type)
        if t.transaction_type == TransactionType.BUY and t.funding_source:
            label += source_suffix.get(t.funding_source, "")
        items.append({
            "id": t.id,
            "kind": "transaction",
            "date": t.executed_at.isoformat() if t.executed_at else None,
            "type": t.transaction_type,
            "label": label,
            "amount": signed,
            "company": t.company.company_name if t.company else None,
            "symbol": t.company.symbol if t.company else None,
        })

    items.sort(key=lambda x: x["date"] or "", reverse=True)
    return success_response(data=items[:limit])

@router.delete("/ledger/{ledger_id}")
async def delete_cash_ledger(ledger_id: int, db: AsyncSession = Depends(get_db)):
    """Undo a wrongly-recorded manual deposit/withdrawal: reverses its
    effect on the cash balance and removes the ledger row — the same
    escape hatch already available for transactions."""
    entry = (await db.execute(select(CashLedger).where(CashLedger.id == ledger_id))).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Ledger entry not found.")
    from app.api.v1.endpoints.transactions import _get_cash
    cash = await _get_cash(db)
    amt = float(entry.amount or 0)
    if entry.kind == CashLedgerKind.DEPOSIT:
        # حذف إيداعٍ يخصم قيمته. وإن كان المال قد أُنفق فعلاً في شراءٍ لاحق
        # هبط الرصيد دون الصفر بصمت — حالةٌ مستحيلة تُفسد كل ما يُبنى عليه.
        if float(cash.available_cash or 0) < amt - 1e-6:
            raise HTTPException(
                422,
                f"حذف هذا الإيداع يخصم {amt:,.2f} والمتاح {float(cash.available_cash or 0):,.2f} فقط. "
                f"أُنفق جزءٌ منه في عمليات لاحقة.",
            )
        cash.available_cash = float(cash.available_cash or 0) - amt
        cash.total_cash = float(cash.total_cash or 0) - amt
    else:
        cash.available_cash = float(cash.available_cash or 0) + amt
        cash.total_cash = float(cash.total_cash or 0) + amt
    await db.delete(entry)
    await db.commit()
    return success_response(message="Ledger entry deleted.")

@router.post("/deposit")
async def deposit_cash(data: CashDeposit, db: AsyncSession = Depends(get_db)):
    from app.api.v1.endpoints.transactions import _get_cash
    cash = await _get_cash(db)
    cash.available_cash = float(cash.available_cash or 0) + data.amount
    cash.total_cash = float(cash.total_cash or 0) + data.amount
    db.add(CashLedger(kind=CashLedgerKind.DEPOSIT, amount=data.amount, note=data.source))
    await db.commit()
    return success_response(message=f"Deposited {data.amount} successfully.")

@router.post("/withdraw")
async def withdraw_cash(data: CashDeposit, db: AsyncSession = Depends(get_db)):
    from app.api.v1.endpoints.transactions import _get_cash
    cash = await _get_cash(db)
    if float(cash.available_cash or 0) < data.amount:
        raise HTTPException(422, "Insufficient available cash")
    cash.available_cash = float(cash.available_cash or 0) - data.amount
    cash.total_cash = float(cash.total_cash or 0) - data.amount
    db.add(CashLedger(kind=CashLedgerKind.WITHDRAW, amount=data.amount, note=data.source))
    await db.commit()
    return success_response(message=f"Withdrew {data.amount} successfully.")
