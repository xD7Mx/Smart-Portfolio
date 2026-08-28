from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.response import success_response
from app.models.portfolio import Company, Holding, Portfolio, PortfolioSnapshot

router = APIRouter()

async def _get_holdings(db: AsyncSession):
    result = await db.execute(select(Holding).options(selectinload(Holding.company)))
    holdings = result.scalars().all()
    # Refresh from live prices (15-min cache) so the dashboard never shows stale zeros.
    from app.api.v1.endpoints.holdings import refresh_holdings_prices
    await refresh_holdings_prices(db, holdings)
    return holdings

@router.get("")
async def get_portfolio(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Portfolio).limit(1))
    p = result.scalar_one_or_none()
    if not p:
        return success_response(data={"id": 1, "name": "My Portfolio", "mode": "BUILD"})
    return success_response(data={"id": p.id, "name": p.name, "mode": p.mode})

@router.get("/summary")
async def get_portfolio_summary(db: AsyncSession = Depends(get_db)):
    holdings = await _get_holdings(db)
    total_invested = sum(float(h.invested_amount or 0) for h in holdings)
    market_value = sum(float(h.market_value or 0) for h in holdings)
    roi_pct = ((market_value - total_invested) / total_invested * 100) if total_invested else 0
    annual_income = sum(float(h.total_dividends_received or 0) for h in holdings)

    # ── المعيار الأول: المحصول التراكمي ──────────────────────────────────
    # مصدرٌ واحد (compute_production) يُغذّي «العائد المحقّق» هنا و«عائد
    # المحفظة» و«نمو العائد» و«الهدف الاستثماري» — أربعة وجوه لرقمٍ واحد،
    # فيستحيل تباعدها. وقد تباعدت ثلاث مرّات في هذا التطبيق قبل جمعها.
    try:
        from app.services.portfolio_return import compute_production
        prod = await compute_production(db)
    except Exception:
        prod = None

    try:
        from app.services.portfolio_return import compute_true_total_return_pct
        total_return_pct = await compute_true_total_return_pct(db)
    except Exception:
        total_return_pct = None

    # ── المعيار الثاني: الحوض المتحرّك — جزءٌ من المحصول لا نظامٌ موازٍ ──
    #   الحوض = المحصول − المنحة (أسهم لا نقد) − ما أُعيد استثماره
    try:
        from app.services.portfolio_return import compute_reinvestment_pool
        reinvestment_pool = (await compute_reinvestment_pool(db))["pool"]
    except Exception:
        reinvestment_pool = 0.0

    # المقياس الموحّد — يغذّي باند الثروة والأهداف وعدّاد نموّ رأس المال.
    try:
        from app.services.portfolio_return import compute_net_profit
        net = await compute_net_profit(db)
    except Exception:
        net = {}

    return success_response(data={
        **{f"np_{k}": v for k, v in net.items()},
        "net_profit": net.get("net_profit"),
        "capital_growth_pct": net.get("capital_growth_pct"),
        "contributed_capital": net.get("contributed"),
        "deployed_pct": net.get("deployed_pct"),
        "total_invested": total_invested,
        "total_current_value": market_value,
        "market_value": market_value,
        "total_cost": total_invested,
        "roi_pct": roi_pct,
        "annual_income": annual_income,
        "dividends_received": annual_income,
        "realized_gains": (prod or {}).get("realized_gains", 0.0),
        "sale_proceeds": (prod or {}).get("sale_proceeds", 0.0),
        "bonus_value": (prod or {}).get("bonus_value", 0.0),
        # ── مقياسان صريحان لا واحد ملتبس ──────────────────────────────
        # «الربح المحقّق»: ما كسبتَه فعلاً — توزيعات + **ربح** التصفية + منحة.
        # «المحصول» (DPI): ما عاد إلى يدك — توزيعات + **حصيلة** التصفية كاملةً
        #   + منحة. يشمل عودة رأس مالك عمداً، فهو مقياس سيولةٍ عائدة لا ربح.
        # كلاهما يُعرض باسمه، فلا يُقرأ أحدهما مكان الآخر: المحصول وحده
        # يُضخّم الإنجاز، والربح وحده يُخفي ما صار قابلاً لإعادة التوظيف.
        "realized_profit": (prod or {}).get("realized_profit", 0.0),
        "sale_gains": (prod or {}).get("sale_gains", 0.0),
        "bonus_market_value": (prod or {}).get("bonus_market_value", 0.0),
        # يبقى realized_income = المحصول (توافقاً مع ما تقرأه الواجهة اليوم).
        "realized_income": (prod or {}).get("total", 0.0),
        "harvest_total": (prod or {}).get("total", 0.0),
        "paid_in_capital": (prod or {}).get("capital_base", 0.0),
        "total_return_pct": total_return_pct,
        "reinvestment_pool": reinvestment_pool,
    })

@router.get("/health")
async def get_portfolio_health(db: AsyncSession = Depends(get_db)):
    """Portfolio evaluation — based on the actual financial/technical analysis
    of the held companies (market-value-weighted), NOT on paper profit/loss.
    A portfolio can be up in price yet hold weak-fundamental companies, and
    vice versa; the verdict must reflect company quality, not luck of timing.
    """
    holdings = await _get_holdings(db)
    if not holdings:
        return success_response(data={
            "health_score": None, "verdict": "NO_DATA", "label": "لا توجد بيانات",
            "companies_scored": 0, "companies_total": 0, "coverage_pct": 0,
        })

    weighted_sum = 0.0
    weight_total = 0.0
    scored = 0
    for h in holdings:
        mv = float(h.market_value or 0)
        c = h.company
        if mv <= 0 or not c:
            continue
        fin = float(c.finance_score) if c.finance_score is not None else None
        tech = float(c.technical_score) if c.technical_score is not None else None
        parts = [v for v in (fin, tech) if v is not None]
        if not parts:
            continue
        overall = sum(parts) / len(parts)
        weighted_sum += overall * mv
        weight_total += mv
        scored += 1

    total = len(holdings)
    coverage_pct = round((scored / total) * 100) if total else 0

    if weight_total <= 0:
        return success_response(data={
            "health_score": None, "verdict": "NO_DATA",
            "label": "لا توجد بيانات تحليل كافية بعد — تُبنى تلقائياً مع مرور الوقت",
            "companies_scored": scored, "companies_total": total, "coverage_pct": coverage_pct,
        })

    score = round(weighted_sum / weight_total, 1)
    if score >= 70:
        verdict, label = "STRONG", "محفظة قوية"
    elif score >= 45:
        verdict, label = "AVERAGE", "محفظة متوسطة"
    else:
        verdict, label = "WEAK", "محفظة ضعيفة"

    return success_response(data={
        "health_score": score,
        "verdict": verdict,
        "label": label,
        "deviation": round(score - 50, 1),  # signed distance from the 50 midpoint, for the diverging bar
        "companies_scored": scored,
        "companies_total": total,
        "coverage_pct": coverage_pct,
    })

@router.get("/roi")
async def get_portfolio_roi(db: AsyncSession = Depends(get_db)):
    holdings = await _get_holdings(db)
    total_invested = sum(float(h.invested_amount or 0) for h in holdings)
    market_value = sum(float(h.market_value or 0) for h in holdings)
    dividends = sum(float(h.total_dividends_received or 0) for h in holdings)
    capital_roi = ((market_value - total_invested) / total_invested * 100) if total_invested else 0
    dividend_roi = (dividends / total_invested * 100) if total_invested else 0
    return success_response(data={
        "capital_roi": capital_roi,
        "dividend_roi": dividend_roi,
        "total_roi": capital_roi + dividend_roi,
    })

@router.get("/income")
async def get_portfolio_income(db: AsyncSession = Depends(get_db)):
    holdings = await _get_holdings(db)
    annual_income = sum(float(h.total_dividends_received or 0) for h in holdings)
    return success_response(data={
        "annual_income": annual_income,
        "monthly_income": annual_income / 12,
    })

@router.get("/history")
async def get_portfolio_history(days: int = 365, db: AsyncSession = Depends(get_db)):
    """Real daily snapshots — accumulates one point per day automatically."""
    result = await db.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(days)
    )
    rows = list(result.scalars().all())[::-1]
    return success_response(data=[
        {
            "date": r.snapshot_date.isoformat(),
            "market_value": float(r.market_value or 0),
            "invested_amount": float(r.invested_amount or 0),
            "cash_balance": float(r.cash_balance or 0),
            "unrealized_profit": float(r.unrealized_profit or 0),
            "governance_score": float(r.governance_score) if r.governance_score is not None else None,
            # درجة التقييم العام — تبقى None في اللقطات المسجَّلة قبل إضافة
            # العمود، فتعرف الواجهة أن الخطّ يبدأ من هنا لا أنّ الدرجة صفر.
            "evaluation_score": float(r.evaluation_score) if r.evaluation_score is not None else None,
        }
        for r in rows
    ])

@router.post("/snapshot")
async def create_snapshot_now(db: AsyncSession = Depends(get_db)):
    """Manually record today's snapshot (idempotent — upserts today's row)."""
    from app.services.snapshots import take_snapshot
    snap = await take_snapshot(db)
    return success_response(data={
        "date": snap.snapshot_date.isoformat(),
        "market_value": float(snap.market_value or 0),
        "invested_amount": float(snap.invested_amount or 0),
    })

@router.get("/metrics")
async def get_portfolio_metrics(db: AsyncSession = Depends(get_db)):
    """Portfolio-level financial indicators — market-value-weighted averages of
    each holding's PE / dividend yield / ROE / EPS, plus analyst-target upside.
    Fundamentals come from the 30-day cache, so this is quota-cheap."""
    from app.services.market_data import market_service
    from app.api.v1.endpoints.holdings import yahoo_symbol
    holdings = await _get_holdings(db)
    rows, total_w = [], 0.0
    for h in holdings:
        if not h.company or float(h.market_value or 0) <= 0:
            continue
        info = await market_service.get_company_info(yahoo_symbol(h.company.symbol)) or {}
        w = float(h.market_value or 0)
        rows.append((w, info, float(h.last_price or 0)))
        total_w += w
    if not rows or total_w <= 0:
        return success_response(data=None)

    def wavg(key):
        num = sum(w * info[key] for w, info, _ in rows if isinstance(info.get(key), (int, float)))
        den = sum(w for w, info, _ in rows if isinstance(info.get(key), (int, float)))
        return round(num / den, 2) if den else None

    # analyst upside: weighted (target-price / last-price - 1)
    up_num = up_den = 0.0
    for w, info, lp in rows:
        tgt = info.get("target_mean_price")
        if isinstance(tgt, (int, float)) and lp > 0:
            up_num += w * (tgt / lp - 1) * 100
            up_den += w
    upside = round(up_num / up_den, 1) if up_den else None

    # ── المسافة عن قمّة ٥٢ أسبوعاً ───────────────────────────────────────
    # متوسّطٌ مرجّح بوزن كل مركز: أين **حيازاتك أنت** من قمّتها السنوية، لا
    # أين المؤشر العام. تاسي قد يكون على قمّته وشركاتك هابطة ٢٥٪ (أو العكس)،
    # فالرقم الذي يخدم قرار الضخّ هو رقم ما تملكه. والقمّة من كاش بيانات
    # الشركات نفسه الذي قرأناه للتوّ — بلا أي نداء إضافي.
    off_num = off_den = 0.0
    for w, info, lp in rows:
        hi = info.get("week52_high")
        if isinstance(hi, (int, float)) and hi > 0 and lp > 0:
            off_num += w * (lp / hi - 1) * 100
            off_den += w
    off_high = round(off_num / off_den, 1) if off_den else None

    from app.services.portfolio_return import compute_net_profit, compute_cagr_pct
    net = await compute_net_profit(db)

    # ── الدخل المتحقّق: من سجلّ توزيعاتك أنت لا من رقمٍ سنوي خارجي ──────────
    from app.models.transaction import Dividend, CashLedger
    divs = (await db.execute(select(Dividend))).scalars().all()
    income = sum(float(d.received_amount or 0) for d in divs)

    # ── حارس السنويّة ────────────────────────────────────────────────────
    # النمو المركّب يُحسب بتواريخ الضخّ، فمدّته هي عمر **سجلّ النقد** لا عمر
    # أوّل صفقة. وتحويل شهرٍ واحد إلى معدّل سنوي يضرب الضجيج في اثني عشر:
    # ١٠٪ في شهر تُعرض ٢٠٠٪ سنوياً، وشهرٌ سيّئ يقلبها إلى سالبٍ فاحش.
    # فلا تُعرض النسبة السنوية قبل ٩٠ يوماً من أوّل ضخّ؛ وقبلها يُعرض العائد
    # منذ البداية بمدّته — صادقٌ ولا يَعِد بما لا يُعرف.
    # وتاريخ بداية المشروع — إن ضبطه المالك — يغلب على سجلّ النقد: السجلّ يبدأ
    # يوم أُدخلت البيانات لا يوم بدأ المشروع، فيقسم العائد على شهرٍ ويضربه في
    # اثني عشر. وحين يُضبط، يصير العائد المركّب تحويلاً للرقم الموحّد نفسه
    # (عائد المحفظة) إلى معدّلٍ سنوي، فلا يتنازع رقمان.
    from app.services.project_start import get_project_start, annualize
    ledger = (await db.execute(select(CashLedger).order_by(CashLedger.created_at))).scalars().all()
    flow_days = None
    if ledger:
        first = ledger[0].created_at
        if first is not None:
            if first.tzinfo is None:
                first = first.replace(tzinfo=timezone.utc)
            flow_days = (datetime.now(timezone.utc) - first).days
    project_start = get_project_start()
    if project_start is not None:
        flow_days = (datetime.now(timezone.utc).date() - project_start).days
        cagr = annualize(net.get("capital_growth_pct"), flow_days)
    else:
        cagr = await compute_cagr_pct(db) if (flow_days or 0) >= 90 else None

    # ── مكرر الربحية مقارناً بوسيط السوق ─────────────────────────────────
    # رقمٌ مجرّد لا يُعرف أمرتفعٌ هو أم منخفض. والوسيط محسوبٌ سلفاً في صفوف
    # الفرز المخزَّنة — بلا أي نداء شبكة.
    pe = wavg("pe_ratio")
    market_pe = None
    try:
        from app.services.market_screener import get_cached_screener, _median
        srows = get_cached_screener() or []
        pes = [float(r["pe_ratio"]) for r in srows
               if isinstance(r.get("pe_ratio"), (int, float)) and r["pe_ratio"] > 0]
        market_pe = round(_median(pes), 2) if len(pes) >= 20 else None
    except Exception:
        market_pe = None
    pe_vs_market = (round((market_pe - pe) / market_pe * 100, 1)
                    if (pe and market_pe and pe > 0) else None)

    return success_response(data={
        "dividend_yield": wavg("dividend_yield"),
        "income_received": round(income, 2),
        "cagr_pct": cagr,
        "cagr_pending_days": None if cagr is not None else max(0, 90 - (flow_days or 0)),
        "period_return_pct": net.get("capital_growth_pct"),
        "period_days": flow_days,
        "project_start": project_start.isoformat() if project_start else None,
        "analyst_upside_pct": upside,
        "off_high_pct": off_high,
        "deployed_pct": net.get("deployed_pct"),
        "pe_ratio": pe,
        "market_pe": market_pe,
        "pe_vs_market_pct": pe_vs_market,
        "companies_covered": len(rows),
        "net_profit": net.get("net_profit"),
        "capital_growth_pct": net.get("capital_growth_pct"),
    })


@router.get("/performance")
async def get_performance(db: AsyncSession = Depends(get_db)):
    """قياس الأداء — خمسة مقاييس مؤسسية من مصدرٍ واحد (services/performance)."""
    from app.services.performance import compute_performance
    return success_response(data=await compute_performance(db))


@router.get("/integrity")
async def get_integrity(db: AsyncSession = Depends(get_db)):
    """فحص السلامة — مطابقةٌ محاسبية على بياناتك الحيّة. لا يكتب شيئاً."""
    from app.services.integrity import run_integrity_check
    return success_response(data=await run_integrity_check(db))


@router.get("/statistics")
async def get_portfolio_statistics(db: AsyncSession = Depends(get_db)):
    holdings = await _get_holdings(db)
    sectors = sorted({h.company.sector for h in holdings if h.company and h.company.sector})
    return success_response(data={
        "companies_count": len(holdings),
        "total_shares": sum(float(h.quantity or 0) for h in holdings),
        "sectors": sectors,
    })


@router.get("/governance")
async def get_portfolio_governance_endpoint(db: AsyncSession = Depends(get_db)):
    """Portfolio-wide oversight — sharia breakdown, weighted financial safety
    score, sector concentration, and a real attention list, aggregated
    across every holding at once. Powers the Governance page."""
    from app.services.governance import get_portfolio_governance
    data = await get_portfolio_governance(db)
    return success_response(data=data)


@router.get("/governance-market")
async def get_market_governance_endpoint(db: AsyncSession = Depends(get_db)):
    """السوق mode of the Governance page — the same disciplined weighted
    methodology scanning the site's own market universe for opportunities
    NOT already held, instead of auditing the current portfolio. Read-only:
    never creates a Company/Holding row."""
    from app.services.governance import get_market_governance
    data = await get_market_governance(db)
    return success_response(data=data)


@router.get("/sector-map")
async def get_sector_map_endpoint(db: AsyncSession = Depends(get_db)):
    """Clickable Sector Performance map: every sector with ALL its companies
    (name + logo + today's move) and each company's governance score — the
    same score the Governance market tab shows."""
    from app.services.governance import get_sector_map
    data = await get_sector_map(db)
    return success_response(data=data)


@router.get("/governance-v2/{symbol}")
async def get_governance_v2_endpoint(symbol: str, db: AsyncSession = Depends(get_db)):
    """The redesigned rule-based governance engine (Feature Engine → Rule
    Engine → four independent scores → Decision Engine → Explainability →
    Confidence Score) for a single company. Purely additive alongside the
    existing /governance endpoint — does not replace finance_score
    anywhere yet; this is the new engine's first real HTTP surface,
    powering the eventual Governance Dashboard rebuild."""
    from app.api.v1.endpoints.holdings import yahoo_symbol
    from app.services.governance_engine import evaluate_company

    result = await db.execute(select(Company.status, Company.sector).where(Company.symbol == symbol))
    row = result.one_or_none()
    company_status = (row[0].value if hasattr(row[0], "value") else row[0]) if row is not None else None
    company_sector = row[1] if row is not None else None

    data = await evaluate_company(yahoo_symbol(symbol), db=db, company_status=company_status, sector=company_sector)
    return success_response(data=data)
