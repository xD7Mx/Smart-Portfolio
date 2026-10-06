"""‏D604: ملخّصُ الإغلاق اليوميّ على تلغرام — بأمر المالك: «ملخّص السوق بعد انتهائه والأخبار المهمّة
التي تؤثّر عليه، بحكمةٍ لا بكثرة: القليلُ المفيد». ولا سطرَ تبريريّ: أوّلُ سطرٍ هو السوقُ نفسُه.

ما فيه، وكلُّه من بياناتٍ في التطبيق (لا اختلاق):
  - تاسي: الإغلاقُ والتغيّر · الاتساعُ (صاعدةٌ/هابطة) · الأقوى والأضعفُ من القطاعات
  - محفظتُك: ما تحرّك منها 2٪ فأكثر (اثنان على الأكثر)
  - برنت
  - أخبارٌ: ثلاثةٌ على الأكثر يختارها النموذجُ من عناوين اليوم بأثرها على السوق — أو لا شيء؛ الصمتُ أصدقُ من الحشو
ويُرسَل مرّةً في اليوم، ولا يُرسَل في يومٍ لم يتداول فيه السوق (الإغلاقُ نفسُه كالأمس).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from loguru import logger

STORE = "digest:close"


def _pct(x) -> str:
    return f"{x:+.2f}٪" if isinstance(x, (int, float)) else "—"


def compose(tasi: dict | None, movers: dict | None, holdings: list[tuple[str, float]],
            brent: dict | None, news: list[dict]) -> list[str]:
    """دالّةٌ نقيّة: البياناتُ ← أسطرُ الرسالة. ما غاب مصدرُه لا يُكتب سطرُه."""
    out: list[str] = []
    px, ch = (tasi or {}).get("price"), (tasi or {}).get("change_pct")
    if isinstance(px, (int, float)):
        head = f"تاسي أغلق {px:,.2f} ({_pct(ch)})"
        if movers and movers.get("advancers") is not None:
            head += f" · صاعدة {movers['advancers']} / هابطة {movers.get('decliners', 0)}"
        out.append(head)
    secs = [s for s in (movers or {}).get("sectors") or [] if isinstance(s.get("avg_change_pct"), (int, float))]
    if len(secs) >= 2:
        out.append(f"الأقوى: {secs[0]['sector']} {_pct(secs[0]['avg_change_pct'])} · "
                   f"الأضعف: {secs[-1]['sector']} {_pct(secs[-1]['avg_change_pct'])}")
    big = sorted([h for h in holdings if abs(h[1]) >= 2], key=lambda h: -abs(h[1]))[:2]
    if big:
        out.append("محفظتك: " + " · ".join(f"{n} {_pct(c)}" for n, c in big))
    bp = (brent or {}).get("price")
    if isinstance(bp, (int, float)):
        out.append(f"برنت {bp:,.2f}$ ({_pct((brent or {}).get('change_pct'))})")
    for n in news[:3]:
        if n.get("headline") and n.get("impact"):
            out.append(f"• {n['headline']} — {n['impact']}")
    return out


async def _holdings_moves(stocks: dict) -> list[tuple[str, float]]:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company, Holding
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Company.symbol, Company.company_name).join(Holding, Holding.company_id == Company.id)
                                 .where(Holding.quantity > 0).execution_options(skip_portfolio_scope=True))).all()
    from app.data.market_universe import MARKET_UNIVERSE
    seen, out = set(), []
    for sym, name in rows:
        s = str(sym).replace(".SR", "")
        name = (MARKET_UNIVERSE.get(s) or {}).get("name_ar") or name
        c = stocks.get(s) if s in stocks else stocks.get(s + ".SR")
        if s in seen or not isinstance(c, (int, float)):
            continue
        seen.add(s)
        out.append((name or s, float(c)))
    return out


async def _important_news(day: str) -> list[dict]:
    """عناوينُ آخر يوم ← ثلاثةٌ على الأكثر بأثرها، يختارها النموذج — أو لا شيء."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.market import MarketNews
    since = datetime.utcnow() - timedelta(hours=26)
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(MarketNews).where(MarketNews.published_at >= since)
                                 .order_by(MarketNews.published_at.desc()).limit(25))).scalars().all()
    heads = list(dict.fromkeys(r.headline.strip() for r in rows if r.headline))[:25]
    if not heads:
        return []
    from app.services.ai_content import _generate_obj
    listing = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(heads))
    prompt = f"""أنت محلّلٌ في السوق السعودية. من عناوين اليوم أدناه اختر ما يؤثّر فعلاً على السوق أو قطاعٍ كبيرٍ فيه
(سياسةٌ نقدية، نفط، نتائجُ شركةٍ قيادية، تنظيمٌ للسوق، تدفّقاتٌ أجنبية…). ثلاثةٌ على الأكثر، وإن لم يكن فيها ما يستحقّ فأعد قائمةً فارغة.
لا تختر خبراً عامّاً أو مكرّراً أو دعائياً. لكلّ خبرٍ سطرٌ قصيرٌ بأثره المتوقّع (عشرُ كلماتٍ على الأكثر) — بلا مبالغة ولا تخمينِ أرقام.

العناوين:
{listing}

أعد JSON فقط: {{"items": [{{"n": 1, "impact": "الأثر"}}]}}"""
    obj = await _generate_obj(prompt, f"ai:digest:v1:{day}", 20 * 3600)
    out = []
    for it in (obj or {}).get("items") or []:
        try:
            h = heads[int(it.get("n")) - 1]
        except (TypeError, ValueError, IndexError):
            continue
        imp = " ".join(str(it.get("impact") or "").split())
        if imp and len(imp.split()) <= 14:
            out.append({"headline": h, "impact": imp})
    return out[:3]


async def send(force: bool = False) -> dict:
    """يُرسَل مرّةً في اليوم بعد الإغلاق — ولا يُرسَل إن لم يتداول السوقُ اليوم."""
    from app.services import lastgood
    from app.services.market_data import market_service
    from app.services.market_movers import get_cached_market_movers
    today = date.today().isoformat()
    last = lastgood.load(STORE) or {}
    if last.get("day") == today and not force:
        return {"sent": False, "why": "أُرسل اليوم"}
    tasi = await market_service.get_price("^TASI.SR")
    px = (tasi or {}).get("price")
    if not isinstance(px, (int, float)):
        return {"sent": False, "why": "لا إغلاقَ لتاسي"}
    if not force and last.get("tasi") == px:
        return {"sent": False, "why": "لم يتداول السوقُ اليوم (الإغلاقُ كالأمس)"}
    movers = get_cached_market_movers() or lastgood.load("market:movers", max_age_seconds=20 * 3600) or {}
    try:
        holdings = await _holdings_moves(movers.get("stocks") or {})
    except Exception as e:                                        # noqa: BLE001
        logger.warning("ملخّص الإغلاق: المحفظة {}", e)
        holdings = []
    try:
        from app.services.commodity_quote import brent_quote
        brent = await brent_quote()
    except Exception:                                             # noqa: BLE001
        brent = None
    try:
        news = await _important_news(today)
    except Exception as e:                                        # noqa: BLE001
        logger.warning("ملخّص الإغلاق: الأخبار {}", e)
        news = []
    lines = compose(tasi, movers, holdings, brent, news)
    if not lines:
        return {"sent": False, "why": "لا بيانات"}
    from app.services.advisor_memory import notify
    await notify("", lines, raw=True)
    lastgood.save(STORE, {"day": today, "tasi": px})
    return {"sent": True, "lines": len(lines), "news": len(news)}
