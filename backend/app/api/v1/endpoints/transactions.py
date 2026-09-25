"""
Transaction engine — the investment reference implementation.
Supported: BUY, SELL, DIVIDEND (cash), BONUS (bonus shares), SPLIT (stock
split), each updating the Holding and the Cash balance exactly as a real
portfolio would. A BUY may optionally carry a funding_source tag (DIVIDEND /
PROFIT) purely for reporting — it never changes the cash/holding math: every
BUY always deducts cash the same way, regardless of where the money
conceptually came from. (REINVESTMENT used to be a separate type with
special skip-cash/deduct-cash rules per source; that's been retired in favor
of this simpler, exception-free model — see backfill migration in database.py.)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.core.database import get_db
from app.core.response import success_response
from app.models.transaction import Transaction, Cash, Dividend, DividendAction
from app.models.portfolio import Holding
from pydantic import BaseModel, model_validator
from datetime import datetime, timedelta, timezone, date as _date, time as _time
from typing import Optional

router = APIRouter()

# توقيت السوق الذي يعمل فيه المالك. كلُّ ما يُكتب في سجلّ العمليات يُختم به
# صراحةً — لا `utcnow()` ساذجة تُفسَّر على هوى المحرّك فتُزيح اليوم.
_RIYADH = timezone(timedelta(hours=3))

# وسوم «إعادة الاستثمار»: الموحّد الجديد + القديمان للتوافق الرجعي. النقد لا
# لون له — التوزيعات وحصيلة التصفية تختلطان في حسابٍ واحد، فالتمييز بينهما عند
# الشراء تصنيفٌ يدوي لا واقعة يمكن إثباتها. الفارق الذي يستحقّ البقاء واحد:
# مالٌ عاد من محفظتك (REINVEST) مقابل رأس مال جديد من خارجها (بلا وسم).
REINVEST_TAGS = ("REINVEST", "DIVIDEND", "PROFIT")


async def backfill_realized_gains(db: AsyncSession) -> int:
    """Historical SELL transactions recorded before realized_gain existed
    have it NULL, which would make past years' 'liquidation income' show as
    zero even though real profit was taken. Since the transaction ledger is
    immutable and complete, the cost basis at each past sale can be
    reconstructed exactly by replaying every transaction in chronological
    order per company — same math _apply uses live, just applied to
    history. Only ever fills rows that are still NULL; safe on every startup."""
    txs = (await db.execute(
        select(Transaction).where(Transaction.transaction_type.in_(["BUY", "SELL", "BONUS", "REINVESTMENT", "SPLIT"]))
        .order_by(Transaction.company_id, Transaction.executed_at, Transaction.id)
    )).scalars().all()

    by_company: dict[int, list[Transaction]] = {}
    for t in txs:
        by_company.setdefault(t.company_id, []).append(t)

    filled = 0
    for company_txs in by_company.values():
        qty = 0.0
        invested = 0.0
        for t in company_txs:
            qty_f = float(t.quantity or 0)
            price_f = float(t.price or 0)
            fees_f = float(t.fees or 0)
            if t.transaction_type == "BUY":
                invested += qty_f * price_f + fees_f
                qty += qty_f
            elif t.transaction_type == "SELL":
                avg = (invested / qty) if qty else 0
                if t.realized_gain is None:
                    t.realized_gain = qty_f * (price_f - avg) - fees_f
                    filled += 1
                invested = max(0, invested - qty_f * avg)
                qty -= qty_f
            elif t.transaction_type == "REINVESTMENT":
                amount = float(t.total_amount or 0)
                new_shares = (amount / price_f) if price_f else 0
                qty += new_shares
                invested += amount
            elif t.transaction_type == "BONUS":
                qty += qty_f
            elif t.transaction_type == "SPLIT":
                factor = qty_f or 1
                qty *= factor
    if filled:
        await db.commit()
    return filled


class TransactionCreate(BaseModel):
    company_id: int
    transaction_type: str
    quantity: Optional[float] = None
    shares: Optional[float] = None
    price: Optional[float] = None
    price_per_share: Optional[float] = None
    amount: Optional[float] = None      # DIVIDEND total amount
    factor: Optional[float] = None      # SPLIT factor (e.g. 2 = 1→2 shares)
    fees: float = 0
    # BUY only. REINVEST = مالٌ عاد من محفظتك (توزيعات أو حصيلة تصفية معاً)،
    # وNone = رأس مال جديد من خارجها. الوسمان القديمان DIVIDEND/PROFIT يبقيان
    # مقبولين ومقروءين للصفقات المسجَّلة سابقاً، فلا يتغيّر رقم واحد في سجلّك.
    funding_source: Optional[str] = None
    notes: Optional[str] = None
    executed_at: Optional[datetime] = None
    transaction_date: Optional[str] = None
    # SPLIT فقط — إقرارٌ صريح بأن كميات العمليات السابقة مسجَّلة **قبل** التجزئة.
    confirm_prior_pre_split: bool = False

    @model_validator(mode="after")
    def resolve_aliases(self):
        self.quantity = self.quantity if self.quantity is not None else self.shares
        self.price = self.price if self.price is not None else self.price_per_share
        # ══ الوقت ومنطقتُه — عطبان قِيسا ══
        # ١) الوقت كان يضيع: الواجهة ترسل `transaction_date` تاريخاً بلا
        #    وقت («2026-08-23»)، و`fromisoformat` تعطي 00:00:00. فكلّ
        #    عمليات المالك مخزَّنةٌ عند منتصف الليل، ولا يُعرف ترتيب
        #    صفقتين في اليوم الواحد إلا بترتيب الإدخال.
        # ٢) وأخطر: انزياحُ اليوم. `utcnow()` توقيتٌ عالميّ والرياض UTC+3،
        #    فصفقةٌ تُسجَّل بعد التاسعة مساءً بتوقيت المالك تُخزَّن **في
        #    اليوم التالي**… بل صفقةُ منتصف الليل تُخزَّن في اليوم السابق.
        #    وذلك يفسد الترتيب وأساس التكلفة والتقارير ومقارنات «اليوم».
        #    والعمود `DateTime(timezone=True)` كان يستقبل قيمةً ساذجة بلا
        #    منطقة — فتُفسَّر على هوى المحرّك.
        #
        # والقاعدة الآن: **توقيت الرياض صراحةً**، والوقت الحقيقيّ متى عُرف.
        # فإن كانت الصفقة اليوم أُخذ وقتُها الفعليّ؛ وإن كانت بتاريخٍ ماضٍ
        # فالوقت مجهولٌ حقّاً — فيُثبَّت منتصف الليل **بتوقيت الرياض** لا
        # يُختلق له وقت، ويبقى اليوم صحيحاً في تقويم المالك.
        _now = datetime.now(_RIYADH)
        if self.executed_at is None:
            if self.transaction_date:
                _d = datetime.fromisoformat(self.transaction_date)
                if _d.tzinfo is None and _d.time() == _time(0, 0):
                    # تاريخٌ مجرّد: وقتُ اليوم إن كان اليوم، وإلّا منتصف الليل.
                    self.executed_at = (_now if _d.date() == _now.date()
                                        else _d.replace(tzinfo=_RIYADH))
                else:
                    self.executed_at = _d if _d.tzinfo else _d.replace(tzinfo=_RIYADH)
            else:
                self.executed_at = _now
        elif self.executed_at.tzinfo is None:
            self.executed_at = self.executed_at.replace(tzinfo=_RIYADH)

        # لا صفقة بتاريخٍ لم يأتِ بعد: كانت تُقبل فتدخل اللقطات والتقارير
        # وحساب العائد بتاريخ مستقبلي، فتشوّه السلسلة الزمنية كلّها. والمقارنة
        # بتقويم الرياض لا بالعالميّ، وإلّا رُفضت صفقةُ اليوم الصحيحة ليلاً.
        if self.executed_at.astimezone(_RIYADH).date() > (_now.date() + timedelta(days=1)):
            raise ValueError("لا يمكن تسجيل صفقة بتاريخ مستقبلي.")
        return self


# ── بوّابة الثوابت المحاسبية (D482 · القيد المزدوج) ─────────────────────
# كل عمليةٍ تُفحص **قبل** حفظها لا بعده: النقدُ المخزَّن يساوي مجموع حركاته،
# ولا بيعَ يتجاوز المملوك في لحظته، ولا كميةَ سالبة. وما كان مختلّاً قبل
# العملية (تسويةٌ يدوية معتمدة مثلاً) لا يُحمَّل عليها — تُرفض فقط العمليةُ
# التي تكسر ثابتاً كان سليماً، فلا يُمنع المالك من العمل بسبب خللٍ قديم.
TOL = 0.01


async def _ledger_state(db: AsyncSession, company_id: int) -> dict:
    from app.services.integrity import _cash_reconciliation
    cash = await _cash_reconciliation(db)
    rep = await _replay(db, company_id, persist_gains=False)
    return {"cash_ok": bool(cash.get("ok")), "cash_diff": cash.get("diff"),
            "clipped": set(rep["clipped_sales"]), "qty": float(rep["quantity"])}


async def _ledger_gate(db: AsyncSession, company_id: int, before: dict) -> None:
    await db.flush()
    after = await _ledger_state(db, company_id)
    if before["cash_ok"] and not after["cash_ok"]:
        raise HTTPException(422, f"رُفضت العملية: تكسر مطابقة النقد (فارق {after['cash_diff']:,.2f}) "
                                 f"— الرصيد لا يعود مساوياً لمجموع حركاته. لم يُحفظ شيء.")
    new = sorted(after["clipped"] - before["clipped"])
    if new:
        raise HTTPException(422, f"رُفضت العملية: تجعل عملية البيع رقم {new[0]} تبيع أسهماً غير "
                                 f"مملوكة في تاريخها. لم يُحفظ شيء.")
    if after["qty"] < -TOL:
        raise HTTPException(422, "رُفضت العملية: تنتج كمية أسهم سالبة. لم يُحفظ شيء.")
    cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    if cash_row is not None and float(cash_row.available_cash or 0) < -TOL:
        raise HTTPException(422, "رُفضت العملية: تجعل السيولة المتاحة سالبة. لم يُحفظ شيء.")


async def _get_cash(db: AsyncSession) -> Cash:
    # FOR UPDATE: two concurrent requests (e.g. a buy and a manual deposit)
    # must not both read the same stale balance and clobber each other's
    # write — this makes the read-modify-write atomic across transactions.
    result = await db.execute(select(Cash).limit(1).with_for_update())
    cash = result.scalar_one_or_none()
    if not cash:
        # Cash FK requires a Portfolio row — bootstrap it on first use
        from app.models.portfolio import Portfolio
        p = (await db.execute(select(Portfolio).limit(1))).scalar_one_or_none()
        if not p:
            p = Portfolio(name="My Portfolio")
            db.add(p)
            await db.flush()
        cash = Cash(portfolio_id=p.id, available_cash=0, total_cash=0)
        db.add(cash)
        await db.flush()
    return cash


def _recalc(h: Holding):
    qty = float(h.quantity or 0)
    inv = float(h.invested_amount or 0)
    lp = float(h.last_price or 0)
    h.average_cost = (inv / qty) if qty else 0
    h.market_value = qty * lp if lp else inv
    mv = float(h.market_value or 0)
    h.unrealized_profit = mv - inv
    h.unrealized_profit_pct = ((mv - inv) / inv * 100) if inv else 0


async def replay_holding(db: AsyncSession, company_id: int) -> dict:
    """Replay the ledger and RETURN the aggregates without writing them — the
    same computation `recompute_holding` persists. Split out so the manual
    correction endpoint can measure how far the owner's broker statement sits
    from the replay, instead of guessing.
    """
    return await _replay(db, company_id, persist_gains=False)


async def recompute_holding(db: AsyncSession, company_id: int) -> None:
    """Canonically rebuild a holding's share/cost aggregates by REPLAYING every
    transaction for the company in strict chronological order — the single
    source of truth. This is what makes every operation button reliable for
    the far future: because a split (and a bonus/reinvestment) multiplies or
    adds shares at a point in time, reversing an earlier transaction from the
    *current* state (the old approach) miscounts once any later split sits
    between it and now. Replaying from scratch is always exact regardless of
    edit order, out-of-order entry, or how many historical splits a company
    has had. Cash is handled separately (absolute amounts, order-independent);
    the live last_price is preserved (refreshed from the market, not replay).
    """
    agg = await _replay(db, company_id)
    qty = agg["quantity"]
    invested = agg["invested"]
    bonus = agg["bonus"]
    reinvest_shares = agg["reinvest_shares"]
    profit_reinvested = agg["profit_reinvested"]
    dividends = agg["dividends"]

    h = (await db.execute(
        select(Holding).where(Holding.company_id == company_id).with_for_update()
    )).scalar_one_or_none()
    if h is None:
        return
    # تصحيح المالك اليدوي يُطبَّق كفارقٍ على النتيجة، لا كرقمٍ يُجمِّد التكلفة:
    # فتظلّ عمليات الشراء والبيع اللاحقة تحرّكها. وإن خرج من السهم كلياً سقط
    # الفارق معه — لا معنى لتكلفةٍ بلا أسهم.
    if qty <= 0:
        invested = 0.0
        # الفارق يسقط عن التكلفة لا عن رأس المال المدفوع: المالك دفعه فعلاً،
        # فيُرحَّل تراكمياً بدل أن يُمحى — وإلا نقص المقام عند كل خروجٍ كامل.
        h.paid_in_adjustment_realized = (float(h.paid_in_adjustment_realized or 0)
                                         + float(h.cost_basis_adjustment or 0))
        h.cost_basis_adjustment = 0
    else:
        invested = max(0.0, invested + float(h.cost_basis_adjustment or 0))
    h.quantity = qty
    h.invested_amount = invested
    h.total_dividends_received = dividends
    h.total_bonus_shares = bonus
    h.reinvestment_shares = reinvest_shares
    h.profit_reinvested = profit_reinvested
    _recalc(h)


async def _replay(db: AsyncSession, company_id: int, persist_gains: bool = True) -> dict:
    """persist_gains=False يجعلها قراءةً محضة: إعادة التشغيل تُعيد احتساب ربح كل
    عملية بيع على أساس التكلفة الزمني، وكتابتها من مسارٍ لا يقصد الحفظ تُعدّل
    السجلّ من حيث لا يتوقّع المستدعي."""
    txs = (await db.execute(
        select(Transaction).where(Transaction.company_id == company_id)
        .order_by(Transaction.executed_at, Transaction.id)
    )).scalars().all()

    qty = 0.0
    invested = 0.0
    bonus = 0.0
    reinvest_shares = 0.0
    profit_reinvested = 0.0
    # عمليات بيعٍ لم تجد أسهماً كافية وقتَها فقُصّت — تُبلَّغ للأعلى بدل أن
    # تُقصّ بصمت: تعديلُ شراءٍ قديم قد يُنقص أسهم لحظةٍ لاحقة فيتغيّر بيعٌ لم
    # يلمسه المالك، وهو أخطر ما في التحرير لأنه لا يترك أثراً مرئياً.
    clipped: list[int] = []

    for t in txs:
        qf = float(t.quantity or 0)
        price = float(t.price or 0)
        fees = float(t.fees or 0)
        total = float(t.total_amount or 0)
        typ = t.transaction_type
        if typ == "BUY":
            invested += qf * price + fees
            qty += qf
            if t.funding_source in REINVEST_TAGS:
                profit_reinvested += (qf * price + fees)
        elif typ == "SELL":
            avg = (invested / qty) if qty else 0
            sell_qty = min(qf, qty)  # never let a replay drive shares negative
            if sell_qty < qf - 1e-9:
                clipped.append(t.id)
            # Realized gain is recomputed here on the chronological cost basis,
            # so it stays exact even after an earlier row is edited/deleted.
            if persist_gains:
                t.realized_gain = sell_qty * (price - avg) - fees
            invested = max(0, invested - sell_qty * avg)
            qty -= sell_qty
            # بيعٌ كامل يُغلق الدورة: بقايا الفاصلة العائمة في التكلفة كانت
            # تُرحَّل إلى أوّل شراءٍ بعد الإغلاق فتُفسد متوسّطه (D480).
            if qty <= 1e-9:
                qty, invested = 0.0, 0.0
        elif typ == "DIVIDEND":
            pass  # dividends don't change shares; income is summed below
        elif typ == "BONUS":
            qty += qf
            bonus += qf
        elif typ == "SPLIT":
            factor = qf or 1
            qty *= factor
        elif typ == "REINVESTMENT":  # legacy (relabeled to BUY on startup) — defensive
            shares = (total / price) if price else 0
            qty += shares
            invested += total
            reinvest_shares += shares

    # Dividend income comes from the dedicated Dividend LEDGER, not from
    # replaying DIVIDEND transactions — because dividends can also be recorded
    # via the standalone /dividends endpoint (no Transaction row). The ledger
    # is the one complete source (transaction flow + standalone + backfill),
    # so deriving it here means a recompute can never silently drop a
    # manually-entered dividend.
    dividends = float(
        (await db.execute(
            select(func.coalesce(func.sum(Dividend.received_amount), 0))
            .where(Dividend.company_id == company_id)
        )).scalar() or 0
    )

    return {"quantity": qty, "invested": invested, "bonus": bonus,
            "reinvest_shares": reinvest_shares, "profit_reinvested": profit_reinvested,
            "dividends": dividends, "clipped_sales": clipped}


async def _apply(db: AsyncSession, tx: TransactionCreate) -> tuple[float, float | None, "Dividend | None"]:
    """Apply the transaction to Holding + Cash. Returns (total_amount, realized_gain, dividend_row)
    — realized_gain is only set for SELL (proceeds minus cost basis at sale time);
    dividend_row is the Dividend record created for DIVIDEND/REINVESTMENT(dividend), if any."""
    # FOR UPDATE: same reasoning as Cash below — two concurrent transactions
    # on the same holding (e.g. two BUYs firing at once) must not both read
    # the same stale quantity/invested_amount and silently drop one write.
    result = await db.execute(select(Holding).where(Holding.company_id == tx.company_id).with_for_update())
    h = result.scalar_one_or_none()
    if not h:
        h = Holding(company_id=tx.company_id, quantity=0, average_cost=0,
                    invested_amount=0, market_value=0, last_price=tx.price or 0)
        db.add(h)
    cash = await _get_cash(db)
    t = tx.transaction_type
    qty0 = float(h.quantity or 0)
    inv0 = float(h.invested_amount or 0)
    realized_gain = None
    div_row: Dividend | None = None

    if t == "BUY":
        if not tx.quantity or not tx.price:
            raise HTTPException(422, "quantity and price are required for BUY")
        if tx.quantity <= 0 or tx.price <= 0 or tx.fees < 0:
            raise HTTPException(422, "quantity and price must be positive for BUY")
        total = tx.quantity * tx.price + tx.fees
        # حارس السيولة: البيع كان محميّاً («لا تبع أكثر مما تملك») والشراء بلا
        # حارس مقابل — فيهبط النقد إلى ما دون الصفر بصمت، وهي حالة مستحيلة
        # واقعاً تفسد كل ما يُبنى على النقد (القابل للاستثمار، الأوزان، الحوض).
        avail = float(cash.available_cash or 0)
        if total > avail + 1e-6:
            raise HTTPException(
                422,
                f"السيولة المتاحة {avail:,.2f} لا تكفي لشراء بـ{total:,.2f}. "
                f"سجّل ضخّاً نقدياً أولاً أو راجع الكمية والسعر.",
            )
        h.quantity = qty0 + tx.quantity
        h.invested_amount = inv0 + total
        h.last_price = tx.price
        cash.available_cash = avail - total
        cash.total_cash = float(cash.total_cash or 0) - total
        # funding_source is purely informational (which conceptual pool this
        # purchase drew from) — cash above is deducted the same way no
        # matter what. profit_reinvested is tracked here only for reporting
        # (wealth banner / goals income annotation); dividend-sourced buys
        # need no extra bookkeeping since the originating DIVIDEND
        # transaction already recorded that income.
        if tx.funding_source in REINVEST_TAGS:
            h.profit_reinvested = float(h.profit_reinvested or 0) + total

    elif t == "SELL":
        if not tx.quantity or not tx.price:
            raise HTTPException(422, "quantity and price are required for SELL")
        if tx.quantity <= 0 or tx.price <= 0 or tx.fees < 0:
            raise HTTPException(422, "quantity and price must be positive for SELL")
        if tx.quantity > qty0:
            raise HTTPException(422, "Cannot sell more shares than held")
        avg = (inv0 / qty0) if qty0 else 0
        proceeds = tx.quantity * tx.price - tx.fees
        realized_gain = tx.quantity * (tx.price - avg) - tx.fees
        h.quantity = qty0 - tx.quantity
        h.invested_amount = max(0, inv0 - tx.quantity * avg)
        h.last_price = tx.price
        cash.available_cash = float(cash.available_cash or 0) + proceeds
        cash.total_cash = float(cash.total_cash or 0) + proceeds
        total = proceeds

    elif t == "DIVIDEND":
        # Cash dividend: amount directly, or per-share (price) × current shares
        amount = tx.amount if tx.amount else (tx.price or 0) * qty0
        if amount <= 0:
            raise HTTPException(422, "amount (or per-share price) required for DIVIDEND")
        h.total_dividends_received = float(h.total_dividends_received or 0) + amount
        cash.available_cash = float(cash.available_cash or 0) + amount
        cash.total_cash = float(cash.total_cash or 0) + amount
        total = amount
        dps = tx.price if tx.price else (amount / qty0 if qty0 else 0)
        div_row = Dividend(
            company_id=tx.company_id, dividend_per_share=dps, shares_at_time=qty0,
            received_amount=amount, action=DividendAction.CASH, payment_date=tx.executed_at,
        )
        db.add(div_row)

    elif t == "REINVESTMENT":
        raise HTTPException(422, "REINVESTMENT is retired — use BUY with funding_source=REINVEST instead")

    elif t == "BONUS":
        # Bonus shares: quantity increases, cost basis unchanged
        if not tx.quantity or tx.quantity <= 0:
            raise HTTPException(422, "quantity is required for BONUS")
        h.quantity = qty0 + tx.quantity
        h.total_bonus_shares = float(h.total_bonus_shares or 0) + tx.quantity
        total = 0

    elif t == "SPLIT":
        if not tx.factor or tx.factor <= 0:
            raise HTTPException(422, "factor is required for SPLIT (e.g. 2)")
        h.quantity = qty0 * tx.factor
        if h.last_price:
            h.last_price = float(h.last_price) / tx.factor
        total = 0

    else:
        raise HTTPException(422, f"Unsupported transaction type: {t}")

    _recalc(h)
    return total, realized_gain, div_row


@router.get("")
async def get_transactions(company_id: int | None = None, limit: int = 500, offset: int = 0,
                           db: AsyncSession = Depends(get_db)):
    """سجل العمليات. **الترشيح بالشركة يجري على الخادم** لا في الواجهة.

    العلّة التي يعالجها: كان الحدّ ١٠٠ عمليةٍ للمحفظة كلّها، وترشّح الواجهة
    منها ما يخصّ الشركة. فمن تجاوز مجموعُ عملياته المئة اختفت عملياته القديمة
    من صفحة الشركة **بلا رسالة ولا أثر** — لا تُعرض ولا تُحرَّر ولا تُحذف،
    ويبدو كأن السجل ناقص. والحسابات لم تكن تتأثّر (تقرأ الجدول كاملاً بلا حدّ)،
    فيصير المعروض مخالفاً للمحسوب وهو أسوأ من نقصٍ ظاهر.

    والحدّ الآن على الشركة الواحدة لا على المحفظة، مع صفحاتٍ صريحة وعدّادٍ
    إجمالي كي تعرف الواجهة إن بقي شيء.
    """
    limit = max(1, min(int(limit or 500), 2000))
    offset = max(0, int(offset or 0))
    q = select(Transaction)
    cq = select(func.count(Transaction.id))
    if company_id is not None:
        q = q.where(Transaction.company_id == company_id)
        cq = cq.where(Transaction.company_id == company_id)
    total = int((await db.execute(cq)).scalar() or 0)
    result = await db.execute(
        q.order_by(Transaction.executed_at.desc(), Transaction.id.desc())
         .limit(limit).offset(offset)
    )
    txs = result.scalars().all()
    items = [{
        "id": t.id, "company_id": t.company_id, "type": t.transaction_type,
        "quantity": float(t.quantity or 0), "price": float(t.price or 0),
        "total": float(t.total_amount or 0), "notes": t.notes,
        "funding_source": t.funding_source,
        # الربح المحقّق للبيع: يُحسب ويُخزَّن ويغذّي الدخل السنوي والتقارير،
        # لكنه لم يكن يظهر في سجلّ العمليات إطلاقاً — يرى المالك حصيلة البيع
        # (9,140) ولا يرى ربحه منها (2,300)، فيقرأ الحصيلة ربحاً. الفرق بينهما
        # هو رأس ماله عائداً إليه، وخلطهما أخطر التباسٍ في التطبيق كلّه.
        "realized_gain": (float(t.realized_gain) if t.realized_gain is not None else None),
        "date": t.executed_at.isoformat() if t.executed_at else None,
    } for t in txs]
    # القائمة تبقى مصفوفةً كما كانت (لا تكسر أي مستهلك حالي)، والعدّاد يُرفَق
    # في الرسالة — الواجهة تقرأه إن احتاجته وتتجاهله إن لم تحتج.
    return success_response(
        data=items,
        message=f"total={total};limit={limit};offset={offset};has_more={int(offset + len(txs) < total)}",
    )


@router.post("")
async def add_transaction(data: TransactionCreate, db: AsyncSession = Depends(get_db)):
    # ── الشركة يجب أن تكون موجودة ─────────────────────────────────────────
    # رقمٌ عشوائي في company_id كان يُقبل بحالة 200 ويُنشئ عمليةً يتيمة: صفٌّ
    # في سجلّ العمليات بلا شركة، يدخل حسابات رأس المال ولا يظهر في أي حيازة —
    # اختلالٌ صامت في الأرقام لا يُكتشف إلا بمطابقةٍ يدوية. المعيار الأول:
    # سلامة البيانات قبل كل شيء.
    from app.models.portfolio import Company as _Co
    if not (await db.execute(
        select(func.count(_Co.id)).where(_Co.id == data.company_id)
    )).scalar():
        raise HTTPException(404, f"لا توجد شركة بالمعرّف {data.company_id} — لم تُسجَّل العملية.")
    # شراءٌ جديد في شركةٍ محذوفة يُعيدها إلى المحفظة بسجلّها كاملاً (D480):
    # كانت العملية تُسجَّل وتبقى الشركة مخفيّة، فيبدو الشراء ضائعاً.
    if data.transaction_type == "BUY":
        _co = (await db.execute(select(_Co).where(_Co.id == data.company_id))).scalar_one()
        if _co.status == "ARCHIVED":
            _co.status = "ACTIVE"

    _before = await _ledger_state(db, data.company_id)

    # ── فخّ التجزئة/المنحة ────────────────────────────────────────────────
    # التجزئة تضرب كل الأسهم المملوكة وقتَها، بما فيها أسهم منحةٍ سابقة. ومن
    # يُدخل محفظته يدوياً يقرأ كمياته من تطبيق الوسيط **بعد** التجزئة، فيسجّل
    # كمياتٍ مُجزَّأة أصلاً ثم يضيف عملية التجزئة فوقها — فتُضرب مرّتين، وتنتفخ
    # الأسهم صامتةً وينهار متوسط التكلفة معها. لا سبيل لتمييز النيّة من الأرقام،
    # فنطلب إقراراً صريحاً بدل أن نخمّن ونُفسد الحيازة.
    if data.transaction_type == "SPLIT" and not data.confirm_prior_pre_split:
        when = data.executed_at
        prior = (await db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.company_id == data.company_id,
                Transaction.transaction_type.in_(["BUY", "SELL", "BONUS"]),
                Transaction.executed_at <= when,
            )
        )).scalar() or 0
        if prior:
            raise HTTPException(
                422,
                f"قبل هذه التجزئة {prior} عملية مسجَّلة. التجزئة تضرب كمياتها كلّها، "
                f"فإن كنت أدخلتها بكمياتٍ مقروءةٍ من الوسيط **بعد** التجزئة فستُضرب "
                f"مرّتين وتفسد حيازتك. أكّد أن الكميات السابقة مسجَّلة قبل التجزئة.",
            )
    total, realized_gain, div_row = await _apply(db, data)
    tx = Transaction(
        company_id=data.company_id,
        transaction_type=data.transaction_type,
        quantity=data.quantity or data.factor or 0,
        price=data.price or 0,
        fees=data.fees,
        total_amount=total,
        funding_source=data.funding_source if data.transaction_type == "BUY" else None,
        realized_gain=realized_gain,
        notes=data.notes,
        executed_at=data.executed_at,
    )
    db.add(tx)
    await db.flush()
    if div_row is not None:
        div_row.transaction_id = tx.id
    # Canonicalize the holding from a full chronological replay — this makes
    # even an out-of-order entry (e.g. back-dating a BUY before an existing
    # split) land on the exact correct share count and cost basis, not just
    # the naive forward-applied one from _apply above.
    await recompute_holding(db, data.company_id)
    await _ledger_gate(db, data.company_id, _before)
    await db.commit()
    await db.refresh(tx)
    return success_response(data={"id": tx.id}, message="Transaction recorded.")


@router.get("/tag-audit")
async def tag_audit(db: AsyncSession = Depends(get_db)):
    """**مراجعة أوسمة التمويل** — كشفُ ما يستحيل حسابياً أن يكون صحيحاً.

    الوسم تصنيفٌ يدوي لا واقعة تُثبت، فيخطئ. والخطأ هنا ليس رأياً يُختلف فيه:
    شراءٌ موسوم «إعادة استثمار» بمبلغٍ يفوق ما كان في الحوض **يوم تنفيذه**
    مستحيل — لا يُنفَق مالٌ لم يدخل الحساب بعد. فنُظهر الفائض المتعذّر لكل
    عملية، ونترك القرار للمالك: لا يُعدَّل شيءٌ من هنا تلقائياً.

    وأثر الوسم الخاطئ ليس تجميلياً: يُبخّس حوض إعادة الاستثمار، ويرفع «عائد
    المحفظة» بتخفيض مقامه (رأس المال المدفوع يطرح المُعاد ضخّه).
    """
    from app.services.portfolio_return import compute_reinvestment_pool
    from app.models.portfolio import Company

    pool = await compute_reinvestment_pool(db)
    detail = pool.get("tagged_detail") or []
    bad = [d for d in detail if d.get("excess", 0) > 0.01 and d.get("tx_id")]
    if not bad:
        return success_response(data={"items": [], "total_excess": 0.0,
                                      "tagged_total": pool.get("tagged_total", 0.0)},
                                message="لا وسم مستحيل — كل شراءٍ موسوم كان الحوض يكفيه يوم تنفيذه.")

    ids = [d["tx_id"] for d in bad]
    rows = (await db.execute(select(Transaction).where(Transaction.id.in_(ids)))).scalars().all()
    by_id = {t.id: t for t in rows}
    names = dict((await db.execute(select(Company.id, Company.company_name))).all())

    items = []
    for d in sorted(bad, key=lambda x: -x["excess"]):
        t = by_id.get(d["tx_id"])
        if t is None:
            continue
        items.append({
            "id": t.id,
            "company": names.get(t.company_id) or "—",
            "date": d["when"],
            "amount": d["amount"],
            "funded": d["funded"],
            "excess": d["excess"],
            "pool_at_time": d["pool_at_time"],
            "funding_source": t.funding_source,
        })
    return success_response(data={
        "items": items,
        "total_excess": round(sum(i["excess"] for i in items), 2),
        "tagged_total": pool.get("tagged_total", 0.0),
        "pool": pool.get("pool", 0.0),
    })


class UntagRequest(BaseModel):
    """إزالة وسم التمويل عن عمليات محدّدة بالمعرّف — لا «إصلاح شامل» أعمى."""
    ids: list[int]


@router.get("/cash-audit")
async def cash_audit(db: AsyncSession = Depends(get_db)):
    """مصالحةُ النقد — **تقرأ ولا تكتب**.

    ══ لماذا وُجدت ══
    الحيازات تُعاد بناؤها من السجلّ كاملاً بعد كل تغيير (`recompute_holding`)،
    فأيّ خطأٍ فيها يُصحَّح نفسه في الطلب التالي. والنقد بخلافها يُدار
    **تراكمياً**: كل عملية تخصم أو تضيف، والتعديل يعكس القديم ويطبّق الجديد.
    وهو صحيحٌ ما دام كلُّ مسارٍ يعكس ما يطبّقه بالضبط — فإن أخطأ مسارٌ مرّةً
    واحدة، انزاح الرصيد **للأبد** بلا تصحيحٍ ذاتيّ ولا أثرٍ ظاهر.

    وهذا المسار يكشف الانزياح إن وقع: يحسب النقد المتوقّع من السجلّ نفسه
    (إيداعات − سحوبات + مبيعات + توزيعات − مشتريات) ويقارنه بالمخزَّن.

    ولا يُصلح شيئاً: تصحيحُ رصيد المالك تعديلٌ لبياناته، ولا يقع إلا بطلبه
    الصريح — يرى الفرق أوّلاً ثم يقرّر.
    """
    from app.models.transaction import CashLedger, CashLedgerKind

    txs = (await db.execute(select(Transaction))).scalars().all()
    from_tx = sum(_cash_effect(t.transaction_type, float(t.total_amount or 0),
                               t.funding_source) for t in txs)

    dep = wdr = 0.0
    for m in (await db.execute(select(CashLedger))).scalars().all():
        amt = float(getattr(m, "amount", 0) or 0)
        kind = getattr(m, "kind", None)
        k = kind.value if hasattr(kind, "value") else str(kind or "")
        if k == CashLedgerKind.DEPOSIT.value:
            dep += amt
        elif k == CashLedgerKind.WITHDRAW.value:
            wdr += amt

    expected = dep - wdr + from_tx
    cash = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    stored = float(cash.available_cash or 0) if cash else 0.0
    gap = round(stored - expected, 2)

    return success_response(data={
        "المخزَّن": round(stored, 2),
        "المتوقَّع من السجلّ": round(expected, 2),
        "الفرق": gap,
        "مكوّنات المتوقَّع": {
            "إيداعات": round(dep, 2), "سحوبات": round(wdr, 2),
            "أثر العمليات": round(from_tx, 2),
        },
        "الحكم": ("مطابق" if abs(gap) <= 0.01 else
                  "انزياح — الرصيد لا يساوي ما يقوله السجلّ"),
    })


@router.post("/untag")
async def untag_transactions(data: UntagRequest, db: AsyncSession = Depends(get_db)):
    """يُزيل الوسم عن العمليات المذكورة — ولا شيء غيره.

    الوسم لا يمسّ النقد ولا الكمية ولا التكلفة (كل شراءٍ يخصم نقده بنفس الطريقة
    مهما كان مصدره المفترض)، فإزالته آمنةٌ بالكامل وقابلة للتراجع: أعِد الوسم
    من تحرير العملية متى شئت. وما يتغيّر: الحوض ورأس المال المدفوع يعودان إلى
    الصواب."""
    if not data.ids:
        raise HTTPException(422, "لم تُحدَّد أي عملية.")
    rows = (await db.execute(select(Transaction).where(Transaction.id.in_(data.ids)))).scalars().all()
    changed = 0
    for t in rows:
        if t.transaction_type != "BUY":
            continue
        if t.funding_source:
            t.funding_source = None
            changed += 1
    if changed:
        await db.commit()
    return success_response(data={"changed": changed},
                            message=f"أُزيل الوسم عن {changed} عملية.")


async def _audit_reason(db: AsyncSession, why: str | None) -> None:
    """سببُ التغيير يُمرَّر إلى قيد التدقيق في قاعدة البيانات (D481) — محليٌّ
    للمعاملة الجارية فلا يتسرّب إلى غيرها."""
    await db.execute(text("SELECT set_config('sp.audit_reason', :r, true)"),
                     {"r": (why or "").strip()[:500]})


@router.get("/audit")
async def get_audit(company_id: int | None = None, limit: int = 200,
                    db: AsyncSession = Depends(get_db)):
    """سجلّ التدقيق (D481): كل إضافةٍ وتعديلٍ وحذفٍ في العمليات بصورته قبل
    وبعد — يُقرأ ولا يُكتب إلا من قاعدة البيانات نفسها."""
    sql = ("SELECT id, at, op, tx_id, company_id, old_row, new_row, reason "
           "FROM transaction_audit")
    params: dict = {"n": max(1, min(limit, 2000))}
    if company_id is not None:
        sql += " WHERE company_id = :c"
        params["c"] = company_id
    sql += " ORDER BY id DESC LIMIT :n"
    try:
        rows = (await db.execute(text(sql), params)).mappings().all()
    except Exception:
        return success_response(data=[], message="سجلّ التدقيق غير متوفّر بعد.")
    return success_response(data=[{
        "id": r["id"], "at": r["at"].isoformat() if r["at"] else None, "op": r["op"],
        "tx_id": r["tx_id"], "company_id": r["company_id"],
        "old": r["old_row"], "new": r["new_row"], "reason": r["reason"],
    } for r in rows])


@router.get("/{tx_id}")
async def get_transaction(tx_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == tx_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return success_response(data={"id": tx.id, "type": tx.transaction_type, "quantity": float(tx.quantity or 0), "price": float(tx.price or 0)})


def _cash_effect(t: str, total: float, funding_source: str | None) -> float:
    """أثر عمليةٍ على رصيد النقد — موجبٌ يزيده وسالبٌ ينقصه.

    مصدرٌ واحد لهذا الجدول يخدم التحرير والحذف معاً، فيستحيل أن يعكس أحدهما
    ما يطبّقه الآخر بخلافه. المبالغ مطلقة فعكسها دقيقٌ دائماً — بخلاف عدد
    الأسهم الذي قد تُعيد تجزئةٌ لاحقة قياسه، ولذلك تُبنى الحيازة من إعادة
    تشغيل السجل كاملاً لا بالطرح."""
    if t == "BUY":
        return -total
    if t in ("SELL", "DIVIDEND"):
        return total
    if t == "REINVESTMENT" and (funding_source or "DIVIDEND") in REINVEST_TAGS:
        return -total
    return 0.0


def _recompute_total(t: str, qty: float, price: float, fees: float, amount: float) -> float:
    """إجمالي العملية بنفس صيغة الإنشاء حرفياً (انظر _apply)."""
    if t == "BUY":
        return qty * price + fees
    if t == "SELL":
        return qty * price - fees
    if t == "DIVIDEND":
        return amount
    return 0.0   # منحة وتجزئة: لا نقد


class TransactionPatch(BaseModel):
    """تحرير عمليةٍ مسجَّلة. كل الحقول اختيارية — ما يُترك None لا يتغيّر.

    **النوع غير قابل للتغيير عمداً**: تحويل شراءٍ إلى توزيعٍ (مثلاً) يستوجب
    إنشاء/حذف صفّ توزيعٍ مرتبط وإعادة بناء علاقات أخرى، فمكانه الصحيح حذف
    العملية وتسجيلها من جديد لتمرّ بمحرّك الإنشاء كاملاً.

    وما عداه محرَّرٌ بالكامل، والسلامة مضمونة بمسارين مُجرَّبين لا بحسابٍ جديد:
      • النقد: يُعكس أثر العملية القديم بالضبط ثم يُطبَّق الجديد — بنفس جدول
        _cash_effect الذي يستعمله الحذف.
      • الحيازة: تُعاد بناؤها من إعادة تشغيل السجل كاملاً (recompute_holding)،
        فتصحّ مهما تغيّر الترتيب أو تخلّلته تجزئة."""
    quantity: Optional[float] = None
    price: Optional[float] = None
    fees: Optional[float] = None
    amount: Optional[float] = None          # مبلغ التوزيع
    executed_at: Optional[datetime] = None
    notes: Optional[str] = None
    funding_source: Optional[str] = None    # "" أو null ⇒ إزالة الوسم
    set_funding_source: bool = False        # علامةٌ صريحة: عالِج الوسم أعلاه
    reason: Optional[str] = None            # سبب التعديل — يُقيَّد في سجلّ التدقيق (D481)


@router.patch("/{tx_id}")
async def patch_transaction(tx_id: int, data: TransactionPatch,
                            db: AsyncSession = Depends(get_db)):
    tx = (await db.execute(select(Transaction).where(Transaction.id == tx_id))).scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    await _audit_reason(db, data.reason)
    _before = await _ledger_state(db, tx.company_id)

    t = tx.transaction_type
    cash = await _get_cash(db)
    div = (await db.execute(select(Dividend).where(Dividend.transaction_id == tx.id))).scalar_one_or_none()
    # حالة القصّ قبل التعديل: ما كان مقصوصاً أصلاً ليس ذنب هذا التعديل.
    before_clipped = (await _replay(db, tx.company_id, persist_gains=False))["clipped_sales"]

    old_total = float(tx.total_amount or 0)
    old_effect = _cash_effect(t, old_total, tx.funding_source)

    # ── الحقول الجديدة ────────────────────────────────────────────────────
    qty   = float(data.quantity if data.quantity is not None else (tx.quantity or 0))
    price = float(data.price    if data.price    is not None else (tx.price or 0))
    fees  = float(data.fees     if data.fees     is not None else (tx.fees or 0))
    amount = float(data.amount  if data.amount   is not None else old_total)
    when  = data.executed_at or tx.executed_at

    if qty < 0 or price < 0 or fees < 0:
        raise HTTPException(422, "لا تُقبل قيمة سالبة.")
    if t in ("BUY", "SELL") and not (qty > 0 and price > 0):
        raise HTTPException(422, "الكمية والسعر مطلوبان ويجب أن يكونا أكبر من صفر.")
    if t == "BONUS" and not (qty > 0):
        raise HTTPException(422, "الكمية مطلوبة للمنحة.")
    if t == "DIVIDEND" and not (amount > 0):
        raise HTTPException(422, "مبلغ التوزيع مطلوب.")
    if t == "SPLIT" and not (qty > 0):
        raise HTTPException(422, "معامل التجزئة مطلوب.")
    # بتقويم الرياض كالإنشاء تماماً — وإلّا رُفض تعديلٌ صحيح ليلاً لأن
    # التقويم العالميّ يكون قد سبق يوم المالك.
    if when is not None and when.tzinfo is None:
        when = when.replace(tzinfo=_RIYADH)
    if when and when.astimezone(_RIYADH).date() > (datetime.now(_RIYADH).date() + timedelta(days=1)):
        raise HTTPException(422, "لا يمكن تسجيل صفقة بتاريخ مستقبلي.")

    new_total = _recompute_total(t, qty, price, fees, amount)

    # ── الوسم ─────────────────────────────────────────────────────────────
    new_funding = tx.funding_source
    if data.set_funding_source:
        if t != "BUY":
            raise HTTPException(422, "وسم التمويل خاصٌّ بعمليات الشراء.")
        v = (data.funding_source or "").strip().upper()
        if not v:
            new_funding = None
        elif v in REINVEST_TAGS:
            new_funding = v
        else:
            raise HTTPException(422, "وسم غير معروف.")

    # ── النقد: اعكس القديم ثم طبّق الجديد ─────────────────────────────────
    new_effect = _cash_effect(t, new_total, new_funding)
    delta = new_effect - old_effect
    # حارس السيولة على التحرير — كان على الإنشاء وحده. رفعُ قيمة شراءٍ قديم أو
    # تخفيضُ بيعٍ يخصم من النقد بلا سقف، فيهبط دون الصفر بصمت: حالةٌ مستحيلة
    # واقعاً تفسد كل ما يُبنى على النقد (القابل للاستثمار، الأوزان، الحوض).
    if delta < 0:
        avail = float(cash.available_cash or 0)
        if -delta > avail + 1e-6:
            raise HTTPException(
                422,
                f"هذا التعديل يخصم {-delta:,.2f} من السيولة، والمتاح {avail:,.2f} فقط. "
                f"سجّل ضخّاً نقدياً أولاً أو راجع الأرقام.",
            )
    if delta:
        cash.available_cash = float(cash.available_cash or 0) + delta
        cash.total_cash = float(cash.total_cash or 0) + delta

    tx.quantity = qty
    tx.price = price
    tx.fees = fees
    tx.total_amount = new_total
    tx.funding_source = new_funding
    if when:
        tx.executed_at = when
    if data.notes is not None:
        tx.notes = data.notes.strip() or None

    # صفّ التوزيع المرتبط يتبع العملية — وإلا تباعد سجل التوزيعات عن مصدره.
    if div is not None and t == "DIVIDEND":
        div.received_amount = new_total
        # ونصيب السهم يتبع المبلغ: تركُه على قيمته القديمة يجعل صفحة الشركة
        # تعرض «التوزيع للسهم» مناقضاً لمبلغ التوزيع نفسه في السطر ذاته.
        shares = float(div.shares_at_time or 0)
        if shares > 0:
            div.dividend_per_share = new_total / shares
        if when:
            div.payment_date = when

    await db.flush()
    # حارس البيع المقصوص: تعديلُ شراءٍ قديم (كميةً أو تاريخاً) قد يُنقص الأسهم
    # المتاحة في لحظةٍ لاحقة، فتُقصّ عملية بيعٍ لم يلمسها المالك بصمتٍ تام —
    # لا رسالة ولا أثر مرئي، ويتغيّر ربحها المحقّق ومحصول المحفظة معه. نمنع
    # التعديل الذي يُحدث قصّاً جديداً، ونسمّي العملية المتضرّرة.
    after = await _replay(db, tx.company_id, persist_gains=False)
    new_clipped = [i for i in after["clipped_sales"] if i not in before_clipped]
    if new_clipped:
        raise HTTPException(
            422,
            f"هذا التعديل يجعل عملية البيع رقم {new_clipped[0]} تبيع أسهماً غير مملوكة "
            f"في تاريخها، فتُقصّ كميتها ويتغيّر ربحها المحقّق. صحّح تلك العملية أولاً.",
        )
    # الحيازة تُبنى من السجل كاملاً — يصحّح الكمية والتكلفة والأرباح المحقّقة
    # مهما تغيّر الترتيب أو تخلّلته تجزئة.
    await recompute_holding(db, tx.company_id)
    await _ledger_gate(db, tx.company_id, _before)
    await db.commit()
    await db.refresh(tx)
    return success_response(data={
        "id": tx.id, "quantity": float(tx.quantity or 0), "price": float(tx.price or 0),
        "fees": float(tx.fees or 0), "total": float(tx.total_amount or 0),
        "funding_source": tx.funding_source,
        "date": tx.executed_at.isoformat() if tx.executed_at else None,
    }, message="تم حفظ التعديل.")


@router.delete("/{tx_id}")
async def delete_transaction(tx_id: int, reason: str | None = None,
                             db: AsyncSession = Depends(get_db)):
    """Undo a wrongly-recorded transaction: reverses its effect on the
    Holding and Cash, and removes any Dividend row it created — the same
    keep-the-UI-clean escape hatch already available on the dividends log."""
    tx = (await db.execute(select(Transaction).where(Transaction.id == tx_id))).scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    await _audit_reason(db, reason)
    _before = await _ledger_state(db, tx.company_id)

    h = (await db.execute(select(Holding).where(Holding.company_id == tx.company_id).with_for_update())).scalar_one_or_none()
    cash = await _get_cash(db)
    qty = float(tx.quantity or 0)
    total = float(tx.total_amount or 0)
    price = float(tx.price or 0)
    t = tx.transaction_type

    # A dividend record may be linked to this transaction even if its type is
    # now BUY (a pre-refactor dividend-reinvestment row, relabeled to BUY by
    # the startup migration) — checked up front so the BUY-reversal below can
    # also undo the total_dividends_received it recorded back when it was
    # still a REINVESTMENT(DIVIDEND) row.
    before_clipped = (await _replay(db, tx.company_id, persist_gains=False))["clipped_sales"]
    div = (await db.execute(select(Dividend).where(Dividend.transaction_id == tx.id))).scalar_one_or_none()
    if not div and t == "DIVIDEND":
        # Legacy rows created before transaction_id existed
        div = (await db.execute(select(Dividend).where(
            Dividend.company_id == tx.company_id,
            Dividend.received_amount == total,
            Dividend.payment_date == tx.executed_at,
            Dividend.transaction_id.is_(None),
        ))).scalar_one_or_none()

    # CASH reversal only — cash moves are absolute amounts, so reversing them
    # from the current balance is always exact (unlike share counts, which a
    # later split rescales). The HOLDING itself is rebuilt from a full replay
    # of the remaining transactions below, which is order/split-proof.
    # عكسٌ دقيق بنفس جدول _cash_effect الذي يستعمله التحرير — مصدرٌ واحد
    # فيستحيل أن يعكس الحذف ما يطبّقه التحرير بخلافه. وبلا أي max(0,…): الرصيد
    # قد يكون سالباً بحق (شراءٌ مموَّل من خارج النقد المتتبَّع)، وبتره صفراً كان
    # يمحو الرصيد الحقيقي عند حذف توزيعة.
    reversal = -_cash_effect(t, total, tx.funding_source)
    if reversal:
        cash.available_cash = float(cash.available_cash or 0) + reversal
        cash.total_cash = float(cash.total_cash or 0) + reversal

    if div:
        await db.delete(div)

    company_id = tx.company_id
    await db.delete(tx)
    await db.flush()
    # نفس حارس البيع المقصوص الذي على التحرير: حذف شراءٍ قديم قد يترك بيعاً
    # لاحقاً بلا أسهم كافية، فيُقصّ بصمت ويتغيّر ربحه المحقّق ومحصول المحفظة.
    after = await _replay(db, company_id, persist_gains=False)
    new_clipped = [i for i in after["clipped_sales"] if i not in before_clipped]
    if new_clipped:
        raise HTTPException(
            422,
            f"حذف هذه العملية يجعل عملية البيع رقم {new_clipped[0]} تبيع أسهماً غير "
            f"مملوكة في تاريخها، فتُقصّ كميتها ويتغيّر ربحها المحقّق. "
            f"احذف تلك العملية أو صحّحها أولاً.",
        )
    # Rebuild the holding from scratch on the remaining ledger — the fix for
    # the delete-before-a-split miscount (and every other ordering edge case).
    await recompute_holding(db, company_id)
    await _ledger_gate(db, company_id, _before)
    await db.commit()
    return success_response(message="Transaction deleted.")
