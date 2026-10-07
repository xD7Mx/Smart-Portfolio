"""كاشفُ D614 حيّاً — قراءةٌ فقط: ما يراه كاشفُ التجزئة لسلوشنز (7202) ولكلّ المحفظة. لا إشعار ولا كتابة في الحيازة."""
import asyncio, sys
sys.path.insert(0, "/app")


async def main():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.market import MarketEvent
    from app.services.market_data import market_service
    from app.services import split_watch as sw
    px = await market_service.get_price("7202.SR")
    d = px.to_dict() if hasattr(px, "to_dict") else px
    print("سعر 7202:", {k: (d or {}).get(k) for k in ("price", "prev_close", "change_pct")})
    async with AsyncSessionLocal() as db:
        evs = (await db.execute(select(MarketEvent).where(MarketEvent.company_symbol.in_(["7202", "7202.SR"]))
                                .order_by(MarketEvent.event_date.desc()).limit(8))).scalars().all()
        for e in evs:
            print("حدث:", e.event_type, e.event_date, (e.description or "")[:120], e.value)
        items = await sw.pending(db, scoped=False)
    print("تجزئاتٌ معلّقة:", len(items))
    for i in items:
        print(" ", i)
    try:
        from app.services.argaam_calendar import cp_kind  # noqa: F401
        from app.services import lastgood
        cal = lastgood.load("calendar:events") or lastgood.load("argaam:calendar")
        hits = [x for x in (cal or []) if isinstance(x, dict) and "7202" in str(x)][:5] if isinstance(cal, list) else []
        print("المفكرة:", hits)
    except Exception as e:  # noqa: BLE001
        print("المفكرة:", e)

asyncio.run(main())
