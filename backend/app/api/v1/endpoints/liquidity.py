"""
إدارة السيولة — خطّة ضخّ رأس المال على دفعات.

نموذج المالك: **رقمٌ واحد** لقيمة الدفعة (٦٠٬٠٠٠ مثلاً)، ولكل شركةٍ **نسبة**
منه. فنصيب الشركة في الدفعة = قيمة الدفعة × نسبتها، والمرصود لها = ذلك النصيب
× عدد الدفعات المؤشَّرة، وعددُ الأسهم = المرصود ÷ السعر.

ولماذا نسبةٌ لا مبلغاً لكل شركة: تعديل قيمة الدفعة يُعيد توزيع الجميع بضربةٍ
واحدة، وهو القرار الذي يُتَّخذ فعلاً («سأضخّ ٨٠ ألفاً بدل ٦٠»). أمّا المبالغ
المفردة فتُحتّم تعديل عشرة حقولٍ يدوياً في كل مرّة، ويسهل أن تختلّ مجاميعها.

والحساب هنا لا في الواجهة — لسببين: أن يبقى تعريفٌ واحد لا نسختان (وهي علّة
تكرّرت في هذا التطبيق سبع مرّات)، وأن تُقارَن الخطّة بالسيولة الفعلية من مصدرها.

ثلاث إضافات على الملف الأصلي، كلٌّ منها يمنع خطأً واقعياً:
  • **أسهمٌ صحيحة**: تداول لا يقبل جزء سهم، فالكسر يُقرَّب للأسفل ويُعرض
    الباقي نقداً — «١٬٦٢٦ سهماً» أمرٌ قابل للتنفيذ، و«١٬٦٢٥٫٨» ليس كذلك.
  • **مقابلة السيولة**: الخطّة تُقارن بالنقد المتاح فعلاً، فيُعلَم العجز قبل
    الالتزام لا بعده.
  • **الوزن الناتج**: وزن كل شركة بعد تنفيذ الخطّة — فقرار الدفعات قرار وزنٍ
    في حقيقته، وإخفاؤه يجعل الخطّة تُبنى بلا أثرها الظاهر.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, field_validator
from typing import Optional

from app.core.database import get_db
from app.core.response import success_response
from app.models.market import Allocation, LiquidityPlan, Settings
from app.models.portfolio import Holding, Company
from app.models.transaction import Cash

router = APIRouter()

TRANCHES = ("t1", "t2", "t3", "t4", "t5")
# قيمة الدفعة رقمٌ واحد للمحفظة كلّها، فمكانه الإعدادات لا صفٌّ لكل شركة.
TRANCHE_KEY = "liquidity.tranche_value"


async def _tranche_value(db) -> float:
    row = (await db.execute(select(Settings).where(Settings.key == TRANCHE_KEY))).scalar_one_or_none()
    try:
        return float(row.value) if row and row.value else 0.0
    except (TypeError, ValueError):
        return 0.0


def _row(plan: LiquidityPlan | None, holding: Holding, company: Company,
         tranche_value: float, auto_pct: float) -> dict:
    # النسبة المحرَّرة تتقدّم، فإن لم تُحرَّر فالوزن **المستهدف** في التوزيع
    # النسبي. والمستهدف لا الحالي: الدفعة أداة الوصول إلى الهدف، فتوزيعها على
    # الأوزان الحالية يُثبّت الانحراف بدل أن يُغلقه.
    # ولا يُفرض هذا على تحريرٍ سابق — ولو كان صفراً.
    raw = getattr(plan, "share_pct", None) if plan is not None else None
    is_auto = raw is None
    pct = auto_pct if is_auto else float(raw)
    # نصيب الشركة من الدفعة الواحدة — يُشتقّ ولا يُخزَّن، فلا يتباعد عن النسبة.
    reserved = tranche_value * pct / 100.0
    flags = [bool(getattr(plan, t, False)) for t in TRANCHES]
    count = sum(1 for f in flags if f)
    override = getattr(plan, "price_override", None)
    live = float(holding.last_price or 0) if holding else 0.0
    price = float(override) if override else live
    amount = reserved * count
    # أوامر الشراء تُحسب بعدد دفعاتها هي — بطاقةٌ مستقلّة بقرارٍ مستقل.
    execn = getattr(plan, "exec_tranches", None)
    execn = int(execn) if execn is not None else 0
    exec_amount = reserved * execn
    # القسمة على سعرٍ صفر مستحيلة الناتج: تُترك الأسهم صفراً ويُعلَن سبب ذلك
    # بدل رقمٍ مُختلَق أو انهيارٍ في الطلب.
    shares = int(amount // price) if price > 0 else 0
    spent = shares * price
    exec_shares = int(exec_amount // price) if price > 0 else 0
    return {
        "company_id": company.id,
        "symbol": company.symbol,
        "name": company.company_name,
        "share_pct": round(pct, 4),
        "pct_is_auto": is_auto,
        "reserved_amount": round(reserved, 2),
        "tranches": flags,
        "tranches_done": count,
        "price": round(price, 4),
        "price_is_override": bool(override),
        "live_price": round(live, 4),
        "amount": round(amount, 2),
        "shares": shares,
        "exec_tranches": execn,
        "exec_amount": round(exec_amount, 2),
        "exec_shares": exec_shares,
        "exec_total": round(exec_shares * price, 2),
        # الباقي بعد شراء أسهمٍ صحيحة — نقدٌ لا يُوظَّف، وإخفاؤه يجعل المجاميع
        # لا تُطابق ما يُخصم من الحساب فعلاً.
        "leftover": round(amount - spent, 2),
        "spent": round(spent, 2),
        "current_value": round(float(holding.market_value or 0), 2) if holding else 0.0,
    }


@router.get("")
async def get_plan(db: AsyncSession = Depends(get_db)):
    holdings = {h.company_id: h for h in (await db.execute(select(Holding))).scalars().all()}
    companies = {c.id: c for c in (await db.execute(select(Company))).scalars().all()}
    plans = {p.company_id: p for p in (await db.execute(select(LiquidityPlan))).scalars().all()}
    tranche_value = await _tranche_value(db)

    # الأوزان المستهدفة — الأساس التلقائي لنسب الشركات غير المحرَّرة.
    live = {cid: h for cid, h in holdings.items()
            if companies.get(cid) and companies[cid].status != "ARCHIVED"}
    targets = {a.company_id: float(a.target_weight or 0)
               for a in (await db.execute(select(Allocation))).scalars().all()}
    # وإن لم تُحدَّد أهدافٌ أصلاً فالوزن الحالي هو البديل الوحيد المعقول —
    # أمّا الصفر فيجعل الجدول كلّه أصفاراً بلا سببٍ ظاهر للمالك.
    has_targets = sum(targets.get(cid, 0.0) for cid in live) > 0
    mv_all = sum(float(h.market_value or 0) for h in live.values())

    rows = []
    for cid, h in live.items():
        c = companies[cid]
        auto = (targets.get(cid, 0.0) if has_targets
                else (float(h.market_value or 0) / mv_all * 100 if mv_all else 0.0))
        rows.append(_row(plans.get(cid), h, c, tranche_value, auto))
    # ترتيب المالك من شاشة الحيازات — مصدرٌ واحد للترتيب في كل البطاقات.
    rank = {cid: (int(h.sort_order or 0) or 10**6, h.id) for cid, h in live.items()}
    rows.sort(key=lambda r: rank.get(r["company_id"], (10**6, 0)))

    cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    cash = float(cash_row.available_cash or 0) if cash_row else 0.0

    pct_total = round(sum(r["share_pct"] for r in rows), 4)
    allocated = round(sum(r["reserved_amount"] for r in rows), 2)
    planned = round(sum(r["amount"] for r in rows), 2)
    spent = round(sum(r["spent"] for r in rows), 2)
    mv_now = sum(r["current_value"] for r in rows)
    after_total = mv_now + spent

    # الوزن الناتج بعد التنفيذ — قرار الدفعات قرار وزنٍ في حقيقته.
    for r in rows:
        after = r["current_value"] + r["spent"]
        r["weight_after"] = round(after / after_total * 100, 2) if after_total else None

    return success_response(data={
        "items": rows,
        "tranche_value": round(tranche_value, 2),
        # مجموع النسب: يجب أن يبلغ ١٠٠٪. ما دونها يعني مالاً غير موزَّع،
        # وما فوقها يعني توزيع أكثر ممّا رُصد — وكلاهما يُعلَن لا يُصحَّح ضمناً.
        "pct_total": pct_total,
        "allocated_per_tranche": allocated,
        "unallocated_per_tranche": round(tranche_value - allocated, 2),
        "planned_total": planned,
        "spent_total": spent,
        "leftover_total": round(planned - spent, 2),
        "available_cash": round(cash, 2),
        # عجزٌ لا فائض: ما ينقص لتنفيذ الخطّة كاملةً بالسيولة الحالية.
        "shortfall": round(max(0.0, spent - cash), 2),
        "remaining_cash": round(cash - spent, 2),
        "tranche_count": len(TRANCHES),
    })


class PlanItem(BaseModel):
    company_id: int
    share_pct: Optional[float] = None
    # العودة إلى الوزن التلقائي — بلا هذا الزرّ لا سبيل للتراجع عن تحريرٍ واحد
    # إلا بحساب الوزن يدوياً وإعادة كتابته، وهو ما لا يُطلَب من المالك.
    clear_share_pct: bool = False
    tranches: Optional[list[bool]] = None
    exec_tranches: Optional[int] = None
    price_override: Optional[float] = None
    clear_price_override: bool = False

    @field_validator("share_pct")
    @classmethod
    def _pct(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("النسبة يجب أن تكون بين صفر ومئة.")
        return v

    @field_validator("exec_tranches")
    @classmethod
    def _ex(cls, v):
        if v is not None and (v < 0 or v > len(TRANCHES)):
            raise ValueError(f"عدد الدفعات بين صفر و{len(TRANCHES)}.")
        return v

    @field_validator("price_override")
    @classmethod
    def _price(cls, v):
        if v is not None and v <= 0:
            raise ValueError("السعر يجب أن يكون أكبر من صفر.")
        return v

    @field_validator("tranches")
    @classmethod
    def _tr(cls, v):
        if v is not None and len(v) != len(TRANCHES):
            raise ValueError(f"عدد الدفعات يجب أن يكون {len(TRANCHES)}.")
        return v


class PlanUpdate(BaseModel):
    items: list[PlanItem]
    tranche_value: Optional[float] = None

    @field_validator("tranche_value")
    @classmethod
    def _tv(cls, v):
        if v is not None and v < 0:
            raise ValueError("قيمة الدفعة لا تكون سالبة.")
        # سقفٌ معقول: رقمٌ فوق التريليون خطأ إدخال، وقبوله يُنتج أوامر شراءٍ
        # بمبالغ لا وجود لها ويُفسد حساب الشحّ (shortfall).
        if v is not None and v > 1e12:
            raise ValueError("قيمة الدفعة أكبر من الحدّ المعقول.")
        return v


@router.put("")
async def save_plan(payload: PlanUpdate, db: AsyncSession = Depends(get_db)):
    """حفظ الخطّة. لا يمسّ نقداً ولا حيازةً ولا سجلّ عمليات — خطّةٌ لا تنفيذ."""
    if not payload.items and payload.tranche_value is None:
        raise HTTPException(422, "لا شيء للحفظ.")
    existing = {p.company_id: p for p in (await db.execute(select(LiquidityPlan))).scalars().all()}
    known = set((await db.execute(select(Company.id))).scalars().all())

    for item in payload.items:
        if item.company_id not in known:
            continue
        p = existing.get(item.company_id)
        if p is None:
            p = LiquidityPlan(company_id=item.company_id)
            db.add(p)
            existing[item.company_id] = p
        if item.clear_share_pct:
            p.share_pct = None
        elif item.share_pct is not None:
            p.share_pct = item.share_pct
        if item.exec_tranches is not None:
            p.exec_tranches = item.exec_tranches
        if item.tranches is not None:
            for name, val in zip(TRANCHES, item.tranches):
                setattr(p, name, bool(val))
        if item.clear_price_override:
            p.price_override = None
        elif item.price_override is not None:
            p.price_override = item.price_override

    if payload.tranche_value is not None:
        row = (await db.execute(select(Settings).where(Settings.key == TRANCHE_KEY))).scalar_one_or_none()
        if row is None:
            row = Settings(key=TRANCHE_KEY, category="liquidity")
            db.add(row)
        row.value = str(payload.tranche_value)

    await db.commit()
    return success_response(message="حُفظت الخطّة.")
