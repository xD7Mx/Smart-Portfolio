"""
التحليل القطاعي للسوق — أداء كل قطاع عبر فترات (٣ شهور … ٥ سنوات) ومتوسط
عائد توزيعاته، لقياس أي القطاعات ينمو فيها رأس المال فعلاً.

يُبنى **من بيانات الفرز المحسوبة سلفاً** (`market:screener`) ومن مخزن
الأساسيات المتراكم — بصفر نداءات إضافية. الفرز يحتفظ بعشر سنوات من الإغلاقات
لكل شركة، فحساب عائد فترةٍ ما = مقارنة الإغلاق الحالي بإغلاق بداية الفترة.

مبدأ لا اختلاق: القطاع الذي لا تكفي بيانات شركاته لفترةٍ ما يُعيد None لتلك
الفترة (لا يُحسب من عيّنة ناقصة صامتة)، ويُذكر عدد الشركات المحتسَبة دائماً.
"""
import asyncio
import logging
from statistics import median

from app.services import cache

logger = logging.getLogger(__name__)

SECTOR_CACHE_KEY = "market:sectors"
SECTOR_TTL = 36 * 60 * 60

# الفترات المعروضة — بعدد جلسات التداول التقريبي (٢٥٢ جلسة/سنة).
PERIODS: list[tuple[str, str, int]] = [
    ("3m", "3 أشهر", 63),
    ("6m", "6 أشهر", 126),
    ("1y", "سنة", 252),
    ("3y", "3 سنوات", 756),
    ("5y", "5 سنوات", 1260),
]

_MIN_COMPANIES = 2   # أقلّ عدد شركات يُسمح معه بإصدار متوسط قطاعي


def _period_return(closes: list[float], bars: int) -> float | None:
    """عائد الفترة٪ = (الإغلاق الحالي ÷ إغلاق بداية الفترة − 1). يُعيد None إن
    لم يبلغ التاريخ طول الفترة — لا نقيس خمس سنوات على ثلاث."""
    if not closes or len(closes) <= bars:
        return None
    start, end = closes[-(bars + 1)], closes[-1]
    if not start:
        return None
    return (end / start - 1) * 100


def _dps_tadawul(sym: str) -> float | None:
    """توزيعاتُ اثني عشر شهراً من جدول «تداول» المحفوظ (D492) — بلا نداءٍ
    جديد. كان عائدُ التوزيع يُقرأ من مخزن الأساسيات وحده فظهر لثلاثة قطاعات."""
    try:
        from datetime import date, timedelta
        from app.services import lastgood
        rows = (lastgood.load(f"div:tadawul:{sym}") or {}).get("rows") or []
        cut = (date.today() - timedelta(days=365)).isoformat()
        amt = sum(float(r.get("amount") or 0) for r in rows if str(r.get("eligibility") or r.get("paid") or r.get("announced") or "") >= cut)
        return amt or None
    except Exception:                                              # noqa: BLE001
        return None


async def compute_sector_analysis() -> list | None:
    """يبني جدول الأداء القطاعي: لكل قطاع عائد كل فترة (وسيط الشركات) ومتوسط
    عائد التوزيعات وعدد الشركات. الوسيط لا المتوسط الحسابي — كي لا تُشوّه
    شركةٌ شاذّة صورة القطاع كلّه."""
    from app.data.market_universe import MARKET_UNIVERSE
    from app.services.market_data import market_service
    from app.services.content_engine import fund_store_load

    from app.data.universe import main_market
    universe = main_market(MARKET_UNIVERSE)
    if not universe:
        return None

    fund_store = fund_store_load()
    sem = asyncio.Semaphore(8)

    async def closes_for(sym: str) -> list[float]:
        async with sem:
            try:
                pts = await market_service._yahoo()._fetch_chart_points(f"{sym}.SR", "10y", "1d")
            except Exception:
                return []
        return [p["close"] for p in (pts or []) if p.get("close") is not None]

    series = await asyncio.gather(*(closes_for(s) for s in universe), return_exceptions=True)

    # تجميع حسب القطاع
    buckets: dict[str, dict] = {}
    for (sym, meta), closes in zip(universe.items(), series):
        if isinstance(closes, Exception) or not closes:
            continue
        sector = meta.get("sector")
        if not sector:
            continue
        b = buckets.setdefault(sector, {"rets": {k: [] for k, _, _ in PERIODS},
                                        "yields": [], "symbols": []})
        b["symbols"].append(sym)
        for key, _, bars in PERIODS:
            r = _period_return(closes, bars)
            if r is not None:
                b["rets"][key].append(r)
        dps = (fund_store.get(sym) or {}).get("dps_ttm") or _dps_tadawul(sym)
        if dps and closes[-1]:
            b["yields"].append(dps / closes[-1] * 100)

    rows = []
    for sector, b in buckets.items():
        row = {
            "sector": sector,
            "companies": len(b["symbols"]),
            "dividend_yield": round(median(b["yields"]), 2) if len(b["yields"]) >= _MIN_COMPANIES else None,
            "dividend_sample": len(b["yields"]),
        }
        for key, label, _ in PERIODS:
            vals = b["rets"][key]
            row[key] = round(median(vals), 2) if len(vals) >= _MIN_COMPANIES else None
            row[f"{key}_n"] = len(vals)
        rows.append(row)

    if not rows:
        return None
    rows.sort(key=lambda r: (r.get("1y") is None, -(r.get("1y") or 0)))
    cache.set(SECTOR_CACHE_KEY, rows, SECTOR_TTL)
    try:
        from app.services import lastgood
        lastgood.save(SECTOR_CACHE_KEY, rows)
    except Exception:
        pass
    logger.info(f"📊 Sector analysis: {len(rows)} sectors over {len(PERIODS)} periods.")
    return rows


def get_cached_sector_analysis() -> list | None:
    data = cache.get(SECTOR_CACHE_KEY)
    if data is not None:
        return data
    try:
        from app.services import lastgood
        return lastgood.load(SECTOR_CACHE_KEY)
    except Exception:
        return None
