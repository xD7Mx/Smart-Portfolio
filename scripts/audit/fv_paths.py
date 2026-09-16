#!/usr/bin/env python3
"""مساراتُ السعر العادل لورقةٍ واحدة — مفتوحةً بمدخلاتها (D334).

    docker exec sp_backend python /app/scripts/audit/fv_paths.py 2222

قِيس على خادم المالك أنّ أرامكو وحدَها تمتنع في محفظته، والسببُ ليس نقصَ
بيانات بل **تضارُبَ مسارات**: «3.5× بين أعلاها وأدناها: 11.34–39.66».
والمحرّكُ يستبعد شاذَّ مضاعفِ القطاع أصلاً، فالتضارُبُ باقٍ بعده.

ولا تُخفَّف عتبةُ الامتناع اجتهاداً: تُفتَح المساراتُ أوّلاً — قيمةُ كلٍّ
منها ووزنُه والمدخلُ الذي بناه — فيُعرف **أيُّ مسارٍ معطوبُ التغذية**
(سلسلةُ تدفّقٍ ناقصة · حقوقٌ سالبة · ربحيةُ سهمٍ على عددٍ قديم) وأيُّها
صادقٌ يخالف غيرَه بحقّ. ثمّ يُصلَح المعطوبُ أو يُقال إنّ الخلافَ حقيقيّ.
"""
from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

SYM = (sys.argv[1] if len(sys.argv) > 1 else "2222").replace(".SR", "")


async def main() -> int:
    from app.services.analysis import analyze_company

    an = await analyze_company(f"{SYM}.SR", allow_supplement=False) or {}
    fv = an.get("fair_value_detail") or {}

    print(f"═ {SYM} · السعرُ العادل ═")
    print(f"  القيمةُ المعروضة: {fv.get('value')} · المدى: "
          f"{fv.get('low')}–{fv.get('high')} · تشتُّت: {fv.get('dispersion')}")
    # ══ ويُطبَع عمرُ البيانات لا تاريخُ الجلب ══ (D380)
    # كان يطبع `asof` وهو تاريخُ آخر جلبٍ — فيُخفي أن المدخلاتَ قديمة.
    print(f"  السعرُ الحاليّ: {an.get('price')}"
          f" · بياناتٌ حتى: {fv.get('data_asof') or '—'}"
          f" · عمرُها: {fv.get('age_days')} يوماً"
          f" · شائخ={fv.get('stale')}"
          f" · ثقة={fv.get('confidence') or '—'}"
          f" · (جُلبت: {fv.get('fetched_at') or fv.get('asof')})")
    if fv.get("unavailable_reason"):
        print(f"  الامتناع: {fv['unavailable_reason']}")
    if fv.get("excluded"):
        print(f"  المستبعَد: {fv['excluded']}")

    print("\n═ المسارات كما حسبها المحرّك ═")
    for m in (fv.get("methods") or []):
        print(f"  {str(m.get('name'))[:34]:<36} {m.get('value')}"
              + (f"  · وزن {m.get('weight')}" if m.get("weight") is not None else "")
              + (f"  · {str(m.get('note'))[:60]}" if m.get("note") else ""))
    if fv.get("_all_vals"):
        print(f"  (قبل الاستبعاد: {fv['_all_vals']})")

    print("\n═ مدخلاتُ الحساب — من القوائم نفسِها ═")
    prov = an.get("governance_provenance") or {}
    print(f"  مصدرُ الأساسيات: {prov.get('مصدر الأساسيات') or '—'}"
          f" · سنواتُ القوائم: {prov.get('سنوات القوائم')}"
          f" · تصحيحاتُ التدقيق: {prov.get('تصحيحات التدقيق')}")
    # والقوائمُ تُقرأ من البابِ الواحد نفسِه لتُعرض بنودُها
    from app.services.market_data import market_service as svc
    _fin = await svc.get_financials(f"{SYM}.SR", allow_supplement=False) or {}
    periods = _fin.get("periods") or []
    print(f"  ومن الباب: مصدرٌ={_fin.get('source') or '—'}"
          f" · فتراتٌ={len(periods)}")
    keys = ("year", "revenue", "net_income", "operating_cash_flow", "capex",
            "total_equity", "total_debt", "shares_outstanding", "eps")
    for p in periods[:4]:
        print("   " + " · ".join(
            f"{k}={p.get(k)}" for k in keys if p.get(k) is not None))

    info = an.get("fundamentals") or {}
    show = ("beta", "trailingPE", "priceToBook", "bookValue", "trailingEps",
            "dividendYield", "marketCap", "sharesOutstanding")
    got = {k: info.get(k) for k in show if info.get(k) is not None}
    print(f"\n  ملخّصُ المزوّد: {json.dumps(got, ensure_ascii=False)[:300]}")

    print("\nالحكم: يُقرأ العمودُ أعلاه — مسارٌ قيمتُه بعيدةٌ عن الباقي"
          " يُنظَر في مدخله: إن كان مدخلُه ناقصاً أو قديماً فالعطبُ عندنا"
          " ويُصلَح؛ وإن كان سليماً فالخلافُ حقيقيٌّ ويبقى الامتناعُ صواباً"
          " — ولا تُخفَّف العتبةُ لتخرج رقماً.")
    return 0


raise SystemExit(asyncio.run(main()))
