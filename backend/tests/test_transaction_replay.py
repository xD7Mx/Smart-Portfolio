"""
Transaction-engine reliability tests — run with:
    python3 tests/test_transaction_replay.py

Drives the REAL add/delete endpoints against an in-memory DB and asserts the
holding + cash land on hand-checked numbers through the full-replay recompute.
Focus: absolute reliability of every operation button for the far future,
especially the delete-before-a-split miscount the replay fix closes.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from datetime import datetime, timezone, timedelta
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.pool import StaticPool
    from sqlalchemy import select
    from app.core.database import Base
    from app.models.portfolio import Company, Holding
    from app.models.transaction import Transaction, Cash
    import app.models.market  # noqa: F401
    from app.api.v1.endpoints.transactions import (
        add_transaction, delete_transaction, TransactionCreate,
    )
    from loguru import logger
    logger.remove()

    eng = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool,
                              connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    S = async_sessionmaker(eng, expire_on_commit=False)

    D = datetime(2026, 1, 1, tzinfo=timezone.utc)

    async def holding(db, cid):
        return (await db.execute(select(Holding).where(Holding.company_id == cid))).scalars().one()

    async def cash(db):
        return (await db.execute(select(Cash))).scalars().one_or_none()

    async def new_company(db, sym):
        c = Company(symbol=sym, company_name=sym, status="ACTIVE")
        db.add(c); await db.commit(); await db.refresh(c)
        return c.id

    async def add(db, cid, day, **kw):
        return await add_transaction(TransactionCreate(company_id=cid, executed_at=D + timedelta(days=day), **kw), db)

    # ── 1) multiple historical splits + a sell ──────────────────────────
    async with S() as db:
        cid = await new_company(db, "2020")
        await add(db, cid, 1, transaction_type="BUY", quantity=100, price=60)
        await add(db, cid, 2, transaction_type="SPLIT", factor=3)
        await add(db, cid, 3, transaction_type="SPLIT", factor=2)      # 100→300→600
        h = await holding(db, cid)
        assert float(h.quantity) == 600 and abs(float(h.average_cost) - 10) < 1e-9, (h.quantity, h.average_cost)
        r = await add(db, cid, 4, transaction_type="SELL", quantity=300, price=15)
        h = await holding(db, cid)
        sold = (await db.execute(select(Transaction).where(Transaction.id == r["data"]["id"]))).scalars().one()
        assert float(h.quantity) == 300 and abs(float(sold.realized_gain) - 1500) < 1e-9, (h.quantity, sold.realized_gain)
    print("1. multiple historical splits + sell — qty/avg/realized all exact")

    # ── 2) THE FIX: delete a BUY that occurred BEFORE a split ────────────
    async with S() as db:
        cid = await new_company(db, "1120")
        r1 = await add(db, cid, 1, transaction_type="BUY", quantity=100, price=50)   # 100 @ 50
        await add(db, cid, 2, transaction_type="SPLIT", factor=2)                     # → 200
        await add(db, cid, 3, transaction_type="BUY", quantity=100, price=30)         # → 300, inv 8000
        h = await holding(db, cid)
        assert float(h.quantity) == 300 and float(h.invested_amount) == 8000
        # delete the FIRST buy (pre-split). Correct result: only the day-3 buy
        # survives → 100 shares, invested 3000 (NOT the naive 200 the old
        # reverse-from-current-state logic produced).
        await delete_transaction(r1["data"]["id"], db)
        h = await holding(db, cid)
        assert float(h.quantity) == 100, f"delete-before-split miscount: {h.quantity}"
        assert float(h.invested_amount) == 3000, h.invested_amount
    print("2. delete a BUY that predates a split — rebuilt to exact 100 shares (bug fixed)")

    # ── 3) out-of-order (back-dated) BUY inserted before an existing split
    async with S() as db:
        cid = await new_company(db, "1150")
        await add(db, cid, 5, transaction_type="BUY", quantity=100, price=40)  # day 5
        await add(db, cid, 6, transaction_type="SPLIT", factor=2)              # day 6 → 200
        # now back-date another BUY to day 1 (BEFORE the split) — replay must
        # apply the split to it too → (100+100)=200 pre-split, ×2 = 400.
        await add(db, cid, 1, transaction_type="BUY", quantity=100, price=40)
        h = await holding(db, cid)
        assert float(h.quantity) == 400, f"out-of-order back-dated buy: {h.quantity}"
        assert float(h.invested_amount) == 8000, h.invested_amount
    print("3. back-dated BUY before an existing split — replay applies split to it (400 shares)")

    # ── 4) delete one split among several ───────────────────────────────
    async with S() as db:
        cid = await new_company(db, "7010")
        await add(db, cid, 1, transaction_type="BUY", quantity=50, price=20)
        s = await add(db, cid, 2, transaction_type="SPLIT", factor=2)   # →100
        await add(db, cid, 3, transaction_type="SPLIT", factor=4)       # →400
        assert float((await holding(db, cid)).quantity) == 400
        await delete_transaction(s["data"]["id"], db)                    # remove the ×2
        h = await holding(db, cid)
        assert float(h.quantity) == 200, f"delete middle split: {h.quantity}"  # 50 ×4
    print("4. delete one split among several — remaining split re-applied exactly (200)")

    # ── 5) cash reconciliation across BUY/SELL/DIVIDEND + deletes ────────
    async with S() as db:
        # Cash is one portfolio-wide balance, so measure DELTAS around this
        # scenario (earlier scenarios moved cash in the shared in-memory DB).
        c0 = await cash(db)
        base = float(c0.available_cash) if c0 else 0.0
        cid = await new_company(db, "2222")
        await add(db, cid, 1, transaction_type="BUY", quantity=100, price=30, fees=10)  # -3010
        rd = await add(db, cid, 2, transaction_type="DIVIDEND", price=1.5)               # +150
        rs = await add(db, cid, 3, transaction_type="SELL", quantity=40, price=35, fees=5)  # +1395
        c = await cash(db)
        assert abs((float(c.available_cash) - base) - (-3010 + 150 + 1395)) < 1e-9, c.available_cash
        # delete the dividend and the sell → net cash effect back to just the buy
        await delete_transaction(rd["data"]["id"], db)
        await delete_transaction(rs["data"]["id"], db)
        c = await cash(db); h = await holding(db, cid)
        assert abs((float(c.available_cash) - base) - (-3010)) < 1e-9, c.available_cash
        assert float(h.quantity) == 100 and float(h.total_dividends_received) == 0
    print("5. cash + holding reconcile exactly after BUY/DIVIDEND/SELL then deletes")

    # ── 6) a standalone /dividends entry must survive a later recompute ──
    from app.api.v1.endpoints.dividends import add_dividend, DividendCreate
    async with S() as db:
        cid = await new_company(db, "4340")
        await add(db, cid, 1, transaction_type="BUY", quantity=200, price=10)
        # record a dividend the standalone way (no Transaction row created)
        await add_dividend(DividendCreate(company_id=cid, dividend_per_share=0.5,
                                          shares_at_time=200, action="CASH"), db)
        h = await holding(db, cid)
        assert float(h.total_dividends_received) == 100, h.total_dividends_received
        # now trigger a recompute via an unrelated transaction (a split)
        await add(db, cid, 2, transaction_type="SPLIT", factor=2)
        h = await holding(db, cid)
        assert float(h.quantity) == 400, h.quantity
        assert float(h.total_dividends_received) == 100, (
            f"standalone dividend dropped by recompute: {h.total_dividends_received}")
    print("6. standalone dividend survives a later transaction recompute (not dropped)")

    await eng.dispose()
    print("ALL TRANSACTION-REPLAY TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
