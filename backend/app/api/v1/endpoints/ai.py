from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from app.core.database import get_db
from app.core.response import success_response
from app.models.market import AIResult

router = APIRouter()

@router.get("/status")
async def ai_status():
    """حالة الذكاء — تُجيب دائماً، ولو كان المزوّد معطوباً.

    كان استيراد `coordinator` هنا يرفع الاستثناء إلى المستخدم (٥٠٠ بأثرٍ
    مكدسيّ) متى تعذّر تحميل مكتبة المزوّد. وصفحةُ **حالةٍ** تسقط عند العطب
    نقيضُ غرضها: هي التي يُسأل عندها «ما الخلل؟».
    """
    from app.core.config import settings
    quota, avail, reason = None, True, None
    try:
        from app.agents.coordinator import coordinator
        from app.agents.base import genai, GENAI_ERROR
        if genai is None:
            avail, reason = False, f"مكتبة المزوّد غير متاحة — {GENAI_ERROR}"
        quota = coordinator.quota_status()
    except Exception as e:                                        # noqa: BLE001
        avail, reason = False, f"{type(e).__name__}: {e}"
        logger.warning(f"حالة الذكاء: {reason}")
    return success_response(data={
        "provider":        settings.AI_PROVIDER,
        "model":           settings.AI_MODEL,
        "key_configured":  bool(settings.AI_API_KEY),
        "available":       avail,
        "reason":          reason,
        "quota":           quota,
    })

@router.get("/quota")
async def ai_quota():
    """Real-time Gemini free-tier quota usage. لا تُسقط الصفحة عند العطب."""
    try:
        from app.agents.coordinator import coordinator
        return success_response(data=coordinator.quota_status())
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"حصّة الذكاء تعذّرت: {e}")
        return success_response(data=None, message="حصّة المزوّد غير متاحة.")

@router.post("/run")
async def run_ai_analysis(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    return success_response(message="AI analysis queued. Results will appear shortly.")

@router.get("/report")
async def get_ai_report(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIResult).order_by(AIResult.generated_at.desc()).limit(10))
    items = result.scalars().all()
    return success_response(data=[{"agent": r.agent_name, "summary": r.summary, "confidence": float(r.confidence or 0)} for r in items])

async def _portfolio_snapshot(db: AsyncSession):
    """Real holdings + cash context for the AI analysts."""
    from sqlalchemy.orm import selectinload
    from app.models.portfolio import Holding
    from app.models.transaction import Cash
    result = await db.execute(select(Holding).options(selectinload(Holding.company)))
    holdings = [
        {
            "name": h.company.company_name, "symbol": h.company.symbol,
            "company_id": h.company.id,
            "qty": float(h.quantity or 0), "avg": float(h.average_cost or 0),
            "mv": float(h.market_value or 0),
            "pnl": float(h.unrealized_profit or 0),
            "pnl_pct": float(h.unrealized_profit_pct or 0),
            "sector": h.company.sector,
        }
        for h in result.scalars().all()
        if h.company and h.company.status != "ARCHIVED" and float(h.quantity or 0) > 0
    ]
    cash_row = (await db.execute(select(Cash).limit(1))).scalar_one_or_none()
    cash = float(cash_row.available_cash or 0) if cash_row else 0.0
    return holdings, cash

async def _target_weights(db: AsyncSession) -> dict:
    """company_id -> declared target_weight (%), from التوزيع النسبي — only
    companies the user has actually assigned a target to are included."""
    from app.models.market import Allocation
    rows = (await db.execute(select(Allocation.company_id, Allocation.target_weight))).all()
    return {company_id: float(tw) for company_id, tw in rows if tw is not None}


async def _performance_context(db: AsyncSession, holdings: list[dict]) -> dict | None:
    """Real performance inputs for the evaluation's fairness boost:
      • total_return_pct — **الرقم الموحّد نفسه**: صافي الربح ÷ تكلفة
        الحيازات، وهو «عائد المحفظة» المعروض في الباند والأهداف والمؤشرات.
        كان هنا تعريفٌ آخر (المحصول ÷ رأس المال المدفوع) فيقول النصّ التحليلي
        رقماً والشاشة رقماً تحت الاسم نفسه.
      • price_return_pct — raw price-only return (unrealized P&L over cost),
        the market-exposed part; the gap between the two is the production
        cushion the method provides against market volatility.
    Returns None (→ no boost, structural score only) if it can't be computed,
    so the evaluation never breaks on a missing/slow performance calc."""
    try:
        from app.services.portfolio_return import compute_net_profit
        net = await compute_net_profit(db)
        total_ret = net.get("capital_growth_pct") if net else None
        if total_ret is None:
            return None
        invested = sum((h.get("mv", 0) - h.get("pnl", 0)) for h in holdings)
        price_ret = (sum(h.get("pnl", 0) for h in holdings) / invested * 100) if invested else 0.0
        return {"total_return_pct": float(total_ret), "price_return_pct": float(price_ret)}
    except Exception:
        return None


async def _capital_recovery_context(db: AsyncSession) -> dict | None:
    """نقطة الصفر على مستوى المحفظة — passed into evaluate()'s recovery
    boost. None (→ no boost) if it can't be computed."""
    try:
        from app.services.portfolio_return import compute_capital_recovery
        return await compute_capital_recovery(db)
    except Exception:
        return None

async def _weekly_context(db: AsyncSession, holdings: list[dict], performance: dict | None) -> dict | None:
    """Real weekly momentum for the narrative — the honest, number-backed story
    the analysis should tell: how the portfolio's value moved over the past ~7
    days and whether it beat TASI over the same window. Everything here is
    computed from real snapshots + real TASI closes; returns whatever it can
    (None fields when a series is too short) so the narrative never fabricates.
      • portfolio_week_pct — change in total market value vs ~7 days ago (from
        the daily PortfolioSnapshot history).
      • tasi_week_pct — TASI close change over the same window.
      • outperformance_pct — the gap (portfolio − TASI), the "تفوّق على السوق".
      • total_return_pct — الإنتاج المحقّق ÷ رأس المال المدفوع، محمولاً من
        سياق الأداء (نفس رقم لوحة التحكم بلا الربح غير المحقّق).
    """
    from datetime import date, timedelta
    ctx: dict = {}
    if performance and performance.get("total_return_pct") is not None:
        ctx["total_return_pct"] = round(performance["total_return_pct"], 2)

    # Portfolio weekly move from real snapshots — measured as the change in
    # the RETURN RATIO (unrealized_profit / invested), NOT in market value:
    # market value drops whenever the owner sells shares or withdraws cash,
    # which once made a profitable week read as "‑6.91% تراجع" in the report
    # while the actual return ROSE. Return-ratio delta is immune to
    # deposits/sells and reflects performance only.
    pf_week = None
    try:
        from app.models.portfolio import PortfolioSnapshot
        rows = list((await db.execute(
            select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(30)
        )).scalars().all())
        def _ret(r):
            inv = float(r.invested_amount or 0)
            pnl = float(r.unrealized_profit or 0) if r.unrealized_profit is not None \
                else float(r.market_value or 0) - inv
            return (pnl / inv * 100) if inv > 0 else None
        if len(rows) >= 2:
            latest = rows[0]
            cutoff = latest.snapshot_date - timedelta(days=7)
            past = next((r for r in rows if r.snapshot_date <= cutoff), rows[-1])
            r_now, r_past = _ret(latest), _ret(past)
            if r_now is not None and r_past is not None and past.snapshot_date != latest.snapshot_date:
                pf_week = round(r_now - r_past, 2)
    except Exception:
        pf_week = None
    if pf_week is not None:
        ctx["portfolio_week_pct"] = pf_week

    # TASI weekly move over the same window.
    tasi_week = None
    try:
        from app.services.market_data import market_service
        hist = await market_service.get_history("^TASI.SR", "1mo")
        if hist and len(hist) >= 2:
            last_close = hist[-1].get("close")
            cutoff = date.today() - timedelta(days=7)
            past_pt = next((p for p in reversed(hist) if p.get("date") and p["date"] <= cutoff.isoformat()), hist[0])
            past_close = past_pt.get("close")
            if last_close and past_close:
                tasi_week = round((last_close - past_close) / past_close * 100, 2)
    except Exception:
        tasi_week = None
    if tasi_week is not None:
        ctx["tasi_week_pct"] = tasi_week

    if pf_week is not None and tasi_week is not None:
        ctx["outperformance_pct"] = round(pf_week - tasi_week, 2)

    return ctx or None


@router.get("/evaluation")
async def get_evaluation(db: AsyncSession = Depends(get_db)):
    """Always populated: rule-based scores from the real portfolio, enriched
    with a Gemini narrative when the key is available."""
    from app.services import portfolio_analytics
    from app.services.ai_content import evaluation_narrative
    holdings, cash = await _portfolio_snapshot(db)
    targets = await _target_weights(db)
    performance = await _performance_context(db, holdings)
    capital_recovery = await _capital_recovery_context(db)
    data = portfolio_analytics.evaluate(holdings, cash, targets, performance, capital_recovery)
    # محفظة فارغة: نُبقي عبارة «المحفظة فارغة» الواضحة ولا نستدعي سرد الذكاء
    # (كان يخترع عبارةً عامّة لا علاقة لها بمحفظة غير موجودة) — كما في المخاطر.
    if not any((h.get("mv") or 0) > 0 for h in holdings):
        return success_response(data=data)
    weekly = await _weekly_context(db, holdings, performance)
    # Same pattern as the governance score's description: ONE positive line —
    # Gemini first, deterministic rule text as the fallback.
    try:
        line = await evaluation_narrative(
            data.get("overall_score") or 0, data.get("diversification_score") or 0,
            data.get("risk_score") or 0, data.get("performance_score") or 0, weekly)
        if line:
            data["summary"] = line
            data["executive_summary"] = line
            data["source"] = "AI"
    except Exception:
        pass
    return success_response(data=data)

@router.get("/opportunities")
async def get_opportunities():
    """Top-momentum companies not already held, re-ranked by the real
    ai_score (financial + technical, same scoring as any company's own
    page) — computed hourly alongside the market-wide movers scan,
    never on-demand (each candidate needs a financials + history lookup,
    not just a price). See app/services/market_movers.py."""
    from app.services.market_movers import get_cached_opportunities
    return success_response(data=get_cached_opportunities() or [], message="فرص مقترحة من تحليل الذكاء الاصطناعي.")

@router.get("/risk")
async def get_risk(db: AsyncSession = Depends(get_db)):
    """Always populated: concrete risks derived from the real portfolio
    (concentration, drawdowns, valuation, safety), Gemini narrative optional."""
    from app.services import portfolio_analytics
    from app.services.ai_content import portfolio_risk
    holdings, cash = await _portfolio_snapshot(db)
    data = portfolio_analytics.risk(holdings, cash)
    try:
        ai = await portfolio_risk(holdings, cash)
        if ai and ai.get("summary"):
            data["summary"] = ai["summary"]
            if ai.get("risks"):
                data["risks"] = ai["risks"] + data["risks"]
            data["source"] = "AI"
    except Exception:
        pass
    return success_response(data=data)

@router.get("/portfolio-insight")
async def get_portfolio_insight(db: AsyncSession = Depends(get_db)):
    """Per-company fair value + safety score (investing.com style) for the
    holdings in the portfolio, plus a Gemini professional-advice summary.
    Never empty when the portfolio has companies."""
    from sqlalchemy.orm import selectinload
    from app.models.portfolio import Holding
    from app.services.analysis import analyze_company
    from app.services.ai_content import portfolio_evaluation

    result = await db.execute(select(Holding).options(selectinload(Holding.company)))
    holdings = [h for h in result.scalars().all()
                if h.company and h.company.status != "ARCHIVED"]

    def yahoo(sym: str) -> str:
        s = (sym or "").strip().upper()
        return f"{s}.SR" if s.isdigit() else s

    companies = []
    for h in holdings:
        a = await analyze_company(yahoo(h.company.symbol), h.company.company_name, db=db)
        if not a:
            continue
        f = a.get("fundamentals") or {}
        price = a.get("price")
        # القيمة العادلة من المحرّك الموحّد (‏services/fair_value.py) لا من
        # `target_mean_price`: ذاك هدفُ سعرٍ لا قيمةٌ جوهرية، وكان يجعل هذه
        # الصفحة تخالف صفحة الشركة في رقمٍ يبني عليه المالك قراره.
        fair = a.get("fair_value")
        upside = a.get("fair_value_upside_pct")
        # درجةٌ غائبة (شركة بلا بيانات مالية بعد) كانت تُقارَن بعددٍ فتُسقط
        # الصفحة كلّها بخطأ ٥٠٠. الغياب يُقال «غير متاحة» ولا يُسقط تحليلاً.
        safety = a["financial"]["score"]
        safety_label = ("غير متاحة" if safety is None
                        else "ممتازة" if safety >= 80 else "جيدة" if safety >= 65
                        else "متوسطة" if safety >= 45 else "ضعيفة")
        # ══ التغطيةُ شاملة: لا «غير متاح» حيث تتوفّر قيمةٌ نسبية ══ (D230)
        # `analyze_company` — المُنتِجُ الواحد — يحسب القيمةَ النسبيةَ إلى
        # القطاع حيث لا هدفَ لبيوت الخبرة، وكانت هذه الشاشةُ تُسقطها من
        # مخرَجها فتعرض «—» و«غير متاح» على شركةٍ لها تقييمٌ في يدنا.
        # فتُمرَّر بحقولها المستقلّة (لا تُدسّ في `fair_value`)، ويُبنى
        # وصفُ التقييم على الفرق المتاح أيّاً كان مصدرُه — ويُعلَن مصدرُه.
        rel_up = a.get("rel_upside_pct")
        eff_up = upside if upside is not None else rel_up
        valuation = ("مقيّم بأقل من قيمته" if (eff_up is not None and eff_up >= 8)
                     else "مقيّم بأعلى من قيمته" if (eff_up is not None and eff_up <= -8)
                     else "قريب من القيمة العادلة" if eff_up is not None else "غير متاح")
        companies.append({
            "rel_value": a.get("rel_value"),
            "rel_low": a.get("rel_low"),
            "rel_high": a.get("rel_high"),
            "rel_conf": a.get("rel_conf"),
            "rel_basis": a.get("rel_basis"),
            "rel_upside_pct": rel_up,
            "valuation_basis": ("أهداف بيوت الخبرة" if upside is not None
                                else a.get("rel_basis") if rel_up is not None else None),
            "symbol": h.company.symbol,
            "name": h.company.company_name,
            "price": price,
            "fair_value": fair,
            "upside_pct": upside,
            "valuation": valuation,
            "safety_score": safety,
            "safety_label": safety_label,
            "ai_score": a.get("ai_score"),
            "decision": a.get("decision"),
        })

    advice = None
    try:
        from app.api.v1.endpoints.ai import _portfolio_snapshot as _snap, _target_weights as _tgts
        from app.services import portfolio_analytics
        hs, cash = await _snap(db)
        tgts = await _tgts(db)
        advice = portfolio_analytics.evaluate(hs, cash, tgts).get("summary")  # rule-based, always
        ai = await portfolio_evaluation(hs, cash)
        if ai and ai.get("summary"):
            advice = ai["summary"]
    except Exception:
        advice = None

    return success_response(data={"companies": companies, "advice": advice})


@router.get("/stock-opinion/{symbol}")
async def get_stock_opinion(symbol: str, name: str = "", db: AsyncSession = Depends(get_db)):
    """One-click "رأي الذكاء" card for any single stock — same fixed prompt
    template for every company (only the symbol/data changes), grounded
    only in our own real price/technical/fundamental numbers. Powers the
    button next to a stock's price, like investing.com's WarrenAI but never
    fabricating stats we don't actually have."""
    from app.services.analysis import analyze_company
    from app.services.ai_content import stock_opinion
    from app.models.market import MarketNews

    s = (symbol or "").strip().upper()
    ysym = f"{s}.SR" if s.isdigit() else s
    analysis = await analyze_company(ysym, name or symbol, db=db)
    if not analysis:
        return success_response(data=None)
    rows = (await db.execute(
        select(MarketNews.headline).where(MarketNews.company_symbol == s)
        .order_by(MarketNews.published_at.desc().nullslast()).limit(5)
    )).scalars().all()
    # شواهدُ «أرقام» — تُجمع بمهلةٍ قصيرة، وغيابُها لا يمنع الرأي (D218).
    _ev_lines: list[str] = []
    try:
        from app.services.argaam_evidence import argaam_evidence, evidence_lines
        _ev_lines = evidence_lines(await argaam_evidence(s))
    except Exception:                                             # noqa: BLE001
        _ev_lines = []
    opinion = None
    try:
        opinion = await stock_opinion(symbol, name or analysis.get("name") or symbol, analysis,
                                      headlines=list(rows), evidence_lines_ar=_ev_lines)
    except Exception:
        opinion = None
    if not opinion:
        # Reliability floor — "ذكاء بدون ذكاء": when Gemini is missing/
        # exhausted/slow, a deterministic rule-based engine builds the SAME
        # structured opinion from the same real numbers, so this feature
        # never shows "تعذّر توليد رأي الذكاء" while the stock has data.
        from app.services.rule_opinion import build_stock_opinion
        opinion = build_stock_opinion(symbol, name or analysis.get("name") or symbol, analysis)

    # Unify the headline verdict across every surface: whatever built the
    # opinion (Gemini or rules), its label IS the app-wide governance
    # decision — so رأي الذكاء can never contradict الحوكمة/تقييم الأداء.
    # ══ الشواهدُ تُعرض كما وردت، أياً كان من كتب الرأي ══ (D218)
    # لو تُركت للنموذج لأعاد صياغتَها، وصياغةُ الشاهد تُفسده. ولو أُلحقت
    # بالمسار القاعديّ وحدَه لاختلف المعروضُ باختلاف من كتب — والمستخدمُ
    # لا يعلم أيَّ محرّكٍ كتب رأيَ اليوم.
    if opinion and _ev_lines:
        opinion["evidence_headline"] = "شواهد من «أرقام»"
        opinion["evidence_bullets"] = _ev_lines[:3]
    unified = (analysis.get("decision") or {}).get("label")
    if opinion and unified:
        opinion["sentiment_label"] = unified
        opinion["decision_color"] = (analysis.get("decision") or {}).get("color")
    return success_response(data=opinion)


@router.get("/full-report")
async def get_full_report(db: AsyncSession = Depends(get_db)):
    """Always populated comprehensive report — rule-based text from the real
    portfolio, upgraded to a Gemini narrative when available."""
    from app.services import portfolio_analytics
    from app.services.ai_content import portfolio_report

    # كل مصدرٍ داخل حارسه. سابقاً كان نداءٌ فرعي واحد يفشل (سياق الأداء أو
    # استرداد رأس المال أو الأوزان المستهدفة) فيسقط الطلب كلّه بـ500، وتعرض
    # الواجهة «لا توجد بيانات… فعّل مفتاح الذكاء» — رسالةٌ تتّهم المفتاح وهو
    # بريء، فيبدو التقرير الشامل معطّلاً بلا سبب ظاهر.
    async def _safe(coro, label, default):
        try:
            return await coro
        except Exception as e:                                    # noqa: BLE001
            logger.warning(f"full-report: مصدر «{label}» فشل — {e}")
            return default

    holdings, cash = await _safe(_portfolio_snapshot(db), "المحفظة", ([], 0.0))
    targets = await _safe(_target_weights(db), "الأوزان المستهدفة", {})
    total = sum(h["mv"] for h in holdings)
    invested = sum(h.get("avg", 0) * h.get("qty", 0) for h in holdings)
    roi = ((total - invested) / invested * 100) if invested else 0
    performance = await _safe(_performance_context(db, holdings), "الأداء", {})
    capital_recovery = await _safe(_capital_recovery_context(db), "استرداد رأس المال", {})
    try:
        data = portfolio_analytics.report(
            holdings, cash, {"market_value": total, "roi_pct": roi},
            targets, performance, capital_recovery)
    except Exception as e:                                        # noqa: BLE001
        logger.error(f"full-report: بناء التقرير القاعدي فشل — {e}")
        data = {"content": "", "source": "rule", "overall_score": None,
                "improvement_steps": []}
    weekly = await _safe(_weekly_context(db, holdings, performance), "الأسبوعي", {})
    try:
        ai = await portfolio_report(holdings, cash, weekly)
        if ai and ai.get("content"):
            data["content"] = ai["content"]
            data["source"] = "AI"
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"full-report: صياغة الذكاء تعذّرت — {e}")
    # لا نُعيد تقريراً فارغاً بصمت: إن سقط كل شيء نقول السبب صراحةً.
    if not (data.get("content") or "").strip():
        data["content"] = ("تعذّر بناء التقرير من بيانات محفظتك الآن. "
                           "السبب مسجَّل في سجلّ الخادم، والأرقام نفسها سليمة "
                           "وتُعرض في بقيّة الشاشات.")
        data["source"] = "error"
    return success_response(data=data)

@router.post("/chat")
async def ai_chat(payload: dict, db: AsyncSession = Depends(get_db)):
    """شات بوت المحفظة — **للقراءة فقط**. يجيب من بيانات التطبيق الحقيقية
    (المحفظة · الحوكمة · الفرز · القطاعات · نبض السوق) ولا يملك أي أداة
    كتابة. الجسم: {"message": "...", "history": [{role, content}, ...]}."""
    from app.services.ai_chat import answer
    msg = (payload or {}).get("message", "")
    hist = (payload or {}).get("history") or []
    if not isinstance(hist, list):
        hist = []
    # حارس أخير: أي خطأ غير متوقّع يُعيد رسالة مفهومة بدل 500 — فالواجهة كانت
    # تعرض «تعذّر الاتصال بالخادم» فيبدو المساعد صامتاً حتى عن الأسئلة الجاهزة.
    try:
        return success_response(data=await answer(db, msg, hist))
    except Exception as e:                                       # noqa: BLE001
        logger.error(f"ai_chat فشل: {e}")
        return success_response(data={
            "reply": "تعذّر تجهيز الإجابة الآن. أعد المحاولة بعد قليل.",
            "grounded": False, "source": "error",
        })
