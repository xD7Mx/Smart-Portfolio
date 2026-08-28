from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.response import success_response
from app.models.transaction import BonusShare
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class BonusCreate(BaseModel):
    company_id: int
    bonus_ratio: float
    shares_received: float
    shares_before: float = 0
    granted_at: datetime

@router.get("")
async def get_bonus_shares(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BonusShare).order_by(BonusShare.granted_at.desc()))
    items = result.scalars().all()
    return success_response(data=[{"id": b.id, "company_id": b.company_id, "ratio": float(b.bonus_ratio), "shares": float(b.shares_received)} for b in items])

@router.post("")
async def add_bonus_shares(data: BonusCreate, db: AsyncSession = Depends(get_db)):
    bonus = BonusShare(**data.model_dump())
    db.add(bonus)
    await db.commit()
    await db.refresh(bonus)
    return success_response(data={"id": bonus.id}, message="Bonus shares recorded.")
