"""
Calculation Engine — Smart Portfolio
======================================
All financial calculations pass through here.
No module may duplicate a formula defined here.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from dataclasses import dataclass
from datetime import date


PRECISION = Decimal("0.000001")


def d(value) -> Decimal:
    """Convert any value to Decimal safely."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value)).quantize(PRECISION, rounding=ROUND_HALF_UP)


# ─── Average Cost ─────────────────────────────────────────────

def calculate_average_cost(
    current_quantity: float,
    current_avg_cost: float,
    new_quantity: float,
    new_price: float,
    fees: float = 0,
) -> Decimal:
    """
    Weighted average cost after a new purchase.
    Used for: BUY, REINVESTMENT, BONUS.
    """
    q1 = d(current_quantity)
    a1 = d(current_avg_cost)
    q2 = d(new_quantity)
    p2 = d(new_price)
    f = d(fees)

    total_cost = (q1 * a1) + (q2 * p2) + f
    total_qty = q1 + q2

    if total_qty == 0:
        return Decimal("0")

    return (total_cost / total_qty).quantize(PRECISION, rounding=ROUND_HALF_UP)


# ─── Portfolio Summary ────────────────────────────────────────

def calculate_portfolio_summary(holdings: list) -> dict:
    """
    Compute the full portfolio summary from a list of holding dicts.
    Each holding must have: quantity, average_cost, last_price
    """
    total_invested = Decimal("0")
    total_market_value = Decimal("0")
    total_unrealized = Decimal("0")

    for h in holdings:
        invested = d(h.get("quantity", 0)) * d(h.get("average_cost", 0))
        market_val = d(h.get("quantity", 0)) * d(h.get("last_price", 0))
        total_invested += invested
        total_market_value += market_val
        total_unrealized += market_val - invested

    roi_pct = Decimal("0")
    if total_invested > 0:
        roi_pct = ((total_market_value - total_invested) / total_invested * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return {
        "total_invested": float(total_invested),
        "total_market_value": float(total_market_value),
        "total_unrealized_profit": float(total_unrealized),
        "roi_pct": float(roi_pct),
    }


# ─── Company Metrics ──────────────────────────────────────────

def calculate_company_metrics(
    quantity: float,
    average_cost: float,
    last_price: float,
    total_portfolio_value: float,
) -> dict:
    qty = d(quantity)
    avg = d(average_cost)
    price = d(last_price)
    portfolio_val = d(total_portfolio_value)

    invested = qty * avg
    market_val = qty * price
    profit = market_val - invested
    profit_pct = (profit / invested * 100) if invested > 0 else Decimal("0")
    weight = (market_val / portfolio_val * 100) if portfolio_val > 0 else Decimal("0")

    return {
        "invested_amount": float(invested),
        "market_value": float(market_val),
        "unrealized_profit": float(profit),
        "unrealized_profit_pct": float(profit_pct.quantize(Decimal("0.01"))),
        "weight": float(weight.quantize(Decimal("0.01"))),
    }


# ─── ROI Engine ───────────────────────────────────────────────

def calculate_roi(
    invested: float,
    market_value: float,
    dividends: float = 0,
    reinvestment_value: float = 0,
    bonus_value: float = 0,
) -> dict:
    inv = d(invested)
    if inv == 0:
        return {"capital_roi": 0, "dividend_roi": 0, "reinvestment_roi": 0, "total_roi": 0}

    cap_gain = d(market_value) - inv
    capital_roi = (cap_gain / inv * 100).quantize(Decimal("0.01"))
    dividend_roi = (d(dividends) / inv * 100).quantize(Decimal("0.01"))
    reinvestment_roi = (d(reinvestment_value) / inv * 100).quantize(Decimal("0.01"))
    total_roi = capital_roi + dividend_roi + reinvestment_roi

    return {
        "capital_roi": float(capital_roi),
        "dividend_roi": float(dividend_roi),
        "reinvestment_roi": float(reinvestment_roi),
        "total_roi": float(total_roi),
    }


# ─── Installment Engine ───────────────────────────────────────

def calculate_installment_progress(
    total_installments: int,
    executed: int,
) -> dict:
    if total_installments == 0:
        return {"progress_pct": 0, "remaining": 0, "is_complete": False}
    pct = (executed / total_installments * 100)
    return {
        "progress_pct": round(pct, 2),
        "remaining": total_installments - executed,
        "is_complete": executed >= total_installments,
    }


def calculate_price_proximity(current_price: float, target_price: float) -> dict:
    """How close is the current price to the installment target?"""
    if target_price == 0:
        return {"proximity_pct": 0, "distance": 0, "is_near": False}
    curr = d(current_price)
    target = d(target_price)
    distance = ((target - curr) / target * 100).quantize(Decimal("0.01"))
    return {
        "proximity_pct": float(abs(distance)),
        "distance": float(target - curr),
        "is_near": abs(distance) <= Decimal("5"),  # within 5%
    }


# ─── Dividend Engine ──────────────────────────────────────────

def calculate_dividend_yield(
    annual_dividend_per_share: float,
    current_price: float,
) -> float:
    if current_price == 0:
        return 0.0
    return float((d(annual_dividend_per_share) / d(current_price) * 100).quantize(Decimal("0.01")))


def calculate_total_dividends(dividend_records: list) -> dict:
    total = sum(d(r.get("received_amount", 0)) for r in dividend_records)
    reinvested = sum(
        d(r.get("received_amount", 0))
        for r in dividend_records
        if r.get("action") == "REINVEST"
    )
    return {
        "total_received": float(total),
        "total_reinvested": float(reinvested),
        "total_cash": float(total - reinvested),
    }


# ─── Share Return Indicator ───────────────────────────────────

def calculate_share_return_indicator(
    reinvestment_shares: float,
    bonus_shares: float,
    current_price: float,
    total_quantity: float,
) -> dict:
    """
    Core Smart Portfolio concept: measures the 'free shares'
    earned through reinvestment and bonus grants.
    """
    free_shares = d(reinvestment_shares) + d(bonus_shares)
    market_value = free_shares * d(current_price)
    contribution_pct = (
        (free_shares / d(total_quantity) * 100).quantize(Decimal("0.01"))
        if total_quantity > 0 else Decimal("0")
    )
    return {
        "reinvestment_shares": float(d(reinvestment_shares)),
        "bonus_shares": float(d(bonus_shares)),
        "total_free_shares": float(free_shares),
        "market_value": float(market_value),
        "contribution_pct": float(contribution_pct),
    }


# ─── Goal Engine ──────────────────────────────────────────────

def calculate_goal_progress(current: float, target: float) -> dict:
    if target == 0:
        return {"completion_pct": 0, "remaining": 0, "is_achieved": False}
    curr = d(current)
    tgt = d(target)
    pct = (curr / tgt * 100).quantize(Decimal("0.01"))
    return {
        "completion_pct": float(min(pct, Decimal("100"))),
        "remaining": float(max(tgt - curr, Decimal("0"))),
        "is_achieved": curr >= tgt,
    }


# ─── Weight / Allocation Engine ───────────────────────────────

def calculate_weight_deviation(current: float, target: float) -> dict:
    curr = d(current)
    tgt = d(target)
    deviation = curr - tgt
    return {
        "current_weight": float(curr),
        "target_weight": float(tgt),
        "deviation": float(deviation),
        "rebalance_required": abs(deviation) > Decimal("2"),  # >2% triggers flag
    }


# ─── Income Engine ────────────────────────────────────────────

def calculate_annual_income(holdings: list) -> dict:
    """
    Estimate annual dividend income based on last known DPS and share counts.
    Each holding: {quantity, annual_dividend_per_share}
    """
    total = sum(
        d(h.get("quantity", 0)) * d(h.get("annual_dividend_per_share", 0))
        for h in holdings
    )
    return {
        "annual_income": float(total),
        "monthly_income": float((total / 12).quantize(Decimal("0.01"))),
    }


# ─── Portfolio Health Score ───────────────────────────────────

def calculate_portfolio_health(
    avg_finance_score: float,
    diversification_score: float,
    income_stability_score: float,
    risk_score: float,  # lower is better
) -> dict:
    """
    Composite health score 0–100.
    Does NOT depend on price performance alone.
    """
    health = (
        d(avg_finance_score) * Decimal("0.40")
        + d(diversification_score) * Decimal("0.25")
        + d(income_stability_score) * Decimal("0.25")
        + (100 - d(risk_score)) * Decimal("0.10")
    ).quantize(Decimal("0.1"))

    if health >= 80:
        label = "Excellent"
    elif health >= 65:
        label = "Good"
    elif health >= 50:
        label = "Fair"
    else:
        label = "Needs Attention"

    return {"health_score": float(health), "label": label}
