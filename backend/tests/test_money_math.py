"""
Money-math + portfolio-protection tests — run with:
    python3 tests/test_money_math.py
(from the backend/ directory; needs aiosqlite for the in-memory DB).

Covers the calculations a mistake in which costs real money, computed with
hand-checked literal numbers:
  - BUY average cost / invested amount / cash deduction (incl. fees)
  - SELL realized gain, cost-basis reduction, over-sell rejection
  - DIVIDEND cash credit + dividend row
  - BONUS shares (quantity up, cost basis unchanged)
  - SPLIT (quantity × factor, price ÷ factor, value unchanged)
  - ghost-company cleanup: deletes ONLY companies with no Transaction ever,
    never touching the owner's confirmed allowlist.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from app.core.database import Base
    from app.models.portfolio import Company, Holding
    from app.models.transaction import Transaction, Cash
    import app.models.market  # noqa: F401
    from app.api.v1.endpoints.transactions import _apply, TransactionCreate
    from fastapi import HTTPException
    from loguru import logger
    logger.remove()

    eng = create_async_engine("sqlite+aiosqlite://")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    S = async_sessionmaker(eng, expire_on_commit=False)

    async with S() as db:
        c = Company(symbol="2222", company_name="أرامكو السعودية", status="ACTIVE")
        db.add(c)
        await db.commit()
        await db.refresh(c)
        cid = c.id

        # 1) BUY 100 @ 27.50 + 10 fees → invested 2760, avg 27.60, cash -2760
        await _apply(db, TransactionCreate(company_id=cid, transaction_type="BUY",
                                           quantity=100, price=27.5, fees=10))
        await db.commit()
        h = (await db.execute(select(Holding).where(Holding.company_id == cid))).scalars().one()
        cash = (await db.execute(select(Cash))).scalars().one()
        assert float(h.quantity) == 100 and float(h.invested_amount) == 2760
        assert abs(float(h.average_cost) - 27.6) < 1e-9
        assert float(cash.available_cash) == -2760
        print("1. BUY math ok (qty/invested/avg-cost/cash incl. fees)")

        # 2) Second BUY 50 @ 30 (no fees) → invested 4260, avg 28.40
        await _apply(db, TransactionCreate(company_id=cid, transaction_type="BUY",
                                           quantity=50, price=30, fees=0))
        await db.commit()
        await db.refresh(h)
        assert float(h.quantity) == 150 and float(h.invested_amount) == 4260
        assert abs(float(h.average_cost) - 28.4) < 1e-9
        print("2. averaging across two BUYs ok")

        # 3) SELL 50 @ 32, fees 5 → realized = 50×(32−28.40)−5 = 175
        #    invested drops by 50×28.40 = 1420 → 2840; qty 100
        total, gain, _ = await _apply(db, TransactionCreate(
            company_id=cid, transaction_type="SELL", quantity=50, price=32, fees=5))
        await db.commit()
        await db.refresh(h)
        assert abs(gain - 175) < 1e-9, gain
        assert float(h.quantity) == 100 and abs(float(h.invested_amount) - 2840) < 1e-9
        assert abs(total - (50 * 32 - 5)) < 1e-9  # proceeds credited to cash
        print("3. SELL realized gain + cost-basis reduction ok")

        # 4) over-sell must be rejected
        try:
            await _apply(db, TransactionCreate(company_id=cid, transaction_type="SELL",
                                               quantity=1000, price=32, fees=0))
            raise AssertionError("over-sell accepted")
        except HTTPException as e:
            assert e.status_code == 422
        print("4. over-sell rejected")

        # 5) DIVIDEND 1.5/share on 100 shares → +150 cash, dividend row created
        cash_before = float(cash.available_cash)
        _, _, div = await _apply(db, TransactionCreate(
            company_id=cid, transaction_type="DIVIDEND", price=1.5))
        await db.commit()
        await db.refresh(cash)
        await db.refresh(h)
        assert abs(float(cash.available_cash) - (cash_before + 150)) < 1e-9
        assert float(h.total_dividends_received) == 150
        assert div is not None and float(div.received_amount) == 150
        print("5. DIVIDEND credit + record ok")

        # 6) BONUS 10 shares → qty 110, invested unchanged
        inv_before = float(h.invested_amount)
        await _apply(db, TransactionCreate(company_id=cid, transaction_type="BONUS", quantity=10))
        await db.commit()
        await db.refresh(h)
        assert float(h.quantity) == 110 and float(h.invested_amount) == inv_before
        print("6. BONUS shares ok (cost basis unchanged)")

        # 7) SPLIT ×2 → qty 220, last_price halved
        lp_before = float(h.last_price)
        await _apply(db, TransactionCreate(company_id=cid, transaction_type="SPLIT", factor=2))
        await db.commit()
        await db.refresh(h)
        assert float(h.quantity) == 220 and abs(float(h.last_price) - lp_before / 2) < 1e-9
        print("7. SPLIT ok (quantity doubled, price halved)")

    # 8) ghost cleanup: no-Transaction companies deleted, allowlist + real kept
    async with S() as db:
        real = (await db.execute(select(Company).where(Company.symbol == "2222"))).scalars().one()
        ghost = Company(symbol="9999", company_name="شركة وهمية", status="ACTIVE")
        allow = Company(symbol="4340", company_name="الراجحي ريت", status="ACTIVE")  # allowlisted, no tx
        db.add_all([ghost, allow])
        await db.commit()

        from app.api.v1.endpoints.settings import cleanup_directory_companies
        res = await cleanup_directory_companies(db)
        removed = (res.get("data") or {}).get("removed_symbols")
        assert removed == ["9999"], removed
        left = set((await db.execute(select(Company.symbol))).scalars().all())
        assert left == {"2222", "4340"}, left
    print("8. ghost cleanup: only the no-transaction, non-allowlisted company removed")

    await eng.dispose()
    print("ALL MONEY-MATH TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
