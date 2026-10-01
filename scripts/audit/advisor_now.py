"""يسأل صقرَ (مستشارَ المحفظة) أسئلةَ المالك الحقيقية على الخادم ويطبع جوابه وموقفه المحسوب (D567).

    docker exec sp_backend python /app/scripts/audit/advisor_now.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")
QS = ["هل اضخ في الراجحي ريت في هذا المستوى السعري او استبدله او احذفه؟",
      "ماذا عن سدافكو؟ هل اغيره بشركة المراعي او انتظره لينزل اكثر؟"]


async def main():
    from app.core.database import AsyncSessionLocal
    from app.services import advisor as A
    from app.services.ai_chat import answer, build_light_context
    async with AsyncSessionLocal() as db:
        for q in QS:
            ctx = await build_light_context(db, q)
            picked = A.companies(q, ctx)
            print("@@Q@@", q, "→", [(p["symbol"], p["name"]) for p in picked])
            for p in picked:
                f = await A.dossier(db, p["symbol"], p["name"])
                st = A.stance(f)
                print("@@STANCE@@", p["symbol"], json.dumps({k: st.get(k) for k in ("action", "why", "tranches", "stop_rules")}, ensure_ascii=False))
                print("@@FILES@@", p["symbol"], f.get("files_cov"), "results_due", f.get("results_due"), "recent", f.get("recent"))
            r = await answer(db, q, prefer_llm=True)
            print("@@SOURCE@@", r.get("source"))
            print(r.get("reply"))
            print("=" * 40)


asyncio.run(main())
