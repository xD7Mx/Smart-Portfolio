"""
Active-portfolio resolution — the single, central choke point that decides
which portfolio a request operates on. Every per-portfolio query scopes by
the id this returns, so isolation is enforced in ONE place instead of being
re-derived (and possibly forgotten) per endpoint.

The client sends the chosen portfolio in an `X-Portfolio-Id` header. If it's
missing, invalid, archived, or (Phase 2) not owned by the caller's account,
we fall back to the account's default portfolio — never to "all data", so a
bad/empty header can never leak or mix portfolios.
"""

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.portfolio import Portfolio


async def _default_portfolio_id(db: AsyncSession) -> int:
    row = (await db.execute(
        select(Portfolio.id)
        .where(Portfolio.is_archived.is_(False))
        .order_by(Portfolio.is_default.desc(), Portfolio.id)
        .limit(1)
    )).first()
    if row:
        return row[0]
    # No portfolio at all yet (brand-new DB before the migration's bootstrap
    # ran in this process) — create the default one on the spot.
    p = Portfolio(name="المحفظة الرئيسية", is_default=True, include_in_aggregate=True)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p.id


async def active_portfolio_id(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> int:
    """FastAPI dependency: the validated id of the portfolio this request
    targets, always falling back to the default (never to unscoped)."""
    raw = request.headers.get("X-Portfolio-Id")
    if raw:
        try:
            pid = int(raw)
        except (TypeError, ValueError):
            pid = None
        if pid is not None:
            exists = (await db.execute(
                select(Portfolio.id).where(
                    Portfolio.id == pid, Portfolio.is_archived.is_(False)
                )
            )).first()
            if exists:
                return pid
    return await _default_portfolio_id(db)


async def scope_portfolio(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Dependency عام على الموجّه المحمي: يضبط سياق العزل لكل طلب.
    - المحفظة النشطة (من الترويسة أو الافتراضية) → يُختم بها الإدخال ويُرشَّح
      بها القراءة.
    - ترويسة X-Portfolio-Aggregate=1 → وضع التوحيد: تُجمَع القراءة عبر كل
      المحافظ (بلا ترشيح)، والإدخال يبقى للمحفظة النشطة."""
    from app.core.portfolio_scope import set_scope
    pid = await active_portfolio_id(request, db)
    read_all = request.headers.get("X-Portfolio-Aggregate") == "1"
    set_scope(pid, read_all)
