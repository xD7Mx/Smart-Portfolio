import json
import os
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, extract
from app.core.database import get_db
from app.core.response import success_response
from app.core.auth import require_owner
from app.models.market import Goal
from app.models.portfolio import Portfolio, Holding
from app.models.transaction import Transaction, TransactionType, Dividend
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

router = APIRouter()

MILLION_TARGET = 1_000_000

# ── إعدادات الأهداف المدمجة: أهدافها وترتيبها يحرّرهما المالك ─────────────
# تعيش ملفّاً في مجلّد البيانات لا في الشيفرة: تبقى بعد تحديث الحزمة وبعد
# إعادة التشغيل، ولا تُمسّ أي جداول مالية.
_BUILTIN_PATH = ("/app/data/goals_builtin.json" if os.path.isdir("/app/data")
                 else os.path.join(os.getcwd(), "goals_builtin.json"))
_BUILTIN_DEFAULT_ORDER = ["million", "income", "growth"]


def _load_builtin_cfg() -> dict:
    try:
        with open(_BUILTIN_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    order = [k for k in (cfg.get("order") or []) if k in _BUILTIN_DEFAULT_ORDER]
    for k in _BUILTIN_DEFAULT_ORDER:
        if k not in order:
            order.append(k)
    return {
        "million_target": float(cfg["million_target"]) if cfg.get("million_target") else None,
        "income_target": float(cfg["income_target"]) if cfg.get("income_target") else None,
        "growth_target_pct": float(cfg["growth_target_pct"]) if cfg.get("growth_target_pct") else None,
        "order": order,
    }

INCOME_BASE_YEAR = 2026
INCOME_BASE_TARGET = 20_000
INCOME_YEARLY_STEP = 10_000
INCOME_CAP_YEAR = 2030


def _income_target_for_year(year: int) -> float:
    """20,000 in 2026, +10,000 each year, capped at 2030's level (60,000)."""
    capped_year = min(year, INCOME_CAP_YEAR)
    steps = max(0, capped_year - INCOME_BASE_YEAR)
    return INCOME_BASE_TARGET + steps * INCOME_YEARLY_STEP


async def _get_portfolio(db: AsyncSession) -> Portfolio:
    p = (await db.execute(select(Portfolio).limit(1))).scalar_one_or_none()
    if not p:
        p = Portfolio(name="My Portfolio")
        db.add(p)
        await db.commit()
        await db.refresh(p)
    return p


async def _total_wealth(db: AsyncSession) -> float:
    from app.api.v1.endpoints.portfolio import _get_holdings
    from app.api.v1.endpoints.transactions import _get_cash
    holdings = await _get_holdings(db)
    market_value = sum(float(h.market_value or 0) for h in holdings)
    cash = await _get_cash(db)
    return market_value + float(cash.available_cash or 0)


async def _year_income(db: AsyncSession, year: int) -> dict:
    """Real income generated in a calendar year:
    - dividends: every Dividend record (cash or historically reinvested)
      paid this year, read from the Dividend table itself rather than
      scanning Transaction rows by type — this stays correct regardless of
      whether the money was taken as cash or immediately used to buy shares
      (a BUY tagged funding_source=DIVIDEND doesn't add anything here; the
      Dividend row from the original DIVIDEND transaction already counted it).
    - liquidation ('تصفية'): **ربح البيع وحده** لا حصيلته. رأس المال العائد
      ليس عائداً بأي معنى، وإدخاله كان يُظهر عائد السنة أربعة أضعاف ما كُسب
      فعلاً (٩٬٩٣٠ بدل ٣٬٠٩٠ في ٢٠٢٦). وبيعٌ بخسارة لا يدخل أصلاً.
      والشراء الموسوم REINVEST لا يُضاف هنا ثانيةً — هو إنفاقٌ للمحصول لا
      محصولٌ جديد، ويُعرض منفصلاً في profit_reinvested.
    - bonus_value: القيمة السوقية لأسهم المنحة الممنوحة في تلك السنة —
      **معروضة لا محتسَبة** في total، فقيمتها ضمن القيمة السوقية للحيازة."""
    txs = (await db.execute(
        select(Transaction).where(extract("year", Transaction.executed_at) == year)
    )).scalars().all()

    divs = (await db.execute(
        select(Dividend).where(extract("year", Dividend.payment_date) == year)
    )).scalars().all()
    dividends = sum(float(d.received_amount or 0) for d in divs)

    # ربح البيع لا حصيلته — نفس تعريف «صافي الربح» في باند الثروة، فلا
    # يتباعد رقمان يحملان اسم العائد.
    from app.services.portfolio_return import sale_profit
    liquidation = sum(
        sale_profit(t) for t in txs
        if t.transaction_type == TransactionType.SELL
    )
    # Not part of "total" (already counted at the original SELL) — shown
    # separately so the income figure makes clear how much of it didn't
    # stay as idle cash but was put back to work in the market this year.
    profit_reinvested = sum(
        float(t.total_amount or 0) for t in txs
        if t.transaction_type == TransactionType.BUY
        and t.funding_source in ("REINVEST", "DIVIDEND", "PROFIT")
    )

    bonus_txs = [t for t in txs if t.transaction_type == TransactionType.BONUS]
    bonus_value = 0.0
    if bonus_txs:
        from app.services.portfolio_return import bonus_share_value
        holdings = {h.company_id: h for h in (await db.execute(select(Holding))).scalars().all()}
        for t in bonus_txs:
            h = holdings.get(t.company_id)
            bonus_value += bonus_share_value(t, h.last_price if h else 0)

    # المنحة خارج المجموع: إصدارها يُرسمل احتياطياً ولا يُنشئ قيمة (الكمية
    # تزيد والسعر ينخفض بالتناسب)، وقيمتها محسوبةٌ أصلاً ضمن القيمة السوقية
    # للحيازة — فإدخالها هنا يعدّها مرّتين. تُعاد بعددها وقيمتها للعرض فقط.
    total = dividends + liquidation
    return {
        "year": year,
        "profit_reinvested": profit_reinvested,
        "dividends": dividends,
        "liquidation": liquidation,
        "bonus_value": bonus_value,
        "total": total,
    }

class GoalCreate(BaseModel):
    goal_name: str
    target_value: float
    target_type: str = "AMOUNT"  # "AMOUNT" (SAR) or "PERCENT" (return %)
    deadline: Optional[datetime] = None

    # هدفٌ بلا اسم أو بهدفٍ سالب كان يُقبل ويُخزَّن، فيظهر شريطٌ بلا عنوان
    # ونسبةٌ سالبة لا معنى لها. الرفض عند الباب أنظف من علاجٍ في العرض.
    @field_validator("goal_name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("اسم الهدف مطلوب.")
        return v[:120]

    @field_validator("target_value")
    @classmethod
    def _target(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError("قيمة الهدف يجب أن تكون أكبر من صفر.")
        if v > 1e12:
            raise ValueError("قيمة الهدف أكبر من الحدّ المعقول.")
        return v

@router.get("")
async def get_goals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal))
    goals = result.scalars().all()
    return success_response(data=[{"id": g.id, "name": g.goal_name, "target": float(g.target_value), "target_type": g.target_type or "AMOUNT", "current": float(g.current_value or 0), "pct": float(g.completion_percentage or 0)} for g in goals])

@router.post("")
async def add_goal(data: GoalCreate, db: AsyncSession = Depends(get_db)):
    # Goal.portfolio_id defaults to 1 — on a brand-new database that row
    # doesn't exist yet, so bootstrap it here (same pattern used by the
    # cash/transaction endpoints) instead of failing with a raw FK error.
    portfolio = (await db.execute(select(Portfolio).limit(1))).scalar_one_or_none()
    if not portfolio:
        portfolio = Portfolio(name="My Portfolio")
        db.add(portfolio)
        await db.flush()
    goal = Goal(**data.model_dump(), portfolio_id=portfolio.id)
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return success_response(data={"id": goal.id}, message="Goal created.")

@router.get("/progress")
async def get_goals_progress(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal))
    goals = result.scalars().all()
    return success_response(data=[{
        "id": g.id, "name": g.goal_name,
        "current_value": float(g.current_value or 0), "target_value": float(g.target_value),
        "target_type": g.target_type or "AMOUNT",
        "pct": float(g.completion_percentage or 0),
        "deadline": g.deadline.isoformat() if g.deadline else None,
    } for g in goals])

@router.patch("/{goal_id}")
async def update_goal(goal_id: int, current_value: float, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Goal not found.")
    goal.current_value = current_value
    if goal.target_value > 0:
        goal.completion_percentage = min(current_value / float(goal.target_value) * 100, 100)
    await db.commit()
    return success_response(message="Goal updated.")

@router.delete("/{goal_id}")
async def delete_goal(goal_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Goal not found.")
    await db.delete(goal)
    await db.commit()
    return success_response(message="Goal deleted.")


@router.get("/builtin-config")
async def get_builtin_config():
    """أهداف الأشرطة الثلاثة وترتيبها كما ضبطها المالك."""
    return success_response(data=_load_builtin_cfg())


@router.post("/builtin-config")
async def save_builtin_config(payload: dict, _: None = Depends(require_owner)):
    """يحفظ الأهداف والترتيب. القيمة الفارغة تعني: عُد إلى الافتراضي."""
    cur = _load_builtin_cfg()
    data = {
        "million_target": payload.get("million_target", cur["million_target"]),
        "income_target": payload.get("income_target", cur["income_target"]),
        "growth_target_pct": payload.get("growth_target_pct", cur["growth_target_pct"]),
        "order": payload.get("order", cur["order"]),
    }
    try:
        os.makedirs(os.path.dirname(_BUILTIN_PATH), exist_ok=True)
        with open(_BUILTIN_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger_warn = getattr(__import__("loguru").logger, "warning", None)
        if logger_warn:
            logger_warn(f"save_builtin_config failed: {e}")
        return success_response(data=_load_builtin_cfg(), message="تعذّر حفظ الأهداف.")
    return success_response(data=_load_builtin_cfg(), message="تم حفظ الأهداف.")


@router.get("/builtin")
async def get_builtin_goals(db: AsyncSession = Depends(get_db)):
    """The two system-tracked goals (auto-computed, not user-editable):
    total wealth toward 1,000,000, and this year's real income toward an
    automatically-escalating yearly target (20,000 in 2026, +10,000/year)."""
    wealth = await _total_wealth(db)
    year = datetime.utcnow().year
    income = await _year_income(db, year)
    cfg = _load_builtin_cfg()
    # ── «عائد المحفظة» = **صافي الربح كاملاً** ──────────────────────────
    # قرار المالك: رقمٌ واحد موحّد في كل موضع — باند الثروة مبلغاً، والمؤشرات
    # نسبةً، والهدف شريطاً. وهو الثروة − رأس مال المشروع، فيشمل الربح غير
    # المحقّق أيضاً لا التوزيعات وربح البيع وحدهما.
    from app.services.portfolio_return import compute_net_profit
    net = await compute_net_profit(db)
    net_profit = net.get("net_profit")
    million_target = cfg["million_target"] or MILLION_TARGET
    target_income = cfg["income_target"] or _income_target_for_year(year)

    return success_response(data={
        "million": {
            "current": wealth,
            "target": million_target,
            "pct": min(100, wealth / million_target * 100) if million_target else 0,
        },
        "income": {
            "year": year,
            "current": net_profit if net_profit is not None else income["total"],
            "target": target_income,
            "pct": (min(100, (net_profit if net_profit is not None else income["total"])
                        / target_income * 100) if target_income else 0),
            # التفصيل السنوي يبقى مرفقاً للاطّلاع، وليس هو الرقم المعروض.
            "breakdown": income,
            "year_income": income["total"],
        },
        "config": cfg,
    })


@router.get("/income-history")
async def get_income_history(db: AsyncSession = Depends(get_db)):
    """Year-by-year breakdown of the real income goal, for every year that
    has at least one relevant transaction, plus the current year even if
    still empty."""
    years_rows = (await db.execute(
        select(extract("year", Transaction.executed_at)).distinct()
    )).scalars().all()
    years = {int(y) for y in years_rows if y is not None}
    years.add(datetime.utcnow().year)

    history = []
    for year in sorted(years):
        income = await _year_income(db, year)
        target_income = _income_target_for_year(year)
        history.append({
            **income,
            "target": target_income,
            "pct": min(100, income["total"] / target_income * 100) if target_income else 0,
        })
    return success_response(data=history)


@router.get("/income-timeline")
async def get_income_timeline(db: AsyncSession = Depends(get_db)):
    """Dated income events (نفس تعريف DPI: توزيعات + حصيلة تصفية رابحة) —
    كلٌّ بتاريخه الفعلي، كي يبني «نمو العائد» منحنًى تراكميًا
    قابلاً للتصفية بالفترات (أسبوع/شهر/٣أشهر/منذ التأسيس). لا يُستنتج من فارق
    القيمة السوقية. يُرفَق رأس المال المدفوع الحالي لحساب النسبة."""
    events: list[dict] = []

    for d in (await db.execute(select(Dividend))).scalars().all():
        amt = float(d.received_amount or 0)
        if amt and d.payment_date:
            events.append({"date": d.payment_date.isoformat()[:10], "amount": amt, "kind": "توزيع"})

    txs = (await db.execute(select(Transaction))).scalars().all()
    holdings = {h.company_id: h for h in (await db.execute(select(Holding))).scalars().all()}
    for t in txs:
        if not t.executed_at:
            continue
        dt = t.executed_at.isoformat()[:10]
        if t.transaction_type == TransactionType.SELL:
            # ══ الحصيلة لا الربح — تصحيح تباعُدٍ حقيقيّ ══
            # كان هنا `sale_profit` بتعليقٍ يزعم أنه «نفس تعريف عائد المحفظة
            # في كل مكان» — وهو عكس الواقع تماماً. المصدر الواحد
            # (`compute_production`) يقرأ `sale_harvest`: الحصيلة كاملةً متى
            # كانت رابحة، لأن المقياس DPI ويشمل عودة رأس المال عمداً.
            # فكان المفهوم الواحد يُعرض برقمين على الشاشة نفسها:
            #   «عائد المحفظة»  13.28٪   (789.93 + 9,139.80) ÷ 74,753.94
            #   «نمو العائد»     4.13٪   (789.93 + 2,299.56) ÷ 74,753.94
            # بفارق 6,840 ريالاً — وهو بالضبط ما يحذّر منه تعليق
            # `compute_production`: «نسخة ثانية من الحساب بدل قراءة المصدر».
            from app.services.portfolio_return import sale_harvest
            h_amt = sale_harvest(t)
            if h_amt:
                events.append({"date": dt, "amount": h_amt, "kind": "تصفية"})
        # المنحة **لا تُدرَج**: إصدارها يُرسمل احتياطياً ولا يُنشئ قيمة، وقيمتها
        # محسوبة أصلاً ضمن القيمة السوقية للحيازة. وإبقاؤها هنا بعد إخراجها من
        # المحرّك يجعل «نمو العائد» يرتفع فوق DPI تحت تعريفٍ واحد — وهو
        # التباعُد السابع في هذا التطبيق، وكلّها من علّةٍ واحدة: نسخة ثانية
        # من الحساب بدل قراءة المصدر.

    events.sort(key=lambda e: e["date"])

    # رأس المال المدفوع الحالي (لحساب النسبة % في الواجهة).
    holdings_all = (await db.execute(select(Holding))).scalars().all()
    # المقام هو **رأس المال المدفوع التراكمي** نفسه الذي يقسم عليه DPI، لا
    # تكلفة المراكز القائمة: تلك تنقص مع كل بيع، فتُعطي «نمو العائد» نسبةً
    # أعلى من DPI تحت تعريفٍ واحد. دالةٌ واحدة تخدم الرقمين.
    from app.services.portfolio_return import compute_paid_in_capital
    invested = await compute_paid_in_capital(db)

    return success_response(data={"events": events, "invested": invested})
