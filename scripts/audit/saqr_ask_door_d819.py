#!/usr/bin/env python3
"""كاشفُ D819 على الخادم — «سؤالُ صقر على تلغرام لا يعطيني نتيجةً ملموسة» (المالك 2026-11-24).

يطرح على صقر — من الباب نفسِه الذي تمرّ منه القناة (‏ai_chat.answer · prefer_llm) — أسئلةً كالتي يسألها المالك، ويطبع لكلٍّ:
مصدرَ الجواب (‏ai · rule · advisor · timeout …) وزمنَه وطولَه وأوّلَ سطوره؛ وحالَ النموذج: اسمُه واحتياطيّاه وحصّتُه، وحجمُ السياق المرسَل،
وهل يعرف السياقُ فرصَ صقر ومسحَه وتقريرَه اليوميّ. لا يكتب شيئاً في المحفظة (الجلسةُ تُلغى في آخرها).

    docker exec sp_backend python /app/scripts/audit/saqr_ask_door_d819.py
"""
import os
import time

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()

import asyncio  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, "/app")

QS = ["ما أفضل فرصة اليوم في السوق الأمريكي؟", "هل أشتري أرامكو الآن؟", "وش رأيك في NVDA؟", "كيف محفظتي اليوم؟",
      "أعطني صفقة عقد خيارات بميزانية 500 دولار", "ما نظرتك لتاسي هذا الأسبوع؟"]


async def main():
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.services import ai_chat as C
    from app.services.usage_tracker import can_call
    print("══ ١ النموذج")
    print("   الأساسيّ:", settings.AI_MODEL, "· الاحتياطيّان:", getattr(settings, "AI_MODEL_FALLBACKS", "—"), "· الحصّةُ تسمح:", can_call("gemini"))
    async with AsyncSessionLocal() as db:
        async def no_commit():
            await db.rollback()
        db.commit = no_commit
        try:
            ctx = await C.build_context(db, QS[0])
            keys = list(ctx.keys())
            js = json.dumps(ctx, ensure_ascii=False, default=str)
            print(f"   السياقُ الكامل: {len(keys)} كتلة · {len(js)} حرفاً")
            saqrish = [k for k in keys if any(w in k for w in ("صقر", "فرص", "مسح", "التقرير اليومي", "عقود", "خيارات"))]
            print("   كتلٌ تخصّ صقرَ وفرصَه:", saqrish or "لا شيء")
        except Exception as e:                                  # noqa: BLE001
            print("   بناءُ السياق تعذّر:", type(e).__name__)
        print("══ ٢ الأسئلة")
        for q in QS:
            t0 = time.monotonic()
            try:
                r = await asyncio.wait_for(C.answer(db, q, prefer_llm=True), 90)
            except Exception as e:                              # noqa: BLE001
                r = {"reply": f"استثناء {type(e).__name__}", "source": "error"}
            txt = str((r or {}).get("reply") or "")
            print(f"   «{q}» · المصدر {r.get('source', '—')} · {time.monotonic() - t0:.1f}ث · {len(txt)} حرفاً")
            for ln in [x for x in txt.splitlines() if x.strip()][:3]:
                print("      ", ln[:140])
        await db.rollback()
    print("══ انتهى")


asyncio.run(main())
