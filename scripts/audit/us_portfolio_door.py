#!/usr/bin/env python3
"""كاشفُ D789 على الخادم (قراءةٌ لا تكتب شيئاً في القاعدة):

قال المالك (2026-11-23): «هل المحفظةُ تدعم شركاتٍ أمريكية؟ هل المعاملاتُ ستكون صحيحة؟ هل ستدعمها الرسوم؟ أبغاها تدعم السوقين
كاملَين — البحثَ والمحفظةَ نفسَها». ويُقاس هنا ما لا يُعرف من الكود:

  ١ المحافظ: عملةُ كلٍّ ومؤرشفتُها وعددُ حيازاتها وعملياتها وحركاتِ سيولتها — هل في القاعدة محفظةٌ بغير الريال؟
  ٢ الشركاتُ غيرُ السعودية في القاعدة (رمزٌ ليس أرقاماً أو عملتُها ليست الريال): في أيّ محفظةٍ وبكم سهماً وكم عمليةً.
  ٣ السعرُ الحيّ لسهمٍ أمريكيّ من المسار نفسِه الذي تحدّث به الحيازاتُ أسعارَها (‏market_service.get_price).
  ٤ سعرُ الصرف: ‏SAR=X من ياهو بالمسار نفسِه، وشموعُه اليومية للسنة (هل يصلح لتحويل تاريخ العمليات؟).

    docker exec sp_backend python /app/scripts/audit/us_portfolio_door.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from sqlalchemy import func, select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company, Holding, Portfolio
    from app.models.transaction import CashLedger, Transaction

    async with AsyncSessionLocal() as db:
        def q(stmt):
            return db.execute(stmt.execution_options(skip_portfolio_scope=True))

        print("══ ١ المحافظ:")
        ps = (await q(select(Portfolio.id, Portfolio.currency, Portfolio.is_archived, Portfolio.is_default,
                             Portfolio.include_in_aggregate))).all()
        hc = dict((await q(select(Holding.portfolio_id, func.count()).where(Holding.quantity > 0)
                           .group_by(Holding.portfolio_id))).all())
        tc = dict((await q(select(Transaction.portfolio_id, func.count()).group_by(Transaction.portfolio_id))).all())
        lc = dict((await q(select(CashLedger.portfolio_id, func.count()).group_by(CashLedger.portfolio_id))).all())
        for p in ps:
            print(f"  محفظة {p.id}: العملة {p.currency} · مؤرشفة {bool(p.is_archived)} · افتراضية {bool(p.is_default)}"
                  f" · في التوحيد {bool(p.include_in_aggregate)} · حيازاتٌ قائمة {hc.get(p.id, 0)}"
                  f" · عمليات {tc.get(p.id, 0)} · حركاتُ سيولة {lc.get(p.id, 0)}")

        print("══ ٢ الشركاتُ غيرُ السعودية في القاعدة:")
        cs = (await q(select(Company.id, Company.symbol, Company.currency, Company.exchange))).all()
        foreign = [c for c in cs if not str(c.symbol or "").split(".")[0].isdigit() or (c.currency or "SAR") != "SAR"]
        print(f"  الشركات {len(cs)} · غيرُ السعودية {len(foreign)}")
        for c in foreign[:40]:
            hs = (await q(select(Holding.portfolio_id, Holding.quantity).where(Holding.company_id == c.id))).all()
            n = (await q(select(func.count()).select_from(Transaction).where(Transaction.company_id == c.id))).scalar()
            print(f"  {c.symbol} · العملة {c.currency} · السوق {c.exchange} · حيازات {[(h.portfolio_id, float(h.quantity or 0)) for h in hs]}"
                  f" · عمليات {n}")

    print("══ ٣ السعرُ الحيّ للأمريكيّ من مسار الحيازات:")
    from app.api.v1.endpoints.holdings import yahoo_symbol
    from app.services.market_data import market_service
    for s in ("AAPL", "NVDA", "BRK-B", "2222"):
        try:
            p = await asyncio.wait_for(market_service.get_price(yahoo_symbol(s)), 20)
            d = p.to_dict() if hasattr(p, "to_dict") else p
            print(f"  {s} ⇐ {yahoo_symbol(s)}: {({k: d.get(k) for k in ('price', 'currency', 'change_pct', 'timestamp') if k in d}) if d else 'لا سعر'}")
        except Exception as e:                                    # noqa: BLE001
            print(f"  {s}: تعذّر {type(e).__name__}: {e}")

    print("══ ٤ سعرُ الصرف (‏SAR=X):")
    try:
        p = await asyncio.wait_for(market_service.get_price("SAR=X"), 20)
        d = p.to_dict() if hasattr(p, "to_dict") else p
        print(f"  الآن: {d}")
    except Exception as e:                                        # noqa: BLE001
        print(f"  الآن: تعذّر {type(e).__name__}: {e}")
    try:
        from app.services.market_data import YahooFinanceAdapter      # النقاطُ عند محوِّل ياهو لا عند الخدمة الجامعة
        pts = await asyncio.wait_for(YahooFinanceAdapter()._fetch_chart_points("SAR=X", "1y", "1d"), 25)
        closes = [x.get("close") for x in pts if isinstance(x, dict) and x.get("close")]
        if closes:
            print(f"  سنةٌ يومية: {len(closes)} نقطة · أدنى {min(closes):.5f} · أعلى {max(closes):.5f} · أوّل {pts[0]} · آخر {pts[-1]}")
        else:
            print(f"  سنةٌ يومية: لا نقاط — {pts[:2]}")
    except Exception as e:                                        # noqa: BLE001
        print(f"  سنةٌ يومية: تعذّر {type(e).__name__}: {e}")

    print("══ ٥ بعد ‏D789 — خدمةُ الصرف المنشورة وأثرُها على القاعدة (قراءة):")
    try:
        from app.services import fx as FX
        r = await asyncio.wait_for(FX.usd_sar(), 20)
        print(f"  ‏usd_sar: {r} · {FX.SOURCE_AR.get(r.get('source'), r.get('source'))}")
        from sqlalchemy import func, select
        from app.core.database import AsyncSessionLocal
        from app.models.portfolio import Company
        from app.models.transaction import Transaction
        async with AsyncSessionLocal() as db:
            ids = [i for (i,) in (await db.execute(select(Company.id).execution_options(skip_portfolio_scope=True))).all()]
            rates = await FX.rates_for(db, ids)
            not_one = {i: v for i, v in rates.items() if v != 1.0}
            with_fx = (await db.execute(select(func.count()).select_from(Transaction).where(Transaction.fx_rate.is_not(None))
                                        .execution_options(skip_portfolio_scope=True))).scalar()
        print(f"  شركات {len(ids)} · سعرُ صرفٍ غيرُ الواحد: {not_one or 'لا شيء'} · عملياتٌ بسعر صرف: {with_fx}")
    except Exception as e:                                        # noqa: BLE001
        print(f"  تعذّر (‏D789 لم يُنشر بعد؟) {type(e).__name__}: {e}")

    # ٦ تغيّرُ اليوم للأمريكيّ — قِيس ‏NVDA ‏+31% في ٣: أيُّ «إغلاقٍ سابق» يعيده ياهو، وأيُّها يصدق؟ (قراءةٌ من المصدر مباشرة)
    print("══ ٦ الإغلاقُ السابق في ياهو (‏meta) لنطاقَي يومٍ وخمسة:")
    import httpx
    for s in ("NVDA", "AAPL", "SAR=X"):
        for rng in ("1d", "5d"):
            try:
                async with httpx.AsyncClient(timeout=12, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as c:
                    r = await c.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range={rng}&interval=1d")
                res = (r.json().get("chart") or {}).get("result") or []
                m = res[0].get("meta", {}) if res else {}
                closes = ((res[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") if res else None
                print(f"  {s} {rng}: سعر {m.get('regularMarketPrice')} · chartPreviousClose {m.get('chartPreviousClose')}"
                      f" · previousClose {m.get('previousClose')} · regularMarketPreviousClose {m.get('regularMarketPreviousClose')}"
                      f" · الإغلاقات {closes}")
            except Exception as e:                                # noqa: BLE001
                print(f"  {s} {rng}: تعذّر {type(e).__name__}: {e}")

asyncio.run(main())
