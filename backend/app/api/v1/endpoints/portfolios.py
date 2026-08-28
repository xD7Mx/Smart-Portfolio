"""
Portfolio management — list / create / rename / recolor / set-default /
archive the account's portfolios, plus the combined ("مجمّع") wealth summary
across the account's portfolios (never across accounts).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response
from app.core.portfolio_context import active_portfolio_id, _default_portfolio_id
from app.models.portfolio import Portfolio

router = APIRouter()


def _serialize(p: Portfolio) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "color": p.color or "#3B82F6",
        "mode": p.mode.value if hasattr(p.mode, "value") else p.mode,
        "is_default": bool(p.is_default),
        "include_in_aggregate": bool(p.include_in_aggregate),
        "is_archived": bool(p.is_archived),
        "sort_order": p.sort_order or 0,
    }


class PortfolioCreate(BaseModel):
    name: str
    color: str | None = None
    include_in_aggregate: bool = True


class PortfolioUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    include_in_aggregate: bool | None = None


@router.get("")
async def list_portfolios(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Portfolio).where(Portfolio.is_archived.is_(False))
        .order_by(Portfolio.sort_order, Portfolio.id)
    )).scalars().all()
    if not rows:
        # Fresh DB safety — guarantee at least the default exists.
        await _default_portfolio_id(db)
        rows = (await db.execute(
            select(Portfolio).where(Portfolio.is_archived.is_(False)).order_by(Portfolio.id)
        )).scalars().all()
    return success_response(data=[_serialize(p) for p in rows])


@router.post("")
async def create_portfolio(data: PortfolioCreate, db: AsyncSession = Depends(get_db)):
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(422, "اسم المحفظة مطلوب")
    p = Portfolio(
        name=name,
        color=(data.color or "#3B82F6"),
        include_in_aggregate=data.include_in_aggregate,
        is_default=False,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return success_response(data=_serialize(p), message="أُنشئت المحفظة.")


@router.patch("/{portfolio_id}")
async def update_portfolio(portfolio_id: int, data: PortfolioUpdate, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "المحفظة غير موجودة")
    if data.name is not None:
        n = data.name.strip()
        if not n:
            raise HTTPException(422, "اسم المحفظة لا يمكن أن يكون فارغاً")
        p.name = n
    if data.color is not None:
        p.color = data.color
    if data.include_in_aggregate is not None:
        p.include_in_aggregate = data.include_in_aggregate
    await db.commit()
    return success_response(data=_serialize(p), message="حُدّثت المحفظة.")


@router.post("/{portfolio_id}/set-default")
async def set_default_portfolio(portfolio_id: int, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "المحفظة غير موجودة")
    for other in (await db.execute(select(Portfolio).where(Portfolio.is_default.is_(True)))).scalars().all():
        other.is_default = False
    p.is_default = True
    await db.commit()
    return success_response(data=_serialize(p), message="أصبحت المحفظة الافتراضية.")


@router.delete("/{portfolio_id}")
async def archive_portfolio(portfolio_id: int, db: AsyncSession = Depends(get_db)):
    """Archive (soft-delete) a portfolio. Refuses to remove the LAST active
    portfolio, and moves the default flag if needed — the account must always
    keep at least one usable portfolio."""
    active = (await db.execute(
        select(Portfolio).where(Portfolio.is_archived.is_(False)).order_by(Portfolio.id)
    )).scalars().all()
    if len(active) <= 1:
        raise HTTPException(422, "لا يمكن حذف المحفظة الوحيدة — أنشئ محفظة أخرى أولاً.")
    p = next((x for x in active if x.id == portfolio_id), None)
    if not p:
        raise HTTPException(404, "المحفظة غير موجودة")
    p.is_archived = True
    if p.is_default:
        p.is_default = False
        remaining = next(x for x in active if x.id != portfolio_id)
        remaining.is_default = True
    await db.commit()
    return success_response(message="أُرشِفت المحفظة (بياناتها محفوظة).")
