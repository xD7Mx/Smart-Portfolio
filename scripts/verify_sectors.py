"""
verify_sectors.py — تحقّق موضوعي بعد مواءمة القطاعات (governance rules v4).

يطبع، لكل شركة في محفظتك: الاسم · القطاع · النمط المطبَّق · درجة الحوكمة،
مرتّبة حسب القطاع — لترى فورًا أن التأمين/الاستثمار/الدوري/المقاولات/السياحة/
الصناعات ارتفعت لنطاقها المنطقي دون أن يُفلِت ضعيفٌ حقيقي.

التشغيل داخل الحاوية:
    docker compose exec backend python scripts/verify_sectors.py
"""

import asyncio


async def main():
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.portfolio import Company, Holding
    from app.services.governance_engine import evaluate_company
    from app.services.governance_rules import load_rules, rules_version
    from app.api.v1.endpoints.holdings import yahoo_symbol

    arche = load_rules().get("sector_archetype", {})
    print(f"governance rules version = {rules_version()}\n")

    async with AsyncSessionLocal() as db:
        companies = (await db.execute(
            select(Company).join(Holding, Holding.company_id == Company.id)
            .where(Company.status != "ARCHIVED").distinct()
        )).scalars().all()

        rows = []
        for c in companies:
            status = c.status.value if hasattr(c.status, "value") else c.status
            try:
                gov = await evaluate_company(yahoo_symbol(c.symbol), db=db,
                                             company_status=status, sector=c.sector)
            except Exception as e:
                rows.append((c.sector or "—", c.company_name, "خطأ", str(e)[:40]))
                continue
            score = (gov or {}).get("finance_score")
            evaluable = (gov or {}).get("evaluable")
            label = score if evaluable else "لا ينطبق"
            rows.append((c.sector or "—", c.company_name,
                         arche.get(c.sector, "general"), label))

    rows.sort(key=lambda r: (r[0], str(r[3])))
    print(f"{'القطاع':<16}{'النمط':<16}{'الدرجة':<10}الشركة")
    print("-" * 60)
    for sector, name, archetype, score in rows:
        print(f"{sector:<16}{archetype:<16}{str(score):<10}{name}")


if __name__ == "__main__":
    asyncio.run(main())
