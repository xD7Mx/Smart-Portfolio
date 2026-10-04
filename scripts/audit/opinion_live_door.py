"""كاشف: رأيُ الذكاء الحقيقيّ لثلاث شركات — هل التزم النموذجُ بالصيغة المختصرة (D584)؟ يكتب مخزَّنَ الرأي وحده.

    docker exec sp_backend python /app/scripts/audit/opinion_live_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")
HEDGE = ("قد ", "ربما", "يُحتمل", "تجدر الإشارة", "من المهم", "نصيحة", "بيد المستثمر")


async def main():
    from app.core.database import AsyncSessionLocal
    from app.api.v1.endpoints.ai import get_stock_opinion
    for s in ("2222", "4340", "2280"):
        async with AsyncSessionLocal() as db:
            r = await get_stock_opinion(s, "", db)
        d = (json.loads(r.body) if hasattr(r, "body") else r).get("data") or {}
        pts = d.get("points") or []
        lens = [len(str(p.get("t", "")).split()) for p in pts]
        txt = " ".join([str(d.get("verdict"))] + [p.get("t", "") for p in pts] + [str(d.get("action")), str(d.get("change"))])
        print("@@OP@@ " + json.dumps({"sym": s, "source": d.get("source", "ai"), "label": d.get("sentiment_label"),
                                     "verdict": d.get("verdict"), "points": pts, "action": d.get("action"),
                                     "change": d.get("change"), "n": len(pts), "max_words": max(lens or [0]),
                                     "hedges": [h for h in HEDGE if h in txt]}, ensure_ascii=False)[:2500])

asyncio.run(main())
