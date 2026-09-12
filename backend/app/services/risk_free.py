"""المعدَّلُ الخالي من المخاطر بالريال — من صكوك المملكة نفسِها (D249 · D250).

## لماذا

محرّكُ خصم التدفّقات جاهزٌ إلا من رقمٍ واحد: `risk_free_sar`. كلُّ ما عداه
مقيسٌ ومؤرَّخ — علاوةُ المخاطر من داموداران، والبيتا من «أرقام». والقيمةُ
`null` في ملفّ المعايير، و`params.py` يرفض العملَ بمفترَض. فكان الجوابُ
المكتوبُ في المسبار: «يجب تعبئتها يدوياً» — وذاك تعليقُ الاستدامة على يدِ
المالك، وقد قال: أريده ذاتياً.

## المصدر

سوقُ الصكوك في «تداول» (يُقرأ الآن بعد أن عُبرت الحمايةُ في
`tadawul_http`). ولكلّ أداةٍ فيه: العملةُ، ونوعُ الاحتساب (ثابتٌ أم عائم)،
ومعدَّلُ الكوبون، وتاريخُ الاستحقاق، وعائدُ آخرِ صفقةٍ وعائدا الطلب
والعرض، والسعرُ نسبةً من الاسميّ. وصكوكُ المملكة المحلّية تُسمّى
«‏KSA Sukuk …» — سياديّةٌ بالريال.

## ستّةُ قيودٍ تمنع رقماً مختلَقاً

  ١· **العنوانُ يُشتقّ من الصفحة** (‏`<base href>` + نداءُ الجدول) — فلا
     معرِّفُ بوّابةٍ مثبَّتٌ في الشيفرة يشيخ بصمت.
  ٢· **السيادةُ والعملةُ تُشترَطان**: صكُّ شركةٍ يحمل مخاطرَ ائتمانِها،
     وأداةٌ بغير الريال ليست معدَّلَ الريال.
  ٣· **الثابتُ وحدَه**: العائمُ (‏`rateCalcType` 4) عائدُه دالّةُ سايبور
     لا معدَّلٌ عشريٌّ ثابت. والدائمُ (‏perpetual) بلا أجلٍ أصلاً.
  ٤· **الأجلُ يُقاس** من تاريخ الاستحقاق: الأقربُ إلى عشرٍ داخل
     `TENOR_BAND`، وخارجَه امتناعٌ لا تقريب.
  ٥· **العائدُ بترتيبٍ واحدٍ معلَن**: عائدُ آخرِ صفقةٍ ← وسَطُ الطلب
     والعرض ← محسوبٌ بالتنصيف من السعر والكوبون. والصفرُ ليس عائداً بل
     أداةٌ لم تُتداول.
  ٦· **نطاقُ معقوليةٍ** من ملفّ المعايير نفسِه، وعمرٌ أقصى للقراءة.

وما يُحفَظ يُحفَظ في مخزن الحالة (‏`market:risk_free_sar`) لا في ملفٍّ
متتبَّع — فيعبر الحزمَ، وله تاريخٌ يُقرأ فيُعرَف متى شاخ.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

from loguru import logger

STORE_KEY = "market:risk_free_sar"

PAGE = ("https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/"
        "sukuk-market-watch")
_AJAX_RE = re.compile(r"url:\s*[\"']([^\"']*getSukukMarketDetails[^\"']*)[\"']")
_BASE_RE = re.compile(r"<base[^>]+href=[\"']([^\"']+)", re.I)

TARGET_YEARS = 10.0
TENOR_BAND = (6.0, 14.0)      # ما خرج عنه لا يُسمّى «عشريّاً»
MAX_AGE_DAYS = 45             # قراءةٌ أقدمُ من ذلك تُعدّ غائبة
FIXED_RATE = 1                # مقابلَ 4 للعائم — كما تُرسلها «تداول»

_SOVEREIGN = re.compile(r"^\s*(ksa|saudi|kingdom)\b|حكوم|المملكة|وزارة\s*المالية", re.I)
_SAR = re.compile(r"^\s*(sar|sr|ريال)", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _num(x) -> float | None:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(x or "").replace(",", ""))
    return float(m.group(0)) if m else None


def _pct(x) -> float | None:
    """نسبةٌ تُقرأ كسراً: «‎5.6873» و«‎5.69%» ⇒ ‎0.056873. والصفرُ ليس عائداً."""
    v = _num(x)
    if v is None or v <= 0:
        return None
    return v / 100.0 if v > 0.5 else v


def _maturity(x) -> date | None:
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", str(x or ""))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


async def fetch_instruments() -> tuple[list[dict], str | None]:
    """أدواتُ سوق الصكوك — أو (فارغ، سببُ التعذّر).

    العنوانُ يُشتقّ من الصفحة: «تداول» بوّابةٌ تُولّد معرِّفاتٍ في المسار،
    فتثبيتُها في الشيفرة يجعلها تشيخ بلا إنذار (القيد ١).
    """
    from app.services.tadawul_http import fetch
    status, body = await fetch(PAGE)
    if status != 200 or not body:
        return [], f"HTTP {status} من صفحة سوق الصكوك"
    mb, ma = _BASE_RE.search(body), _AJAX_RE.search(body)
    if not (mb and ma):
        return [], ("لم يُعثر على "
                    + ("أساسِ الصفحة" if not mb else "نداءِ جدول الصكوك")
                    + " — تغيّرت بنيةُ الصفحة")
    url = mb.group(1).rstrip("/") + "/" + ma.group(1).lstrip("/")
    status, body = await fetch(
        url, params={"sectorParameter": "All", "iswatchListSelected": "NO",
                     "requestLocale": "en"}, referer=PAGE)
    if status != 200:
        return [], f"HTTP {status} من نقطة بيانات الصكوك"
    try:
        data = json.loads(body)
    except Exception:                                             # noqa: BLE001
        return [], "مخرَجٌ غيرُ JSON من نقطة البيانات"
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list) or not rows:
        return [], "لا صفوفَ في مخرَج نقطة البيانات"
    return rows, None


def ytm(price: float, coupon_rate: float, years: float, *, face: float = 100.0) -> float | None:
    """العائدُ إلى الاستحقاق — يُحلّ لا يُقرَّب.

    السعرُ نسبةٌ من القيمة الاسمية، والكوبونُ سنويٌّ كسراً عشريّاً. الدفعاتُ
    سنويّةٌ في `years` وما دونها، والأصلُ في آخرها. يُحلّ بالتنصيف —
    فالدالّةُ رِدْفةٌ في العائد، والتنصيفُ لا يتشعّب كنيوتن.
    """
    if not (price and price > 0) or years <= 0 or coupon_rate is None or coupon_rate < 0:
        return None

    def pv(y: float) -> float:
        c = face * coupon_rate
        t, total = years, 0.0
        while t > 1e-9:
            total += c / (1.0 + y) ** t
            t -= 1.0
        return total + face / (1.0 + y) ** years

    lo, hi = -0.90, 1.00
    if pv(lo) < price or pv(hi) > price:
        return None                     # السعرُ خارج ما يمكن أن يُنتجه عائد
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if pv(mid) > price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _row_yield(r: dict, years: float) -> tuple[float | None, str]:
    """ترتيبٌ واحدٌ معلَن للعائد (القيد ٥)."""
    y = _pct(r.get("lastTadeYield"))
    if y is not None:
        return y, "آخر صفقة"
    bid, ask = _pct(r.get("bidYield")), _pct(r.get("askYield"))
    if bid is not None and ask is not None:
        return (bid + ask) / 2.0, "وسط الطلب والعرض"
    if bid is not None or ask is not None:
        return (bid if bid is not None else ask), "طرفٌ واحدٌ من السوق"
    px, cp = _num(r.get("lastTradePrice")), _pct(r.get("couponRate"))
    if px and px > 0 and cp is not None:
        v = ytm(px, cp, years)
        if v is not None:
            return v, "محسوب من السعر والكوبون"
    return None, "—"


def choose(rows: list[dict], *, today: date | None = None,
           sanity: tuple[float, float] = (0.02, 0.09)) -> tuple[dict | None, str | None]:
    """الصكُّ السياديُّ الثابتُ بالريال الأقربُ إلى عشر سنوات — أو (None، السبب)."""
    today = today or date.today()
    cands: list[dict] = []
    skip = {"غير سيادي": 0, "غير الريال": 0, "عائم": 0, "دائم": 0,
            "بلا استحقاق": 0, "خارج النطاق": 0, "بلا عائد": 0, "خارج المعقولية": 0}
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = str(r.get("issuerName") or "")
        if not _SOVEREIGN.search(name):
            skip["غير سيادي"] += 1
            continue
        cur = r.get("issueCurrency")
        if cur is not None and str(cur).strip() and not _SAR.search(str(cur)):
            skip["غير الريال"] += 1
            continue
        rct = _num(r.get("rateCalcType"))
        if rct is not None and int(rct) != FIXED_RATE:
            skip["عائم"] += 1
            continue
        if r.get("isPerpetualBond") is True:
            skip["دائم"] += 1
            continue
        mat = _maturity(r.get("maturityDateStr") or r.get("maturityDate"))
        if mat is None:
            skip["بلا استحقاق"] += 1
            continue
        years = (mat - today).days / 365.25
        if not (TENOR_BAND[0] <= years <= TENOR_BAND[1]):
            skip["خارج النطاق"] += 1
            continue
        y, how = _row_yield(r, years)
        if y is None:
            skip["بلا عائد"] += 1
            continue
        if not (sanity[0] <= y <= sanity[1]):
            skip["خارج المعقولية"] += 1
            continue
        cands.append({"symbol": str(r.get("symbol") or ""), "name": name,
                      "maturity": mat.isoformat(), "tenor_years": round(years, 2),
                      "value": round(y, 5), "basis": how})
    if not cands:
        why = "، ".join(f"{k}: {v}" for k, v in skip.items() if v)
        return None, f"لا صكَّ سيادياً ثابتاً بالريال بأجلٍ عشريٍّ وعائدٍ مقروء ({why or 'لا صفوف'})"
    best = min(cands, key=lambda c: abs(c["tenor_years"] - TARGET_YEARS))
    best["peers"] = len(cands)
    return best, None


def _sanity_from_config() -> tuple[float, float]:
    try:
        from app.services.fair_value_engine.params import CONFIG_DIR
        raw = json.loads((CONFIG_DIR / "market_params.json").read_text(encoding="utf-8"))
        lo, hi = raw["risk_free_sar"]["sanity_range"]
        return float(lo), float(hi)
    except Exception:                                             # noqa: BLE001
        return 0.02, 0.09


async def refresh() -> dict:
    """يجلب ويقرأ ويحفظ — أو يعيد سببَ التعذّر بلا كتابة."""
    rows, why = await fetch_instruments()
    if why:
        logger.warning("risk_free_sar لم يُقرأ: {}", why)
        return {"value": None, "error": why}
    best, why = choose(rows, sanity=_sanity_from_config())
    if best is None:
        logger.warning("risk_free_sar لم يُقرأ: {}", why)
        return {"value": None, "error": why}
    rec = {
        "value": best["value"],
        "as_of": _now(),
        "tenor_years": best["tenor_years"],
        "instrument": best["name"],
        "symbol": best["symbol"],
        "maturity": best["maturity"],
        "basis": best["basis"],
        "peers": best["peers"],
        "source": PAGE,
        "rows_read": len(rows),
    }
    from app.services import lastgood
    lastgood.save(STORE_KEY, rec)
    logger.info("risk_free_sar = {} ({} سنة · {} · {})", rec["value"],
                rec["tenor_years"], rec["instrument"], rec["basis"])
    return rec


def reading() -> dict | None:
    """القراءةُ المحفوظة كاملةً — أو None إن غابت أو شاخت."""
    from app.services import lastgood
    rec = lastgood.load(STORE_KEY)
    if not isinstance(rec, dict) or not isinstance(rec.get("value"), (int, float)):
        return None
    try:
        age = (date.today() - date.fromisoformat(str(rec.get("as_of")))).days
    except Exception:                                             # noqa: BLE001
        return None
    if age > MAX_AGE_DAYS:
        return None
    return rec


def current() -> float | None:
    """الرقمُ وحدَه — منتِجٌ واحدٌ يقرأ منه `params.py` ولا يفترض."""
    rec = reading()
    return float(rec["value"]) if rec else None
