"""كاشف D680 · تحقّق: «الخطوطُ الحمراء» و«التحذيرات» 0/14 في حزمة المستشار — صفاتُ المراكز أم مفتاحٌ لا يصل؟ قراءةٌ فقط.

يقرأ الحقلين من analyze_company (ما تعرضه صفحةُ السهم ويقرؤه المستشار) لمراكز المحفظة، ثمّ لشركاتٍ من السوق حتى يجد
ثلاثاً لها خطٌّ أحمر أو تحذير — فإن وُجدت في السوق وغابت عن المراكز فالصفرُ صفةٌ لا عطب.
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company, Holding
    from app.services.analysis import analyze_company
    from app.data.market_universe import MARKET_UNIVERSE as MU
    async with AsyncSessionLocal() as db:
        held = sorted({str(s).replace(".SR", "") for (s,) in (await db.execute(
            select(Company.symbol).join(Holding, Holding.company_id == Company.id)
            .execution_options(skip_portfolio_scope=True))).all()})

    async def one(s):
        a = await asyncio.wait_for(analyze_company(f"{s}.SR", None, db=None), timeout=30) or {}
        return len(a.get("red_lines") or []), len(a.get("warnings") or []), (a.get("red_lines") or a.get("warnings") or [None])[0]
    tot = [0, 0]
    for s in held:
        try:
            r, w, ex = await one(s)
            tot[0] += bool(r); tot[1] += bool(w)
            print(f"   مركز {s}: خطوط {r} · تحذيرات {w}" + (f" · {str(ex)[:80]}" if ex else ""))
        except Exception as e:                                    # noqa: BLE001
            print(f"   مركز {s}: تعذّر {type(e).__name__}")
    print(f"═ المراكز {len(held)} · لها خطٌّ أحمر {tot[0]} · لها تحذير {tot[1]}")
    found = 0
    for s in list(MU)[:120]:
        if s in held:
            continue
        try:
            r, w, ex = await one(s)
        except Exception:                                         # noqa: BLE001
            continue
        if r or w:
            found += 1
            print(f"   سوق {s}: خطوط {r} · تحذيرات {w} · {str(ex)[:90]}")
            if found >= 3:
                break
    print(f"═ في السوق: {'الحقلان يحملان قيماً — فالصفرُ في المراكز صفةٌ لها' if found else 'لم يُعثر على حاملٍ في 120 — يُفحص المنتِج'}")


asyncio.run(main())
