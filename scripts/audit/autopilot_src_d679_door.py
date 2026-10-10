"""كاشف D679 · تشخيص: لماذا «القادم» و«الثبات» فارغان في حزمة المستشار (0/14 في autopilot_pack_d679_door)؟ قراءةٌ فقط.

لكلّ مركزٍ من المحفظة الافتراضية: زمنُ مفكرة الشركة وعددُ أحداثها وكم منها قادمٌ ومفاتيحُ تاريخها، وزمنُ محرّك الحوكمة
ووسمُ الثبات منه، وعنوانُ أوّل حدثٍ جوهريّ من عرض الصفحة (‏events_view) مقابل الخام.
"""
import asyncio
import json
import sys
import time
from datetime import date

sys.path.insert(0, "/app")


async def main():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company, Holding
    from app.api.v1.endpoints import market as M
    from app.services.governance_engine import evaluate_company
    from app.services.events_view import for_display
    from app.services.material_events import events_for
    async with AsyncSessionLocal() as db:
        syms = [s for (s,) in (await db.execute(select(Company.symbol).join(Holding, Holding.company_id == Company.id)
                                                .execution_options(skip_portfolio_scope=True).distinct())).all()][:6]
    today = date.today().isoformat()
    for s in syms:
        sym = str(s).replace(".SR", "")
        t0 = time.perf_counter()
        try:
            r = await M.get_company_events(sym, "")
            rows = (json.loads(r.body) if hasattr(r, "body") else r).get("data") or []
            up = [e for e in rows if str(e.get("date") or "")[:10] >= today]
            keys = sorted({k for e in rows[:5] for k in e})
            cal = f"{len(rows)} حدثاً · قادمٌ {len(up)} · {time.perf_counter() - t0:.1f}ث · مفاتيح {keys[:10]} · أوّلُ تاريخ {rows[0].get('date') if rows else None}"
        except Exception as e:                                    # noqa: BLE001
            cal = f"تعذّر {type(e).__name__} بعد {time.perf_counter() - t0:.1f}ث"
        t0 = time.perf_counter()
        try:
            g = await evaluate_company(sym) or {}
            st = f"{(g.get('confidence') or {}).get('stability_label')} · {time.perf_counter() - t0:.1f}ث"
        except Exception as e:                                    # noqa: BLE001
            st = f"تعذّر {type(e).__name__}"
        try:
            v = (await for_display(sym, limit=1) or {}).get("events") or []
            raw = (await events_for(sym) or {}).get("events") or []
            ttl = f"العرض: {str(v[0].get('title'))[:70] if v else '—'} · الخام: {str(raw[0].get('title'))[:50] if raw else '—'}"
        except Exception as e:                                    # noqa: BLE001
            ttl = f"تعذّر {type(e).__name__}"
        print(f"═ {sym}\n   المفكرة: {cal}\n   الثبات: {st}\n   {ttl}")


asyncio.run(main())
