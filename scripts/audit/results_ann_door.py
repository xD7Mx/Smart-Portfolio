"""كاشف (قراءةٌ فقط): إعلاناتُ النتائج الربعية في «تداول» لشركاتٍ بلا ربعٍ حديث — هل تحمل جدولاً يُبنى منه.

    docker exec sp_backend python /app/scripts/audit/results_ann_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


def out(tag, obj):
    print(f"@@{tag}@@ " + json.dumps(obj, ensure_ascii=False, default=str)[:3800])


async def main():
    from app.services import tadawul_disclosure as D
    for s in ("2010", "8210", "2330"):
        items = await D.list_for(s, size=40)
        out("T" + s, [(i.get("date"), (i.get("title") or "")[:120]) for i in items[:14]])
        for it in items:
            t = (it.get("title") or "").lower()
            if ("result" in t or "النتائج" in t) and ("interim" in t or "الأولية" in t or "period" in t or "الفترة" in t):
                det = await D.detail(it["url"])
                out("R" + s, {"title": it.get("title"), "date": it.get("date"), "text": ((det or {}).get("text") or "")[40:3400]})
                break

asyncio.run(main())
