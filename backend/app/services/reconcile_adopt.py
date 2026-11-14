"""‏D725: تثبيتُ تصحيح الكمية اليدويّ نقطةَ مطابقة — مرّةً واحدة.

كان تصحيحُ المركز يكتب الكميةَ رقماً نهائياً بلا أثرٍ في السجل (قِيس: الألبان 45 سهماً والسجلُّ 22)، فيعدّه فحصُ السلامة خطأً،
ويمحوه أوّلُ تعديلٍ لاحق (إعادةُ البناء من السجل)، ويُرفض بيعُ الأسهم المصحَّحة. فكلُّ حيازةٍ تخالف كميتُها المخزَّنةُ سجلَّها ولا
نقطةَ لها تُثبَّت كما هي — الكميةُ والتكلفةُ المخزَّنتان — نقطةَ مطابقةٍ بتاريخ التثبيت. لا يتغيّر رقمٌ يراه المالك.
"""
from datetime import datetime, timezone

TOL = 1e-6


async def adopt_quantity_corrections(db) -> int:
    from sqlalchemy import select
    from app.models.portfolio import Holding
    from app.api.v1.endpoints.transactions import replay_holding
    n = 0
    for h in (await db.execute(select(Holding))).scalars().all():
        if h.reconciled_at is not None:
            continue
        rq = float((await replay_holding(db, h.company_id))["quantity"])
        if abs(float(h.quantity or 0) - rq) > TOL:
            h.reconciled_at = datetime.now(timezone.utc)
            h.reconciled_quantity = float(h.quantity or 0)
            h.reconciled_invested = float(h.invested_amount or 0)
            h.cost_basis_adjustment = 0
            n += 1
    if n:
        await db.commit()
    return n
