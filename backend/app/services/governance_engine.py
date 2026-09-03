"""
Governance Engine orchestrator — wires Phases 1-12 together into one
callable per symbol: Feature Engine → Rule Engine → Four Scores →
Decision Engine → Explainability → Confidence Score.

Purely additive: does not import from or modify analysis.py, scores.py,
or governance.py — every existing page (AI page, per-holding tabs,
portfolio-wide Governance page) keeps using the old finance_score exactly
as before. This powers a new endpoint only, so the old and new engines can
run side by side until the frontend is ready to switch over.
"""

from __future__ import annotations

from typing import Optional

from app.services import cache

GOVERNANCE_V2_TTL = 24 * 60 * 60


async def evaluate_company(symbol: str, db=None, company_status: Optional[str] = None, sector: Optional[str] = None) -> Optional[dict]:
    from app.services.governance_rules import rules_version
    ck = f"governance_v2:{symbol}:{sector or ''}:{rules_version()}"  # auto-busts on any rules edit
    cached = cache.get(ck)
    if cached is not None:
        return cached

    from app.services.market_data import market_service
    from app.services import technical
    from app.services.valuation import get_valuation_context
    from app.services.four_scores import (
        build_features, compute_four_scores, technical_to_timing_snapshot,
        valuation_to_snapshot, hard_filter_flags_from_company, resolve_sector,
    )
    from app.services.decision_engine import decide
    from app.services.explainability import explain
    from app.services.confidence import compute_confidence

    data = await market_service.get_financials(symbol)
    periods = (data or {}).get("periods") or []
    if not periods:
        return None

    info = await market_service.get_company_info(symbol) or {}
    # The canonical Arabic sector (Company.sector, e.g. "البنوك") drives every
    # sector-archetype exemption. Yahoo returns English ("Financial Services"),
    # which never matches the archetype map — so the DB sector wins, falling
    # back to a resolver that maps Yahoo English → Arabic (or looks the symbol
    # up) only when no DB sector was passed.
    resolved_sector = sector or resolve_sector(info.get("sector"), symbol)
    history = await market_service.get_history(symbol, "1y")
    tech = technical.analyze(history) if history else None

    valuation_ctx = None
    if db is not None:
        try:
            valuation_ctx = await get_valuation_context(
                db, symbol, resolved_sector, info.get("pe_ratio"), info.get("price_to_book"),
            )
        except Exception as e:
            from loguru import logger
            logger.debug(f"Valuation lookup skipped for {symbol}: {e}")

    # المصدرُ الواحد للسمات — يُدقّق الأساسيات ويضيف أركان الإطار القطاعيّ،
    # فيرى هذا المحرّك ما تراه صفحة الشركة بالضبط (انظر
    # `four_scores.build_company_features`).
    from app.services.four_scores import build_company_features
    features, info, _q = build_company_features(
        periods, info=info, sector=resolved_sector,
        valuation_snapshot=valuation_to_snapshot(info, valuation_ctx),
        timing_snapshot=technical_to_timing_snapshot(tech),
        hard_filter_flags=hard_filter_flags_from_company(company_status),
    )
    scores = compute_four_scores(features, sector=resolved_sector)
    from app.services.decision_engine import evaluate_decision, ABSTAIN
    decision = evaluate_decision(scores, features, resolved_sector)
    explanation = explain(scores, decision)
    confidence = compute_confidence(features)

    from app.services.four_scores import composite_finance_score
    from app.services.financial_narrative import rule_based_narrative
    from app.services.expert_panel import build_expert_panel
    # ══ الدرجةُ من المحرّك الأصليّ ══ (بأمر المالك)
    # ستُّ إشاراتٍ كلٌّ منها سطرٌ يراه المستثمر في جدول القوائم نفسِه:
    # نموُّ الإيراد · جودةُ الأرباح · العائدُ على حقوق الملكية · هامشُ
    # التدفّق الحرّ · اتّجاهُ المديونية · تغطيةُ الفوائد. والبنوكُ والتأمين
    # تُعفى من ثلاثٍ منها، ويُستدَلّ عليها **من البيانات لا من اسم
    # القطاع**. وكانت الدرجةُ تأتي من `composite_finance_score` فانفصل
    # الرقمُ عن الجدول الذي تحته. (D151)
    from app.services.scores import _finance_score_from_periods
    finance = _finance_score_from_periods(periods, resolved_sector)
    narrative = rule_based_narrative(scores, explanation)
    panel = build_expert_panel(features, resolved_sector, scores)  # the expert consensus

    # The score is PURELY fundamental — the technical/timing read never
    # enters the verdict (a board of value legends doesn't judge by RSI/MACD).
    overall = finance

    # When the panel couldn't be adequately informed, the system abstained —
    # the UI must then withhold the (untrustworthy) numeric grade and tell
    # the user to research, rather than showing a fabricated score.
    evaluable = decision.matched_rule_id != "insufficient_data"

    result = {
        "symbol": symbol,
        "sector": resolved_sector,
        "evaluable": evaluable,         # False → data too thin; grade withheld
        "finance_score": finance if evaluable else None,
        "overall": overall if evaluable else None,
        "narrative": narrative,         # the finance verdict sentence
        "expert_panel": panel,          # per-legend readings → the consensus
        "enriched_fields": (features.get("_enriched_fields") or {}).get("value"),
        "scores": scores.to_dict(),
        "decision": {
            "decision": decision.decision,
            "rule_id": decision.matched_rule_id,
            "reason": decision.reason,
        },
        "explanation": {
            "summary": explanation.summary,
            "strengths": explanation.strengths,
            "weaknesses": explanation.weaknesses,
            "improve": explanation.improve,
        },
        "confidence": {
            "score": confidence.score,
            "warning": confidence.warning,
            "years_available": confidence.years_available,
            "completeness_pct": confidence.completeness_pct,
        },
    }
    cache.set(ck, result, GOVERNANCE_V2_TTL)
    return result
