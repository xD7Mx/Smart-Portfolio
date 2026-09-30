"""كاشفٌ (قراءةٌ فقط): أين مكالماتُ المستثمرين/المحللين في «تداول»؟ (D559)
يبحث في إعلانات السوق بعباراتها ويطبع العناوين، ثمّ متنَ إعلانين ومرفقاتهما.

    docker exec sp_backend python /app/scripts/audit/investor_calls_door.py
"""
import asyncio
import json
import re
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import tadawul_disclosure as D
    from app.services.tadawul_http import smart_fetch, fetch
    ep = await D._endpoint()
    seen = []
    for q in ("مؤتمر", "المحللين", "المستثمرين", "conference call"):
        form = {"annoucmentType": "1_-1", "symbol": "", "sectorDpId": "", "searchType": "", "fromDate": "",
                "toDate": "", "datePeriod": "", "productType": "", "advisorsList": "", "textSearch": q,
                "pageNumberDb": "1", "pageSize": "30"}
        try:
            st, raw = await smart_fetch(ep, method="POST", data=form, referer=D.PAGE, warm=D.PAGE,
                                        headers={"X-Requested-With": "XMLHttpRequest"})
            rows = (json.loads(raw) or {}).get("announcementList") or []
        except Exception as e:                                    # noqa: BLE001
            print("@@ERR@@", q, repr(e)); continue
        tot = rows[0].get("totalCount") if rows else 0
        print(f"@@Q@@ {q} → {len(rows)} (المجموع {tot})")
        for r in rows[:14]:
            print("   ", r.get("PR_DATE"), r.get("SYMBOL"), (r.get("SHORT_DESC") or "")[:110])
            if len(seen) < 3 and re.search(r"مؤتمر|conference", r.get("SHORT_DESC") or "", re.I):
                seen.append(D.O + r["announcementUrl"])
    for u in seen[:3]:
        st, h = await fetch(u)
        d = D.parse_detail(h or "") or {}
        print("@@DETAIL@@", u[-60:])
        print((d.get("text") or "")[:1500])
        links = sorted(set(re.findall(r'href="([^"]+\.(?:pdf|mp3|mp4|pptx?)[^"]*)"', h or "", re.I)))
        ext = sorted(set(re.findall(r'https?://(?!www\.saudiexchange)[^\s"<>]+', d.get("text") or "")))
        print("@@ATTACH@@", links[:6], "@@LINKS@@", ext[:6])


asyncio.run(main())
