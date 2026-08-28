"""
Backup/restore engine tests — run with:  python3 tests/test_backup_service.py
(from the backend/ directory; needs aiosqlite installed for the in-memory DB).

Covers the real disaster-recovery path end-to-end on the actual models:
dump integrity checksum, tamper rejection BEFORE any row is deleted,
full round-trip restore with type coercion (isoformat -> datetime,
float -> Decimal), atomic file writes, and the 14-copy retention prune.
"""
import asyncio
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["BACKUP_DIR"] = tempfile.mkdtemp()


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select, func as F
    from app.core.database import Base
    from app.models.portfolio import Company, Holding
    from app.models.transaction import Transaction
    import app.models.market  # noqa: F401 — register remaining tables
    from app.services import backup_service as bs
    from datetime import datetime, timezone
    from decimal import Decimal
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
        db.add(Holding(company_id=c.id, quantity=Decimal("100"), average_cost=Decimal("27.5"),
                       invested_amount=Decimal("2750"), market_value=Decimal("2900")))
        db.add(Transaction(company_id=c.id, transaction_type="BUY", quantity=Decimal("100"),
                           price=Decimal("27.5"), total_amount=Decimal("2750"),
                           executed_at=datetime(2026, 1, 5, 10, 30, tzinfo=timezone.utc)))
        await db.commit()

    # 1) dump embeds a correct checksum and serializes datetimes as isoformat
    async with S() as db:
        dump = await bs.build_dump(db)
    assert dump["checksum"] == bs._tables_checksum(dump["tables"])
    assert dump["tables"]["transactions"][0]["executed_at"].startswith("2026-01-05T10:30")
    print("1. dump ok — checksum embedded, datetimes serialized")

    # 2) a tampered file is rejected before a single row is deleted
    bad = json.loads(json.dumps(dump))
    bad["tables"]["holdings"][0]["quantity"] = 999999
    async with S() as db:
        try:
            await bs.restore_dump(db, bad)
            raise AssertionError("tampered file was accepted")
        except ValueError:
            pass
        assert (await db.execute(select(F.count()).select_from(Holding))).scalar() == 1
    print("2. tampered file rejected, existing rows untouched")

    # 3) full round-trip restore, JSON scalars coerced back to DB types
    async with S() as db:
        await bs.restore_dump(db, dump)
        t = (await db.execute(select(Transaction))).scalars().one()
        assert t.executed_at is not None
        assert float(t.quantity) == 100.0 and float(t.price) == 27.5
        h = (await db.execute(select(Holding))).scalars().one()
        assert float(h.average_cost) == 27.5
        c2 = (await db.execute(select(Company))).scalars().one()
        assert c2.company_name == "أرامكو السعودية"
    print("3. round-trip restore ok — datetime/Decimal coercion verified")

    # 4) file backups are written atomically and are readable
    async with S() as db:
        for _ in range(3):
            await bs.write_backup_file(db)
    bdir = pathlib.Path(os.environ["BACKUP_DIR"])
    files = sorted(bdir.glob("smart-portfolio-backup-*.json"))
    assert len(files) == 3
    data = json.loads(files[-1].read_text())
    assert data["checksum"] and data["tables"]["companies"][0]["symbol"] == "2222"
    assert not list(bdir.glob("*.tmp"))
    print("4. backup files written atomically and readable")

    # 5) retention prunes to the newest KEEP_FILES copies
    for i in range(20):
        (bdir / ("smart-portfolio-backup-2025010%d-00000%d.json" % (i // 10, i % 10))).write_text("{}")
    async with S() as db:
        await bs.write_backup_file(db)
    remaining = list(bdir.glob("smart-portfolio-backup-*.json"))
    assert len(remaining) == bs.KEEP_FILES, f"retention failed: {len(remaining)} files"
    print(f"5. retention prunes to {bs.KEEP_FILES} copies")

    await eng.dispose()
    print("ALL BACKUP TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
