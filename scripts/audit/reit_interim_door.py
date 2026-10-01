"""كاشفٌ (قراءةٌ فقط): أين القوائمُ النصف سنوية للريتات؟ إعلاناتُ الراجحي ريت ومرفقاتُها (D574).

    docker exec sp_backend python /app/scripts/audit/reit_interim_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_disclosure as D
    from app.services.tadawul_http import fetch
    for sym in ("4340", "4348"):
        items = await D.list_for(sym, 60)
        print("@@LIST@@", sym, len(items))
        hits = []
        for it in items:
            t = it.get("title") or ""
            flag = bool(re.search(r"قوائم|القوائم|financial statements|النتائج|results|أولية|interim", t, re.I))
            print("   ", it.get("date"), "★" if flag else " ", t[:120])
            if flag:
                hits.append(it)
        for it in hits[:2]:
            st, h = await fetch(it["url"])
            links = sorted(set(re.findall(r'href="([^"]+)"', h or "")))
            att = [l for l in links if re.search(r"\.pdf|wcm/connect|attach|download|\.xlsx|\.zip", l, re.I)]
            print("@@DETAIL@@", it["date"], it["title"][:80], "HTTP", st, "روابط", len(links))
            print("   مرفقات:", att[:8])
            d = D.parse_detail(h or "") or {}
            print("   ", (d.get("text") or "")[:600])


asyncio.run(main())
