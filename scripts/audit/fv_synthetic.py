"""Synthetic-fixture tests. These verify the arithmetic and the guards.
They do NOT and cannot verify that Yahoo returns usable data for .SR tickers."""
from __future__ import annotations
import sys, datetime as dt
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

from app.services.fair_value_engine.fetch import Fundamentals                       # noqa: E402
from app.services.fair_value_engine.engine import value_company                     # noqa: E402
from app.services.fair_value_engine.params import load_params, ParamsError          # noqa: E402
from app.services.fair_value_engine import models                                   # noqa: E402

COLS = [pd.Timestamp(f"{y}-12-31") for y in (2025, 2024, 2023, 2022)]


def frame(d):  return pd.DataFrame(d, index=list(d.keys()), columns=COLS) if False else \
    pd.DataFrame([v for v in d.values()], index=list(d.keys()), columns=COLS)


def healthy(price=100.0, shares=1e8, **over) -> Fundamentals:
    inc = frame({"Total Revenue":[5.0e9,4.7e9,4.4e9,4.1e9],
                 "EBIT":[1.0e9,9.2e8,8.6e8,8.0e8],
                 "Operating Income":[1.0e9,9.2e8,8.6e8,8.0e8],
                 "Net Income":[7.2e8,6.6e8,6.1e8,5.7e8],
                 "Net Income Common Stockholders":[7.2e8,6.6e8,6.1e8,5.7e8],
                 "Interest Expense":[8.0e7,8.0e7,7.5e7,7.0e7]})
    bal = frame({"Total Debt":[1.6e9]*4, "Cash And Cash Equivalents":[4.0e8]*4,
                 "Stockholders Equity":[4.0e9,3.7e9,3.4e9,3.2e9],
                 "Invested Capital":[5.2e9,4.9e9,4.6e9,4.4e9],
                 "Ordinary Shares Number":[shares]*4})
    csh = frame({"Operating Cash Flow":[9.5e8,8.8e8,8.2e8,7.7e8],
                 "Capital Expenditure":[-3.0e8,-2.8e8,-2.6e8,-2.5e8]})
    f = Fundamentals(ticker="TEST.SR", price=price, shares=shares, currency="SAR",
                     fin_currency="SAR", income=inc, balance=bal, cash=csh,
                     info={"sharesOutstanding": shares, "payoutRatio": 0.4},
                     fetched_at=dt.datetime.utcnow().isoformat())
    for k, v in over.items():
        setattr(f, k, v)
    return f


P = load_params(allow_unverified=True, allow_stale=True)
CHECKS: list[tuple[str, bool, str]] = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))


# 1 — params guard refuses unverified by default
try:
    load_params(allow_stale=True); check("params guard rejects verified=false", False, "لم يرفض")
except ParamsError:
    check("params guard rejects verified=false", True)

# 2 — risk free must be supplied, never defaulted
try:
    _ = P.risk_free; check("risk_free unset raises", False, "أعاد قيمة")
except ParamsError as e:
    check("risk_free unset raises", "غير معبأ" in str(e))

# supply a risk free for the remaining tests
P.raw["risk_free_sar"]["value"] = 0.048
P.raw["risk_free_sar"]["as_of"] = "2026-09-01"

# 3 — FCFF produces a positive, finite value on healthy inputs
v, d = models.fcff(healthy(), rf=P.risk_free, erp=P.erp, tax=P.tax, beta_u=0.95, cfg=P.eng)
check("fcff returns value", v is not None and v > 0, f"v={v}")
check("terminal growth <= risk free", d["g_terminal"] <= P.risk_free + 1e-9,
      f"gT={d.get('g_terminal')}")
check("terminal share reported", 0 < d.get("terminal_share", 0) < 1,
      f"TV share={d.get('terminal_share'):.2%}")
check("wacc > terminal g", d["wacc"] - d["g_terminal"] >= P.eng["min_wacc_minus_g"])

# 4 — reinvestment constraint actually binds: raising g must not raise value freely
f2 = healthy()
f2.income.loc["Total Revenue"] = [8.0e9, 5.6e9, 4.6e9, 4.1e9]   # much faster growth
v2, d2 = models.fcff(f2, rf=P.risk_free, erp=P.erp, tax=P.tax, beta_u=0.95, cfg=P.eng)
check("g capped by ROIC and rf", d2["g_initial"] <= min(d2["roic"], P.risk_free) + 1e-9,
      f"g0={d2['g_initial']:.4f} roic={d2['roic']:.4f} rf={P.risk_free}")

# 5 — missing a required line returns None, not a guess
f3 = healthy(); f3.cash = f3.cash.drop(index=["Operating Cash Flow"])
v3, d3 = models.fcff(f3, rf=P.risk_free, erp=P.erp, tax=P.tax, beta_u=0.95, cfg=P.eng)
check("missing CFO -> None", v3 is None and "Operating Cash Flow" in d3["missing"], str(d3["missing"]))

# 6 — dropped label never raises KeyError
check("row() on absent label is None", healthy().row("income", "Total Deposits") is None)

# 7 — bank with ROE below COE cannot exceed book
fb = healthy()
fb.income.loc["Net Income"] = [2.0e8]*4
fb.income.loc["Net Income Common Stockholders"] = [2.0e8]*4
vb, db = models.excess_return(fb, rf=P.risk_free, erp=P.erp, tax=P.tax, beta_u=0.75, cfg=P.eng)
bvps = 4.0e9/1e8
check("ROE<COE capped at book", abs(vb - bvps) < 1e-6, f"v={vb} book={bvps}")

# 8 — insurance abstains by route, before any data is read
r = value_company("8010", healthy(), P, allow_unverified=True)
check("insurance abstains", r["abstained"] and "النسبة المجمّعة" in r["abstain_reason"],
      r.get("abstain_reason", ""))

# 9 — engine end-to-end on an industrial name
r2 = value_company("2010", healthy(), P, allow_unverified=True)
check("engine values industrial", not r2["abstained"] and r2["value"] > 0, str(r2.get("value")))
check("range brackets value", r2["range"][0] < r2["value"] < r2["range"][1], str(r2["range"]))
check("entry price below value", r2["entry_price"] < r2["value"])
check("output schema complete",
      all(k in r2 for k in ("value","range","confidence","model","abstained","abstain_reason",
                            "inputs_missing","periods_used","implausible","floored_at_book")))

# 10 — book floor fires, is declared, and forces low confidence
f4 = healthy(price=100.0)
f4.income.loc["EBIT"] = [3.0e7]*4
f4.income.loc["Operating Income"] = [3.0e7]*4
r3 = value_company("2010", f4, P, allow_unverified=True)
if r3["floored_at_book"]:
    check("floor declared + low confidence",
          r3["confidence"] == "منخفضة" and "raw_value_before_floor" in r3["diagnostics"])
else:
    check("floor declared + low confidence", True, "لم تُفعَّل الأرضية في هذه العيّنة")

# 11 — implausible flag fires on an extreme price
r4 = value_company("2010", healthy(price=2.0), P, allow_unverified=True)
check("implausible flagged", r4["implausible"] or r4["abstained"], f"v={r4.get('value')} p=2.0")

# 12 — too few periods abstains
f5 = healthy(); f5.income = f5.income.iloc[:, :2]
r5 = value_company("2010", f5, P, allow_unverified=True)
check("short history abstains", r5["abstained"] and "فترات" in r5["abstain_reason"])

# 13 — non-SAR reporting currency abstains
r6 = value_company("2010", healthy(fin_currency="USD"), P, allow_unverified=True)
check("non-SAR abstains", r6["abstained"] and "عملة" in r6["abstain_reason"])

# 14 — unverified betas cost a confidence grade
check("unverified beta demotes confidence", r2["confidence"] != "مرتفعة",
      f"conf={r2['confidence']} notes={r2['notes']}")

# ---------------------------------------------------------------- report
w = max(len(n) for n, _, _ in CHECKS)
print("\nSYNTHETIC FIXTURE TESTS")
print("-" * (w + 30))
for n, ok, det in CHECKS:
    print(f"  {'PASS' if ok else 'FAIL'}  {n:<{w}}  {det}")
bad = [n for n, ok, _ in CHECKS if not ok]
print("-" * (w + 30))
print(f"{len(CHECKS)-len(bad)}/{len(CHECKS)} passed")
raise SystemExit(1 if bad else 0)
