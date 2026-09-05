"""Valuation models. Each returns (value_per_share | None, diagnostics dict).

None is a legitimate, expected return. It means: the inputs this model requires
were not present, so no number is produced. It is never substituted with a guess.
"""
from __future__ import annotations
import math
from statistics import median

from .fetch import Fundamentals

# Yahoo statement labels, in fallback order. Existence is always checked by Fundamentals.row().
L_REVENUE  = ["Total Revenue", "Operating Revenue"]
L_EBIT     = ["EBIT", "Operating Income", "Total Operating Income As Reported"]
L_NI       = ["Net Income Common Stockholders", "Net Income"]
L_CFO      = ["Operating Cash Flow"]
L_CAPEX    = ["Capital Expenditure"]
L_INTEXP   = ["Interest Expense"]
L_DEBT     = ["Total Debt"]
L_CASH     = ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]
L_EQUITY   = ["Stockholders Equity", "Common Stock Equity"]
L_INVCAP   = ["Invested Capital"]
L_SHARES   = ["Ordinary Shares Number", "Share Issued", "Diluted Average Shares"]


# ---------------------------------------------------------------- helpers
def cost_of_equity(rf: float, beta: float, erp: float, floor: float, cap: float) -> float:
    return min(max(rf + beta * erp, floor), cap)


def levered_beta(bu: float, debt: float | None, equity: float | None, tax: float,
                 floor: float, cap: float, blume: bool, m: float, c: float) -> float:
    de = 0.0
    if debt and equity and equity > 0:
        de = max(0.0, debt / equity)
    b = bu * (1 + (1 - tax) * de)
    if blume:
        b = m * b + c
    return min(max(b, floor), cap)


def shares_out(f: Fundamentals) -> float | None:
    s = f.shares or f.info.get("sharesOutstanding") or f.any_of("balance", L_SHARES)
    return float(s) if s and s > 0 else None


def book_value_per_share(f: Fundamentals) -> float | None:
    eq, n = f.any_of("balance", L_EQUITY), shares_out(f)
    if eq is None or not n:
        bv = f.info.get("bookValue")
        return float(bv) if bv else None
    return eq / n


def _gordon(cf1: float, r: float, g: float, min_spread: float) -> float | None:
    if r - g < min_spread:
        return None
    return cf1 / (r - g)


# ---------------------------------------------------------------- FCFF
def fcff(f: Fundamentals, *, rf, erp, tax, beta_u, cfg) -> tuple[float | None, dict]:
    d: dict = {"model": "fcff", "missing": []}
    ebit_s = f.series("income", "EBIT") or f.series("income", "Operating Income")
    if not ebit_s:
        for lb in L_EBIT:
            ebit_s = f.series("income", lb)
            if ebit_s:
                break
    cfo   = f.any_of("cash", L_CFO)
    capex = f.any_of("cash", L_CAPEX)
    debt  = f.any_of("balance", L_DEBT)
    cash  = f.any_of("balance", L_CASH)
    eq    = f.any_of("balance", L_EQUITY)
    inv   = f.any_of("balance", L_INVCAP)
    n     = shares_out(f)

    for name, v in (("EBIT", ebit_s), ("Operating Cash Flow", cfo),
                    ("Capital Expenditure", capex), ("shares", n), ("Stockholders Equity", eq)):
        if not v:
            d["missing"].append(name)
    if d["missing"]:
        return None, d

    ebit = ebit_s[0]
    nopat = ebit * (1 - tax)
    capital = inv if inv else (eq + (debt or 0.0) - (cash or 0.0))
    if not capital or capital <= 0:
        d["missing"].append("Invested Capital"); return None, d

    roic = nopat / capital
    d["roic"] = roic
    if roic <= 0:
        d["reason"] = "ROIC غير موجب — الخصم غير معرّف"
        return None, d

    beta = levered_beta(beta_u, debt, eq, tax, cfg["beta_floor"], cfg["beta_cap"],
                        cfg["apply_blume_to_bottom_up"], cfg["blume_slope"], cfg["blume_intercept"])
    coe = cost_of_equity(rf, beta, erp, cfg["cost_of_equity_floor"], cfg["cost_of_equity_cap"])
    kd = rf + 0.015
    ie = f.any_of("income", L_INTEXP)
    if ie and debt and debt > 0:
        kd = min(max(abs(ie) / debt, rf), rf + 0.06)
    e_mv = (f.price or 0) * n
    d_mv = debt or 0.0
    w = e_mv / (e_mv + d_mv) if (e_mv + d_mv) > 0 else 1.0
    wacc = w * coe + (1 - w) * kd * (1 - tax)
    d.update(beta=beta, coe=coe, wacc=wacc, kd=kd)

    # growth is never free: g = ROIC x reinvestment rate, and terminal g <= risk free
    hist_g = None
    rev = f.series("income", L_REVENUE[0]) or f.series("income", L_REVENUE[1])
    if len(rev) >= 3 and rev[-1] > 0:
        hist_g = (rev[0] / rev[-1]) ** (1 / (len(rev) - 1)) - 1
    g0 = min(hist_g if hist_g is not None else 0.03, roic, rf)
    g0 = max(g0, 0.0)
    gT = min(rf, g0, 0.03 if hist_g is None else gT_cap(hist_g, rf))
    d.update(g_initial=g0, g_terminal=gT, growth_source="revenue CAGR" if hist_g else "default")

    years = int(cfg["explicit_years"])
    pv, cf = 0.0, nopat
    for t in range(1, years + 1):
        g = g0 + (gT - g0) * (t - 1) / max(years - 1, 1)
        rir = min(max(g / roic, 0.0), 0.95)
        cf = cf * (1 + g)
        pv += cf * (1 - rir) / (1 + wacc) ** t
    rir_T = min(max(gT / roic, 0.0), 0.95)
    tv = _gordon(cf * (1 + gT) * (1 - rir_T), wacc, gT, cfg["min_wacc_minus_g"])
    if tv is None:
        d["reason"] = "WACC − g أقل من الحد الأدنى"; return None, d
    d["terminal_share"] = (tv / (1 + wacc) ** years) / (pv + tv / (1 + wacc) ** years)

    ev = pv + tv / (1 + wacc) ** years
    equity_val = ev - (debt or 0.0) + (cash or 0.0)
    return (equity_val / n if equity_val > 0 else None), d


def gT_cap(hist_g: float, rf: float) -> float:
    return min(max(min(hist_g, 0.03), 0.0), rf)


# ---------------------------------------------------------------- normalized earnings (cyclicals)
def normalized(f: Fundamentals, *, rf, erp, tax, beta_u, cfg) -> tuple[float | None, dict]:
    d: dict = {"model": "normalized", "missing": []}
    rev = f.series("income", L_REVENUE[0]) or f.series("income", L_REVENUE[1])
    ni  = f.series("income", L_NI[0]) or f.series("income", L_NI[1])
    eq  = f.any_of("balance", L_EQUITY)
    n   = shares_out(f)
    if not rev or not ni or not eq or not n:
        d["missing"] = [k for k, v in (("Total Revenue", rev), ("Net Income", ni),
                                       ("Stockholders Equity", eq), ("shares", n)) if not v]
        return None, d

    k = min(len(rev), len(ni))
    margins = [ni[i] / rev[i] for i in range(k) if rev[i] > 0]     # loss years included, by design
    if not margins:
        d["missing"].append("usable margins"); return None, d
    norm_margin = median(margins)
    d.update(periods=k, margins=margins, norm_margin=norm_margin)
    if norm_margin <= 0:
        d["reason"] = "الهامش المعياري غير موجب عبر الدورة المتاحة"
        return None, d

    norm_earn = norm_margin * rev[0]
    roe = norm_earn / eq if eq > 0 else None
    if not roe or roe <= 0:
        d["reason"] = "ROE معياري غير موجب"; return None, d

    debt = f.any_of("balance", L_DEBT)
    beta = levered_beta(beta_u, debt, eq, tax, cfg["beta_floor"], cfg["beta_cap"],
                        cfg["apply_blume_to_bottom_up"], cfg["blume_slope"], cfg["blume_intercept"])
    coe = cost_of_equity(rf, beta, erp, cfg["cost_of_equity_floor"], cfg["cost_of_equity_cap"])
    g = min(rf, 0.03, roe * 0.5)
    justified_pe = (1 - g / roe) / (coe - g) if coe - g >= cfg["min_wacc_minus_g"] else None
    d.update(beta=beta, coe=coe, roe=roe, g=g, justified_pe=justified_pe)
    if justified_pe is None or justified_pe <= 0:
        d["reason"] = "مضاعف مبرَّر غير معرّف"; return None, d
    return norm_earn * justified_pe / n, d


# ---------------------------------------------------------------- excess return (banks)
def excess_return(f: Fundamentals, *, rf, erp, tax, beta_u, cfg) -> tuple[float | None, dict]:
    d: dict = {"model": "excess_return", "missing": []}
    eq = f.any_of("balance", L_EQUITY)
    ni = f.series("income", L_NI[0]) or f.series("income", L_NI[1])
    n  = shares_out(f)
    if not eq or not ni or not n:
        d["missing"] = [k for k, v in (("Stockholders Equity", eq), ("Net Income", ni),
                                       ("shares", n)) if not v]
        return None, d

    roe0 = ni[0] / eq
    beta = levered_beta(beta_u, None, None, tax, cfg["beta_floor"], cfg["beta_cap"],
                        cfg["apply_blume_to_bottom_up"], cfg["blume_slope"], cfg["blume_intercept"])
    coe = cost_of_equity(rf, beta, erp, cfg["cost_of_equity_floor"], cfg["cost_of_equity_cap"])
    d.update(roe0=roe0, coe=coe, beta=beta)

    if roe0 <= coe:
        # Value-destroying on its own equity: cannot exceed book. Stated, not floored silently.
        d["reason"] = "ROE أقل من تكلفة حقوق الملكية — القيمة لا تتجاوز الدفترية"
        return eq / n, d

    payout = f.info.get("payoutRatio")
    retention = 1 - float(payout) if payout and 0 <= float(payout) <= 1 else 0.6
    years = int(cfg["explicit_years"])
    target = coe + float(cfg["roe_fade_spread"])
    bv, pv = eq, 0.0
    for t in range(1, years + 1):
        roe_t = roe0 + (target - roe0) * t / years
        pv += (roe_t - coe) * bv / (1 + coe) ** t
        bv = bv * (1 + roe_t * retention)
    # terminal excess return decays to zero: no perpetual above-cost ROE assumed
    d.update(retention=retention, terminal_roe=target, terminal_excess="0 by construction")
    return (eq + pv) / n, d


# ---------------------------------------------------------------- DDM (REITs)
def ddm(f: Fundamentals, *, rf, erp, tax, beta_u, cfg) -> tuple[float | None, dict]:
    d: dict = {"model": "ddm", "missing": []}
    if f.dividends is None or len(f.dividends) < 3:
        d["missing"].append("dividend history >= 3"); return None, d
    by_year: dict[int, float] = {}
    for ts, v in f.dividends.items():
        by_year[ts.year] = by_year.get(ts.year, 0.0) + float(v)
    yrs = sorted(by_year)[-5:]
    if len(yrs) < 3:
        d["missing"].append("3 dividend years"); return None, d
    vals = [by_year[y] for y in yrs]
    mean = sum(vals) / len(vals)
    cv = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5 / mean if mean > 0 else 9.9
    d.update(dividend_years=yrs, dividends=vals, cv=cv)
    if cv > 0.35:
        d["reason"] = f"التوزيعات غير مستقرة (معامل اختلاف {cv:.2f})"
        return None, d

    eq, n = f.any_of("balance", L_EQUITY), shares_out(f)
    debt = f.any_of("balance", L_DEBT)
    beta = levered_beta(beta_u, debt, eq, tax, cfg["beta_floor"], cfg["beta_cap"],
                        cfg["apply_blume_to_bottom_up"], cfg["blume_slope"], cfg["blume_intercept"])
    coe = cost_of_equity(rf, beta, erp, cfg["cost_of_equity_floor"], cfg["cost_of_equity_cap"])
    g = min(rf, 0.02)
    d.update(beta=beta, coe=coe, g=g)
    v = _gordon(vals[-1] * (1 + g), coe, g, cfg["min_wacc_minus_g"])
    if v is None:
        d["reason"] = "COE − g أقل من الحد"; return None, d
    return v, d


MODELS = {"fcff": fcff, "normalized": normalized, "excess_return": excess_return, "ddm": ddm}
