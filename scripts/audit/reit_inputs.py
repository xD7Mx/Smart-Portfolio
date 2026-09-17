#!/usr/bin/env python3
"""مدخلاتُ خريطة الريت — ما يملكه التسعةَ عشرَ فعلاً (D388).

    docker exec sp_backend python /app/scripts/audit/reit_inputs.py

قال المالك: «لنضع معياراً مختصّاً لقطاع الصناديق — ما الفرق؟ نحن
وضعنا لكلّ قطاعٍ خريطةَ تقييم». وهو محقّ: «الصناديقُ العقارية
المتداولة» قطاعٌ في الدليل الرسميّ (‏19 شركةً من 273)، وخريطتُه
مكتوبةٌ في `VALUATION` منذ البداية: رسملةُ العائد 0.55 · الدخلُ
المتبقّي 0.25 · مضاعفُ القطاع 0.20، ومعامَلُ صافي الأصول 1.00.

فالخريطةُ موجودةٌ، والامتناعُ سببُه **مدخلٌ غائب** لا مسطرةٌ ناقصة:
قِيس على 4330 أن مساراته كلَّها سقطت لغياب التوزيع والحقوق. ولا
يُبنى معيارٌ على ظنٍّ بما نملك: يُطبَع لكلّ ورقةٍ ما لها وما عليها —
توزيعٌ للوحدة · حقوقٌ · أصولٌ · مطلوبات · وحداتٌ · إيجارٌ · سعرٌ —
فيُعرف **أيُّ مسارٍ يقوم بالفعل** وأيُّ مدخلٍ يُجلَب.
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

KEYS = ("dividend_per_share", "equity", "total_assets", "total_liabilities",
        "shares_outstanding", "revenue", "net_income", "operating_cash_flow")


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    from app.services import tadawul_market as tm
    from app.services.market_data import market_service as svc

    mm = main_market(MARKET_UNIVERSE)
    reits = sorted(s for s, m in mm.items()
                   if (m or {}).get("sector") == "الصناديق العقارية المتداولة")
    print(f"═ مدخلاتُ خريطة الريت ═ {len(reits)} ورقةً في الدليل الرسميّ")
    have = {k: 0 for k in KEYS}
    have["price"] = 0
    have["dividend_yield"] = 0
    for s in reits:
        row = tm.row_for(s) or {}
        px = row.get("price")
        dy = row.get("dividend_yield")
        try:
            fin = await svc.get_financials(f"{s}.SR",
                                           allow_supplement=False) or {}
        except Exception as e:                                    # noqa: BLE001
            print(f"  {s}: تعذّرت القوائمُ — {type(e).__name__}")
            continue
        per = fin.get("periods") or []
        last = per[-1] if per else {}
        got = [k for k in KEYS if last.get(k) is not None]
        for k in got:
            have[k] += 1
        if px is not None:
            have["price"] += 1
        if dy is not None:
            have["dividend_yield"] += 1
        print(f"  {s}: سعر={px} · عائدُ توزيعٍ في اللقطة={dy}"
              f" · فتراتٌ={len(per)} · مصدرٌ={fin.get('source') or '—'}"
              f" · عنده: {' · '.join(got) or 'لا شيء'}")

    n = len(reits) or 1
    print("\n═ التغطيةُ عبر القطاع ═")
    for k, v in sorted(have.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<22} {v:>3}/{n}  {'█' * (20 * v // n)}")
    print("\nالحكم: المسارُ يُبنى على مدخلٍ **مقيسِ التغطية** لا على أمنية."
          " فرسملةُ العائد تلزمها توزيعاتٌ للوحدة، وصافي الأصول يلزمه"
          " حقوقٌ أو (أصولٌ − مطلوبات) مع عددِ وحدات. وما تغطيتُه عالية"
          " يُبنى عليه المسارُ الأوّل، وما غاب يُجلَب باسمه لا يُفترَض.")
    return 0


raise SystemExit(asyncio.run(main()))
