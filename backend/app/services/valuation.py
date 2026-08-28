"""
Sector-relative valuation — answers a DIFFERENT question from the finance
score: not "is this company healthy?" but "is its current price cheap or
expensive relative to its own sector peers, right now?"

Deliberately kept separate from finance_score (scores.py): a company can be
perfectly healthy and still be a poor buy at today's price, or struggling
yet already priced for it. Blending the two into one number would answer
neither question well.

Peer P/E and P/B come from the same cached get_company_info() every other
part of the app already uses, so this costs nothing extra beyond the first
lookup per peer per 30-day cache window.
"""

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Company
from app.services import cache

VALUATION_TTL = 24 * 60 * 60


def _market_sector_multiples(sector: str) -> dict | None:
    """وسيطُ مضاعفات القطاع من مسح السوق — أو None إن لم يبلغ حدَّ الأقران.

    والوسيط لا المتوسط، وثلاثةُ أقران حدٌّ أدنى: هذان شرطا أيّ مقارنةٍ
    نظائر تُقدَّم لمستثمر. وغيابُهما يعني رقماً يبدو مرجعاً وليس مرجعاً.
    """
    try:
        from app.services import lastgood
        from statistics import median
        rows = lastgood.load("market:screener") or []
    except Exception:                                             # noqa: BLE001
        return None
    if not isinstance(rows, list):
        return None
    pes = [float(r["pe_ratio"]) for r in rows
           if r.get("sector") == sector
           and isinstance(r.get("pe_ratio"), (int, float)) and r["pe_ratio"] > 0]
    pbs = [float(r["price_to_book"]) for r in rows
           if r.get("sector") == sector
           and isinstance(r.get("price_to_book"), (int, float)) and r["price_to_book"] > 0]
    if len(pes) < 3 and len(pbs) < 3:
        return None
    return {"pe": round(median(pes), 2) if len(pes) >= 3 else None,
            "pb": round(median(pbs), 2) if len(pbs) >= 3 else None,
            "n": max(len(pes), len(pbs))}


def _verdict(pe: float | None, sector_pe: float | None) -> str | None:
    if pe is None or pe <= 0 or not sector_pe:
        return None
    diff = (pe - sector_pe) / sector_pe * 100
    return ("أرخص من متوسط القطاع" if diff <= -10
            else "أغلى من متوسط القطاع" if diff >= 10
            else "قريب من متوسط القطاع")


async def _sector_peers(db: AsyncSession, sector: str, exclude_symbol: str) -> list[str]:
    rows = await db.execute(
        select(Company.symbol).where(Company.sector == sector, Company.status != "ARCHIVED")
    )
    return [r[0] for r in rows.all() if r[0] != exclude_symbol]


async def get_valuation_context(db: AsyncSession, symbol: str, sector: str | None,
                                  pe: float | None, pb: float | None) -> dict | None:
    """Compares this company's current P/E and P/B to the average of its
    real sector peers already tracked in the app. Returns None (honest
    empty) when there's no sector, no peers, or no P/E to compare — never a
    fabricated benchmark."""
    if not sector or (pe is None and pb is None):
        return None

    ck = f"valuation:{symbol}:{sector}"
    cached = cache.get(ck)
    if cached is not None:
        return cached

    from app.services.market_data import market_service
    from app.api.v1.endpoints.holdings import yahoo_symbol

    # ══ نظائرُ السوق لا نظائرُ المحفظة ══ (بأمر المالك: جودةٌ استثمارية)
    # كان القرين يُؤخذ من جدول شركات التطبيق — أي **شركات المالك نفسه**.
    # وقِيس فعلاً: عشر شركات، البنوك اثنتان وبقيّة القطاعات واحدة لكلٍّ.
    # وبعد استبعاد الشركة المقيَّمة يبقى قرينٌ واحد أو صفر — فيُعرض «متوسط
    # القطاع» وهو مضاعفُ شركةٍ واحدة، أو يسقط المسار صامتاً.
    # وهذا رقمٌ لا يصلح لقرارٍ استثماريّ: مضاعف شركةٍ واحدة ليس متوسط قطاع.
    #
    # ومسحُ السوق (‏market:screener) يحمل ~٣٩٥ شركة بقطاعاتها ومضاعفاتها،
    # ويحسب **الوسيط** لكل قطاع بحدٍّ أدنى ثلاثة أقران — وهو ما تفعله
    # المقارنات المهنية: الوسيط لا المتوسط (مضاعفٌ شاذّ واحد يجرّ المتوسط
    # ولا يُزحزح الوسيط)، وحدٌّ أدنى للعدد وإلا فليس قطاعاً يُقاس عليه.
    # فيُقرأ منه أوّلاً، ويبقى قرين المحفظة احتياطاً معلَّماً.
    market = _market_sector_multiples(sector)
    if market:
        out = {
            "sector": sector, "pe": pe, "pb": pb,
            "sector_avg_pe": market["pe"], "sector_avg_pb": market["pb"],
            "peer_count": market["n"], "peer_basis": "السوق",
            "verdict": _verdict(pe, market["pe"]),
        }
        cache.set(ck, out, 6 * 60 * 60)
        return out

    # المسار الاحتياطيّ القديم (أقران المحفظة بمتوسطٍ حسابيّ) **حُذف**.
    # كان يُنتج «متوسط قطاع» من قرينٍ واحد حين يعجز مسح السوق — ورقمٌ من
    # قرينٍ واحد يُقدَّم مرجعاً أسوأ من غياب المرجع: الغياب يُعرف، والرقم
    # الضعيف يُصدَّق. فإن لم يبلغ القطاعُ ثلاثةَ أقران في مسح السوق فلا
    # مقارنةَ نظائر لهذه الشركة، ويسقط مسارُ المضاعف من القيمة العادلة
    # ويبقى الخصم وحده — وهو الأدقّ أصلاً.
    return None

    verdict = None
    if pe is not None and pe > 0 and sector_avg_pe:
        diff_pct = (pe - sector_avg_pe) / sector_avg_pe * 100
        if diff_pct <= -15:
            verdict = "أرخص من متوسط القطاع"
        elif diff_pct >= 15:
            verdict = "أغلى من متوسط القطاع"
        else:
            verdict = "قريب من متوسط القطاع"

    result = {
        "pe": pe,
        "pb": pb,
        "sector": sector,
        "sector_avg_pe": sector_avg_pe,
        "sector_avg_pb": sector_avg_pb,
        "peer_count": len(peer_pes) or len(peer_pbs),
        "verdict": verdict,
    }
    cache.set(ck, result, VALUATION_TTL)
    return result
