"""بيتا قطاعيةٌ مقيسةٌ من سوقنا — لا مستوردةٌ من جدولٍ أجنبيّ (D257).

## لماذا

محرّكُ القيمة العادلة يطلب **بيتا قطاعيةً غيرَ مرفوعة**، وما في ملفّ
المعايير معلَّمٌ `unverified_default`: أرقامٌ من جدول أسواقٍ ناشئة لا من
تاسي، تُنزِل درجةَ الثقة في كلّ مخرَجٍ وتمنع الاعتماد أصلاً. و«أرقام»
تنشر بيتا **لكلّ شركة** مقيسةً من سوقنا (قِيست التغطيةُ ‎30/30).

## المعادلة، ولماذا لا يُنسَخ الرقمُ كما هو

بيتا «أرقام» **مرفوعةٌ** (تحمل أثرَ دَين الشركة)، والمحرّك يطلب غيرَ
المرفوعة ليُعيد رفعَها ببنية كلّ شركة. فتُنزَع الرافعةُ بمعادلة هامادا:

    βu = βl ÷ (1 + (1 − ضريبة) × دَين/حقوق)

ثمّ **وسيطُ القطاع** لا متوسّطُه: شركةٌ واحدةٌ شاذّةُ الرافعة لا تُزيح
قطاعاً كاملاً.

## أربعةُ قيودٍ تمنع جدولاً كاذباً

  ١· **الشاذُّ يُستبعَد**: بيتا سالبةٌ أو فوق ثلاثةٍ انحيازُ قياسٍ في
     سوقٍ ضحل، لا خاصيّةُ سهم.
  ٢· **بلا رافعةٍ مقروءةٍ لا يُنزَع شيء**: من لا دَينَ ولا حقوقَ في
     مخزوننا يُترك ويُعَدّ — ولا تُفترَض رافعةٌ صفرية.
  ٣· **قطاعٌ دون `MIN_PEERS` يبقى على الافتراضيّ** ويبقى غيرَ موثَّق:
     وسيطُ اثنين ليس قطاعاً.
  ٤· **الحدّان من ملفّ المعايير نفسِه** (`beta_floor`/`beta_cap`).

وما يُحفَظ يُحفَظ في مخزن الحالة بتاريخه وعددِ شركاتِ كلّ قطاع، فيُقرأ
منه `params.unlevered_beta` — ولا يُكتب في ملفٍّ متتبَّع.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from statistics import median

from loguru import logger

STORE_KEY = "market:sector_betas"
MIN_PEERS = 3             # دونها: وسيطٌ لا يمثّل قطاعاً
MAX_AGE_DAYS = 120
BETA_SANE = (0.0, 3.0)    # خارجَها انحيازُ قياسٍ لا خاصيّةُ سهم


def _num(x) -> float | None:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def unlever(beta_l: float, debt: float | None, equity: float | None,
            tax: float) -> float | None:
    """هامادا — أو None إن لم تُقرأ الرافعة (القيد ٢)."""
    if not (BETA_SANE[0] < beta_l < BETA_SANE[1]):
        return None
    d, e = _num(debt), _num(equity)
    if d is None or e is None or e <= 0 or d < 0:
        return None
    return beta_l / (1.0 + (1.0 - tax) * (d / e))


def build_table(betas: dict[str, float], leverage: dict[str, tuple],
                sectors: dict[str, str], *, tax: float,
                floor: float, cap: float) -> tuple[dict, dict]:
    """(جدولُ القطاعات، تقريرُ ما لم يدخل) — بلا كتابة."""
    per: dict[str, list[float]] = {}
    rep = {"شاذّة": 0, "بلا رافعة": 0, "بلا قطاع": 0, "دخلت": 0}
    for sym, bl in (betas or {}).items():
        b = _num(bl)
        if b is None or not (BETA_SANE[0] < b < BETA_SANE[1]):
            rep["شاذّة"] += 1
            continue
        sec = (sectors or {}).get(sym)
        if not sec:
            rep["بلا قطاع"] += 1
            continue
        d, e = (leverage or {}).get(sym) or (None, None)
        bu = unlever(b, d, e, tax)
        if bu is None:
            rep["بلا رافعة"] += 1
            continue
        per.setdefault(sec, []).append(bu)
        rep["دخلت"] += 1
    table = {sec: {"beta": round(min(max(median(v), floor), cap), 4), "n": len(v)}
             for sec, v in per.items() if len(v) >= MIN_PEERS}
    rep["قطاعاتٌ موثَّقة"] = len(table)
    rep["قطاعاتٌ دون الحدّ"] = sum(1 for v in per.values() if len(v) < MIN_PEERS)
    return table, rep


def _params_raw() -> dict:
    from app.services.fair_value_engine.params import CONFIG_DIR
    return json.loads((CONFIG_DIR / "market_params.json").read_text(encoding="utf-8"))


async def refresh(symbols: list[str] | None = None) -> dict:
    """يحصد البيتا ويبني الجدولَ ويحفظه — أو يعيد سببَ التعذّر بلا كتابة."""
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    from app.services.argaam_beta import harvest

    raw = _params_raw()
    tax = float(raw["tax_rate"]["value"])
    eng = raw["engine"]
    uni = main_market(MARKET_UNIVERSE)
    syms = symbols or list(uni)
    betas = await harvest(syms)
    if not betas:
        return {"error": "لم تُقرأ بيتا لأيّ شركة"}

    sectors = {s: (uni.get(s) or {}).get("sector") for s in betas}
    leverage: dict[str, tuple] = {}
    from app.services import lastgood
    for s in betas:
        fund = lastgood.load(f"fundamentals:{s}.SR") or {}
        periods = (fund.get("periods") or []) if isinstance(fund, dict) else []
        last = periods[-1] if periods else {}
        eq = last.get("equity")
        dr = last.get("debt_ratio")          # نسبةُ الالتزامات إلى الأصول ٪
        if isinstance(eq, (int, float)) and isinstance(dr, (int, float)) and 0 < dr < 100:
            assets = eq / max(1e-9, (1 - dr / 100.0))
            leverage[s] = (assets - eq, eq)
    table, rep = build_table(betas, leverage, sectors, tax=tax,
                             floor=float(eng["beta_floor"]), cap=float(eng["beta_cap"]))
    if not table:
        logger.warning("بيتا قطاعية: لا قطاعَ بلغ الحدَّ — {}", rep)
        return {"error": "لا قطاعَ بلغ حدَّ النظائر", "تقرير": rep}
    rec = {"as_of": datetime.now(timezone.utc).date().isoformat(),
           "source": "أرقام — بيتا الشركات، منزوعةُ الرافعة بهامادا",
           "tax": tax, "sectors": table, "report": rep}
    lastgood.save(STORE_KEY, rec)
    logger.info("بيتا قطاعية: {} قطاعاً موثَّقاً · {}", len(table), rep)
    return {"ok": True, "sectors": len(table), "تقرير": rep}


def reading() -> dict | None:
    """الجدولُ المحفوظ — أو None إن غاب أو شاخ."""
    from app.services import lastgood
    rec = lastgood.load(STORE_KEY)
    if not isinstance(rec, dict) or not isinstance(rec.get("sectors"), dict):
        return None
    try:
        age = (date.today() - date.fromisoformat(str(rec.get("as_of")))).days
    except Exception:                                             # noqa: BLE001
        return None
    return None if age > MAX_AGE_DAYS else rec


def beta_for(sector: str) -> tuple[float, int] | None:
    """(بيتا القطاع، عددُ شركاتِه) — أو None إن لم يُقَس."""
    rec = reading() or {}
    row = (rec.get("sectors") or {}).get(sector)
    if not isinstance(row, dict):
        return None
    b = _num(row.get("beta"))
    return (b, int(row.get("n") or 0)) if b else None
