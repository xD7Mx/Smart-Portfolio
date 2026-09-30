"""يقرأ ملفّين لشركتين بالقارئ البصريّ ويطبع المعرفةَ والذاكرةَ قبل وبعد (D557).

    docker exec sp_backend python /app/scripts/audit/file_reader_now.py
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, "/app")


async def main():
    from app.services import file_reader as F
    from app.services.tadawul_pdf import mem_available_mb, pdf_links
    from app.services.usage_tracker import usage
    for s, n in (("4340", "الراجحي ريت"), ("1120", "مصرف الراجحي")):
        links, why = await pdf_links(s)
        print("@@LINKS@@", s, len(links), why, [l["filed"] for l in F.pick(links)])
        m0, t0 = mem_available_mb(), time.time()
        rep = {}
        got = await F.learn(s, n, budget=2, report=rep)
        print("@@LEARN@@", s, got, rep, f"mem {m0:.0f}→{mem_available_mb():.0f}MB", f"{time.time() - t0:.0f}s")
        print("@@KNOW@@", s, json.dumps(F.coverage(s), ensure_ascii=False))
        for line in F.knowledge(s):
            print("   ", line)
    print("@@GEMINI@@", usage("gemini"))


asyncio.run(main())
