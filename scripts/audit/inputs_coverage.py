#!/usr/bin/env python3
"""غربلةُ المدخلات: لماذا يمتنع السعرُ العادل وتصمت الحوكمة؟ (D334)

    docker exec sp_backend python /app/scripts/audit/inputs_coverage.py
    docker exec sp_backend python /app/scripts/audit/inputs_coverage.py --market 60

قال المالك: «لنحارب جملةَ بيانات غير كافية — أصبح لدينا جميعُ البيانات
الكافية وزيادة، سواءً من تداول أو أرقام». والحربُ لا تبدأ بشفرةٍ بل
بترتيب الأسباب: **أيُّ مدخلٍ ينقص، لكم شركة، وأيُّ طبقةٍ كانت تملكه**.

فلكلّ شركةٍ يُطبع: أيُّ مصدرٍ أعطى القوائمَ وكم فترة · أتُقيَّم الحوكمة
أم تمتنع · أيُقدَّر السعرُ العادل أم يمتنع وبأيّ نصٍّ · وما في التطبيق
من أرقامٍ لهذه الورقة (لقطةُ تداول · نتائجُ أرقام · صفُّ الشركة). ثمّ
**جدولُ الأسباب مرتَّباً** — فيُعرف ما يُصلَح أوّلاً لا ما يُظنّ.

ولا يكتب حرفاً في قاعدة البيانات: قراءةٌ وقياسٌ فقط.
"""
from __future__ import annotations

import asyncio
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

LIMIT = None
if "--market" in sys.argv:
    i = sys.argv.index("--market")
    LIMIT = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 60


async def main() -> int:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company, Holding
    from app.services import tadawul_market as tm
    from app.services.market_data import market_service as svc

    # ── مَن يُغربَل: المحفظةُ افتراضاً، أو عيّنةٌ من السوق بـ‎--market ──
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Company.symbol, Company.company_name)
            .join(Holding, Holding.company_id == Company.id)
            .where(Holding.quantity > 0))
        names = {str(s): n for s, n in res.all()}
    if LIMIT:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        for s in list(main_market(MARKET_UNIVERSE).keys())[:LIMIT]:
            names.setdefault(str(s), (MARKET_UNIVERSE.get(s) or {}).get("name") or s)

    rows_snap, live, at = tm.usable_rows()
    print(f"═ لقطةُ «تداول»: {len(rows_snap)} رمزاً · حيّةٌ={live} · {at} ═")
    print(f"═ الشركاتُ المغربَلة: {len(names)} ═\n")

    why_fv: Counter = Counter()
    why_gov: Counter = Counter()
    src_cnt: Counter = Counter()
    have_else: Counter = Counter()

    print(f"{'الرمز':<7}{'مصدرُ القوائم':<16}{'فترات':>6}"
          f"{'حوكمة':>8}{'عادل':>8}  سببُ الامتناع")
    for sym, name in sorted(names.items()):
        base = sym.replace(".SR", "")
        fin = None
        try:
            fin = await svc.get_financials(f"{base}.SR", allow_supplement=False)
        except Exception as e:                                    # noqa: BLE001
            fin = {"source": f"تعذّر:{type(e).__name__}"}
        src = str((fin or {}).get("source") or "لا شيء")
        periods = (fin or {}).get("periods") or []
        src_cnt[src if periods else "لا قوائم"] += 1

        # ══ مسارُ الشاشة نفسُه لا مسارٌ ثانٍ ══
        # `analyze_company` هي التي تُغذّي صفحةَ الشركة: منها الحوكمةُ
        # (‏`evaluable`) ومنها تفصيلُ السعر العادل (‏`fair_value_detail`).
        # فلا يُقاس محرّكٌ لا يراه المالك.
        gov_ok = None
        fv_val = None
        reason = ""
        try:
            from app.services.analysis import analyze_company
            an = await analyze_company(f"{base}.SR", allow_supplement=False) or {}
            gov_ok = an.get("evaluable")
            if gov_ok is False:
                conf = (an.get("confidence") or {})
                why_gov[str(conf.get("warning")
                            or "المحرّكُ امتنع (‏insufficient_data)")[:70]] += 1
            det = an.get("fair_value_detail") or {}
            fv_val = det.get("value")
            reason = str(det.get("unavailable_reason") or "")
            if fv_val is None:
                why_fv[(reason.split("—")[0] or "بلا سبب")[:70].strip()] += 1
        except Exception as e:                                    # noqa: BLE001
            why_gov[f"تعذّر: {type(e).__name__}"] += 1
            why_fv[f"تعذّر: {type(e).__name__}"] += 1

        # ── وما يملكه التطبيقُ لهذه الورقة من مصادرَ أخرى ──
        snap = rows_snap.get(base) or {}
        extra = []
        for k, lbl in (("pe_ratio", "مكرّر"), ("price_to_book", "دفترية"),
                       ("market_cap", "قيمةٌ سوقية"), ("week52_high", "مدى سنة")):
            if snap.get(k) is not None:
                extra.append(lbl)
                have_else[f"لقطة/{lbl}"] += 1
        print(f"{base:<7}{(src if periods else '—')[:15]:<16}{len(periods):>6}"
              f"{('نعم' if gov_ok else 'لا'):>8}"
              f"{('نعم' if fv_val is not None else 'لا'):>8}  "
              f"{reason[:60]}")

    print("\n═ مصادرُ القوائم ═")
    for k, n in src_cnt.most_common():
        print(f"  {n:>4}  {k}")
    print("\n═ أسبابُ امتناع السعر العادل — مرتَّبةً ═")
    for k, n in why_fv.most_common():
        print(f"  {n:>4}  {k}")
    print("\n═ أسبابُ امتناع الحوكمة — مرتَّبةً ═")
    for k, n in why_gov.most_common() or [("لا امتناع", 0)]:
        print(f"  {n:>4}  {k}")
    print("\n═ وما تملكه لقطةُ «تداول» لهذه الأوراق ═")
    for k, n in have_else.most_common() or [("لا شيء", 0)]:
        print(f"  {n:>4}  {k}")
    print("\nالحكم: يُصلَح **أعلى سببٍ في القائمة** أوّلاً — لا ما يُظنّ."
          " وكلُّ سببٍ يُقابل بطبقةٍ تملكه أو يُقال إنه ليس عندنا.")
    return 0


raise SystemExit(asyncio.run(main()))
