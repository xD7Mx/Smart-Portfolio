"""كاشف (قراءةٌ فقط): لماذا لم تُقرأ نتائجُ سابك والاتصالات وغيرها من إعلاناتها — D580.

    docker exec sp_backend python /app/scripts/audit/results_ann_debug.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_disclosure as D
    from app.services import results_announcements as R
    for s in ("2010", "7010", "8050", "6014", "7204"):
        items = await D.list_for(s, size=30)
        hits = [i for i in items if R.is_results_title(i.get("title") or "")]
        info = {"sym": s, "n": len(items), "hits": len(hits), "titles": [(i.get("title") or "")[:100] for i in items[:6]]}
        if hits:
            det = await D.detail(hits[0]["url"])
            txt = (det or {}).get("text") or ""
            info["parsed"] = R.parse(txt, hits[0].get("title") or "")
            info["text"] = txt[:1500]
            info["title"] = hits[0].get("title")
        print("@@D@@ " + json.dumps(info, ensure_ascii=False)[:3500])

asyncio.run(main())
