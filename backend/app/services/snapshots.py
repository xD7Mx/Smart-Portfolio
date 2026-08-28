"""
Daily portfolio snapshots — real performance history that accumulates
day by day. One row per calendar day (upsert on re-run).
"""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.portfolio import Holding, PortfolioSnapshot
from app.models.transaction import Cash

logger = logging.getLogger(__name__)


async def take_snapshot(db: AsyncSession) -> PortfolioSnapshot | None:
    """لقطة يومية لكل محفظة على حدة (بيانات معزولة) — فيبني كلٌّ منها تاريخ ثروتها
    المستقل. نضبط سياق العزل لكل محفظة فتُرشَّح الحيازات والسيولة تلقائيًا."""
    from app.core.portfolio_scope import set_scope, reset_scope
    from app.models.portfolio import Portfolio
    pids = (await db.execute(
        select(Portfolio.id).where(Portfolio.is_archived.is_(False)).order_by(Portfolio.id)
    )).scalars().all()
    last = None
    try:
        for pid in pids:
            set_scope(pid, False)
            last = await _snapshot_one(db)
    finally:
        reset_scope()
    return last


async def _snapshot_one(db: AsyncSession) -> PortfolioSnapshot:
    """لقطة المحفظة النشطة في السياق الحالي (يُرشَّح كل شيء بها تلقائيًا)."""
    result = await db.execute(select(Holding).options(selectinload(Holding.company)))
    holdings = result.scalars().all()

    from app.api.v1.endpoints.holdings import refresh_holdings_prices
    await refresh_holdings_prices(db, holdings)

    market_value = sum(float(h.market_value or 0) for h in holdings)
    invested = sum(float(h.invested_amount or 0) for h in holdings)
    unrealized = market_value - invested

    cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    cash = float(cash_row.available_cash or 0) if cash_row else 0.0

    # Governance score history — same daily cadence as the value snapshot,
    # so "is my portfolio getting safer over time" gets a real trend line
    # instead of only today's single number.
    governance_score = None
    try:
        from app.services.governance import get_portfolio_governance
        gov = await get_portfolio_governance(db)
        governance_score = gov.get("overall_score")
    except Exception as e:
        logger.warning("Governance score skipped in snapshot: %s", e)

    # درجة **التقييم العام** — وهي غير درجة الحوكمة أعلاه.
    #
    # تُحسب بنفس مُدخلات نقطة `/ai/evaluation` بالضبط (الأهداف، وسياق الأداء،
    # واسترداد رأس المال)، لا بنسختها المختصرة. ولو حُسبت مختصرةً لسجّلنا
    # رقماً يخالف ما يراه المالك على الشاشة، فيرسم الخطُّ تاريخاً لمقياسٍ لا
    # ينتهي إلى الرقم المكتوب فوقه — وهو خطأٌ لا يُكتشف لأنه يبدو صحيحاً.
    evaluation_score = None
    try:
        from app.services import portfolio_analytics
        from app.api.v1.endpoints.ai import (
            _portfolio_snapshot, _target_weights,
            _performance_context, _capital_recovery_context,
        )
        ev_holdings, ev_cash = await _portfolio_snapshot(db)
        ev = portfolio_analytics.evaluate(
            ev_holdings, ev_cash,
            await _target_weights(db),
            await _performance_context(db, ev_holdings),
            await _capital_recovery_context(db),
        )
        evaluation_score = ev.get("overall_score")
    except Exception as e:
        logger.warning("Evaluation score skipped in snapshot: %s", e)

    today = date.today()
    snap = (
        await db.execute(
            select(PortfolioSnapshot).where(PortfolioSnapshot.snapshot_date == today)
        )
    ).scalar_one_or_none()
    if not snap:
        snap = PortfolioSnapshot(snapshot_date=today)
        db.add(snap)

    snap.market_value = market_value
    snap.invested_amount = invested
    snap.cash_balance = cash
    snap.unrealized_profit = unrealized
    snap.governance_score = governance_score
    snap.evaluation_score = evaluation_score
    await db.commit()
    logger.info("Snapshot %s: mv=%.2f invested=%.2f cash=%.2f governance=%s evaluation=%s",
                today, market_value, invested, cash, governance_score, evaluation_score)
    return snap


async def snapshot_if_missing_today(db: AsyncSession) -> None:
    """Startup guard: يضمن لقطة اليوم لكل محفظة (upsert لكلٍّ — بلا تكرار)."""
    await take_snapshot(db)
