#!/usr/bin/env python3
"""فرقُ المصدرَين على أرقام المالك — يُقاس قبل التسليم (D330).

    docker exec sp_backend python /app/scripts/audit/price_source_shift.py

صار مصدرُ السعر الأوّل «تداول» بدل ياهو (بأمر المالك). وهذا يمسّ **قيمةَ
محفظته** لا شاشةً فحسب — فلا يُسلَّم بكلامٍ: يُقرأ لكلّ شركةٍ في المحفظة
سعرُ اللقطة الرسمية وسعرُ المزوّد، ويُطبع الفرقُ للسهم، ثمّ **فرقُ قيمةِ
المحفظة كاملةً** ريالاً ونسبةً.

ولا يُكتب حرفٌ في قاعدة البيانات: قراءةٌ ومقارنةٌ فقط.
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")


async def main() -> int:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company, Holding
    from app.services.market_data import market_service as svc
    from app.services.tadawul_market import age_seconds, usable_rows

    rows, live, at = usable_rows()
    print(f"═ لقطةُ «تداول»: {len(rows)} رمزاً · حيّةٌ={live} · بتاريخ {at} "
          f"· عمرُها {age_seconds()}ث ═")

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Company.symbol, Company.company_name, Holding.total_shares)
            .join(Holding, Holding.company_id == Company.id)
            .where(Holding.total_shares > 0))
        held = [(str(s), n, float(q or 0)) for s, n, q in res.all()]

    if not held:
        print("لا حيازاتٌ — لا فرقَ يُقاس.")
        return 0

    print(f"\n{'الرمز':<8}{'أسهم':>12}{'تداول':>10}{'المزوّد':>10}"
          f"{'الفرق':>10}  الشركة")
    tad_total = prov_total = 0.0
    missing = []
    for sym, name, qty in held:
        base = sym.replace(".SR", "")
        t = svc._tadawul_price(base)
        # المزوّدُ يُنادى مباشرةً — لا عبر السلسلة، وإلا ردّت «تداول» نفسَها.
        p = None
        for prov in (svc.primary, svc.secondary):
            try:
                d = await prov.get_price(base if prov is svc.secondary else sym)
            except Exception:                                     # noqa: BLE001
                d = None
            if d:
                p = d.to_dict()
                break
        tp = (t or {}).get("price")
        pp = (p or {}).get("price")
        if tp is None:
            missing.append(base)
        tad_total += (tp or pp or 0) * qty
        prov_total += (pp or tp or 0) * qty
        diff = (tp - pp) if (tp is not None and pp is not None) else None
        print(f"{base:<8}{qty:>12,.0f}"
              f"{(f'{tp:.2f}' if tp is not None else '—'):>10}"
              f"{(f'{pp:.2f}' if pp is not None else '—'):>10}"
              f"{(f'{diff:+.2f}' if diff is not None else '—'):>10}  {name}")

    gap = tad_total - prov_total
    pct = (gap / prov_total * 100) if prov_total else 0.0
    print(f"\nقيمةُ المحفظة بـ«تداول»: {tad_total:,.2f} ريال")
    print(f"وبالمزوّد (ياهو/سهمك):   {prov_total:,.2f} ريال")
    print(f"الفرق: {gap:+,.2f} ريال ({pct:+.3f}٪)")
    if missing:
        print(f"وشركاتٌ ليست في اللقطة فتبقى للمزوّد: {' · '.join(missing)}")
    print()
    if abs(pct) <= 1.0:
        print("الحكم: الفرقُ في القروش — تغيُّرُ مصدرٍ لا تغيُّرُ محفظة.")
        return 0
    print("الحكم: **الفرقُ يتجاوز واحداً بالمئة** — يُراجَع سهماً سهماً"
          " قبل التسليم، ولا يُعدّ فرقَ مصدرٍ بلا فحص.")
    return 1


raise SystemExit(asyncio.run(main()))
