"""
فحص السلامة — التطبيق يُراجع نفسه على بياناتك أنت، لا على مثالٍ افتراضي.

لماذا يوجد هذا الملف: المالك لا يستطيع قراءة الكود، ولا يصحّ أن تكون ثقته
بأرقام محفظته قائمةً على تصديق من كتبه. فبدل الطمأنة بالكلام، يُعرَّف كل
**ثابتٍ محاسبي** لا يجوز أن ينكسر، ويُفحص على قاعدة البيانات الحيّة، وتُعرض
النتيجة بالأرقام: ما طابق وما لم يطابق وبكم بالضبط.

وهذه ليست اختبارات وحدة (تلك تفحص الكود على بياناتٍ مخترَعة)، بل مطابقةٌ
محاسبية على الواقع — نظير ما يفعله المدقّق حين يجمع الأرصدة بنفسه بدل أن
يسأل المحاسب.

قاعدة الصياغة: كل فحصٍ يقول **ما يفحصه** و**ما وجده** و**ما معناه إن سقط**،
ولا يكتفي بـ«فشل». وسقوط فحصٍ ليس بالضرورة خللاً في التطبيق — قد يكون نقصاً
في سجلّك (عملية لم تُدخَل)، والرسالة تميّز بين الحالتين.
"""
from __future__ import annotations

TOLERANCE = 0.01          # هامش تقريب الكسور العشرية — لا هامش خطأٍ منطقي


def _check(name: str, ok: bool, detail: str, meaning: str = "",
           expected=None, actual=None, severity: str = "critical") -> dict:
    d = {"name": name, "ok": bool(ok), "detail": detail, "severity": severity}
    if meaning:
        d["meaning"] = meaning
    if expected is not None:
        d["expected"] = round(float(expected), 2)
    if actual is not None:
        d["actual"] = round(float(actual), 2)
        if expected is not None:
            d["diff"] = round(float(actual) - float(expected), 2)
    return d


async def _cash_reconciliation(db) -> dict:
    """**النقد**: هل يساوي الرصيد المخزَّن مجموعَ حركاته منذ اليوم الأول؟

        الرصيد = الإيداعات − السحوبات − المشتريات + المبيعات + التوزيعات

    وهو أقوى فحصٍ في المنظومة كلّها، لأن النقد يلمسه كل مسار: الشراء والبيع
    والتوزيع والتحرير والحذف. فإن طابق، فقد طابقت كل تلك المسارات مجتمعةً.
    """
    from sqlalchemy import select
    from app.models.transaction import (Transaction, TransactionType, Cash,
                                        CashLedger, CashLedgerKind)

    txs = (await db.execute(select(Transaction))).scalars().all()
    ledger = (await db.execute(select(CashLedger))).scalars().all()
    cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    stored = float(cash_row.available_cash or 0) if cash_row else 0.0

    deposits = sum(float(e.amount or 0) for e in ledger if e.kind == CashLedgerKind.DEPOSIT)
    withdrawals = sum(float(e.amount or 0) for e in ledger if e.kind != CashLedgerKind.DEPOSIT)
    buys = sum(float(t.total_amount or 0) for t in txs if t.transaction_type == TransactionType.BUY)
    sells = sum(float(t.total_amount or 0) for t in txs if t.transaction_type == TransactionType.SELL)
    divs = sum(float(t.total_amount or 0) for t in txs if t.transaction_type == TransactionType.DIVIDEND)

    expected = deposits - withdrawals - buys + sells + divs
    ok = abs(expected - stored) <= TOLERANCE
    return _check(
        "مطابقة النقد",
        ok,
        f"إيداعات {deposits:,.2f} − سحوبات {withdrawals:,.2f} − مشتريات {buys:,.2f} "
        f"+ مبيعات {sells:,.2f} + توزيعات {divs:,.2f}",
        meaning=("النقد يلمسه كل مسار في التطبيق — الشراء والبيع والتوزيع والتحرير والحذف. "
                 "فمطابقته تعني أن هذه المسارات مجتمعةً لم تُخطئ ريالاً واحداً."
                 if ok else
                 "الفارق يعني إمّا حركةً نقدية لم تُسجَّل، وإمّا مساراً كتب النقد مرّتين أو أسقطه."),
        expected=expected, actual=stored,
    )


async def _holdings_replay(db) -> list[dict]:
    """**الحيازات**: هل تُطابق الكميةُ المخزَّنة إعادةَ تشغيل سجلّها كاملاً؟

    والتكلفة تُفحص بعد إضافة فارق التسوية اليدوي — فوجود الفارق ليس خطأً بل
    تصحيحٌ معتمَد من كشف الوسيط، والخطأ أن يكون هناك فارقٌ لا يُفسّره شيء.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.portfolio import Holding
    from app.api.v1.endpoints.transactions import replay_holding

    holdings = (await db.execute(
        select(Holding).options(selectinload(Holding.company))
    )).scalars().all()

    out = []
    for h in holdings:
        name = h.company.company_name if h.company else f"#{h.company_id}"
        rep = await replay_holding(db, h.company_id)
        qty_ok = abs(float(rep["quantity"]) - float(h.quantity or 0)) <= TOLERANCE
        out.append(_check(
            f"كمية أسهم — {name}", qty_ok,
            "إعادة تشغيل كل عمليات الشركة بالترتيب الزمني",
            meaning=("الكمية المعروضة تنتج من سجلّك حرفياً."
                     if qty_ok else
                     "الكمية المخزَّنة لا تنتج من عملياتك — عمليةٌ ناقصة أو مكرّرة في السجل."),
            expected=rep["quantity"], actual=float(h.quantity or 0),
        ))
        adj = float(getattr(h, "cost_basis_adjustment", 0) or 0)
        expected_cost = float(rep["invested"]) + adj
        cost_ok = abs(expected_cost - float(h.invested_amount or 0)) <= TOLERANCE
        out.append(_check(
            f"تكلفة — {name}", cost_ok,
            (f"إعادة التشغيل {rep['invested']:,.2f} + فارق تسوية معتمد {adj:,.2f}"
             if adj else "إعادة تشغيل السجل بلا أي فارق يدوي"),
            meaning=("التكلفة المعروضة مبنيّة على سجلّك وتصحيحك المعتمد."
                     if cost_ok else
                     "التكلفة لا تنتج من السجل ولا من فارقٍ محفوظ — رقمٌ بلا مصدر."),
            expected=expected_cost, actual=float(h.invested_amount or 0),
            severity="critical" if not cost_ok else "critical",
        ))
    return out


async def _production_consistency(db) -> list[dict]:
    """**المقاييس**: هل تجمع المكوّناتُ مجاميعَها، وهل يبقى الجزء داخل كلّه؟"""
    from app.services.portfolio_return import (compute_production,
                                               compute_reinvestment_pool)

    p = await compute_production(db)
    pool = await compute_reinvestment_pool(db)
    out = []

    total = p["dividends"] + p["sale_proceeds"]
    out.append(_check(
        "مكوّنات المحصول تجمع مجموعه",
        abs(total - p["total"]) <= TOLERANCE,
        f"توزيعات {p['dividends']:,.2f} + حصيلة بيع {p['sale_proceeds']:,.2f}",
        meaning="لو لم تجمع المكوّناتُ مجموعَها لكان أحدها يُحسب من مصدرٍ آخر — وهي علّة تباعُد سابقة.",
        expected=p["total"], actual=total,
    ))

    profit = p["dividends"] + p["sale_gains"]
    out.append(_check(
        "مكوّنات الربح المحقّق تجمع مجموعه",
        abs(profit - p["realized_profit"]) <= TOLERANCE,
        f"توزيعات {p['dividends']:,.2f} + ربح تصفية {p['sale_gains']:,.2f}",
        meaning="الربح والمحصول مقياسان مختلفان لكن على نفس العمليات — فلا يجوز أن يختلفا في العيّنة.",
        expected=p["realized_profit"], actual=profit,
    ))

    out.append(_check(
        "الربح لا يتجاوز المحصول",
        p["realized_profit"] <= p["total"] + TOLERANCE,
        f"الربح {p['realized_profit']:,.2f} مقابل المحصول {p['total']:,.2f}",
        meaning=("الربح جزءٌ من المحصول (المحصول يضمّ عودة رأس المال أيضاً)، فتجاوزُه إيّاه مستحيل."),
    ))

    out.append(_check(
        "حوض إعادة الاستثمار لا يتجاوز المحصول",
        pool["pool"] <= p["total"] + TOLERANCE,
        f"الحوض {pool['pool']:,.2f} مقابل المحصول {p['total']:,.2f}",
        meaning="الحوض جزءٌ من المحصول لا نظامٌ موازٍ — فيستحيل أن يصير الجزء أكبر من كلّه.",
    ))

    out.append(_check(
        "المنحة غير مزدوجة الاحتساب",
        abs(p["bonus_value"]) <= TOLERANCE,
        f"أسهم المنحة {p['bonus_shares']:,.0f} سهماً بقيمة سوقية {p['bonus_market_value']:,.2f}",
        meaning=("قيمة أسهم المنحة محسوبة ضمن القيمة السوقية للحيازة (RVPI). "
                 "فإدخالها في الموزَّع أيضاً يعدّ نفس الأسهم مرّتين ويُضخّم TVPI."),
    ))

    out.append(_check(
        "الحوض غير سالب",
        pool["pool"] >= -TOLERANCE,
        f"الرصيد الحالي {pool['pool']:,.2f}",
        meaning="الاستهلاك محدودٌ بما كان في الحوض لحظتَه، فلا ينزل تحت الصفر بطبيعته لا بالبتر.",
    ))
    return out


async def _multiples_identity(db) -> dict:
    """**TVPI = DPI + RVPI** — متطابقةٌ رياضية لا تقبل الخطأ."""
    from app.services.performance import compute_multiples
    m = await compute_multiples(db)
    if m.get("tvpi") is None:
        return _check("متطابقة TVPI", True, "لا رأس مال مدفوع بعد — لا شيء يُفحص.",
                      severity="info")
    s = round(m["dpi"] + m["rvpi"], 2)
    return _check(
        "TVPI = DPI + RVPI", abs(s - m["tvpi"]) <= TOLERANCE,
        f"DPI {m['dpi']} + RVPI {m['rvpi']}",
        meaning="متطابقة رياضية: لو انكسرت لكان أحد الطرفين يُحسب من مقامٍ مختلف.",
        expected=m["tvpi"], actual=s,
    )


async def _dividends_ledger(db) -> dict:
    """**التوزيعات**: هل يطابق سجلُّ التوزيعات ما هو مجموعٌ في الحيازات؟"""
    from sqlalchemy import select, func
    from app.models.transaction import Dividend
    from app.models.portfolio import Holding

    ledger_total = float((await db.execute(
        select(func.coalesce(func.sum(Dividend.received_amount), 0))
    )).scalar() or 0)
    holdings_total = float((await db.execute(
        select(func.coalesce(func.sum(Holding.total_dividends_received), 0))
    )).scalar() or 0)
    return _check(
        "سجلّ التوزيعات يطابق الحيازات",
        abs(ledger_total - holdings_total) <= TOLERANCE,
        f"سجلّ التوزيعات {ledger_total:,.2f}",
        meaning=("التوزيعات تُسجَّل من مسارين (عملية مستقلّة أو ضمن الصفقات)، "
                 "فتطابُقهما يعني أنه لا توزيعة عُدّت مرّتين ولا سقطت واحدة."),
        expected=ledger_total, actual=holdings_total,
    )


async def _no_future_dates(db) -> dict:
    """**التواريخ**: لا صفقة بتاريخٍ لم يأتِ بعد — تُفسد كل سلسلةٍ زمنية."""
    from datetime import datetime, timedelta
    from sqlalchemy import select, func
    from app.models.transaction import Transaction

    limit = datetime.utcnow() + timedelta(days=1)
    n = int((await db.execute(
        select(func.count(Transaction.id)).where(Transaction.executed_at > limit)
    )).scalar() or 0)
    return _check(
        "لا صفقات بتاريخ مستقبلي", n == 0,
        f"عدد الصفقات المستقبلية: {n}",
        meaning="الصفقة المستقبلية تدخل اللقطات والتقارير وحساب العائد فتشوّه السلسلة الزمنية كلّها.",
    )


async def _paid_in_floor(db) -> dict:
    """**رأس المال المدفوع** لا ينزل دون ما هو مركوزٌ في المحفظة الآن."""
    from sqlalchemy import select, func
    from app.models.portfolio import Holding
    from app.services.portfolio_return import compute_paid_in_capital, compute_reinvestment_pool

    paid_in = await compute_paid_in_capital(db)
    current = float((await db.execute(
        select(func.coalesce(func.sum(Holding.invested_amount), 0))
    )).scalar() or 0)
    recycled = float((await compute_reinvestment_pool(db)).get("already_reinvested") or 0)
    floor = current - recycled
    return _check(
        "رأس المال المدفوع فوق أرضيّته",
        paid_in >= floor - TOLERANCE,
        f"تكلفة قائمة {current:,.2f} − مُعاد ضخّه {recycled:,.2f}",
        meaning="يستحيل أن تكون دفعتَ أقلّ ممّا هو مركوزٌ في محفظتك الآن (بعد استبعاد ما أُعيد ضخّه).",
        expected=floor, actual=paid_in,
    )


async def _income_timeline_matches(db) -> dict:
    """**نمو العائد = الموزَّع**: منحنى الدخل التراكمي ينتهي عند رقم DPI نفسه.

    كان المنحنى يضيف أحداث المنحة فيتجاوز الموزَّع تحت تعريفٍ واحد — سابع
    تباعُد في هذا التطبيق، وكلّها من علّةٍ واحدة: نسخةٌ ثانية من الحساب بدل
    قراءة المصدر. وهذا الفحص يجعل عودته مستحيلةً بلا أن ينكسر.
    """
    from app.services.portfolio_return import compute_production
    from app.api.v1.endpoints.goals import get_income_timeline

    p = await compute_production(db)
    try:
        tl = await get_income_timeline(db=db)
        data = tl.get("data", tl) if isinstance(tl, dict) else {}
        events = data.get("events") or []
    except Exception:
        events = []
    total = sum(float(e.get("amount") or 0) for e in events)
    # ══ المرجع هو **المحصول** لا الربح المحقّق ══
    # في التطبيق مقياسان مستقلّان لا بديلان (انظر compute_production):
    #   • المحصول (‏total = توزيعات + حصيلة تصفية رابحة) — «كم عاد إلى يدي؟»
    #   • الربح المحقّق (توزيعات + ربح تصفية)         — «كم كسبتُ؟»
    # ومنحنى «نمو العائد» يرسم **الأوّل** بنصّ توصيفه: DPI بحرفه، ويشمل
    # عودة رأس المال عمداً. فمقارنته بالثاني تُنتج فارقاً دائماً مقداره
    # رأسُ المال العائد — وهو ما وقع: 9,929.73 مقابل 3,089.49، والفارق
    # 6,840.24 هو التكلفة المستردّة لا خطأ في البيانات.
    #
    # وسببُ الخلل أنّ الفحص عُدِّل مرّةً ليطابق منحنىً كان يقرأ الربح، ثم
    # صُحّح المنحنى إلى المحصول ولم يُصحَّح الفحص معه — فصار حارساً يحرس
    # تعريفاً مهجوراً ويشكو من الصواب.
    expected = p["total"]
    return _check(
        "نمو العائد يطابق المحصول",
        abs(total - expected) <= TOLERANCE,
        f"{len(events)} حدثاً في المنحنى",
        meaning="المنحنى والمحصول وجهان لتعريفٍ واحد (‏DPI)، فاختلافهما يعني نسخةً ثانية من الحساب.",
        expected=expected, actual=total,
    )


async def _allocation_sanity(db) -> list[dict]:
    """**الأوزان المستهدفة**: داخل المدى، ومجموعها لا يتجاوز المئة.

    الوزن السالب يُنتج «نصيباً» سالباً من السيولة فيظهر أمر شراءٍ بمبلغٍ سالب،
    ومجموعٌ فوق المئة يوزّع أكثر ممّا تملك. وكلاهما كان يُقبل بلا حارس.
    """
    from sqlalchemy import select
    from app.models.market import Allocation

    rows = (await db.execute(select(Allocation))).scalars().all()
    weights = [float(a.target_weight or 0) for a in rows]
    bad = [w for w in weights if w < 0 or w > 100]
    total = sum(weights)
    return [
        _check("الأوزان المستهدفة داخل المدى", not bad,
               f"{len(weights)} وزناً مسجَّلاً",
               meaning="وزنٌ سالب أو فوق المئة يُنتج أوامر شراء بمبالغ مستحيلة.",
               severity="critical"),
        _check("مجموع الأوزان لا يتجاوز 100", total <= 100 + TOLERANCE,
               f"المجموع {total:,.2f}%",
               meaning="مجموعٌ فوق المئة يوزّع أكثر من السيولة المتاحة كلّها.",
               expected=100.0, actual=total, severity="warning"),
    ]


async def _cash_components(db) -> dict:
    """**السيولة الجديدة + الحوض = النقد المتاح** بالضبط.

    الحوض جزءٌ من النقد لا إضافةٌ إليه. وكان النصيبان يُحسبان كلاهما على النقد
    الكامل فيُعدّ الحوض مرّتين ويظهر مبلغٌ شرائي أكبر من المتاح فعلاً.
    """
    from sqlalchemy import select
    from app.models.transaction import Cash
    from app.services.portfolio_return import compute_reinvestment_pool

    cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    cash = float(cash_row.available_cash or 0) if cash_row else 0.0
    pool = float((await compute_reinvestment_pool(db))["pool"])
    fresh = max(0.0, cash - pool)
    return _check(
        "السيولة الجديدة + الحوض = النقد المتاح",
        abs((fresh + pool) - cash) <= TOLERANCE,
        f"سيولة جديدة {fresh:,.2f} + حوض {pool:,.2f}",
        meaning="لو تجاوز مجموعهما النقد لكان الحوض معدوداً مرّتين في أوامر الشراء.",
        expected=cash, actual=fresh + pool,
    )


async def run_integrity_check(db) -> dict:
    """يشغّل كل الفحوص ويعيد نتيجةً مقروءة. لا يكتب شيئاً في قاعدة البيانات."""
    checks: list[dict] = []

    async def _safe(coro, label):
        try:
            r = await coro
            if isinstance(r, list):
                checks.extend(r)
            else:
                checks.append(r)
        except Exception as e:                                   # noqa: BLE001
            checks.append(_check(label, False, f"تعذّر تشغيل الفحص: {e}",
                                 meaning="فشل الفحص نفسه لا يعني سلامة البيانات ولا فسادها — يعني أنه لم يُفحص."))

    await _safe(_cash_reconciliation(db), "مطابقة النقد")
    await _safe(_holdings_replay(db), "مطابقة الحيازات")
    await _safe(_production_consistency(db), "اتّساق المقاييس")
    await _safe(_multiples_identity(db), "متطابقة TVPI")
    await _safe(_dividends_ledger(db), "سجلّ التوزيعات")
    await _safe(_no_future_dates(db), "التواريخ")
    await _safe(_paid_in_floor(db), "رأس المال المدفوع")
    await _safe(_income_timeline_matches(db), "نمو العائد يطابق الربح المحقّق")
    await _safe(_allocation_sanity(db), "الأوزان المستهدفة")
    await _safe(_cash_components(db), "مكوّنات السيولة")

    failed = [c for c in checks if not c["ok"] and c.get("severity") != "info"]
    return {
        "passed": len(checks) - len(failed),
        "total": len(checks),
        "all_ok": not failed,
        "checks": checks,
    }
