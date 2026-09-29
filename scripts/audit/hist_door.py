"""كاشفٌ (قراءةٌ فقط): مدخلاتُ صافولا السنوية، وإحصاءُ التقييمات الشاذّة، وعمقُ
التاريخ المتاح لاختبار نجوم تاسي منذ 2015 (القوائم · الأسعار · التوزيعات · تاسي).

    docker exec sp_backend python /app/scripts/audit/hist_door.py
"""
import asyncio
import json
import sys
from collections import Counter

sys.path.insert(0, "/app")


def out(tag, obj):
    print(f"@@{tag}@@" + json.dumps(obj, ensure_ascii=False, default=str)[:3000])


async def main():
    from app.services import tadawul_xbrl as X, lastgood
    from app.services.market_screener import get_cached_screener
    K = ("as_of", "col", "revenue", "ebit", "ebitda", "net_income", "net_income_parent", "eps",
         "shares_outstanding", "equity", "total_assets", "total_debt", "ending_cash")
    for kind in ("annual", "quarterly"):
        for p in X.for_symbol("2050", kind) or []:
            out("SAV_" + kind, {k: p.get(k) for k in K})
    rows = get_cached_screener() or []
    odd = [(r.get("symbol"), r.get("name"), r.get("fair_value_upside_pct"), r.get("fair_value_conf"))
           for r in rows if (r.get("fair_value_upside_pct") or 0) > 80]
    out("ODD", sorted(odd, key=lambda x: -(x[2] or 0)))
    first = Counter()
    for r in rows:
        s = str(r.get("symbol"))
        an = X.for_symbol(s, "annual") or []
        first[str(an[0].get("as_of"))[:4] if an else "none"] += 1
    out("XBRL_FIRST_YEAR", dict(sorted(first.items())))
    from app.services.market_data import market_service
    for s in ("1120", "2050", "4030"):
        for rng, iv in (("max", "1mo"), ("max", "1d")):
            try:
                pts = await market_service._yahoo()._fetch_chart_points(f"{s}.SR", rng, iv)
            except Exception as e:                                # noqa: BLE001
                pts = []; out("PX_ERR", [s, rng, iv, str(e)])
            out("PX", [s, rng, iv, len(pts or []), (pts or [{}])[0].get("date"), (pts or [{}])[-1].get("date")])
    from app.services import tasi_history as TH
    from app.services.tadawul_http import fetch
    st, body = await fetch(TH.URL_DAILY)
    tp = TH.daily_candles(json.loads(body)) if st == 200 and body else []
    out("TASI", [st, len(tp), tp[0] if tp else None, tp[-1] if tp else None])
    d = lastgood.load("div:tadawul:1120") or {}
    rs = d.get("rows") or []
    out("DIV", [len(rs), min((str(r.get("eligibility")) for r in rs), default=None)])


asyncio.run(main())
