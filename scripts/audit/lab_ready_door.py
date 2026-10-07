"""كاشف (قراءةٌ فقط): هل المحرّكاتُ جاهزةٌ لمشاريع «مختبر الأبحاث»؟ على شركات المالك الحقيقية:
تغطيةُ التاريخ، والأداءُ مقابل تاسي، والقيمةُ العادلة ودرجةُ ثقتها لكلّ شركة. لا كتابة."""
import asyncio, sys, json
sys.path.insert(0, "/app")


async def main():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company, Holding
    from app.services.stars_backtest import lab
    async with AsyncSessionLocal() as db:
        syms = sorted({str(s).replace(".SR", "") for (s,) in (await db.execute(
            select(Company.symbol).join(Holding, Holding.company_id == Company.id).where(Holding.quantity > 0)
            .execution_options(skip_portfolio_scope=True))).all()})
    print("شركاتُ المالك:", len(syms), syms)
    for start in ("2015-01", "2020-01", "2024-01"):
        r = await lab(syms, start)
        if not r:
            print(start, "→ لا بيانات (المحرّك يُحمّل التاريخ)"); continue
        print(f"{start} → أشهر {r.get('months')} · العائد {r.get('total')}٪ مقابل تاسي {r.get('tasi_total')}٪ · "
              f"المركّب {r.get('cagr')}٪/{r.get('tasi_cagr')}٪ · أقصى تراجع {r.get('max_dd')}٪ · غائبة {r.get('missing')}")
    f = (r or {}).get("forward") or {}
    print(f"التوقّع: {f.get('n')} شركة · موثوقةُ الثقة {f.get('reliable_n')} · صعودٌ موثوق {f.get('upside_reliable')}٪")
    from collections import Counter
    print("درجاتُ الثقة:", dict(Counter(i.get("conf") for i in f.get("items") or [])))
    for i in f.get("items") or []:
        print("  ", json.dumps({k: i.get(k) for k in ("symbol", "name", "price", "fair_value", "upside", "conf", "decision")}, ensure_ascii=False))

asyncio.run(main())
