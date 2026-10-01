"""يسأل صقرَ أسئلةَ الحلّ على الخادم: هيكلةُ المحفظة، وبديلٌ أفضل، ثمّ يُشغّل المتابعةَ مرّةً (D568 · D569).

    docker exec sp_backend python /app/scripts/audit/advisor_now2.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")
QS = ["أريد تقليل عدد الشركات في المحفظة والاكتفاء بالقيادية، ما الذي أتخلص منه؟",
      "هل لسدافكو بديل أفضل في قطاعها؟"]


async def main():
    from app.core.database import AsyncSessionLocal
    from app.services.ai_chat import answer
    from app.services import advisor as A
    async with AsyncSessionLocal() as db:
        p = await A.portfolio_pack(db, QS[0])
        print("@@PLAN@@", json.dumps({k: p[k] for k in ("عدد الشركات", "حصيلة البيع", "ربحٌ أو خسارةٌ تُثبَّت", "وزنٌ يُعاد توزيعه٪")}, ensure_ascii=False))
        for x in p["يخرج"]:
            print("   يخرج", json.dumps(x, ensure_ascii=False, default=str)[:400])
        for k in p["يبقى"]:
            print("   يبقى", k.get("الرمز"), k.get("الشركة"), k.get("الدرجة"), "قيادية" if k.get("قيادية") else "-", k.get("الهدف الحالي٪"), "⇒", k.get("الهدف الجديد٪"))
        for q in QS:
            r = await answer(db, q, prefer_llm=True)
            print("@@Q@@", q, "@@SOURCE@@", r.get("source"))
            print(r.get("reply"))
            print("=" * 40)
    from app.services.advisor_memory import watch
    from app.services import lastgood
    print("@@ADVICES@@", lastgood.keys_with_prefix("advice:"))
    print("@@WATCH@@", await watch())


asyncio.run(main())
