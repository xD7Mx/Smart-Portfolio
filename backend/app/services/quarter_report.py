"""تقريرُ الربع لكلّ شركة (D528) — على نمط تقارير بيوت الخبرة، من «تداول» وحدها.

الترويسة: التوصية · آخرُ سعر · السعرُ المستهدف 12 شهراً · التغيّر · عائدُ التوزيع ·
إجماليُّ العائد المتوقّع. والتوصيةُ بحدود السوق المعروفة: فوق +15٪ شراء، ودون −15٪
بيع، وما بينهما حياد.

الجدول: الربعُ الحاليّ · المقابلُ من العام الماضي · التغيّرُ السنويّ · الربعُ السابق ·
التغيّرُ الربعيّ · توقّعاتُنا. وبنودُ الميزانية تُقرأ من عمود الملفّ الأوّل وحدَه
(الثاني فيه نهايةُ السنة لا الربعُ المقابل).

توقّعاتُنا للربع: البنودُ الدوريّة = الربعُ المقابلُ × نموُّ آخر أربعة أرباعٍ على
الأربعة قبلها؛ وبنودُ الميزانية = الربعُ السابقُ × نموُّه على ما قبله.
"""
from __future__ import annotations

from datetime import date, timedelta

BUY, SELL = 15.0, -15.0

BANK = [("bank_nfi", "صافي دخل التمويل والاستثمار", "flow"),
        ("bank_op_income", "الدخل التشغيلي الإجمالي", "flow"),
        ("net_income_parent", "صافي الدخل", "flow"),
        ("bank_loans", "المحفظة الإقراضية", "stock"),
        ("bank_deposits", "الودائع", "stock")]
GENERAL = [("revenue", "الإيرادات", "flow"),
           ("ebit", "الربح التشغيلي", "flow"),
           ("net_income_parent", "صافي الدخل", "flow"),
           ("eps", "ربحية السهم", "flow")]


def _d(p) -> date | None:
    try:
        return date.fromisoformat(str(p.get("as_of"))[:10])
    except (TypeError, ValueError):
        return None


def _val(p: dict | None, key: str, kind: str):
    if not p:
        return None
    if kind == "stock" and p.get("col") not in (None, 0):
        return None
    v = p.get(key)
    if v is None and key == "net_income_parent":
        v = p.get("net_income")
    return v if isinstance(v, (int, float)) else None


def _chg(a, b):
    return round((a / b - 1) * 100, 1) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None


def _near(qs: list[dict], target: date, tol: int = 20) -> dict | None:
    best = min(qs, key=lambda p: abs((_d(p) - target).days), default=None) if qs else None
    return best if best and abs((_d(best) - target).days) <= tol else None


def table(quarterly: list[dict], bank: bool) -> dict:
    """جدولُ الربع — دالّةٌ نقيّةٌ يقيسها الحارس."""
    qs = sorted([p for p in quarterly or [] if _d(p)], key=_d)
    if not qs:
        return {}
    cur = qs[-1]
    t = _d(cur)
    back = lambda n: _near(qs, t - timedelta(days=round(91.3 * n)))
    q = {n: back(n) for n in range(1, 9)}
    rows = []
    for key, label, kind in (BANK if bank else GENERAL):
        v0 = _val(cur, key, kind)
        if v0 is None:
            continue
        y, p1 = _val(q[4], key, kind), _val(q[1], key, kind)
        exp = None
        if kind == "flow":
            last4 = [_val(q[n], key, kind) for n in range(1, 5)]
            prev4 = [_val(q[n], key, kind) for n in range(5, 9)]
            if y is not None and None not in last4 and None not in prev4 and sum(prev4):
                exp = y * sum(last4) / sum(prev4)
            elif y is not None and p1 is not None and _val(q[5], key, kind):
                exp = y * p1 / _val(q[5], key, kind)
        else:
            p2 = _val(q[2], key, kind)
            if p1 is not None and p2:
                exp = p1 * p1 / p2
        rows.append({"key": key, "label": label, "cur": v0, "yoy_base": y, "yoy": _chg(v0, y),
                     "prev": p1, "qoq": _chg(v0, p1), "expected": round(exp, 2) if exp is not None else None})
    return {"as_of": cur.get("as_of"), "prior_year": (q[4] or {}).get("as_of"),
            "prev_quarter": (q[1] or {}).get("as_of"), "rows": rows}


def recommendation(total) -> str | None:
    if not isinstance(total, (int, float)):
        return None
    return "شراء" if total > BUY else "بيع" if total < SELL else "حياد"


def _ret(points, days: int):
    pts = [p for p in points or [] if isinstance(p, dict) and p.get("close") and p.get("date")]
    if len(pts) < 2:
        return None
    end = date.fromisoformat(str(pts[-1]["date"])[:10])
    target = end - timedelta(days=days)
    first = next((p for p in pts if date.fromisoformat(str(p["date"])[:10]) >= target), None)
    if not first or (date.fromisoformat(str(first["date"])[:10]) - target).days > 20:
        return None
    return round((pts[-1]["close"] / first["close"] - 1) * 100, 1)


async def build(symbol: str) -> dict:
    from app.services import fair_value_models, tadawul_xbrl
    from app.services.dividend_yield import resolve as _dy
    from app.services.market_data import market_service
    from app.services.market_screener import get_cached_screener
    from app.services.tadawul_market import row_for

    sym = str(symbol).replace(".SR", "").strip()
    arch = tadawul_xbrl._arch_of(sym)
    tbl = table(tadawul_xbrl.for_symbol(sym, "quarterly"), arch == "bank")
    snap = row_for(sym)
    price = snap.get("price")
    fvm = await fair_value_models.for_symbol(sym) or {}
    target = fvm.get("target_12m")
    change = _chg(target, price)
    dy = None
    try:
        dy = _dy(sym, price)[0]
    except Exception:                                             # noqa: BLE001
        dy = None
    total = round(change + (dy or 0), 1) if change is not None else None
    srow = next((r for r in get_cached_screener() or [] if str(r.get("symbol")) == sym), {})
    mcap = snap.get("market_cap")
    perf = {}
    try:
        s_h = await market_service.get_history(f"{sym}.SR", "2y")
        t_h = await market_service.get_history("^TASI.SR", "2y")
        for k, days in (("6m", 182), ("1y", 365), ("2y", 730)):
            perf[k] = {"stock": _ret(s_h, days), "tasi": _ret(t_h, days)}
    except Exception:                                             # noqa: BLE001
        perf = {}
    return {
        "symbol": sym, "bank": arch == "bank",
        "header": {"recommendation": recommendation(total), "price": price, "target_12m": target,
                   "change": change, "dividend_yield": dy, "total_return": total},
        "table": tbl,
        "market": {"high_52w": srow.get("high_52w"), "low_52w": srow.get("low_52w"),
                   "market_cap": mcap, "shares": round(mcap / price) if mcap and price else None},
        "performance": perf,
    }
