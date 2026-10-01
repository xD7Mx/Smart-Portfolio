"""كاشفٌ (قراءةٌ فقط إلا ملفّاً واحداً للتشخيص): حالُ القارئ البصري — تقريرُ آخر ليلة، والأولوية،
وتغطيةُ شركات المحفظة والمراقبة، والذاكرة والحصّة؛ ثمّ يجرّب ملفّاً واحداً لسدافكو ليُرى سببُ التعثّر.

    docker exec sp_backend python /app/scripts/audit/file_reader_status.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import lastgood
    from app.services import file_reader as F
    from app.services.tadawul_pdf import mem_available_mb
    from app.services.usage_tracker import usage
    print("@@LAST_RUN@@", json.dumps(lastgood.load("know:_last_run"), ensure_ascii=False))
    keys = [k for k in lastgood.keys_with_prefix("know:") if not k.startswith("know:_")]
    done = sum(1 for k in keys if (lastgood.load(k) or {}).get("files"))
    print("@@STORE@@ مفاتيح", len(keys), "بملفّات", done)
    pr = await F._priority()
    print("@@PRIORITY@@ العدد", len(pr), "الأوائل", [s for s, _ in pr[:30]])
    for s, n in pr[:30]:
        print("   ", s, n[:20], F.coverage(s), (F.load(s) or {}).get("at"), (F.load(s) or {}).get("complete"))
    print("@@MEM@@", mem_available_mb(), "@@GEMINI@@", usage("gemini"))
    rep = {}
    n = await F.learn("2270", "سدافكو", budget=1, report=rep)
    print("@@TRY_2270@@ قُرئ", n, rep, F.coverage("2270"))
    for l in F.knowledge("2270", 10):
        print("    ", l)


asyncio.run(main())
