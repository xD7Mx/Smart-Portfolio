from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.response import success_response
from app.models.transaction import Installment
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class InstallmentCreate(BaseModel):
    company_id: int
    installment_number: int
    target_price: float
    allocated_amount: float = 0
    target_quantity: float = 0
    notes: Optional[str] = None

@router.get("")
async def get_installments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Installment).order_by(Installment.company_id, Installment.installment_number))
    items = result.scalars().all()
    return success_response(data=[{"id": i.id, "company_id": i.company_id, "number": i.installment_number, "target_price": float(i.target_price), "status": i.status} for i in items])

@router.post("")
async def add_installment(data: InstallmentCreate, db: AsyncSession = Depends(get_db)):
    inst = Installment(**data.model_dump())
    db.add(inst)
    await db.commit()
    await db.refresh(inst)
    return success_response(data={"id": inst.id}, message="Installment created.")

@router.get("/nearest")
async def get_nearest_installment(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Installment).where(Installment.status == "WAITING").order_by(Installment.target_price).limit(5))
    items = result.scalars().all()
    return success_response(data=[{"id": i.id, "company_id": i.company_id, "target_price": float(i.target_price)} for i in items])

@router.patch("/{inst_id}")
async def update_installment(inst_id: int, status: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Installment).where(Installment.id == inst_id))
    inst = result.scalar_one_or_none()
    if not inst:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Installment not found.")
    inst.status = status
    await db.commit()
    return success_response(message="Installment updated.")
