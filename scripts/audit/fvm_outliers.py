#!/usr/bin/env python3
"""أبعدُ الأوراق عن المحللين: مدخلاتُها ونماذجُها لتشخيص الجذر. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fvm_outliers.py
"""
import asyncio, sys
sys.path.insert(0, "/app")

SYMS = ["7200", "2190", "2070", "8313", "4193", "1111", "2050", "1320", "2330", "1201"]


async def main():
    from app.services import fair_value_models as F
    from app.services.market_screener import get_cached_screener
    scr = {x["symbol"]: x for x in (get_cached_screener() or [])}
    for s in SYMS:
        x = scr.get(s) or {}
        i = await F.gather(s)
        print(f"\n═ {s} · {x.get('name_ar') or x.get('name')} · هدف {x.get('analyst_target')} · قائم {x.get('fair_value')} · سعر {x.get('price')}")
        if not i:
            print("   لا مدخلات"); continue
        print(f"   قطاع {i.sector} · نمط {i.archetype} · أسهم {i.shares:,.0f} · سعر {i.price} · مصدر {i.ttm_source} · توزيع {i.dps_ttm}")
        t = i.ttm or {}
        print("   TTM:", {k: t.get(k) for k in ("revenue", "net_income", "ebit", "operating_cash_flow", "capex", "eps")})
        print("   ميزانية:", {k: (i.balance or {}).get(k) for k in ("equity", "total_debt", "ending_cash", "total_assets")})
        for a in (i.annual or [])[-3:]:
            print("   سنوي", a.get("year"), {k: a.get(k) for k in ("revenue", "net_income", "equity", "eps", "shares_outstanding")})
        mc = (i.price or 0) * (i.shares or 0)
        print(f"   القيمةُ السوقية {mc:,.0f} · P/E {mc / t['net_income']:.1f}" if t.get("net_income") else f"   القيمةُ السوقية {mc:,.0f}")
        r = F.value(i) or {}
        print(f"   النماذج → {r.get('value')} · مجموعة {r.get('model_set')}")
        for m in r.get("models") or []:
            print(f"     {m['key']:16} {m['value']:10.2f}")
        for e in r.get("excluded") or []:
            print(f"     ✗ {e['key']:14} {e.get('value')} — {e.get('excluded')}")
        print("   أقران:", (i.peers or {}).get("pe"), "·", r.get("peers"))
    return 0

sys.exit(asyncio.run(main()))
