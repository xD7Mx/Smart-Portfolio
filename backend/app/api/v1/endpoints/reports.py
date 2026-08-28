from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from app.core.database import get_db
from app.core.response import success_response
from app.models.market import Report, ReportType

router = APIRouter()

_PERIOD_AR = {"DAILY": "يومي", "WEEKLY": "أسبوعي", "MONTHLY": "شهري", "ANNUAL": "سنوي", "QUARTERLY": "ربع سنوي"}


@router.get("")
async def get_reports(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).order_by(Report.generated_at.desc()).limit(30))
    items = result.scalars().all()
    return success_response(data=[{
        "id": r.id,
        "type": r.report_type.value if hasattr(r.report_type, "value") else r.report_type,
        "period": r.report_period,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
        "has_content": bool(r.summary),
    } for r in items])


@router.get("/{report_id}")
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")
    return success_response(data={
        "id": r.id,
        "type": r.report_type.value if hasattr(r.report_type, "value") else r.report_type,
        "period": r.report_period,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
        **(r.summary or {}),
    })


@router.delete("/{report_id}")
async def delete_report(report_id: int, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")
    await db.delete(r)
    await db.commit()
    return success_response(message="تم حذف التقرير.")


_PERIOD_DAYS = {"DAILY": 1, "WEEKLY": 7, "MONTHLY": 30, "QUARTERLY": 90, "ANNUAL": 365}


def _month_first(y: int, m: int):
    from datetime import date as _d
    return _d(y, m, 1)


def _period_anchors(today, rtype: str):
    """حدود الفترة التقويمية المغلقة: يعيد (نهاية آخر فترة مكتملة, نهاية التي
    قبلها) كتاريخين. فيصبح التقرير يمثّل فترةً مغلقة ثابتة — إعادة التوليد داخل
    الفترة تعطي نفس الأرقام، والتقارير تتّصل تلقائيًا فترةً بعد فترة."""
    from datetime import timedelta
    if rtype == "DAILY":
        return today - timedelta(days=1), today - timedelta(days=2)
    if rtype == "WEEKLY":
        # الأسبوع التداولي ينتهي الخميس (weekday()==3). نأخذ آخر خميس ≤ اليوم.
        offset = (today.weekday() - 3) % 7
        now_a = today - timedelta(days=offset)
        return now_a, now_a - timedelta(days=7)
    if rtype == "MONTHLY":
        cur = _month_first(today.year, today.month)
        now_a = cur - timedelta(days=1)                       # آخر يوم من الشهر السابق
        pm = _month_first(now_a.year, now_a.month)
        return now_a, pm - timedelta(days=1)                  # آخر يوم من الشهر الأسبق
    if rtype == "QUARTERLY":
        qm = ((today.month - 1) // 3) * 3 + 1
        cur = _month_first(today.year, qm)
        now_a = cur - timedelta(days=1)                       # نهاية الربع السابق
        pqm = qm - 3
        py = today.year
        if pqm <= 0:
            pqm += 12; py -= 1
        return now_a, _month_first(py, pqm) - timedelta(days=1)
    # ANNUAL
    now_a = _month_first(today.year, 1) - timedelta(days=1)   # ٣١ ديسمبر للسنة السابقة
    return now_a, _month_first(now_a.year, 1) - timedelta(days=1)


async def _true_total_return_at_dates(db, date_now, date_past,
                                      invested_now: float, invested_past: float,
                                      unreal_now: float, unreal_past: float):
    """«عائد المحفظة» مؤرَّخاً عند تاريخين (السابق › الحالي)، **بنفس تعريف
    portfolio_return.compute_true_total_return_pct حرفياً**: الإنتاج المحقّق
    (توزيعات + حصيلة البيع الرابحة + قيمة أسهم منحة) ÷ رأس المال المدفوع.

    كان هذا الحساب يخالف محرّك لوحة التحكم في أمرين معاً، فيظهر رقمان مختلفان
    تحت اسمٍ واحد في شاشتين:
      • المقام: كان «صافي الإيداعات» — يشمل النقد الخامل الذي لم يُستثمر. ثم
        صار تكلفة اللقطة اليومية، وهي تنقص مع كل بيع فتُخالف اللوحة من جديد.
        والمعتمد الآن compute_paid_in_capital نفسها بنافذةٍ تاريخية: رأس المال
        المدفوع التراكمي عند ذلك التاريخ — دالةٌ واحدة لا تعريفان.
      • البسط: كان يُضيف الربح غير المحقّق، فيتذبذب «العائد» مع السعر لحظياً
        بينما نفس البطاقة في لوحة التحكم لا تفعل.

    ويُعاد أيضاً عائدٌ ثانٍ «شامل السعر» (مع الربح غير المحقّق) — ليس للعرض،
    بل لمقارنة تاسي وحدها: مؤشر تاسي عائدُ سعرٍ صرف، فطرحه من عائدٍ لا يحتوي
    حركة السعر مقارنةٌ بين مقياسين مختلفين تُظهر تفوّقاً سلبياً وهمياً في سوق
    صاعدة. كلُّ صندوق يأخذ المقياس الذي يُقارن به بحق.

    تُعاد: (محقّق_الآن, محقّق_السابق, شامل_الآن, شامل_السابق)."""
    from app.models.transaction import Transaction, TransactionType, Dividend
    from app.models.portfolio import Holding

    txs = (await db.execute(select(Transaction))).scalars().all()
    divs = (await db.execute(select(Dividend))).scalars().all()
    def d_of(dt):
        return dt.date() if dt is not None else None

    def parts_asof(as_of):
        dividends = sum(float(x.received_amount or 0) for x in divs
                        if (d_of(x.payment_date) or d_of(x.created_at)) and
                        (d_of(x.payment_date) or d_of(x.created_at)) <= as_of)
        # ربح البيع الرابح — نفس دالة sale_profit المستعملة في
        # «العائد المحقّق» و«عائد المحفظة» و«نمو العائد» و«الهدف الاستثماري».
        from app.services.portfolio_return import sale_profit
        # تاريخ التنفيذ لا تاريخ الإدخال: صفقةٌ مؤرَّخة بالماضي أُدخلت اليوم
        # كانت تسقط من تقارير الفترة التي وقعت فيها فعلاً، ويختلف تأريخها عن
        # المحرّك والحوض اللذين يقرآن executed_at.
        def _when(t):
            return d_of(t.executed_at) or d_of(t.created_at)
        realized = sum(sale_profit(t) for t in txs
                       if t.transaction_type == TransactionType.SELL and _when(t) and _when(t) <= as_of)
        # المنحة خارج المحصول — إصدارها لا يُنشئ قيمة، وقيمتها محسوبة ضمن
        # القيمة السوقية للحيازة. إبقاؤها هنا بعد إخراجها من المحرّك كان
        # سيجعل التقرير يعرض رقماً تحت اسمٍ يعرضه غيرُه مختلفاً — وهو نمط
        # التباعُد نفسه الذي تكرّر في هذا التطبيق ستّ مرّات.
        return dividends + realized

    def pair(as_of, base, unrealized):
        if not base or base <= 0:
            return None, None
        produced = parts_asof(as_of)
        return produced / base * 100, (produced + unrealized) / base * 100

    r_now, f_now = pair(date_now, invested_now, unreal_now)
    r_past, f_past = pair(date_past, invested_past, unreal_past)
    return r_now, r_past, f_now, f_past


async def _return_growth_boxes(db: AsyncSession, report_type: str, weekly: dict | None) -> dict:
    """Three side-by-side «السابق › الحالي» boxes for the report, each derived
    from real data (daily PortfolioSnapshot series + TASI closes) — never faked:
      1. عائد المحفظة — **نفس الرقم الموحّد**: (الثروة − رأس مال المشروع) ÷
         تكلفة الحيازات، مؤرَّخاً عند كل تاريخ من اللقطة اليومية وسجلّ النقد.
      2. التفوّق على تاسي — عائد المحفظة شاملَ السعر ناقص عائد سعر تاسي، بالنقاط.
      3. نسبة السيولة النقدية — cash ÷ (market value + cash), shown neutral.
    Each box carries prev/now; a field is null when its history is too short,
    and the report renders «—» for it rather than inventing a number."""
    from datetime import timedelta, date as _date
    from app.models.portfolio import PortfolioSnapshot

    boxes = [
        {"key": "return",  "label": "عائد المحفظة",         "suffix": "%",    "prev": None, "now": None},
        {"key": "vs_tasi", "label": "التفوّق على تاسي",      "suffix": " نقطة", "prev": None, "now": None},
        # السيولة ليست خيراً أو شراً بذاتها (نطاق أمثل) → تُعرَض بلون محايد.
        {"key": "cash",    "label": "نسبة السيولة النقدية", "suffix": "%",    "prev": None, "now": None, "neutral": True},
    ]

    rows = list((await db.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(2000)
    )).scalars().all())
    # وضع التوحيد: تأتي لقطة لكل محفظة في اليوم الواحد — نجمعها في لقطة واحدة
    # مركّبة لكل تاريخ (جمع القيم العددية) كي يمثّل «باند الثروة» مجموع الكل.
    from app.core.portfolio_scope import is_aggregate
    if is_aggregate():
        from types import SimpleNamespace
        by_date: dict = {}
        for r in rows:
            a = by_date.get(r.snapshot_date)
            if a is None:
                a = SimpleNamespace(snapshot_date=r.snapshot_date, market_value=0.0,
                                    invested_amount=0.0, cash_balance=0.0, unrealized_profit=0.0)
                by_date[r.snapshot_date] = a
            a.market_value += float(r.market_value or 0)
            a.invested_amount += float(r.invested_amount or 0)
            a.cash_balance += float(r.cash_balance or 0)
            a.unrealized_profit += float(r.unrealized_profit or 0)
        rows = sorted(by_date.values(), key=lambda x: x.snapshot_date, reverse=True)
    if len(rows) < 2:
        return {"boxes": boxes}

    # حدود تقويمية مغلقة: «الحالي» = آخر لقطة ≤ نهاية آخر فترة مكتملة،
    # و«السابق» = آخر لقطة ≤ نهاية الفترة التي قبلها. فتُقاس فترة مغلقة ثابتة.
    now_a, prev_a = _period_anchors(_date.today(), report_type)
    latest = next((r for r in rows if r.snapshot_date <= now_a), None)
    past = next((r for r in rows if r.snapshot_date <= prev_a), None)
    inception = rows[-1]
    if latest is None or past is None or latest.snapshot_date == past.snapshot_date:
        # تاريخ أقصر من فترة كاملة بعد — نرجع للأحدث مقابل الأقدم المتاح كي لا
        # يظهر الجدول فارغًا في الأسابيع الأولى.
        latest = rows[0]
        past = rows[-1]
        if latest.snapshot_date == past.snapshot_date:
            return {"boxes": boxes}

    # 1) عائد المحفظة — الإنتاج المحقّق ÷ رأس المال المدفوع، مؤرَّخاً عند كل
    #    تاريخ من اللقطة اليومية المخزَّنة، بنفس تعريف محرّك لوحة التحكم تماماً
    #    فلا يختلف رقمٌ عن رقم تحت نفس الاسم في شاشتين.
    # المقام: رأس المال المدفوع التراكمي مؤرَّخاً — **نفس دالة لوحة التحكم**
    # بنافذةٍ تاريخية، لا تكلفةُ اللقطة القائمة وقتها. فتلك تنقص مع كل بيع،
    # فيرتفع عائد التقرير مرّتين عن سببٍ واحد ويخالف الرقم المعروض في اللوحة.
    from app.services.portfolio_return import compute_paid_in_capital
    base_now = await compute_paid_in_capital(db, as_of=latest.snapshot_date)
    base_past = await compute_paid_in_capital(db, as_of=past.snapshot_date)

    # ── عائد المحفظة مؤرَّخاً: الرقم الموحّد نفسه لا تعريفاً ثانياً ──────────
    # صافي الربح عند تاريخٍ = (القيمة السوقية + النقد) − صافي الضخّ حتى ذلك
    # التاريخ؛ ونسبته إلى تكلفة الحيازات وقتها. كل مدخلاته من اللقطة اليومية
    # وسجلّ النقد، فيطابق ما تراه اللوحة اليوم ويصحّ للأمس.
    from app.models.transaction import CashLedger, CashLedgerKind

    ledger_rows = (await db.execute(select(CashLedger))).scalars().all()

    def _contributed_asof(as_of):
        total = 0.0
        for e in ledger_rows:
            when = getattr(e, "created_at", None)
            d = when.date() if hasattr(when, "date") else when
            if d is None or d > as_of:
                continue
            amt = float(e.amount or 0)
            total += amt if e.kind == CashLedgerKind.DEPOSIT else -amt
        return total

    def _return_at(snap):
        cost = float(snap.invested_amount or 0)
        if cost <= 0:
            return None
        contributed = _contributed_asof(snap.snapshot_date)
        if contributed <= 0:
            return None
        wealth = float(snap.market_value or 0) + float(snap.cash_balance or 0)
        return round((wealth - contributed) / cost * 100, 2)

    r_now, r_past = _return_at(latest), _return_at(past)
    if r_now is not None and r_past is not None:
        boxes[0]["now"] = r_now
        boxes[0]["prev"] = r_past

    # العائد شامل السعر يبقى محسوباً — لمقارنة تاسي وحدها (مؤشرها عائد سعر).
    _ttr_now, _ttr_past, full_now, full_past = await _true_total_return_at_dates(
        db, latest.snapshot_date, past.snapshot_date,
        base_now, base_past,
        float(latest.unrealized_profit or 0), float(past.unrealized_profit or 0))

    # 2) outperformance vs TASI — portfolio total return minus the TASI price
    #    return, both measured cumulatively from inception, at each date.
    try:
        from app.services.market_data import market_service
        from sqlalchemy import func as _f
        from app.models.transaction import Transaction as _T
        _first = (await db.execute(select(_f.min(_T.executed_at)))).scalar()
        anchor_date = _first.date() if hasattr(_first, "date") else _first
        # المدى يتبع عمر المحفظة: «1y» كان يقصّ الأساس عند سنةٍ واحدة، فتُقارن
        # محفظةٌ أقدم بتاسي من نقطةٍ لم تكن قد بدأت عندها.
        _age_days = (latest.snapshot_date - anchor_date).days if anchor_date else 0
        _range = "5y" if _age_days > 700 else ("2y" if _age_days > 330 else "1y")
        hist = await market_service.get_history("^TASI.SR", _range)
        if hist and full_now is not None and full_past is not None and anchor_date:
            by_date = {p["date"]: p["close"] for p in hist if p.get("close")}
            dates = sorted(by_date.keys())
            def tasi_at(target: str):
                elig = [d for d in dates if d <= target]
                return by_date[elig[-1]] if elig else (by_date[dates[0]] if dates else None)
            # الأساس هو **تأسيس المحفظة** (أول صفقة) لا أقدم لقطة يومية: عائد
            # المحفظة تراكميٌّ منذ التأسيس، فقياسه على تاسي منذ بدء التسجيل
            # يقارن نافذتين مختلفتين — سنةً كاملة مقابل شهر — والفرق بينهما
            # يُقرأ «تفوّقاً» وهو أثر اختلاف المدى لا أثر الأداء.
            base = tasi_at(anchor_date.isoformat()) if anchor_date else None
            t_now = tasi_at(latest.snapshot_date.isoformat())
            t_past = tasi_at(past.snapshot_date.isoformat())
            _earliest = dates[0] if dates else None
            _covers = bool(_earliest) and _earliest <= anchor_date.isoformat()
            if base and t_now and t_past and base > 0 and _covers:
                tasi_cum_now = (t_now / base - 1) * 100
                tasi_cum_past = (t_past / base - 1) * 100
                # عائدٌ شامل السعر مقابل عائد سعر تاسي — مقياسان متكافئان.
                boxes[1]["now"] = round(full_now - tasi_cum_now, 2)
                boxes[1]["prev"] = round(full_past - tasi_cum_past, 2)
    except Exception:
        pass

    # 3) cash liquidity ratio = cash / (market value + cash)
    def cash_ratio(r):
        mv = float(r.market_value or 0)
        c = float(r.cash_balance or 0)
        total = mv + c
        return (c / total * 100) if total > 0 else None
    cr_now, cr_past = cash_ratio(latest), cash_ratio(past)
    if cr_now is not None and cr_past is not None:
        boxes[2]["now"] = round(cr_now, 1)
        boxes[2]["prev"] = round(cr_past, 1)

    # كل نوع يقيس طول فترته الثابت (weekly=7 · monthly=30 · quarter=90 ·
    # annual=365) منتهيةً بتاريخ التقرير — عبر «days» و«past» أعلاه. فالشهري
    # دائمًا ≈ شهر والأسبوعي ≈ أسبوع. توليد تقريرٍ واحد لكل فترة (أسبوعي كل
    # أسبوع…) يجعل السلسلة متّصلة طبيعيًا؛ وتوليد أكثر من تقرير داخل الفترة
    # يُظهر نوافذ متداخلة (سلوك صحيح لا خطأ).
    return {"boxes": boxes}


@router.post("/generate")
async def generate_report(report_type: str = "WEEKLY", db: AsyncSession = Depends(get_db)):
    """Build a real report: portfolio snapshot + weighted metrics + a Gemini
    Arabic narrative, persisted so it stays in the archive."""
    report_type = (report_type or "WEEKLY").upper()
    try:
        rtype = ReportType[report_type]
    except KeyError:
        rtype = ReportType.WEEKLY

    from app.api.v1.endpoints.portfolio import _get_holdings, get_portfolio_metrics
    from app.api.v1.endpoints.ai import _portfolio_snapshot, _target_weights, _performance_context, _capital_recovery_context, _weekly_context
    from app.models.transaction import Cash
    from app.services import portfolio_analytics

    holdings = await _get_holdings(db)
    total_invested = sum(float(h.invested_amount or 0) for h in holdings)
    market_value = sum(float(h.market_value or 0) for h in holdings)
    dividends = sum(float(h.total_dividends_received or 0) for h in holdings)
    roi = ((market_value - total_invested) / total_invested * 100) if total_invested else 0

    positions = [{
        "name": h.company.company_name if h.company else "",
        "symbol": h.company.symbol if h.company else "",
        "shares": float(h.quantity or 0),
        "market_value": float(h.market_value or 0),
        "pnl": float(h.unrealized_profit or 0),
        "pnl_pct": float(h.unrealized_profit_pct or 0),
    } for h in holdings if float(h.quantity or 0) > 0]

    # التقرير الشامل نفسه (نفس المحرك خلف /ai/full-report) كأساس دائم
    # الظهور — لا يعتمد فقط على Gemini، ويُحفظ كنسخة ثابتة عند لحظة الإنشاء.
    hs, cash = await _portfolio_snapshot(db)
    targets = await _target_weights(db)
    performance = await _performance_context(db, hs)
    capital_recovery = await _capital_recovery_context(db)
    full = portfolio_analytics.report(hs, cash, {"market_value": market_value, "roi_pct": roi}, targets, performance, capital_recovery)
    # النصّ التحليلي **لا يُستدعى هنا**: هو موجودٌ أصلاً في قسم تحليل الذكاء،
    # وتكراره كان يعني انتظار ردّ المزوّد داخل طلب إنشاء التقرير — فيتأخّر
    # التقرير ثوانيَ لأجل نصٍّ يقرأه المالك في مكانٍ آخر. والمحتوى المحسوب
    # (portfolio_analytics.report) يبقى: خلاصةٌ من أرقامك أنت بلا شبكة.
    narrative = full.get("content")
    weekly = None
    try:
        weekly = await _weekly_context(db, hs, performance)
    except Exception:
        pass

    # Two report boxes (Model ① reduced to numbers, per the owner's request):
    #   • العائد الكلي منذ التأسيس (النسبي)
    #   • نمو العائد خلال فترة التقرير (يوم/أسبوع/شهر...)
    # Both computed from the REAL daily PortfolioSnapshot history — never faked.
    growth = await _return_growth_boxes(db, report_type, weekly)

    # الرقم الموحَّد في التطبيق — من نفس دالة بطاقة المقاييس لا من حسابٍ ثانٍ.
    # كان التقرير المؤرشَف يحمل roi_pct (عائد الربح غير المحقّق: 2.73%) بلا
    # صافي ربحٍ إطلاقاً، فيقرأ المالك في تقريره رقماً يخالف كل شاشةٍ أخرى
    # (7,462.9 و10.27%). المعيار التاسع: رقمٌ واحد في كل مكان.
    try:
        from app.services.portfolio_return import compute_net_profit
        _net = await compute_net_profit(db)
    except Exception:                                             # noqa: BLE001
        _net = {}

    # ── ثلاثةٌ يطلبها المالك في شبكة التقرير، ومصدرُها واحدٌ مع الشاشة ──
    # «إجمالي الثروة» و«نسبة السيولة» من `compute_net_profit` (السوقية+النقد)،
    # و«العائد المركّب» من **مسار المقاييس نفسه** لا من حسابٍ ثانٍ هنا: ذاك
    # يحترم تاريخ بداية المشروع وقاعدة التسعين يوماً، ولو حسبتُه هنا لأعطى
    # التقرير رقماً يخالف ما تحت عين المالك في شاشة المحفظة.
    _cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    _cash = float(_cash_row.available_cash or 0) if _cash_row else 0.0
    _wealth = market_value + _cash
    try:
        _m = (await get_portfolio_metrics(db)) or {}
        _cagr = (_m.get("data") or _m).get("cagr_pct")
    except Exception:                                             # noqa: BLE001
        _cagr = None

    content = {
        "content": narrative,
        "overall_score": full.get("overall_score"),
        "metrics": {
            "total_invested": total_invested,
            "market_value": market_value,
            "wealth": round(_wealth, 2),
            "available_cash": round(_cash, 2),
            # نسبة ما لم يدخل السوق بعد من الثروة — لا من رأس المال.
            "cash_pct": round(_cash / _wealth * 100, 2) if _wealth else None,
            "cagr_pct": _cagr,
            "unrealized_pnl": market_value - total_invested,
            # يبقى للتوافق مع التقارير القديمة، لكن اسمه يقول ما هو بالضبط.
            "roi_pct": round(roi, 2),
            "unrealized_roi_pct": round(roi, 2),
            "net_profit": _net.get("net_profit"),
            "capital_growth_pct": _net.get("capital_growth_pct"),
            "cost_basis": _net.get("cost_basis"),
            "dividends": dividends,
            "positions_count": len(positions),
        },
        "growth": growth,
        "positions": positions,
    }

    r = Report(report_type=rtype, report_period=f"{_PERIOD_AR.get(report_type, report_type)} — {date.today().isoformat()}", summary=content)
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return success_response(data={"id": r.id}, message="تم إنشاء التقرير.")
