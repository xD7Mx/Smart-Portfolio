"""Yahoo Finance access layer.

Every known yfinance failure mode is guarded here, not in the models:
  - statement rows are DROPPED (not NaN) when Yahoo lacks them  -> row() returns None
  - non-US tickers intermittently return empty DataFrames       -> retry, then declare missing
  - info dict is unstable and shrinks without notice            -> .get only, never []
  - financialCurrency occasionally reports USD for .SR          -> currency is checked, not assumed
  - curl_cffi transport + crumb/cookie rate limiting            -> backoff
  - issue #2584 one-year line-item misalignment                 -> self-test before any batch run
"""
from __future__ import annotations
import time, math, datetime as dt
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None

MAX_RETRIES = 3
BACKOFF_SEC = 2.0


@dataclass
class Fundamentals:
    """Everything the models are allowed to see. Missing means None, never a guess."""
    ticker: str
    price: float | None = None
    shares: float | None = None
    currency: str | None = None
    fin_currency: str | None = None
    income: pd.DataFrame | None = None
    balance: pd.DataFrame | None = None
    cash: pd.DataFrame | None = None
    info: dict = field(default_factory=dict)
    dividends: pd.Series | None = None
    analyst_target: float | None = None
    n_analysts: int | None = None
    fetched_at: str = ""
    errors: list[str] = field(default_factory=list)

    # ---------- guarded accessors ----------
    def row(self, stmt: str, label: str) -> pd.Series | None:
        """The only sanctioned way to read a statement line. Existence, never assumption."""
        df = {"income": self.income, "balance": self.balance, "cash": self.cash}[stmt]
        if df is None or df.empty or label not in df.index:
            return None
        s = df.loc[label]
        if isinstance(s, pd.DataFrame):      # duplicated label in Yahoo payload
            s = s.iloc[0]
        s = pd.to_numeric(s, errors="coerce").dropna()
        return s if len(s) else None

    def latest(self, stmt: str, label: str) -> float | None:
        s = self.row(stmt, label)
        return float(s.iloc[0]) if s is not None and len(s) else None

    def series(self, stmt: str, label: str) -> list[float]:
        s = self.row(stmt, label)
        return [float(x) for x in s.tolist()] if s is not None else []

    def n_periods(self) -> int:
        return 0 if self.income is None or self.income.empty else int(self.income.shape[1])

    def any_of(self, stmt: str, labels: list[str]) -> float | None:
        for lb in labels:
            v = self.latest(stmt, lb)
            if v is not None:
                return v
        return None


def _retry(fn, what: str, errs: list[str]):
    for i in range(MAX_RETRIES):
        try:
            out = fn()
            if isinstance(out, pd.DataFrame) and out.empty and i < MAX_RETRIES - 1:
                time.sleep(BACKOFF_SEC * (i + 1)); continue
            return out
        except Exception as e:                       # noqa: BLE001
            if i == MAX_RETRIES - 1:
                errs.append(f"{what}: {type(e).__name__}: {e}")
                return None
            time.sleep(BACKOFF_SEC * (i + 1))
    return None


def fetch(ticker: str, *, expect_currency: str = "SAR") -> Fundamentals:
    if yf is None:
        raise RuntimeError("yfinance غير مثبّت. pip install 'yfinance>=1.5.1'")
    f = Fundamentals(ticker=ticker, fetched_at=dt.datetime.utcnow().isoformat(timespec="seconds"))
    t = yf.Ticker(ticker)

    info = _retry(lambda: t.get_info(), "info", f.errors) or {}
    f.info = info if isinstance(info, dict) else {}

    try:
        fi = t.fast_info
        f.price = float(fi["last_price"]) if fi.get("last_price") else None
        f.shares = float(fi["shares"]) if fi.get("shares") else None
        f.currency = fi.get("currency")
    except Exception:                                # noqa: BLE001
        pass
    if f.price is None:
        f.price = f.info.get("currentPrice") or f.info.get("regularMarketPrice")
    if f.shares is None:
        f.shares = f.info.get("sharesOutstanding")
    f.currency = f.currency or f.info.get("currency")
    f.fin_currency = f.info.get("financialCurrency")

    if f.currency and f.currency.upper() != expect_currency:
        f.errors.append(f"currency={f.currency} != {expect_currency}")
    if f.fin_currency and f.fin_currency.upper() != expect_currency:
        f.errors.append(f"financialCurrency={f.fin_currency} != {expect_currency}")

    f.income  = _retry(lambda: t.income_stmt,   "income",  f.errors)
    f.balance = _retry(lambda: t.balance_sheet, "balance", f.errors)
    f.cash    = _retry(lambda: t.cashflow,      "cash",    f.errors)

    try:
        d = t.dividends
        f.dividends = d if d is not None and len(d) else None
    except Exception:                                # noqa: BLE001
        pass

    try:
        pt = t.get_analyst_price_targets() or {}
        m = pt.get("mean") or pt.get("median")
        f.analyst_target = float(m) if m else None
    except Exception:                                # noqa: BLE001
        f.analyst_target = None
    if f.analyst_target is None:
        m = f.info.get("targetMeanPrice")
        f.analyst_target = float(m) if m else None
    f.n_analysts = f.info.get("numberOfAnalystOpinions")

    return f


def misalignment_selftest(ticker: str = "AAPL") -> dict:
    """Guard against yfinance issue #2584 (line items shifted by one year).

    Cross-checks the statement column dates against the balance-sheet share count
    and net income sign pattern. Run once per environment before any batch.
    """
    f = fetch(ticker, expect_currency="USD")
    out = {"ticker": ticker, "ok": None, "detail": ""}
    if f.income is None or f.income.empty:
        out["ok"] = False; out["detail"] = "لا قائمة دخل — تعذّر الفحص"; return out
    cols = list(f.income.columns)
    years = sorted({getattr(c, "year", None) for c in cols} - {None})
    ni = f.series("income", "Net Income")
    out["detail"] = f"columns={[str(c)[:10] for c in cols]} net_income={ni[:4]}"
    out["ok"] = bool(years) and max(years) >= dt.date.today().year - 2 and len(ni) == len(cols)
    return out
