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
            # العمودُ `quantity` لا `total_shares` — قُرئ من النموذج لا
            # خُمِّن (أوّلُ صياغةٍ سقطت بـ`AttributeError` على خادم المالك).
            select(Company.symbol, Company.company_name, Holding.quantity,
                   Holding.last_price)
            .join(Holding, Holding.company_id == Company.id)
            .where(Holding.quantity > 0))
        held = [(str(s), n, float(q or 0), float(lp or 0))
                for s, n, q, lp in res.all()]

    if not held:
        print("لا حيازاتٌ — لا فرقَ يُقاس.")
        return 0

    print(f"\n{'الرمز':<8}{'أسهم':>12}{'تداول':>10}{'المزوّد':>10}"
          f"{'المخزَّن':>10}{'الفرق':>10}  الشركة")
    tad_total = prov_total = stored_total = 0.0
    missing = []
    compared = 0          # مقارناتٌ تمّت فعلاً — لا يُحكم بغيرها
    for sym, name, qty, stored in held:
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
        # ══ ولا يُسند الغائبُ إلى الحاضر ══
        # أوّلُ صياغةٍ جمعت `tp or pp` في الطرفين، فطبعت «الفرقُ صفرٌ»
        # والمزوّدُ لم يردّ حرفاً (حصّتُه منفدة) — أخضرُ كاذبٌ سُجِّل.
        # فالمجاميعُ صارت كلٌّ على مصدره، والمقارنةُ تُعدّ.
        tad_total += (tp or 0) * qty
        prov_total += (pp or 0) * qty
        stored_total += (stored or 0) * qty
        base_ref = pp if pp is not None else (stored or None)
        diff = (tp - base_ref) if (tp is not None and base_ref) else None
        if diff is not None:
            compared += 1
        print(f"{base:<8}{qty:>12,.0f}"
              f"{(f'{tp:.2f}' if tp is not None else '—'):>10}"
              f"{(f'{pp:.2f}' if pp is not None else '—'):>10}"
              f"{(f'{stored:.2f}' if stored else '—'):>10}"
              f"{(f'{diff:+.2f}' if diff is not None else '—'):>10}  {name}")

    print(f"\nقيمةُ المحفظة بـ«تداول»:  {tad_total:,.2f} ريال")
    print(f"وبالمزوّد (ياهو/سهمك):    "
          + (f"{prov_total:,.2f} ريال" if prov_total else
             "— لم يردّ المزوّدُ لسهمٍ واحد (حصّتُه منفدة)"))
    print(f"وبالسعر المخزَّن سابقاً:   {stored_total:,.2f} ريال")
    ref = prov_total or stored_total
    label = "المزوّد" if prov_total else "المخزَّن"
    gap = tad_total - ref
    pct = (gap / ref * 100) if ref else 0.0
    print(f"الفرق عن {label}: {gap:+,.2f} ريال ({pct:+.3f}٪)")
    if missing:
        print(f"وشركاتٌ ليست في اللقطة فتبقى للمزوّد: {' · '.join(missing)}")
    print()
    if not compared:
        print("الحكم: **لا مقارنة** — لم يردّ المزوّدُ ولا سعرٌ مخزَّن."
              " ويُقال ما يُقاس: اللقطةُ أعطت سعراً لكلّ سهمٍ في المحفظة،"
              " والمزوّدُ لا شيء — فبلا هذه الطبقة تبقى المحفظةُ بلا"
              " أسعارٍ اليوم.")
        return 1
    if abs(pct) <= 1.0:
        print(f"الحكم: الفرقُ في القروش ({compared} مقارنةً) — تغيُّرُ"
              " مصدرٍ لا تغيُّرُ محفظة.")
        return 0
    print("الحكم: **الفرقُ يتجاوز واحداً بالمئة** — يُراجَع سهماً سهماً"
          " قبل التسليم، ولا يُعدّ فرقَ مصدرٍ بلا فحص.")
    return 1


raise SystemExit(asyncio.run(main()))
