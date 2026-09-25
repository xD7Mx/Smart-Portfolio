from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger
from app.core.database import get_db
from app.core.response import success_response
from app.models.portfolio import Holding, Company

router = APIRouter()


def yahoo_symbol(symbol: str) -> str:
    """Saudi tickers (pure digits) map to Yahoo as e.g. 2222.SR."""
    s = (symbol or "").strip().upper()
    if s.isdigit() and not s.endswith(".SR"):
        return f"{s}.SR"
    return s


async def refresh_holdings_prices(db: AsyncSession, holdings) -> None:
    """Pull live prices (served from the 15-min cache — no quota abuse) and
    recompute market_value / P&L for each holding, persisting to the DB.
    This is THE link between price providers and the portfolio."""
    from app.services.market_data import market_service
    changed = False
    for h in holdings:
        if not h.company:
            continue
        try:
            p = await market_service.get_price(yahoo_symbol(h.company.symbol))
            if p and p.get("price"):
                qty = float(h.quantity or 0)
                inv = float(h.invested_amount or 0)
                h.last_price = p["price"]
                h.market_value = qty * float(p["price"])
                h.unrealized_profit = float(h.market_value) - inv
                h.unrealized_profit_pct = ((float(h.market_value) - inv) / inv * 100) if inv else 0
                changed = True
        except Exception as e:
            logger.warning(f"price refresh failed for {h.company.symbol}: {e}")
    if changed:
        await db.commit()


def _effective_sharia(company):
    """Maqasid rating is authoritative; fall back to the stored status
    (which AI may have resolved) for symbols Maqasid doesn't cover."""
    from app.services import maqasid
    r = maqasid.rating(company.symbol) if company else None
    if r:
        return r.get("status"), r.get("purification")
    return (company.sharia_status if company else None), None


def _day_change(h: Holding) -> float | None:
    """تغيّر اليوم للسهم — بمصدرين لا مصدرٍ واحد.

    العلّة: كان يُقرأ من **مسح السوق الكامل** وحده. وذلك المسح يمرّ على كل
    تداول ويكتمل متأخراً، فيبقى «آخر سعر» بلا لونٍ دقائقَ بعد فتح التطبيق ثم
    يتلوّن فجأة — يبدو كأن البطاقة عالقة. وسعر السهم نفسه مخزَّنٌ لكل رمزٍ
    على حدة (`price:yahoo:{symbol}`) ويصل أبكر بكثير، لأنه يُجلب مع تحديث
    الحيازات لا مع مسح السوق.
    فنقرأ المخزَّن الفردي أوّلاً، ونُبقي مسح السوق احتياطياً — ولا نداء
    جديداً في الحالتين."""
    sym = h.company.symbol if h.company else None
    if not sym:
        return None
    try:
        from app.services import cache
        for key in (f"price:yahoo:{sym}", f"price:yahoo:{sym}.SR"):
            p = cache.get(key)
            v = getattr(p, "change_pct", None) if p is not None else None
            if v is None and isinstance(p, dict):
                v = p.get("change_pct")
            if isinstance(v, (int, float)):
                return float(v)
    except Exception:
        pass
    try:
        from app.services.market_movers import get_cached_market_movers
        stocks = (get_cached_market_movers() or {}).get("stocks") or {}
        v = stocks.get(sym)
        return float(v) if isinstance(v, (int, float)) else None
    except Exception:
        return None


def _serialize(h: Holding) -> dict:
    qty = float(h.quantity or 0)
    invested = float(h.invested_amount or 0)
    mv = float(h.market_value or 0)
    sharia, purif = _effective_sharia(h.company) if h.company else (None, None)
    return {
        "id": h.id,
        "company_id": h.company_id,
        "sort_order": int(h.sort_order or 0),
        # both naming conventions, so every page finds what it expects
        "quantity": qty,
        "total_shares": qty,
        "invested_amount": invested,
        "total_cost": invested,
        "market_value": mv,
        "current_value": mv,
        "average_cost": float(h.average_cost or 0),
        # فارق التسوية اليدوي — يُعرض كي لا يكون تصحيحٌ مخفيّ في التكلفة
        "cost_basis_adjustment": float(h.cost_basis_adjustment or 0),
        "last_price": float(h.last_price or 0),
        # تغيّر اليوم عن إغلاق أمس — من لقطة المحرّكين المخزَّنة نفسها التي
        # يقرأها فرز الأسهم: بلا نداء إضافي. وغيابه يعني «لا لون» لا صفراً،
        # فلا يُرسم أخضرُ ثباتٍ على سهمٍ لم تصل حركته بعد.
        "change_pct": _day_change(h),
        "unrealized_profit": float(h.unrealized_profit or 0),
        "unrealized_profit_pct": float(h.unrealized_profit_pct or 0),
        "reinvestment_shares": float(h.reinvestment_shares or 0),
        "total_bonus_shares": float(h.total_bonus_shares or 0),
        "total_dividends_received": float(h.total_dividends_received or 0),
        "profit_reinvested": float(h.profit_reinvested or 0),
        "company": {
            "id": h.company.id,
            "symbol": h.company.symbol,
            "name": h.company.company_name,
            "name_ar": h.company.company_name,
            "company_name": h.company.company_name,
            "sector": h.company.sector,
            "sharia_status": sharia,
            "purification": purif,
            "finance_score": float(h.company.finance_score or 0),
            "technical_score": float(h.company.technical_score or 0),
            "color": h.company.color,
            "logo_url": h.company.logo_url,
        } if h.company else None,
    }


@router.get("")
async def get_holdings(db: AsyncSession = Depends(get_db)):
    # Self-heal: companies added before holdings auto-creation get a zero
    # row — but ONLY companies with real evidence of belonging in the
    # portfolio (at least one real Transaction). This used to run for
    # EVERY company unconditionally, which silently resurrected ~200+
    # directory-only "ghost" rows (created by a since-removed logo-lookup
    # feature) into what looked like real zero-share portfolio positions
    # the moment this page was opened — the exact incident this guard now
    # prevents from ever happening again.
    from app.models.transaction import Transaction
    companies = (await db.execute(select(Company).where(Company.status != "ARCHIVED"))).scalars().all()
    have = set((await db.execute(select(Holding.company_id))).scalars().all())
    transacted = set((await db.execute(select(Transaction.company_id).distinct())).scalars().all())
    added = False
    for c in companies:
        if c.id not in have and c.id in transacted:
            db.add(Holding(company_id=c.id, quantity=0, average_cost=0, invested_amount=0, market_value=0))
            added = True
    if added:
        await db.commit()
    # ترتيب المالك أوّلاً. والصفر يعني «لم يُرتَّب بعد» فيُذيَّل بالمعرّف،
    # فلا تقفز شركة جديدة إلى الصدارة لمجرّد أن ترتيبها لم يُضبط.
    result = await db.execute(
        select(Holding).options(selectinload(Holding.company))
        .order_by(Holding.sort_order.asc(), Holding.id.asc())
    )
    holdings = [h for h in result.scalars().all()
                if h.company and h.company.status != "ARCHIVED"]
    await refresh_holdings_prices(db, holdings)
    return success_response(data=[_serialize(h) for h in holdings])


from pydantic import BaseModel
from typing import Optional


class OrderUpdate(BaseModel):
    """ترتيب الشركات كما يريده المالك — قائمة معرّفات بالترتيب المطلوب."""
    order: list[int]


@router.put("/order")
async def set_order(payload: OrderUpdate, db: AsyncSession = Depends(get_db)):
    """يُثبّت ترتيب العرض. لا يمسّ كميةً ولا تكلفةً ولا سجلّ عمليات.

    الترقيم يبدأ من واحد لا صفر: الصفر محجوز لمعنى «لم يُرتَّب»، ولو بدأ منه
    لالتبس أوّل صفٍّ مرتَّب بصفٍّ لم يُرتَّب قطّ.
    """
    rows = {h.company_id: h for h in (await db.execute(select(Holding))).scalars().all()}
    applied = 0
    for i, cid in enumerate(payload.order[:500], start=1):
        h = rows.get(cid)
        if h is not None:
            h.sort_order = i
            applied += 1
    await db.commit()
    # يُعاد عدد ما طُبّق: معرّفٌ غير موجود كان يُتجاهَل بصمت فتظنّ الواجهة أن
    # الترتيب كلّه حُفظ. والتجاهل نفسه صحيح (لا يُخترع صفّ)، لكن الصمت ليس.
    return success_response(data={"applied": applied, "received": len(payload.order)},
                            message="حُفظ الترتيب.")


class HoldingUpdate(BaseModel):
    quantity: Optional[float] = None
    average_cost: Optional[float] = None


@router.patch("/{company_id}")
async def update_holding(company_id: int, data: HoldingUpdate, db: AsyncSession = Depends(get_db)):
    """Direct correction of shares / average cost (e.g. migrating an existing
    portfolio in, or reconciling against the broker statement).

    invested_amount is qty × avg_cost. The correction is ALSO stored as a
    reconciliation delta against the ledger replay, because any later edit to
    a transaction rebuilds the holding from that replay and would otherwise
    silently wipe the correction out. Storing the difference — not the final
    figure — keeps future buys and sells moving the cost basis normally.
    """
    from app.api.v1.endpoints.transactions import replay_holding
    result = await db.execute(
        select(Holding).options(selectinload(Holding.company)).where(Holding.company_id == company_id)
    )
    h = result.scalar_one_or_none()
    if not h:
        h = Holding(company_id=company_id, quantity=0, average_cost=0, invested_amount=0, market_value=0)
        db.add(h)
    if data.quantity is not None:
        h.quantity = data.quantity
    if data.average_cost is not None:
        h.average_cost = data.average_cost
    qty = float(h.quantity or 0)
    avg = float(h.average_cost or 0)
    h.invested_amount = qty * avg
    replayed = await replay_holding(db, company_id)
    h.cost_basis_adjustment = round(qty * avg - float(replayed["invested"]), 6) if qty > 0 else 0
    lp = float(h.last_price or 0)
    h.market_value = qty * lp if lp else h.invested_amount
    inv = float(h.invested_amount or 0)
    h.unrealized_profit = float(h.market_value) - inv
    h.unrealized_profit_pct = ((float(h.market_value) - inv) / inv * 100) if inv else 0
    await db.commit()
    await db.refresh(h, ["company"])
    await refresh_holdings_prices(db, [h])
    return success_response(data=_serialize(h), message="Holding updated.")


class ReconcileItem(BaseModel):
    company_id: int
    quantity: float


class ReconcileRequest(BaseModel):
    items: list[ReconcileItem] = []
    cash: Optional[float] = None


@router.post("/reconcile")
async def reconcile(data: ReconcileRequest, db: AsyncSession = Depends(get_db)):
    """المطابقة مع كشف الوسيط (D483): المالك يُدخل ما في كشفه، والتطبيق يعرض
    الفرق لكل شركةٍ وللنقد. قراءةٌ محضة — لا يُصحَّح شيءٌ تلقائياً؛ التصحيح
    قرار المالك بعمليةٍ تُقيَّد في السجلّ. وتُعرض كمية إعادة التشغيل بجانب
    المخزَّنة كي يظهر إن كان الفرق من السجلّ نفسه أم من إدخالٍ ناقص."""
    from app.api.v1.endpoints.transactions import replay_holding
    from app.models.transaction import Cash
    TOL = 1e-6
    rows = []
    for it in data.items:
        h = (await db.execute(select(Holding).options(selectinload(Holding.company))
                              .where(Holding.company_id == it.company_id))).scalar_one_or_none()
        app_qty = float(h.quantity or 0) if h else 0.0
        rep = await replay_holding(db, it.company_id)
        diff = round(it.quantity - app_qty, 6)
        rows.append({
            "company_id": it.company_id,
            "symbol": h.company.symbol if h and h.company else None,
            "name": h.company.company_name if h and h.company else None,
            "broker": it.quantity, "app": app_qty, "ledger": float(rep["quantity"]),
            "diff": diff, "ok": abs(diff) <= TOL,
        })
    cash = None
    if data.cash is not None:
        c = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
        app_cash = float(c.available_cash or 0) if c else 0.0
        d = round(data.cash - app_cash, 2)
        cash = {"broker": data.cash, "app": round(app_cash, 2), "diff": d, "ok": abs(d) <= 0.01}
    ok = all(r["ok"] for r in rows) and (cash is None or cash["ok"])
    return success_response(data={"items": rows, "cash": cash, "ok": ok})


@router.get("/closed")
async def get_closed_positions(db: AsyncSession = Depends(get_db)):
    """الصفقات المغلقة (D480): كل شركةٍ بيعت كاملةً — محذوفةً من الجدول أو
    باقيةً بصفر سهم. الحذف أرشفةٌ تُخفي الشركة من كل قائمة، فكان سجلّ
    عملياتها وربحها المحقَّق بلا بابٍ يُفتح منه، وتبدو المضاربة كأنها لم تكن.
    هنا تبقى مرئيةً من سجلّها نفسه: لا أرقام تُخزَّن، والربح مجموع ما حسبته
    إعادة التشغيل لكل بيع."""
    from sqlalchemy import func
    from app.models.transaction import Transaction
    rows = (await db.execute(
        select(Transaction.company_id,
               func.count(Transaction.id),
               func.min(Transaction.executed_at),
               func.max(Transaction.executed_at),
               func.coalesce(func.sum(Transaction.realized_gain), 0))
        .where(Transaction.transaction_type == "SELL")
        .group_by(Transaction.company_id)
    )).all()
    if not rows:
        return success_response(data=[])
    ids = [r[0] for r in rows]
    cos = {c.id: c for c in (await db.execute(select(Company).where(Company.id.in_(ids)))).scalars().all()}
    qty = dict((await db.execute(
        select(Holding.company_id, Holding.quantity).where(Holding.company_id.in_(ids))
    )).all())
    counts = dict((await db.execute(
        select(Transaction.company_id, func.count(Transaction.id))
        .where(Transaction.company_id.in_(ids)).group_by(Transaction.company_id)
    )).all())
    firsts = dict((await db.execute(
        select(Transaction.company_id, func.min(Transaction.executed_at))
        .where(Transaction.company_id.in_(ids)).group_by(Transaction.company_id)
    )).all())
    out = []
    for cid, _n, _f, last, gain in rows:
        c = cos.get(cid)
        if not c or float(qty.get(cid) or 0) > 1e-9:
            continue
        out.append({
            "company_id": cid, "symbol": c.symbol, "name": c.company_name,
            "archived": c.status == "ARCHIVED",
            "transactions": int(counts.get(cid) or 0),
            "opened_at": firsts[cid].isoformat() if firsts.get(cid) else None,
            "closed_at": last.isoformat() if last else None,
            "realized_gain": round(float(gain or 0), 2),
        })
    out.sort(key=lambda x: x["closed_at"] or "", reverse=True)
    return success_response(data=out)


@router.get("/{company_id}/production")
async def get_company_production(company_id: int, db: AsyncSession = Depends(get_db)):
    """إنتاج الشركة ونقطة الصفر — بنفس تعريف المحفظة، من مصدرٍ واحد."""
    from app.services.portfolio_return import compute_company_production
    return success_response(data=await compute_company_production(db, company_id))


@router.get("/{company_id}")
async def get_holding(company_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Holding).options(selectinload(Holding.company)).where(Holding.company_id == company_id)
    )
    h = result.scalar_one_or_none()
    if not h:
        return success_response(data=None, message="No holding found.")
    await refresh_holdings_prices(db, [h])
    return success_response(data=_serialize(h))
