"""كاشف (قراءةٌ فقط): عناوينُ إعلانات الصناديق التي لم تُقرأ لها قوائم — لنعرف صيغتَها.

    docker exec sp_backend python /app/scripts/audit/reit_titles_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


def out(tag, obj):
    print(f"@@{tag}@@ " + json.dumps(obj, ensure_ascii=False, default=str)[:2500])


async def main():
    from app.services import tadawul_disclosure as D
    from app.services.reit_advisor import _STMT_TITLE, parse_statement
    for s in ("4331", "4332", "4333", "4334", "4339", "4342", "4345", "4337"):
        items = await D.list_for(s, size=80)
        out("TITLES", {"sym": s, "n": len(items), "t": [(i.get("date"), (i.get("title") or "")[:90]) for i in items[:25]]})
        for it in items:
            t = it.get("title") or ""
            if _STMT_TITLE.search(t) or "مالي" in t or "financial" in t.lower():
                det = await D.detail(it["url"])
                txt = (det or {}).get("text") or ""
                out("STMT_TXT", {"sym": s, "title": t[:120], "parsed": parse_statement(txt), "text": txt[:900]})
                break

asyncio.run(main())
