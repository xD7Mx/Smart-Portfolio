"""كاشف (قراءةٌ فقط): نصُّ إعلان قوائم ميفك ريت (4346) — لماذا لا يُقرأ — وأثرُ D577 على صافولا.

    docker exec sp_backend python /app/scripts/audit/mefic_stmt_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


def out(tag, obj):
    print(f"@@{tag}@@ " + json.dumps(obj, ensure_ascii=False, default=str)[:3000])


async def main():
    from app.services import tadawul_disclosure as D
    from app.services.reit_advisor import parse_statement, _STMT_TITLE
    n = 0
    for it in await D.list_for("4346", size=80):
        t = it.get("title") or ""
        if _STMT_TITLE.search(t) and "valuation" not in t.lower():
            det = await D.detail(it["url"])
            txt = (det or {}).get("text") or ""
            out("S", {"date": it.get("date"), "title": t[:160], "parsed": parse_statement(txt), "text": txt[60:1100]})
            n += 1
            if n >= 3:
                break
    from app.services import fair_value_models as FV
    i = await FV.gather("2050")
    out("SAVOLA_HIST", i.hist if i else None)

asyncio.run(main())
