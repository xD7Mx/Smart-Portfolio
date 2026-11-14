#!/usr/bin/env python3
"""كاشفُ فحص السلامة (ملاحظةُ المالك 2026-11-14: «فحصُ السلامة يظهر إنذاراً قبيحاً») — قارئٌ فقط: أيُّ فحصٍ لم يمرّ ولماذا."""
import asyncio, os, sys, time
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


async def main():
    from app.core.database import AsyncSessionLocal
    from app.services.integrity import run_integrity_check
    async with AsyncSessionLocal() as db:
        r = await run_integrity_check(db)
        # سجلُّ عمليات الشركة الساقطة (النوعُ والتاريخُ والكمية) — ليُعرف مصدرُ الفرق
        from sqlalchemy import select
        from app.models.portfolio import Company
        from app.models.transaction import Transaction
        bad = [c.get("name", "").split("— ", 1)[-1] for c in (r or {}).get("checks") or [] if not c.get("ok")]
        for nm in bad:
            comp = (await db.execute(select(Company).where(Company.company_name == nm))).scalars().first()
            if not comp:
                continue
            rows = (await db.execute(select(Transaction).where(Transaction.company_id == comp.id)
                                     .order_by(Transaction.executed_at))).scalars().all()
            print(f"— سجلُّ {nm} ({comp.symbol}): {len(rows)} عملية")
            for t in rows:
                tt = getattr(t.transaction_type, "value", t.transaction_type)
                print(f"   {str(t.executed_at)[:10]} {tt} {float(t.quantity or 0):g} @ {float(t.price or 0):g}"
                      f"{' · ' + str(t.notes)[:60] if getattr(t, 'notes', None) else ''}")
    for c in (r or {}).get("checks") or []:
        if not c.get("ok"):
            print("✘", c.get("name"), "— المتوقَّع من السجل:", c.get("expected"), "· المخزَّن:", c.get("actual"), "·", c.get("meaning"))


asyncio.run(main())
