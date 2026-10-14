"""كاشفُ D704 (قراءةٌ فقط): شركةٌ دخلت السوقَ الرئيسية بدليل «تداول» — ما الذي ينقصها في خطّ الإنتاج؟

قِيس (‏A/B run 38563768377 بعد النشر): «وطني للحديد والصلب» (1325) بلا درجة جودةٍ ولا سببٍ مسمّى وبلا مؤشّراتٍ فنّية. فيطبع لها:
قوائمَها في المخزن، وصفَّها في لقطة السوق، ومدخلَها في مخزن المسحة، وصفَّها في الفرز، وطولَ سلسلة أسعارها.

    docker exec sp_backend python /app/scripts/audit/new_listing_door.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main(sym="1325"):
    from app.services.tadawul_xbrl import for_symbol as X
    from app.services import tadawul_market as TM
    from app.services.content_engine import fund_store_load
    from app.services.market_screener import get_cached_screener
    from app.data.market_universe import MARKET_UNIVERSE as MU
    from app.data.universe import main_market, market_of
    a, q = X(sym, "annual") or [], X(sym, "quarterly") or []
    print(f"@@UNI@@ في الكون {sym in MU} · السوق {market_of(sym)} · في الرئيسية {sym in main_market(MU)} · {MU.get(sym)}")
    print(f"@@STMT@@ سنوية {len(a)} {[p.get('as_of') for p in a[-3:]]} · ربعية {len(q)} {[p.get('as_of') for p in q[-3:]]}")
    row = TM.row_for(sym) or {}
    print(f"@@TM@@ {({k: row.get(k) for k in ('price', 'sector_en', 'company_url', 'market_cap')})}")
    st = (fund_store_load() or {}).get(sym)
    print(f"@@STORE@@ {({k: v for k, v in (st or {}).items() if k in ('finance_score', 'finance_score_unavailable', 'fair_value', 'fair_value_unavailable', 'score_asof')}) if st else 'لا مدخل'}")
    scr = [r for r in (get_cached_screener() or []) if str(r.get("symbol")).replace(".SR", "") == sym]
    print(f"@@SCREENER@@ {'صفّ' if scr else 'لا صفّ'} · {({k: scr[0].get(k) for k in ('finance_score', 'rsi', 'fair_value')}) if scr else ''} · "
          f"صفوفُ الفرز {len(get_cached_screener() or [])}")
    try:
        from app.services.market_data import market_service
        s = await asyncio.wait_for(market_service._yahoo()._fetch_chart_points(f"{sym}.SR", "1y", "1d"), 25)
        from app.services.technical import analyze
        print(f"@@SERIES@@ {len(s or [])} يوماً · التحليلُ الفنّيّ {'موجود' if analyze(s or []) else 'لا'}")
    except Exception as e:                                         # noqa: BLE001
        print(f"@@SERIES@@ تعذّر: {type(e).__name__} {e}")


asyncio.run(main())
