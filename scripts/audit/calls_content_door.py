"""كاشفٌ (قراءةٌ فقط): هل في «تداول» مضمونُ مكالمات المستثمرين — ما نوقش ونتائجُه — أم موعدُها فقط؟ (D559)

يفتح متنَ كلّ إعلانٍ مخزَّن ويقيس: طولَ المتن دون إخلاء المسؤولية، وهل فيه كلماتُ مضمون
(توجيه، نظرة مستقبلية، أسئلة وأجوبة، تفريغ، تسجيل)، وهل له مرفقات، وإلامَ تشير روابطُه.

    docker exec sp_backend python /app/scripts/audit/calls_content_door.py
"""
import asyncio
import collections
import re
import sys

sys.path.insert(0, "/app")

CONTENT = re.compile(r"guidance|outlook|Q&A|questions and answers|transcript|recording|recorded|replay|"
                     r"highlights?|key (?:points|takeaways)|discussed the following|management (?:said|stated|noted)", re.I)


async def main():
    from app.services import investor_calls as C
    from app.services import tadawul_disclosure as D
    from app.services.tadawul_http import fetch
    calls = list((C.load().get("calls") or {}).values())
    lens, hits, attach, hosts = [], [], 0, collections.Counter()
    longest = None
    for c in calls:
        try:
            st, h = await fetch(c["url"])
        except Exception:                                         # noqa: BLE001
            continue
        d = D.parse_detail(h or "") or {}
        t = re.split(r"The Capital Market Authority and Saudi Exchange take no responsibility", d.get("text") or "")[0]
        lens.append(len(t))
        if longest is None or len(t) > longest[0]:
            longest = (len(t), c["symbol"], t)
        m = CONTENT.findall(t)
        if m:
            hits.append((c["symbol"], c.get("date"), sorted({x.lower() for x in m})))
        if re.search(r'href="[^"]+\.(?:pdf|mp3|mp4|pptx?)', h or "", re.I):
            attach += 1
        for u in re.findall(r"https?://([^/\s\"<>]+)", t):
            if "saudiexchange" not in u:
                hosts[u.lower()] += 1
    lens.sort()
    print("@@N@@", len(lens), "متوسطُ المتن", sum(lens) // max(1, len(lens)), "حرفاً · الوسيط",
          lens[len(lens) // 2] if lens else None, "· الأطول", lens[-1] if lens else None)
    print("@@ATTACH@@ إعلاناتٌ بمرفقٍ (pdf/صوت/عرض):", attach)
    print("@@CONTENT_WORDS@@", len(hits), "إعلاناً فيه كلمةُ مضمون")
    for h in hits[:15]:
        print("   ", h)
    print("@@HOSTS@@", hosts.most_common(20))
    if longest:
        print("@@LONGEST@@", longest[1], longest[0])
        print(longest[2][:2500])


asyncio.run(main())
