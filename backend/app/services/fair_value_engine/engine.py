"""The single producer of fair value. One entry point: value_company().

Abstention is a correct output, not a failure. The engine never invents a number
to avoid returning "غير متوفّرة".
"""
from __future__ import annotations
import json
from pathlib import Path

from .fetch import Fundamentals
from .models import MODELS, book_value_per_share, shares_out
from .params import Params

CONFIG_DIR = Path(__file__).resolve().parents[2] / "data" / "fv_config"
_UNIVERSE: dict | None = None

CONF_ORDER = ["مرتفعة", "متوسطة", "منخفضة"]
CONF_KEY = {"مرتفعة": "high", "متوسطة": "medium", "منخفضة": "low"}


def universe() -> dict:
    global _UNIVERSE
    if _UNIVERSE is None:
        raw = json.loads((CONFIG_DIR / "market_universe.json").read_text(encoding="utf-8"))
        _UNIVERSE = {c["code"]: c for c in raw["companies"]}
    return _UNIVERSE


def _blank(code: str, reason: str, missing=None, **extra) -> dict:
    out = {
        "code": code, "value": None, "range": None, "confidence": None,
        "model": None, "abstained": True, "abstain_reason": reason,
        "inputs_missing": missing or [], "periods_used": 0,
        "implausible": False, "floored_at_book": False,
    }
    out.update(extra)
    return out


def _demote(conf: str, steps: int = 1) -> str:
    return CONF_ORDER[min(CONF_ORDER.index(conf) + steps, len(CONF_ORDER) - 1)]


def value_company(code: str, f: Fundamentals, p: Params, *, allow_unverified=False) -> dict:
    u = universe().get(str(code))
    if u is None:
        return _blank(code, "الشركة خارج نطاق السوق الرئيسة المعرّف")

    sector, route = u["tadawul_sector"], u["model"]
    ceiling = {"high": "مرتفعة", "medium": "متوسطة", "low": "منخفضة", "none": None}[u["confidence_ceiling"]]

    if route == "abstain":
        reason = ("التأمين: النسبة المجمّعة والقيمة الكامنة غير متاحة في ياهو"
                  if sector == "التأمين" else "قطاع غير مصنّف — لا نموذج مناسب")
        return _blank(code, reason, sector=sector)

    n_per = f.n_periods()
    if n_per < int(p.eng["min_annual_periods"]):
        return _blank(code, f"فترات سنوية متاحة {n_per} — دون الحد {p.eng['min_annual_periods']}",
                      sector=sector, periods_used=n_per)
    if f.price is None or f.price <= 0:
        return _blank(code, "لا سعر سوقي", sector=sector, periods_used=n_per)
    if f.fin_currency and f.fin_currency.upper() != "SAR":
        return _blank(code, f"عملة القوائم {f.fin_currency} وليست SAR", sector=sector, periods_used=n_per)

    beta_u, beta_verified = p.unlevered_beta(sector)
    kw = dict(rf=p.risk_free, erp=p.erp, tax=p.tax, beta_u=beta_u, cfg=p.eng)

    value, diag = MODELS[route](f, **kw)
    if value is None or not (value == value) or value <= 0:
        return _blank(code, diag.get("reason") or "بنود مطلوبة غير متاحة",
                      missing=diag.get("missing", []), sector=sector,
                      periods_used=n_per, model=route, diagnostics=diag)

    # ---- confidence, degraded by every real weakness ----
    conf = ceiling or "منخفضة"
    notes = []
    if not beta_verified:
        conf = _demote(conf); notes.append("بيتا قطاعية غير موثّقة")
    if not allow_unverified and not p.provenance()["params_verified"]:
        conf = _demote(conf); notes.append("معايير غير موثّقة")
    if n_per < 4:
        conf = _demote(conf); notes.append(f"فترات {n_per} فقط")
    if diag.get("missing"):
        conf = _demote(conf); notes.append("بنود ناقصة")
    if route == "normalized" and n_per < 5:
        notes.append("التاريخ المتاح لا يسع دورة كاملة")
    if f.errors:
        notes.append("; ".join(f.errors[:2]))
    ts = diag.get("terminal_share")
    if ts and ts > 0.85:
        conf = _demote(conf); notes.append(f"القيمة النهائية {ts:.0%} من الرقم")

    # ---- book floor: applied, and always declared ----
    floored = False
    bvps = book_value_per_share(f)
    floor_mult = float(p.eng["book_value_floor_multiple"])
    if bvps and value < floor_mult * bvps:
        diag["raw_value_before_floor"] = value
        value = floor_mult * bvps
        floored = True
        conf = "منخفضة"
        notes.append("انهيار النموذج — طُبّقت أرضية الدفترية، والرقم ليس مخرج نموذج")

    # ---- range from sensitivity on cost of equity and terminal growth ----
    band = {"مرتفعة": 0.18, "متوسطة": 0.28, "منخفضة": 0.40}[conf]
    rng = [round(value * (1 - band), 2), round(value * (1 + band), 2)]

    lo, hi = p.eng["plausible_band"]
    implausible = not (lo * f.price <= value <= hi * f.price)

    mos = p.eng["margin_of_safety"][CONF_KEY[conf]]
    mos = min(mos, p.eng["margin_of_safety"]["cap"])

    return {
        "code": code,
        "value": round(value, 2),
        "range": rng,
        "confidence": conf,
        "model": route,
        "abstained": False,
        "abstain_reason": None,
        "inputs_missing": diag.get("missing", []),
        "periods_used": n_per,
        "implausible": implausible,
        "floored_at_book": floored,
        # ---- provenance and audit, never displayed as part of the number ----
        "sector": sector,
        "price_at_calc": f.price,
        "entry_price": round(value * (1 - mos), 2),
        "margin_of_safety": mos,
        "notes": notes,
        "diagnostics": diag,
        "provenance": p.provenance() | {"fetched_at": f.fetched_at},
        "analyst_target": f.analyst_target,
        "n_analysts": f.n_analysts,
    }
