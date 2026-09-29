"""لقطةُ ما تستلمه الشاشات فعلاً (قراءةٌ فقط) — لتُرسم محلّياً بالبيانات الحقيقية.

تُنادى دوالُّ النقاط نفسُها وتُطبع مخرجاتُها JSON بين علامتين، سطراً لكلّ نقطة.

    docker exec sp_backend python /app/scripts/audit/views_snapshot.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")

SYMS = ["1120", "2050", "4200"]


async def main():
    from app.api.v1.endpoints import market as M
    calls = [("/api/v1/market/tasi-stars", M.get_tasi_stars())]
    for s in SYMS:
        calls += [(f"/api/v1/market/quarter-reports/{s}", M.get_quarter_reports(s)),
                  (f"/api/v1/market/quarter-report/{s}", M.get_quarter_report(s)),
                  (f"/api/v1/market/dividends/{s}", M.get_company_dividends(s))]
    for path, coro in calls:
        try:
            res = await coro
        except Exception as e:                                    # noqa: BLE001
            res = {"success": False, "error": f"{type(e).__name__}: {e}"}
        print("@@VIEW@@" + json.dumps({"path": path, "body": res}, ensure_ascii=False, default=str))
    # صافولا: مدخلاتُ سعرها العادل (+194٪) — لمعرفة سببه
    from app.services import fair_value_models as F
    r = await F.for_symbol("2050") or {}
    print("@@SAVOLA@@" + json.dumps({k: r.get(k) for k in ("value", "price", "upside", "low", "high", "count", "uncertainty",
                                                           "families", "model_set", "weights_kind", "notes")},
                                    ensure_ascii=False, default=str)[:4000])
    for m in (r.get("models") or [])[:20]:
        print("@@SAVOLA_M@@" + json.dumps({k: m.get(k) for k in ("key", "name", "family", "value", "assumptions")},
                                          ensure_ascii=False, default=str)[:900])


asyncio.run(main())
