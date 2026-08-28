"""
Portfolio compound growth (XIRR) and combined "عائد المحفظة" metric —
separate from the market-quoted per-stock financial ratios in /metrics.

CAGR here is computed as a money-weighted rate of return (XIRR) using the
real cash deposit/withdrawal ledger as external cash flows and the current
total wealth as the final flow — this is the only correct way to annualize
growth for a portfolio that received money at different times, since a naive
(end/start)^(1/years) on total wealth would count new deposits as "growth".
"""
from datetime import datetime, timezone


def _npv(rate: float, flows: list[tuple[float, float]]) -> float:
    """flows: list of (years_from_start, amount)."""
    return sum(amount / (1 + rate) ** years for years, amount in flows)


def xirr(dated_flows: list[tuple[datetime, float]]) -> float | None:
    """dated_flows: list of (date, amount) — negative for money going into
    the portfolio, positive for money coming out (including the final
    liquidation-equivalent value). Returns the annualized rate, or None if
    it can't be solved (e.g. all flows same sign, or fewer than 2 flows)."""
    if len(dated_flows) < 2:
        return None
    t0 = min(d for d, _ in dated_flows)
    flows = [((d - t0).days / 365.0, amt) for d, amt in dated_flows]
    if not any(a < 0 for _, a in flows) or not any(a > 0 for _, a in flows):
        return None  # no sign change — can't be a real investment/return pair

    lo, hi = -0.9999, 10.0
    f_lo, f_hi = _npv(lo, flows), _npv(hi, flows)
    if f_lo * f_hi > 0:
        return None  # no root in a sane range
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = _npv(mid, flows)
        if abs(f_mid) < 1e-6:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


async def compute_net_profit(db) -> dict:
    """**المقياس الموحّد**: صافي الربح ونموّ رأس المال.

        صافي الربح = الثروة (سوقية + نقد) − رأس مال المشروع (صافي الضخّ)
        نموّ رأس المال٪ = صافي الربح ÷ إجمالي المدفوع (تكلفة الحيازات)

    ولماذا هذا التعريف دون غيره:
      • **المبلغ** مربوطٌ بالنقد الفعلي والقيمة السوقية الفعلية، فلا يخدعه
        إدخالٌ ناقص في السجل ولا عمولة غير مسجّلة ولا تعديلٌ يدوي على
        المتوسط — وهي كلّها تُزحزح المقاييس المبنيّة على السجل وحده.
      • **الضخّ لا يخلق ربحاً ولا يمحوه**: كل إيداع يرفع الثروة ورأس المال
        بنفس القدر، فالفرق ثابت. هذه الخاصّية هي ما يجعله صادقاً مع ضخٍّ
        شهري متكرّر.
      • **المقام تكلفة الحيازات لا رأس المال كلّه**: قياس الأداء على مالٍ لم
        يدخل السوق يُبخّس النتيجة بلا ذنب — ٧٩٪ نقداً تحوّل ١٠٪ إلى ٢٪.

    ويحلّ محلّ DPI والمحصول و«الربح المحقّق» — مقياسٌ واحد لا يُقرأ إلا وجهاً
    واحداً، بدل أرقامٍ متقاربة يتنازعها القارئ."""
    from sqlalchemy import select
    from app.models.transaction import CashLedger, CashLedgerKind, Cash
    from app.models.portfolio import Holding

    ledger = (await db.execute(select(CashLedger))).scalars().all()
    contributed = sum(float(e.amount or 0) * (1 if e.kind == CashLedgerKind.DEPOSIT else -1)
                      for e in ledger)
    holdings = (await db.execute(select(Holding))).scalars().all()
    market_value = sum(float(h.market_value or 0) for h in holdings)
    cost = sum(float(h.invested_amount or 0) for h in holdings)
    cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    cash = float(cash_row.available_cash or 0) if cash_row else 0.0

    wealth = market_value + cash
    # بلا سجلّ ضخٍّ لا مرجع للقياس: يُعاد None لا صفرٌ يُقرأ «لا ربح».
    net_profit = round(wealth - contributed, 2) if ledger else None
    growth = round(net_profit / cost * 100, 2) if (net_profit is not None and cost > 0) else None
    return {
        "wealth": round(wealth, 2),
        "contributed": round(contributed, 2),
        "net_profit": net_profit,
        "capital_growth_pct": growth,
        "deployed_pct": round(cost / contributed * 100, 2) if contributed > 0 else None,
        "cost_basis": round(cost, 2),
    }


async def compute_cagr_pct(db) -> float | None:
    """Money-weighted annualized growth rate of the portfolio, using the
    real deposit/withdrawal history as cash flows and current total wealth
    as the final flow. None if there's no deposit history to anchor it."""
    from sqlalchemy import select
    from app.models.transaction import CashLedger, CashLedgerKind, Cash
    from app.api.v1.endpoints.portfolio import _get_holdings

    ledger = (await db.execute(select(CashLedger).order_by(CashLedger.created_at))).scalars().all()
    if not ledger:
        return None

    flows: list[tuple[datetime, float]] = []
    for entry in ledger:
        amount = float(entry.amount or 0)
        when = entry.created_at or datetime.now(timezone.utc)
        # tz hardening: a naive timestamp (legacy rows / non-tz drivers) must
        # not crash the whole /metrics endpoint when compared with aware ones.
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if entry.kind == CashLedgerKind.DEPOSIT:
            flows.append((when, -amount))
        else:
            flows.append((when, amount))

    holdings = await _get_holdings(db)
    market_value = sum(float(h.market_value or 0) for h in holdings)
    cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    cash = float(cash_row.available_cash or 0) if cash_row else 0.0
    current_wealth = market_value + cash
    flows.append((datetime.now(timezone.utc), current_wealth))

    rate = xirr(flows)
    return round(rate * 100, 2) if rate is not None else None


def sale_harvest(tx) -> float:
    """محصول عملية بيعٍ واحدة — **الحصيلة كاملةً متى كانت رابحة**، وصفرٌ إن
    كانت خاسرة.

    ولماذا الحصيلة لا الربح: هذا هو مقياس DPI المؤسسي
    (Distributions to Paid-In) بحرفه — «كم ريالاً عاد إلى يدي مقابل كل ريال
    دفعته؟» — وهو يشمل عودة رأس المال عمداً لا سهواً، لأن السؤال عن المحصول
    لا عن الربح. فالمالك يحصد ثم يُعيد الضخّ، والتراكم عنده حقيقي.

    وشرط «الرابحة» شرط المالك: بيعٌ بخسارة ليس محصولاً بأي معنى، فلا يدخل.

    القيد المعروف: بيعٌ بسعر التكلفة ثم إعادة شراء يرفع الرقم بلا ربحٍ حقيقي.
    ويحمي منه المعيار الثاني (حوض إعادة الاستثمار): الشراء الموسوم يُنقصه،
    فيبقى المحصول ثابتاً ويقول الحوض «صُرِف» — والرقمان معاً يرويان القصة،
    كما تعرض المؤسسات DPI مع RVPI ولا تعرضه وحده."""
    gain = float(getattr(tx, "realized_gain", 0) or 0)
    return float(getattr(tx, "total_amount", 0) or 0) if gain > 0 else 0.0


def sale_profit(tx) -> float:
    """**ربح** عملية بيعٍ واحدة — لا حصيلتها.

    هذا ما يدخل «عائد المحفظة» بعد توحيد المقاييس: السؤال «كم كسبتُ؟» لا «كم
    عاد إلى يدي». الحصيلة تحوي رأس المال العائد، فتُظهر إنتاجاً لم يحدث —
    بيعُ ما اشتريتَه بالأمس بسعر الأمس نفسه يرفع الحصيلة ولا يكسبك ريالاً.

    والخسارة لا تُخصم من العائد هنا لأن العينة نفسها عينة sale_harvest
    (العمليات الرابحة وحدها)، فيبقى المقياسان يصفان نفس العمليات ويختلفان في
    المقدار لا في العيّنة: هذا حصيلتها وذاك ربحها."""
    gain = float(getattr(tx, "realized_gain", 0) or 0)
    return gain if gain > 0 else 0.0


async def compute_paid_in_capital(db, holdings=None, txs=None, as_of=None) -> float:
    """**رأس المال المدفوع التراكمي** — مقام كل نسبة عائد في التطبيق.

    والعلّة التي يعالجها: كان المقام «تكلفة الحيازات القائمة الآن»، وهي تنقص
    مع كل عملية بيع (تُحذف تكلفة الأسهم المباعة). فالبيع كان يرفع النسبة
    مرّتين عن سببٍ واحد: يزيد البسط ويُنقص المقام معاً. والفجوة تتّسع كلّما
    باع المالك أكثر، وتنتهي في التصفية الكاملة إلى مقامٍ صفرٍ فلا تُعرض نسبةٌ
    أصلاً — محفظةٌ حصدت كل شيء تقول «لا يوجد عائد».

    والصواب المؤسسي أن مقام DPI هو رأس المال المُساهَم به، وهو **لا ينقص**:

        المدفوع = مجموع كل عمليات الشراء (بعمولاتها)
                − ما استُهلك فعلاً من حوض إعادة الاستثمار
                + تصحيحات المالك اليدوية على التكلفة

    ولماذا يُطرح المستهلك من الحوض: الشراء المموَّل من حصيلةٍ سابقة ليس مالاً
    جديداً دخل المحفظة، بل المحصول نفسه يُعاد ضخّه — فعدّه مساهمةً جديدة يحسبه
    مرّتين (في البسط محصولاً وفي المقام رأس مال).

    ونطرح **المستهلك زمنياً** لا مجموع المشتريات الموسومة: الوسم تصنيفٌ لا
    قياس، ووسمٌ واحد خاطئ بمبلغٍ ضخم كان سيُبخّس المقام فيقفز العائد إلى رقمٍ
    خيالي. أما المستهلك فمحدودٌ بما كان في الحوض لحظتَه، فيستحيل أن يتجاوز
    المحصول الحقيقي مهما أخطأت الأوسمة.

    وأرضيةٌ أخيرة: لا ينزل المقام أبداً دون تكلفة الحيازات القائمة — فمن
    المستحيل أن تكون قد دفعت أقلّ ممّا هو مركوزٌ في محفظتك الآن."""
    from sqlalchemy import select
    from app.models.transaction import Transaction, TransactionType
    from app.models.portfolio import Holding

    if txs is None:
        txs = (await db.execute(select(Transaction))).scalars().all()
    if holdings is None:
        # قراءةٌ مباشرة لا عبر _get_holdings: تلك تُحدّث الأسعار من السوق، ولا
        # شأن للسعر برأس المال المدفوع — فكانت كل قراءةٍ للمقام تستدعي الشبكة
        # (والتقارير تستدعيها مرّتين إضافيّتين لكل تقرير).
        holdings = (await db.execute(select(Holding))).scalars().all()

    def _in_window(t) -> bool:
        if as_of is None:
            return True
        when = _as_dt(t.executed_at) or _as_dt(t.created_at)
        return bool(when) and when.date() <= as_of

    gross_buys = sum(float(t.total_amount or 0)
                     for t in txs
                     if t.transaction_type == TransactionType.BUY and _in_window(t))
    adjustments = sum(float(getattr(h, "cost_basis_adjustment", 0) or 0)
                      + float(getattr(h, "paid_in_adjustment_realized", 0) or 0)
                      for h in holdings)
    current_cost = sum(float(h.invested_amount or 0) for h in holdings)

    pool = await compute_reinvestment_pool(db, as_of=as_of)
    recycled = float(pool.get("already_reinvested") or 0)

    paid_in = gross_buys + adjustments - recycled
    # الأرضية تحمي من سجلٍّ ناقص (عمليات قديمة لم تُدخَل، فتكون التكلفة القائمة
    # أكبر من مجموع المشتريات المسجَّلة). ويُطرح منها المُعاد ضخّه: من باع ثم
    # أعاد الشراء من الحصيلة تكون تكلفته القائمة أكبر من مساهمته الحقيقية،
    # فأرضيةٌ بلا هذا الطرح كانت تعيد عدّ المحصول رأسَ مالٍ من جديد — وهي حالة
    # المالك نفسها لا حالةٌ نادرة.
    # الأرضية حارسٌ لليوم لا للتاريخ: التكلفة القائمة رقمُ اليوم، فإقحامها في
    # نافذةٍ ماضية يُقحم مشترياتٍ لم تكن قد وقعت بعد.
    floor = (current_cost - recycled) if as_of is None else 0.0
    return round(max(paid_in, floor), 2)


async def compute_production(db) -> dict:
    """**المصدر الوحيد للمعيار الأول** — الإنتاج التراكمي («كم حُلِبت البقرة»).

        المحصول = حصيلة البيع الرابحة كاملةً + التوزيعات + قيمة أسهم المنحة

    ورقمٌ واحد يُعرض بأربعة وجوه لا أربعة أرقام:
      • «العائد المحقّق»      → المبلغ نفسه
      • «عائد المحفظة»        → نسبتُه إلى رأس المال المدفوع (وهو DPI)
      • «نمو العائد»          → نفسه موزّعاً على الزمن
      • «الهدف الاستثماري»    → نفسه مقابل هدف السنة
    فجمعها في دالةٍ واحدة يجعل تباعدها مستحيلاً بنيوياً — وقد تباعدت فعلاً
    ثلاث مرّات في هذا التطبيق قبل أن تُجمع.

    وهو **ثابت لا ينقص أبداً**: إعادة استثمار المحصول تحويلٌ لشكله لا إلغاءٌ
    له. المتحرّك هو المعيار الثاني وحده (compute_reinvestment_pool)، وهو
    **جزءٌ من هذا الرقم** لا نظامٌ موازٍ:
        الحوض = المحصول − المنحة (أسهم لا نقد) − ما أُعيد استثماره
    فيستحيل أن يصير الجزء أكبر من كلّه."""
    from sqlalchemy import select
    from app.models.transaction import Transaction, TransactionType, Dividend
    from app.api.v1.endpoints.portfolio import _get_holdings

    txs = (await db.execute(select(Transaction))).scalars().all()
    # التوزيعات من جدول Dividend (كل العمر) لا بمسح نوع العملية — يبقى صحيحاً
    # سواء قُبضت نقداً أو استُعملت فوراً في شراء.
    divs = (await db.execute(select(Dividend))).scalars().all()
    holdings = await _get_holdings(db)
    by_company = {h.company_id: h for h in holdings}

    dividends = sum(float(d.received_amount or 0) for d in divs)
    sale_proceeds = sum(sale_harvest(t) for t in txs if t.transaction_type == TransactionType.SELL)
    realized_gains = sum(float(t.realized_gain or 0)
                         for t in txs if t.transaction_type == TransactionType.SELL)
    # ربح التصفية الداخل في «الربح المحقّق»: الأرباح الموجبة وحدها، بنفس شرط
    # sale_harvest تماماً (بيعٌ خاسر ليس محصولاً ولا ربحاً). توحيد الشرط يضمن
    # أن المقياسين يصفان **نفس** العمليات، ويختلفان في المقدار لا في العيّنة.
    sale_gains = sum(g for g in (float(t.realized_gain or 0)
                                 for t in txs if t.transaction_type == TransactionType.SELL)
                     if g > 0)
    # قيمة المنحة بسعر يوم المنح — تبقى محسوبةً للمراجعة والمقارنة.
    bonus_at_grant = sum(bonus_share_value(t, (by_company.get(t.company_id).last_price
                                               if by_company.get(t.company_id) else 0))
                         for t in txs if t.transaction_type == TransactionType.BONUS)
    # ── قيمة المنحة الداخلة في كل المقاييس: **بسعر السوق اليوم** ──────────
    # قرار المالك صريحاً. والمقايضة معلومة ومقبولة منه: يصير مكوّنٌ من
    # «المحقّق» متحرّكاً، فينزل الإنتاج التراكمي وعائد المحفظة مع هبوط السعر
    # بلا أن يبيع سهماً. ومقابلها أن الرقم يعكس ما تساويه المنحة فعلاً اليوم لا
    # ما ساوته يوم منحها. وتبقى قيمة يوم المنح محسوبةً (bonus_at_grant) للمقارنة.
    bonus_shares = sum(float(t.quantity or 0)
                       for t in txs if t.transaction_type == TransactionType.BONUS)
    bonus_market_value = sum(
        float(t.quantity or 0) * float(getattr(by_company.get(t.company_id), "last_price", 0) or 0)
        for t in txs if t.transaction_type == TransactionType.BONUS)

    capital_base = await compute_paid_in_capital(db, holdings=holdings, txs=txs)
    return {
        "dividends": round(dividends, 2),
        "sale_proceeds": round(sale_proceeds, 2),
        # الربح المحقّق — للعرض والمقارنة فقط، لا يدخل المحصول.
        "realized_gains": round(realized_gains, 2),
        # المنحة **خارج** المحصول: إصدار أسهم المنحة يُرسمل احتياطياً ولا
        # يُنشئ قيمة — عدد الأسهم يزيد وسعر السهم ينخفض بالتناسب، فثروة المالك
        # بعده كثروته قبله. وإدخالها في الموزَّع كان يعدّها مرّتين: مرّةً هنا
        # بقيمتها السوقية، ومرّةً في RVPI لأنها ضمن حيازته أصلاً — فيقول
        # TVPI 1.40 والصواب 1.20 (مبالغة 17٪ تتضخّم مع كل ارتفاع سعر).
        # وتُعرض أسهم المنحة مستقلّةً بعددها وقيمتها، فلا تُبخَس ولا تُعدّ مرّتين.
        "bonus_value": 0.0,
        "total": round(dividends + sale_proceeds, 2),
        # ── المقياس الثاني، مستقلٌّ لا بديل ────────────────────────────────
        # «الربح المحقّق»: ما كسبتَه فعلاً — التوزيعات + **ربح** التصفية (لا
        # حصيلتها) + قيمة المنحة. يختلف عن المحصول لأنه يستبعد عودة رأس مالك
        # إليك، وعودةُ رأس المال ليست ربحاً بأي معنى محاسبي.
        # ولماذا يبقى المحصول معه: المحصول يجيب «كم عاد إلى يدي؟» (DPI)
        # والربح يجيب «كم كسبتُ؟». الصناديق تعرض الاثنين ولا تكتفي بأحدهما،
        # وإخفاء أيّهما يُضلّل في اتجاه: المحصول وحده يُضخّم، والربح وحده
        # يُخفي السيولة التي عادت وصارت قابلة لإعادة التوظيف.
        "sale_gains": round(sale_gains, 2),
        "bonus_market_value": round(bonus_market_value, 2),
        "bonus_at_grant": round(bonus_at_grant, 2),
        "bonus_shares": round(bonus_shares, 2),
        "realized_profit": round(dividends + sale_gains, 2),
        "capital_base": round(capital_base, 2),
    }


async def compute_company_production(db, company_id: int) -> dict:
    """إنتاج شركةٍ واحدة — **بنفس تعريف المحفظة حرفياً** لا بتعريفٍ خاص.

    كان يُحسب في الواجهة هكذا:
        الإنتاج = التوزيعات + أسهم المنحة × السعر + أسهم إعادة الاستثمار × السعر
    وفيه خطآن:
      • **المنحة مزدوجة**: قيمتها محسوبة أصلاً ضمن القيمة السوقية للحيازة.
      • **أسهم إعادة الاستثمار ليست إنتاجاً بحال**: هي أسهمٌ **اشتريتَها**،
        وثمنها مقيَّدٌ في تكلفتك. فعدّ قيمتها السوقية إنتاجاً يحسب المال
        مرّتين: مرّةً حين خرج من الحوض ومرّةً حين صار سهماً.
      • ولا تدخله حصيلة البيع أصلاً، وهي أكبر مكوّنٍ في تعريف المحفظة.

    فكانت «نقطة الصفر» لكل شركة تقيس شيئاً لا يقيسه أي رقمٍ آخر في التطبيق."""
    from sqlalchemy import select, func
    from app.models.transaction import Transaction, TransactionType, Dividend
    from app.models.portfolio import Holding

    dividends = float((await db.execute(
        select(func.coalesce(func.sum(Dividend.received_amount), 0))
        .where(Dividend.company_id == company_id)
    )).scalar() or 0)

    txs = (await db.execute(
        select(Transaction).where(Transaction.company_id == company_id)
    )).scalars().all()
    sale_proceeds = sum(sale_harvest(t) for t in txs
                        if t.transaction_type == TransactionType.SELL)
    sale_gains = sum(g for g in (float(t.realized_gain or 0) for t in txs
                                 if t.transaction_type == TransactionType.SELL) if g > 0)

    h = (await db.execute(
        select(Holding).where(Holding.company_id == company_id)
    )).scalar_one_or_none()
    invested = float(h.invested_amount or 0) if h else 0.0
    last_price = float(h.last_price or 0) if h else 0.0
    bonus_shares = float(h.total_bonus_shares or 0) if h else 0.0

    total = dividends + sale_proceeds
    return {
        "dividends": round(dividends, 2),
        "sale_proceeds": round(sale_proceeds, 2),
        "sale_gains": round(sale_gains, 2),
        "total": round(total, 2),
        "invested": round(invested, 2),
        "remaining_to_recover": round(max(0.0, invested - total), 2),
        "recovered_pct": round(min(100.0, total / invested * 100), 1) if invested > 0 else None,
        # المنحة معروضة لا محتسَبة — قيمتها ضمن القيمة السوقية للحيازة.
        "bonus_shares": round(bonus_shares, 2),
        "bonus_market_value": round(bonus_shares * last_price, 2),
    }


async def compute_true_total_return_pct(db) -> float | None:
    """«عائد المحفظة» — وجهٌ نسبيّ للمعيار الأول: المحصول ÷ رأس المال المدفوع.
    وهو DPI المؤسسي بحرفه. مطابقٌ لـ«نمو العائد» و«الهدف الاستثماري» رقماً
    برقم لأن ثلاثتها تقرأ compute_production نفسها.

    والمقام موضعُ خطأٍ أُصلح سابقاً: كان «صافي الإيداعات» — أي كل ما أُودع في
    الحساب سواء استُثمر أم بقي نقداً خاملاً. فمن أودع ٣٢١ ألفاً واستثمر منها
    ٧٠ ألفاً كان محصوله يُقسم على ٣٢١ ألفاً، فيُقرأ ٢٪ بدل ٢٠٪. النقد الخامل
    لم يُنتج ولم يُطلب منه إنتاج، فوجوده في المقام يُعاقب المحفظة على سيولة
    لم تُوظَّف بعد."""
    p = await compute_production(db)
    if p["capital_base"] <= 0:
        return None
    return round(p["total"] / p["capital_base"] * 100, 2)


async def compute_return_breakdown(db) -> dict:
    """مكوّنات المحصول — كي يكون الرقم قابلاً للمراجعة لا صندوقاً مغلقاً.
    قشرةٌ رقيقة فوق compute_production فلا تتباعد المكوّنات عن مجموعها أبداً."""
    p = await compute_production(db)
    return {
        "realized_profit": p["realized_profit"],
        "sale_gains": p["sale_gains"],
        "bonus_market_value": p["bonus_market_value"],
        "bonus_at_grant": p["bonus_at_grant"],
        # نسبة كل مكوّن من رأس المال المدفوع — تفصيل «عائد المحفظة» الذي
        # كان رقماً واحداً مبهماً لا يُعرف ممّ تكوّن.
        "pct_dividends": round(p["dividends"] / p["capital_base"] * 100, 2) if p["capital_base"] else None,
        "pct_sale": round(p["sale_proceeds"] / p["capital_base"] * 100, 2) if p["capital_base"] else None,
        "pct_bonus": round(p["bonus_value"] / p["capital_base"] * 100, 2) if p["capital_base"] else None,
        "dividends": p["dividends"],
        # حصيلة البيع كاملةً (الرابحة) — هي الداخلة في المحصول.
        "sale_proceeds": p["sale_proceeds"],
        # الربح المحقّق منها — للمراجعة فقط، ليس مكوّناً.
        "realized_gains": p["realized_gains"],
        "bonus_value": p["bonus_value"],
        "total_profit": p["total"],
        "capital_base": p["capital_base"],
        "capital_base_source": "رأس المال المدفوع التراكمي",
    }


def bonus_share_value(tx, fallback_price) -> float:
    """قيمة أسهم منحةٍ واحدة — **بسعر يوم المنح إن كان مسجَّلاً**، وإلا بالسعر
    الأخير كتقديرٍ اضطراري.

    لماذا يهمّ هذا التمييز: قيمة المنحة تدخل «العائد المحقّق»، وهو المقياس الذي
    استُثني منه الربح غير المحقّق تحديداً كي لا يتقلّب رقم الأداء مع السوق. فإذا
    قُيّمت المنحة بسعر اليوم صار جزءٌ من هذا الرقم «الثابت» متحرّكاً: في محفظةٍ
    حقيقية بلغت المنحة ٤٣٤١ من أصل ٧٤٠٨ — أي ٥٩٪ من الإنتاج — فنزولُ سعرٍ بـ١٠٪
    يُنقص «الإنتاج التراكمي» و«عائد المحفظة» بلا أن يبيع المالك سهماً واحداً.
    وذلك يهدم الغرض من المقياس.

    والسعر الصحيح اقتصادياً هو سعر لحظة المنح: يومَ مُنحت السهم مجاناً تلقّيت
    قيمةً تساوي سعره وقتها، وتلك هي الإنتاج. ما جرى للسعر بعدها ربحٌ/خسارة
    غير محقّقة على مركزك، ومكانها هناك لا هنا.

    تُقرأ من حقل price في عملية المنحة — كان يُخزَّن صفراً دائماً قبل ذلك."""
    grant_price = float(getattr(tx, "price", 0) or 0)
    price = grant_price if grant_price > 0 else float(fallback_price or 0)
    return float(getattr(tx, "quantity", 0) or 0) * price


def _as_dt(value):
    """توحيد أي تاريخ/وقت إلى datetime واعٍ بالتوقيت — الفرز الزمني يخلط صفوفاً
    قديمة بلا منطقة زمنية مع أخرى واعية، ومقارنتها مباشرةً تُسقط الطلب كاملاً."""
    from datetime import datetime as _dt, date as _d, timezone as _tz
    if value is None:
        return None
    if isinstance(value, _dt):
        return value if value.tzinfo else value.replace(tzinfo=_tz.utc)
    if isinstance(value, _d):
        return _dt(value.year, value.month, value.day, tzinfo=_tz.utc)
    return None


async def compute_reinvestment_pool(db, as_of=None) -> dict:
    """رصيد «إعادة الاستثمار» — **مقياس نقدٍ متاح للتوظيف، لا مقياس ربح**:
    حصيلة البيع الكلية + التوزيعات المستلمة، ناقصاً ما أُعيد توظيفه منه.

    ولماذا حصيلة البيع كاملةً لا ربحها المحقّق وحده: حين تبيع سهماً يدخل حسابك
    ثمنه كلّه، والشقّ الذي هو «رأس مالك العائد» قابلٌ لإعادة التوظيف تماماً كما
    الشقّ الرابح — النقد لا لون له. أما «العائد المحقّق» فمقياسٌ آخر تماماً
    (أداءٌ لا سيولة) ويأخذ الربح وحده بحق. الرقمان مختلفان لأنهما يجيبان على
    سؤالين مختلفين: «كم أنتجت محفظتي؟» و«كم أستطيع أن أوظّف الآن؟».

    ولا تدخله المنحة: أسهمٌ مجانية لا نقد قابل للإنفاق.

    ── لماذا صار الحساب زمنياً بدل جمعٍ وطرحٍ بسيط ──────────────────────────
    كان: الحوض = (توزيعات + أرباح بيع) − مجموع المشتريات الموسومة. والعلّة أن
    الوسم **تصنيفٌ لا قياس**: شراءٌ بـ١٥٠٢٠ يُوسَم «إعادة استثمار» يخصم ١٥٠٢٠
    كاملةً من حوضٍ لم يحمل يوماً إلا بضع مئات. فوسمٌ واحد خاطئ يدفع الناتج إلى
    سالبٍ عميق (−٧٤ ألفاً في محفظةٍ حقيقية)، ثم يُبتَر بـ max(0,…) فيظهر
    **صفراً أبدياً** بلا سبب مرئي — يُقرأ كأن الحساب «يبدأ اليوم» لا كأنه يعكس
    عمر المحفظة، ولا سبيل للمستخدم لمعرفة ما جرى.

    والصواب أن الشراء لا يستهلك من الحوض إلا ما كان فيه **لحظة تنفيذه**: لا
    يُنفَق ما لم يكن موجوداً. فتُرتَّب الأحداث زمنياً (توزيعة تُضيف · حصيلة بيع
    تُضيف · شراء موسوم يستهلك بحدّ الرصيد القائم)، فيبقى الحوض دائماً ≥ صفر
    بطبيعته لا بالبتر، ويحتفظ بكل ما دخل الحساب بعد آخر شراء موسوم.

    وتُعاد معه أرقام تشخيصية (tagged_total و ignored_excess) كي تستطيع الواجهة
    أن تُفسّر رصيداً منخفضاً بدل أن تعرض رقماً صامتاً يُشكَّك في صحّته."""
    from sqlalchemy import select
    from app.models.transaction import Transaction, TransactionType, Cash, Dividend

    cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    cash = float(cash_row.available_cash or 0) if cash_row else 0.0

    # التوزيعات من جدول Dividend نفسه — لا من مجموع الحيازات: هنا نحتاج تاريخ
    # كل توزيعة للترتيب الزمني، ولأن حيازةً مؤرشَفة أو مُصفّاة لا يصحّ أن تمحو
    # توزيعاتها التاريخية من الحوض.
    divs = (await db.execute(select(Dividend))).scalars().all()
    txs = (await db.execute(select(Transaction))).scalars().all()

    dividends_received = sum(float(d.received_amount or 0) for d in divs)
    # حصيلة البيع الرابحة — **نفس دالة sale_harvest** التي يقرأها المعيار
    # الأول. توحيد الشرط مقصود: الحوض جزءٌ من المحصول لا مصدرٌ مستقل، فلو
    # اختلف تعريف «البيع» بينهما لأمكن أن يتجاوز الجزءُ كلَّه.
    sale_proceeds = sum(sale_harvest(t)
                        for t in txs if t.transaction_type == TransactionType.SELL)
    # يبقى الربح المحقّق مُعاداً للعرض وحده (يُقارن به «العائد المحقّق»)، ولم
    # يعد داخلاً في حساب الحوض.
    realized_gains = sum(float(t.realized_gain or 0)
                         for t in txs if t.transaction_type == TransactionType.SELL and t.realized_gain)
    tagged_total = sum(float(t.total_amount or 0)
                       for t in txs
                       if t.transaction_type == TransactionType.BUY
                       and t.funding_source in ("REINVEST", "DIVIDEND", "PROFIT"))

    # ── الأحداث مرتّبة زمنياً ──────────────────────────────────────────────
    # المفتاح: (الوقت, أولوية). الإضافة قبل الاستهلاك عند تساوي الوقت تماماً،
    # فتوزيعةٌ وشراءٌ في اللحظة نفسها يعني منطقياً أن التوزيعة موّلت الشراء.
    events: list[tuple] = []
    for d in divs:
        amt = float(d.received_amount or 0)
        when = _as_dt(d.payment_date) or _as_dt(d.created_at)
        if amt and when:
            events.append((when, 0, amt, None))
    for t in txs:
        when = _as_dt(t.executed_at) or _as_dt(t.created_at)
        if not when:
            continue
        if t.transaction_type == TransactionType.SELL:
            # الحصيلة كاملةً للعمليات الرابحة — نفس شرط المعيار الأول.
            proceeds = sale_harvest(t)
            if proceeds > 0:
                events.append((when, 0, proceeds, None))
        elif (t.transaction_type == TransactionType.BUY
              and t.funding_source in ("REINVEST", "DIVIDEND", "PROFIT")):
            amt = float(t.total_amount or 0)
            if amt > 0:
                events.append((when, 1, -amt, t.id))
    # as_of: نافذةٌ تاريخية للتقارير — نفس المحرّك مقطوعاً عند تاريخ، لا حساباً
    # ثانياً يتباعد عنه. (تقرير الشهر الماضي يجب أن يقرأ ما كان صحيحاً وقتَه.)
    if as_of is not None:
        events = [e for e in events if e[0].date() <= as_of]
    events.sort(key=lambda e: (e[0], e[1]))

    pool_running = 0.0
    consumed = 0.0
    # سجلّ التشخيص: لكل شراءٍ موسوم، كم استُهلك منه فعلاً وكم تعذّر. الفائض
    # المتعذّر دليلٌ حسابي قاطع على وسمٍ خاطئ — لا يمكن أن يُموَّل شراءٌ من
    # حوضٍ لم يكن فيه المال يومَ نُفِّذ.
    per_tx: list[dict] = []
    for _when, _prio, delta, _tid in events:
        if delta >= 0:
            pool_running += delta
        else:
            take = min(pool_running, -delta)   # لا يُنفَق ما ليس موجوداً
            pool_running -= take
            consumed += take
            per_tx.append({"tx_id": _tid, "amount": round(-delta, 2),
                           "funded": round(take, 2), "excess": round(-delta - take, 2),
                           "pool_at_time": round(pool_running + take, 2),
                           "when": _when.date().isoformat()})

    # سقفٌ حاكم أخير: النقد المتاح فعلاً. لا يُقترح إنفاق ما ليس في الحساب.
    capped_by_cash = pool_running > cash
    pool = round(max(0.0, min(pool_running, cash)), 2)
    return {
        "dividends_received": round(dividends_received, 2),
        # مكوّن الحوض الثاني: حصيلة البيع الكلية.
        "sale_proceeds": round(sale_proceeds, 2),
        # الربح المحقّق — للعرض والمقارنة فقط، لا يدخل حساب الحوض.
        "realized_gains": round(realized_gains, 2),
        # ما استُهلك فعلاً من الحوض (لا مجموع المشتريات الموسومة).
        "already_reinvested": round(consumed, 2),
        "available_cash": round(cash, 2),
        "pool": pool,
        "capped_by_cash": capped_by_cash,
        # تشخيص: إجمالي المشتريات الموسومة، والفائض الذي تجاوز رصيد الحوض
        # وقتَه فتعذّر خصمه — مؤشّرٌ قويّ على وسمٍ خاطئ إن كان كبيراً.
        "tagged_total": round(tagged_total, 2),
        "ignored_excess": round(max(0.0, tagged_total - consumed), 2),
        "tagged_detail": per_tx,
    }


async def compute_portfolio_return(db) -> dict:
    cagr = await compute_cagr_pct(db)
    total_return = await compute_true_total_return_pct(db)
    return {
        "cagr_pct": cagr,
        "portfolio_return_pct": total_return,
        "return_breakdown": await compute_return_breakdown(db),
    }


async def compute_capital_recovery(db) -> dict | None:
    """نقطة الصفر على مستوى المحفظة: كم استُرِدَّ من رأس المال المدفوع.

    كانت هذه الدالة **تعريفاً خامساً متبايناً للإنتاج**، وهو بالضبط ما وُحّد
    `compute_production` لمنعه — فبقيت وحدها خارج التوحيد تحسب:
      • بلا حصيلة البيع أصلاً — أكبر مكوّنٍ في المحصول يسقط كلّه.
      • والمنحة **بسعر اليوم** لا بسعر يوم المنح، فيتحرّك رقمُ استردادٍ يُفترض
        أنه محصولٌ مقبوض مع تقلّب السوق.
      • ورقمها يغذّي درجة تقييم المحفظة ونصّها التحليلي، فكان التطبيق يقول عن
        المحفظة الواحدة شيئين متناقضين في صفحتين.

    فصارت الآن قشرةً فوق المصدر الواحد، ويستحيل أن تتباعد عنه.

    وتُعاد النسبة غير المبتورة أيضاً (`recovered_pct_uncapped`): بترُ المئة
    صامتاً يُخفي أن المحفظة تجاوزت نقطة التعادل — وهي أهمّ خبرٍ فيها."""
    p = await compute_production(db)
    invested = float(p["capital_base"])
    if invested <= 0:
        return None

    production = float(p["total"])
    pct = production / invested * 100
    return {
        "capital_recovered_pct": round(min(100.0, pct), 1),
        "recovered_pct_uncapped": round(pct, 1),
        "total_production": round(production, 2),
        "invested_capital": round(invested, 2),
        "remaining_to_recover": round(max(0.0, invested - production), 2),
    }
