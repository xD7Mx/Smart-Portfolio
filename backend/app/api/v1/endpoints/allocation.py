"""
Target weights & rebalancing — decision support only, never auto-executes.
Weights are % of investable capital (market value + available cash).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.response import success_response
from app.models.market import Allocation, Settings
from app.models.portfolio import Holding, Company
from app.models.transaction import Cash, Transaction, TransactionType
from typing import Optional
from pydantic import BaseModel, field_validator

router = APIRouter()


class TargetItem(BaseModel):
    company_id: int
    target_weight: float  # percent 0-100

    @field_validator("target_weight")
    @classmethod
    def _range(cls, v: float) -> float:
        # الوزن كان يُقبل سالباً أو فوق المئة بلا حارس. والسالب يُنتج «نصيباً»
        # سالباً من السيولة والحوض فيظهر أمر شراءٍ بمبلغٍ سالب، وما فوق المئة
        # يوزّع أكثر من كل ما تملك على شركةٍ واحدة.
        if v is None or v < 0 or v > 100:
            raise ValueError("الوزن المستهدف يجب أن يكون بين صفر ومئة.")
        return v


class TargetsUpdate(BaseModel):
    items: list[TargetItem]


async def _snapshot(db: AsyncSession):
    # ترتيب المالك من شاشة الحيازات — يسري على كل بطاقة تعرض شركات.
    result = await db.execute(
        select(Holding).options(selectinload(Holding.company))
        .order_by(Holding.sort_order.asc(), Holding.id.asc())
    )
    holdings = [h for h in result.scalars().all() if h.company and h.company.status != "ARCHIVED"]
    cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    cash = float(cash_row.available_cash or 0) if cash_row else 0.0
    total_mv = sum(float(h.market_value or 0) for h in holdings)
    investable = total_mv + cash
    targets = {a.company_id: float(a.target_weight or 0)
               for a in (await db.execute(select(Allocation))).scalars().all()}
    return holdings, cash, total_mv, investable, targets


@router.get("")
async def get_allocation(db: AsyncSession = Depends(get_db)):
    holdings, cash, total_mv, investable, targets = await _snapshot(db)

    # نصيب كل شركة من السيولة ومن رصيد إعادة الاستثمار — **بنسبة وزنها
    # المستهدف مباشرةً**، لا بحصّة حاجتها كما كان سابقاً. أبسط وأصرح: شركة
    # وزنها ٣٠٪ تأخذ ٣٠٪ من كل مصدر، بصرف النظر عن قربها أو بعدها عن هدفها
    # حالياً. شركة بلا وزن مستهدف لا حصّة لها أصلاً — تُترك None فتُعرض
    # الواجهة «لم تحدد» بدل رقم مُختلَق.
    #
    # ── إزالة ازدواج الحساب ───────────────────────────────────────────────
    # حوض إعادة الاستثمار **جزءٌ من السيولة لا إضافةٌ إليها**: نفس الريالات
    # موجودة في available_cash. وكان النصيبان يُحسبان كلاهما على النقد الكامل،
    # فيُجمَعان في «المبلغ الكلي» فيُعدّ الحوض مرّتين ويظهر مبلغٌ شرائي أكبر
    # من المتاح فعلاً. الفرق كان ~١٪ حين كان الحوض صغيراً فمرّ دون ملاحظة،
    # وبلغ ~٤٪ بعد أن صار مصدره حصيلة البيع الكلية، ويكبر مع كل بيع.
    #
    # الفصل الآن قاطع: «سيولة» = النقد الجديد (النقد ناقص الحوض)، و«إعادة
    # استثمار» = الحوض. فمجموعهما = النقد المتاح بالضبط، لا أكثر، ويبقى
    # التمييز ظاهراً لبيان مصدر التمويل.
    from app.services.portfolio_return import compute_reinvestment_pool
    pool_info = await compute_reinvestment_pool(db)
    pool = pool_info["pool"]
    fresh_cash = max(0.0, cash - pool)

    # ── عائدُ التوزيعات لكلّ شركة — من مخزن الفرز، بلا نداءِ شبكة ──────────
    # يُطلب ليُحسب **معدّلُ عائد التوزيعات المرجّح بالأوزان المستهدفة** في صفّ
    # المجموع: المالك يوازن الأوزان لا لِتُوزَّع السيولة وحدَها، بل ليعرف ماذا
    # يُدرّ عليه هذا التوزيع نفسُه. والرقمُ من الصفوف المخزَّنة التي تُغذّي قسم
    # السوق — نفسُ الرقم الذي يراه هناك، لا رقمٌ ثانٍ باسمٍ واحد.
    from app.data.company_sectors import SYMBOL_TO_SECTOR_AR

    dy_by_symbol: dict[str, float] = {}
    try:
        from app.services.market_screener import get_cached_screener
        for r in (get_cached_screener() or []):
            v = r.get("dividend_yield")
            if isinstance(v, (int, float)) and v > 0:
                dy_by_symbol[str(r.get("symbol"))] = float(v)
    except Exception:                                             # noqa: BLE001
        dy_by_symbol = {}

    data = []
    for h in holdings:
        mv = float(h.market_value or 0)
        tw = targets.get(h.company_id, 0)
        lp = float(h.last_price or 0)
        if tw > 0:
            liquidity_share = round(tw / 100 * fresh_cash, 2)
            reinvest_share = round(tw / 100 * pool, 2)
            total_amount = round(liquidity_share + reinvest_share, 2)
            total_shares = round(total_amount / lp, 1) if lp else None
        else:
            liquidity_share = reinvest_share = total_amount = total_shares = None
        data.append({
            "company_id": h.company_id,
            "symbol": h.company.symbol,
            "name": h.company.company_name,
            "market_value": mv,
            "current_weight": round(mv / investable * 100, 2) if investable else 0,
            "target_weight": tw,
            "last_price": lp,
            # None تعني «غير متوفّر» — لا صفراً يُقرأ «لا توزيعات».
            "dividend_yield": dy_by_symbol.get(str(h.company.symbol)),
            # ══ الحكمُ الشرعيّ في جدول القرار ══ (بأمر المالك · D232)
            # الجدولُ يقول «اشترِ كذا سهماً» — فحكمُ الورقة شرطُ قراءةِ
            # الأمر لا زينةٌ بجانبه. من حقل الشركة نفسِه الذي تقرؤه
            # صفحةُ الحيازات، فلا مصدرَ ثانياً يخالفه.
            "sharia_status": h.company.sharia_status,
            # القطاع من دليل التطبيق المنسَّق أوّلاً — لا من تصنيفٍ خارجيّ
            # قد يخالفه. يُنشَر ليُرسم توزيعُ القطاعات مع الجدول نفسِه.
            "sector": (SYMBOL_TO_SECTOR_AR.get(str(h.company.symbol).replace(".SR", ""))
                       or h.company.sector or None),
            "liquidity_share": liquidity_share,
            "reinvest_share": reinvest_share,
            "total_amount": total_amount,
            "total_shares": total_shares,
        })
    return success_response(data={
        "items": data,
        "total_market_value": total_mv,
        "available_cash": cash,
        # النقد الجديد = النقد ناقص الحوض. مجموعه مع الحوض = النقد المتاح تماماً.
        "fresh_cash": round(fresh_cash, 2),
        "investable": investable,
        "reinvestment_pool": pool,
        # تشخيص الحوض — كي تُفسّر الواجهة رصيداً منخفضاً بدل رقمٍ صامت يُشكَّك فيه.
        "reinvestment_diag": {
            # مصدر الحوض: حصيلة البيع الكلية + التوزيعات (لا الربح المحقّق وحده).
            "produced": round(pool_info["dividends_received"] + pool_info["sale_proceeds"], 2),
            "consumed": pool_info["already_reinvested"],
            "tagged_total": pool_info["tagged_total"],
            "ignored_excess": pool_info["ignored_excess"],
        },
    })


@router.put("/targets")
async def set_targets(payload: TargetsUpdate, db: AsyncSession = Depends(get_db)):
    for item in payload.items:
        result = await db.execute(select(Allocation).where(Allocation.company_id == item.company_id))
        a = result.scalar_one_or_none()
        if not a:
            a = Allocation(company_id=item.company_id)
            db.add(a)
        a.target_weight = item.target_weight
    await db.commit()
    return success_response(message="Targets saved.")


@router.get("/rebalance")
async def calculate_rebalance(db: AsyncSession = Depends(get_db)):
    """Suggested trades to reach target weights. Advisory only — nothing executes."""
    holdings, cash, total_mv, investable, targets = await _snapshot(db)
    if not investable or not any(targets.values()):
        return success_response(data={"suggestions": [], "message": "لا توجد أوزان مستهدفة بعد"})
    # ── حوض إعادة الاستثمار ───────────────────────────────────────────────
    # مقياس **نقدٍ متاح للتوظيف**، فمصدره ما دخل الحساب فعلاً:
    #
    #  • حصيلة البيع الكلية → ثمن البيع كاملاً بشقّيه. رأس المال العائد قابل
    #                          لإعادة التوظيف تماماً كالربح — النقد لا لون له.
    #  • التوزيعات           → نقدٌ استُلم فعلاً.
    #  • المنحة              → **ليست نقداً إطلاقاً**. أسهمٌ مجانية زادت حيازتك
    #                          بتكلفة صفر، فهي رأس مال مُستثمَر سلفاً لا مالٌ
    #                          يُوزَّع. تُعرض رقماً منفصلاً كي لا تُخلط بالنقد.
    #
    # ثم يُطرح ما أُعيد توظيفه سلفاً (المشتريات الموسومة) — وإلا اقتُرح إنفاق
    # نفس الريال مرّتين — بحدّ الرصيد القائم لحظة كل شراء لا بمبلغه كاملاً.
    # وأخيراً سقفٌ حاكم: **النقد المتاح فعلاً**.
    #
    # ملاحظة: هذا الحوض **جزءٌ من السيولة لا إضافةٌ إليها** — نفس الريالات
    # موجودة في available_cash. فجمع «نصيبه من السيولة» و«نصيبه من إعادة
    # الاستثمار» يعدّ بعض المال مرّتين؛ العرض يفصلهما لبيان مصدر التمويل لا
    # لتُجمَع طاقتهما الشرائية.
    #
    # الحساب مركزيٌّ في compute_reinvestment_pool — نفس الدالة التي يقرأها
    # شريط الثروة وبطاقة التوزيع النسبي، فلا يتباعد رقمٌ عن آخر.
    from app.services.portfolio_return import compute_reinvestment_pool, bonus_share_value
    pool_info = await compute_reinvestment_pool(db)
    dividends_received = pool_info["dividends_received"]
    realized_gains = pool_info["realized_gains"]
    dividends_pool = pool_info["pool"]
    # قيمة المنحة من عملياتها لا من مجموع الأسهم في الحيازة: المجموع لا يحمل
    # سعر يوم المنح، فيُقيَّم بسعر اليوم ويتباعد عن الرقم في بقيّة الشاشات.
    from app.models.transaction import Transaction, TransactionType
    bonus_txs = (await db.execute(
        select(Transaction).where(Transaction.transaction_type == TransactionType.BONUS)
    )).scalars().all()
    _lp = {h.company_id: float(h.last_price or 0) for h in holdings}
    bonus_value = round(sum(bonus_share_value(t, _lp.get(t.company_id, 0.0))
                            for t in bonus_txs), 2)

    # قاعدة واحدة لا نظامان: تمويل شراء أيّ شركة يُشتقّ من **وزنها المستهدف
    # هي وحدها** (نفس الصيغة المستعملة في بطاقة التوزيع النسبي وبطاقة
    # المعاملة) — لا من مقارنتها بحاجة بقيّة الشركات. سابقاً كانت حصّة الشركة
    # من الحوض تتغيّر بتغيّر حاجة شركاتٍ أخرى (delta/total_need)، فتتذبذب
    # نتيجتها هنا عن نتيجة بطاقة التوزيع النسبي لنفس الشركة بنفس الوزن —
    # وهذا هو التناقض الذي أُزيل.
    #
    # الوحيد الذي يبقى خاصّاً بسياق «الاقتراح»: تمويل هذه الصفقة تحديداً لا
    # يتجاوز حاجتها الفعلية (delta) — لا معنى لاقتراح شراء أكثر ممّا يلزم
    # لبلوغ الهدف. هذا قيدٌ منطقي واحد يُطبَّق على كل شركة بمفردها، لا مقارنةً
    # نسبية بين الشركات.
    suggestions = []
    for h in holdings:
        target_pct = targets.get(h.company_id, 0)
        mv = float(h.market_value or 0)
        target_value = investable * target_pct / 100
        delta = target_value - mv
        if abs(delta) < max(1.0, investable * 0.002):  # ignore noise < 0.2%
            action = "HOLD"
        else:
            action = "BUY" if delta > 0 else "SELL"
        lp = float(h.last_price or 0)

        reinvest_amount = cash_amount = 0.0
        reinvest_shares = cash_shares = None
        if action == "BUY":
            raw_reinvest = target_pct / 100 * dividends_pool
            reinvest_amount = round(min(delta, raw_reinvest), 2)
            cash_amount = round(delta - reinvest_amount, 2)
            if lp:
                reinvest_shares = round(reinvest_amount / lp, 2)
                cash_shares = round(cash_amount / lp, 2)

        suggestions.append({
            "company_id": h.company_id,
            "symbol": h.company.symbol,
            "name": h.company.company_name,
            "current_weight": round(mv / investable * 100, 2),
            "target_weight": target_pct,
            "delta_value": round(delta, 2),
            "est_shares": round(abs(delta) / lp, 2) if lp else None,
            # السعر الذي حُسب عليه عدد الأسهم — يُعرض صراحةً كي يعرف القارئ
            # على أي أساس بُني الرقم، فالسعر يتغيّر ويتغيّر معه العدد.
            "price_basis": round(lp, 2) if lp else None,
            "action": action,
            "reinvest_amount": reinvest_amount,
            "reinvest_shares": reinvest_shares,
            "cash_amount": cash_amount,
            "cash_shares": cash_shares,
        })
    return success_response(data={
        "suggestions": suggestions,
        "investable": investable,
        "dividends_pool": dividends_pool,
        "dividends_used": round(sum(s["reinvest_amount"] for s in suggestions), 2),
        "pool_breakdown": {
            "dividends_received": round(dividends_received, 2),
            "sale_proceeds": pool_info["sale_proceeds"],
            "realized_gains": round(realized_gains, 2),
            "already_reinvested": pool_info["already_reinvested"],
            "available_cash": round(cash, 2),
            "capped_by_cash": pool_info["capped_by_cash"],
            "tagged_total": pool_info["tagged_total"],
            "ignored_excess": pool_info["ignored_excess"],
        },
        # المنحة خارج الحوض عمداً — رأس مال مجاني مستثمر لا نقد قابل للتوزيع.
        "bonus_value": bonus_value,
    })


THRESHOLD_KEY = "liquidation.threshold_pct"
DEFAULT_THRESHOLD = 20.0


async def _threshold(db) -> float:
    row = (await db.execute(select(Settings).where(Settings.key == THRESHOLD_KEY))).scalar_one_or_none()
    try:
        return float(row.value) if row and row.value else DEFAULT_THRESHOLD
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD


class ThresholdUpdate(BaseModel):
    # بلا company_id ⇒ العتبة العامة. ومعه ⇒ عتبة تلك الشركة وحدها.
    threshold_pct: Optional[float] = None
    company_id: Optional[int] = None
    # العودة إلى العتبة العامة — لا سبيل للتراجع عن تخصيصٍ بلا زرٍّ صريح.
    inherit: bool = False

    @field_validator("threshold_pct")
    @classmethod
    def _t(cls, v):
        if v is not None and (v < 0 or v > 500):
            raise ValueError("العتبة يجب أن تكون بين صفر و٥٠٠٪.")
        return v


@router.put("/liquidation-threshold")
async def set_threshold(payload: ThresholdUpdate, db: AsyncSession = Depends(get_db)):
    """عتبة التصفية: العامة أو عتبة شركةٍ بعينها. لا تمسّ بيانات ولا حسابات."""
    if payload.company_id is None:
        if payload.threshold_pct is None:
            raise HTTPException(422, "العتبة مطلوبة.")
        row = (await db.execute(select(Settings).where(Settings.key == THRESHOLD_KEY))).scalar_one_or_none()
        if row is None:
            row = Settings(key=THRESHOLD_KEY, category="liquidation")
            db.add(row)
        row.value = str(payload.threshold_pct)
    else:
        # شركةٌ غير موجودة تُنشئ صفّاً يتيماً يخرق المفتاح الأجنبي ويُسقط الطلب.
        known = (await db.execute(
            select(Company.id).where(Company.id == payload.company_id)
        )).scalar_one_or_none()
        if known is None:
            raise HTTPException(404, "شركة غير معروفة.")
        alloc = (await db.execute(
            select(Allocation).where(Allocation.company_id == payload.company_id)
        )).scalar_one_or_none()
        if alloc is None:
            alloc = Allocation(company_id=payload.company_id)
            db.add(alloc)
        if payload.inherit:
            alloc.liquidation_threshold_pct = None
        elif payload.threshold_pct is not None:
            alloc.liquidation_threshold_pct = payload.threshold_pct
        else:
            raise HTTPException(422, "العتبة مطلوبة.")
    await db.commit()
    return success_response(message="حُفظت العتبة.")


@router.get("/profit-liquidation")
async def profit_liquidation(db: AsyncSession = Depends(get_db)):
    """حَكَمُ التصفية: لكل مركزٍ حكمٌ صريح — أقابلٌ للتصفية الآن أم لا — ومقدارٌ
    متاح.

    والعتبة هي القاعدة كلّها: التصفية تبيع ما يعادل الربح الورقي وتُبقي التكلفة
    مستثمرة، فيعود المركز إلى تكلفته وكأنه بدأ من جديد. ولذلك يصلح الشرط نفسه
    للتصفية الثانية والثالثة بلا قاعدةٍ جديدة لكل مرّة.

    ولماذا حكمٌ لا تصفية للقائمة: عرض كل مركزٍ ربحه فوق الصفر يُغري بتصفياتٍ
    صغيرة متكرّرة، وكل واحدة تُخرج جزءاً من رأس المال بالتقريب والعمولة.
    والحكم الصريح («دون العتبة، يلزمه ٤٫٢٠») يمنع ذلك ويُبقي المركز مرئياً."""
    holdings, cash, total_mv, investable, targets = await _snapshot(db)
    threshold = await _threshold(db)
    # عتبات الشركات — ما لم تُخصَّص ترث العامة.
    custom = {a.company_id: (float(a.liquidation_threshold_pct)
                             if a.liquidation_threshold_pct is not None else None)
              for a in (await db.execute(select(Allocation))).scalars().all()}

    # عدد التصفيات السابقة، ونقطة القياس لكل مركز.
    #
    # نقطة القياس متوسطُ تكلفةٍ له ذاكرةٌ قصيرة، يُبنى بإعادة تشغيل السجلّ:
    #   • عند البيع  ← تُصفَّر إلى سعر البيع.
    #   • عند الشراء ← تُمزَج بالسعر الجديد بحسب الكميات، كمتوسط التكلفة.
    #
    # ولماذا تُصفَّر عند البيع: البيع الجزئي لا يُفرغ الربح الورقي — يبقى باقي
    # الأسهم حاملاً نفس الفارق عن التكلفة، فيظلّ العدّاد مرتفعاً ويُغري بتصفيةٍ
    # تالية فوراً. والتصفير يجعل الحصاد التالي مشروطاً بارتفاعٍ **جديد**.
    #
    # ولماذا تُمزَج عند الشراء: بدونها يبقى المرجع عند سعر بيعٍ قديم، فمن باع
    # بـ٤٠ ثم أعاد الشراء بـ٤٥ يُقال له عند ٤٤ «ربحت» وهو خاسر — والفارق
    # يُضرب في كل أسهمه بما فيها المشتراة أغلى.
    #
    # والتكلفة الحقيقية لا تُمسّ بشيء من هذا: عدّاد قياسٍ لا رقم محاسبي.
    sells: dict[int, int] = {}
    ref_price: dict[int, float] = {}
    ref_qty: dict[int, float] = {}
    has_sale: dict[int, bool] = {}

    # أعمدةٌ محدّدة ومرتّبةٌ في الخادم: كائنات ORM كاملة لكل عملية في المحفظة
    # تُحمَّل وتُهيَّأ بلا حاجة، والترتيب في بايثون يُكرّر ما تفعله قاعدة
    # البيانات أسرع منه.
    all_txs = (await db.execute(
        select(Transaction.company_id, Transaction.transaction_type,
               Transaction.quantity, Transaction.price, Transaction.total_amount)
        .where(Transaction.transaction_type.in_([
            TransactionType.BUY, TransactionType.SELL, TransactionType.BONUS,
            TransactionType.SPLIT, TransactionType.REINVESTMENT]))
        .order_by(Transaction.executed_at.asc().nullslast(), Transaction.id.asc())
    )).all()
    for t in all_txs:
        cid = t.company_id
        qty = float(t.quantity or 0)
        px = float(t.price or 0)
        if t.transaction_type == TransactionType.SELL:
            sells[cid] = sells.get(cid, 0) + 1
            ref_qty[cid] = max(0.0, ref_qty.get(cid, 0.0) - qty)
            if px > 0:
                ref_price[cid] = px
                has_sale[cid] = True
        elif t.transaction_type in (TransactionType.BUY, TransactionType.REINVESTMENT):
            # REINVESTMENT سجلٌّ قديم لم تُملأ كميّته دائماً — تُشتقّ من المبلغ.
            if t.transaction_type == TransactionType.REINVESTMENT and qty <= 0 and px > 0:
                qty = float(t.total_amount or 0) / px
            held = ref_qty.get(cid, 0.0)
            base = ref_price.get(cid)
            if px > 0 and qty > 0:
                # أوّل شراء، أو شراءٌ بعد خروجٍ كامل: السعر نفسه هو المرجع.
                ref_price[cid] = px if (base is None or held <= 0) else \
                    (base * held + px * qty) / (held + qty)
            ref_qty[cid] = held + qty
        elif t.transaction_type == TransactionType.BONUS:
            # المنحة أسهمٌ بلا ثمن: تُخفّض المرجع بنسبة التخفيف تماماً كما
            # تُخفّض متوسط التكلفة. وإهمالها يترك المرجع مرتفعاً على كميّةٍ
            # أكبر، فيتضخّم العدّاد بربحٍ لم يقع.
            held = ref_qty.get(cid, 0.0)
            base = ref_price.get(cid)
            if qty > 0 and base is not None and held > 0:
                ref_price[cid] = base * held / (held + qty)
            ref_qty[cid] = held + qty
        elif t.transaction_type == TransactionType.SPLIT:
            # التجزئة تضرب الكمية وتقسم السعر. وإهمالها كارثة: مرجعٌ قبل
            # التجزئة أمام سعرٍ بعدها يجعل العدّاد يقرأ انهياراً أو طفرة.
            factor = qty or 1
            if factor > 0:
                if ref_price.get(cid) is not None:
                    ref_price[cid] = ref_price[cid] / factor
                ref_qty[cid] = ref_qty.get(cid, 0.0) * factor

    rows = []
    for h in holdings:
        avg_cost = float(h.average_cost or 0)
        lp = float(h.last_price or 0)
        shares = float(h.quantity or 0)
        if avg_cost <= 0 or lp <= 0 or shares <= 0:
            continue
        profit_per_share = lp - avg_cost
        unrealized_profit = profit_per_share * shares
        # الربح فوق التكلفة منذ التأسيس — يبقى معروضاً للسياق بجانب العدّاد.
        profit_pct = profit_per_share / avg_cost * 100

        # المرجع من إعادة التشغيل. ولمن لم يُصفَّ قطّ يبقى متوسط التكلفة
        # **المخزَّن** هو المرجع: هو الرقم المعتمد في هذا التطبيق، ولا يصحّ أن
        # يزاحمه متوسطٌ مُعاد اشتقاقه من سجلٍّ قد يكون ناقصاً.
        ref = (ref_price.get(h.company_id) or avg_cost) if has_sale.get(h.company_id) else avg_cost
        since_per_share = lp - ref
        # العدّاد لا ينزل تحت الصفر: سهمٌ نزل عن سعر آخر تصفية لا شيء فيه
        # ليُحصد، وعرض رقمٍ سالب هنا يخلطه بالخسارة المحاسبية وليست هي.
        since_profit = max(0.0, since_per_share * shares)
        since_pct = since_per_share / ref * 100 if ref else 0.0

        own = custom.get(h.company_id)
        thr = own if own is not None else threshold
        eligible = since_pct >= thr
        # السعر الذي يبلغ عنده المركز العتبة — «كم ينقصه» بلغة السوق لا بلغة
        # النِّسَب، فهو الرقم الذي يُراقَب على الشاشة فعلاً.
        price_needed = ref * (1 + thr / 100)
        # Shares whose sale proceeds, at the last close, equal the total
        # unrealized profit — i.e. how many shares to sell to "cash out"
        # the gain while leaving the rest of the position (≈ original cost) invested.
        # الكمية تُشتقّ من عدّاد ما بعد آخر تصفية لا من الربح منذ التأسيس:
        # الثاني يُعيد حصاد ربحٍ سبق أن حُصد.
        # تداول لا يقبل جزء سهم — يُقرَّب للأسفل فيكون الرقم قابلاً للتنفيذ.
        shares_to_sell = float(int(since_profit // lp)) if lp else 0.0
        # ── الرقم الحاسم الذي كان غائباً ──────────────────────────────────
        # حصيلة بيع هذه الأسهم = الربح الورقي كاملاً (هذا تعريفها أصلاً)، لكن
        # **الربح المحاسبي المحقّق** منها ليس كذلك: كل سهم مبيع يحمل تكلفته معه،
        # فلا يُحقّق إلا فارق سعره عن تكلفته. غياب هذا التمييز جعل اللوحة تقول
        # «بِع ١٧٨ سهماً لتصفية ربح ٤١٦٠» فيُفهم أن ٤١٦٠ ربحٌ محقَّق، والواقع أن
        # ١٠٧٠ فقط ربح و٣٠٩١ رأس مالٍ عاد. الفرق يُشوّه ذاكرة المستخدم عن أدائه
        # ويجعله يشكّ في «العائد المحقّق» الصحيح المعروض في لوحة التحكم.
        realized_if_sold = shares_to_sell * profit_per_share
        rows.append({
            "company_id": h.company_id,
            "symbol": h.company.symbol,
            "name": h.company.company_name,
            "shares_held": shares,
            "shares_to_sell": shares_to_sell,
            "average_cost": round(avg_cost, 2),
            "last_price": round(lp, 2),
            "profit_per_share": round(profit_per_share, 2),
            "profit_pct": round(profit_pct, 2),
            # الحكم ومقداره: ما لم يبلغ المركز العتبة فلا مقدار متاح — صفرٌ
            # صريح لا رقمٌ صغير يُغري.
            "eligible": eligible,
            "sellable_shares": round(shares_to_sell, 2) if eligible else 0.0,
            "sellable_amount": round(shares_to_sell * lp, 2) if eligible else 0.0,
            "gap_pct": round(max(0.0, thr - since_pct), 2),
            "threshold_pct": round(thr, 2),
            "threshold_is_custom": own is not None,
            "price_needed": round(price_needed, 2),
            # العدّاد: الربح المتراكم منذ آخر تصفية — يصفّر عند كل حلبة.
            "since_profit": round(since_profit, 2),
            "since_pct": round(since_pct, 2),
            "reference_price": round(ref, 2),
            "reference_is_last_sale": bool(has_sale.get(h.company_id)),
            "prior_liquidations": sells.get(h.company_id, 0),
            "unrealized_profit": round(unrealized_profit, 2),
            # حصيلة البيع (نقدٌ يدخل حسابك) — تساوي الربح الورقي بحكم التعريف.
            "proceeds": round(shares_to_sell * lp, 2),
            # الربح المحاسبي المحقّق فعلاً من هذا البيع.
            "realized_if_sold": round(realized_if_sold, 2),
            # رأس المال العائد إليك ضمن الحصيلة — ليس ربحاً.
            "capital_returned": round(shares_to_sell * avg_cost, 2),
        })
    # ترتيب المالك من شاشة الحيازات — لا ترتيبٌ حسابي يُنقل الشركة من موضعها
    # كلّما تحرّك السعر، فيضيع مكانها المألوف على الشاشة.
    _rank = {h.company_id: (int(getattr(h, "sort_order", 0) or 0) or 10**6, h.id) for h in holdings}
    rows.sort(key=lambda r: _rank.get(r["company_id"], (10**6, 0)))
    ok = [r for r in rows if r["eligible"]]
    return success_response(data={
        "rows": rows,
        "threshold_pct": round(threshold, 2),
        "eligible_count": len(ok),
        # المجاميع للقابل وحده: جمع مراكز دون العتبة يُنتج رقماً لا يُنفَّذ.
        "totals": {
            "proceeds": round(sum(r["sellable_amount"] for r in ok), 2),
            "realized_if_sold": round(sum(r["realized_if_sold"] for r in ok), 2),
            "capital_returned": round(sum(r["capital_returned"] for r in ok), 2),
        },
    })
