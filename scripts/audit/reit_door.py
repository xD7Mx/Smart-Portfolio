"""كاشفٌ (قراءةٌ فقط): إفصاحاتُ صناديق الريت في «تداول» — عناوينُها، ومتنُ إفصاحات التقييم
وصافي قيمة الأصول والتوزيع — لبناء مستشار الريت (قراءةُ ما نشره الصندوق نفسُه).

    docker exec sp_backend python /app/scripts/audit/reit_door.py
"""
import asyncio
import json
import re
import sys

sys.path.insert(0, "/app")
SYMS = ["4340", "4349"]


async def main():
    from app.services import tadawul_disclosure as D
    from app.services.tadawul_http import smart_fetch
    ep = await D._endpoint()
    print("@@EP@@", bool(ep))
    for sym in SYMS:
        form = {"annoucmentType": "1_-1", "symbol": sym, "sectorDpId": "", "searchType": "", "fromDate": "",
                "toDate": "", "datePeriod": "", "productType": "", "advisorsList": "", "textSearch": "",
                "pageNumberDb": "1", "pageSize": "60"}
        st, raw = await smart_fetch(ep, method="POST", data=form, referer=D.PAGE, warm=D.PAGE,
                                    headers={"X-Requested-With": "XMLHttpRequest"})
        rows = (json.loads(raw) or {}).get("announcementList") or [] if st == 200 else []
        print("@@KEYS@@", sym, st, len(rows), sorted(rows[0].keys()) if rows else None)
        for r in rows[:60]:
            t = next((r.get(k) for k in ("TITLE", "ANNOUNCEMENT_TITLE", "announcementTitle", "title", "PR_TITLE") if r.get(k)), "")
            print("@@ROW@@" + json.dumps({"s": sym, "d": r.get("PR_DATE"), "t": str(t)[:160], "u": r.get("announcementUrl")}, ensure_ascii=False))
        hits = [r for r in rows if re.search(r"تقييم|صافي قيمة|valuation|NAV|net asset|توزيع|distribut",
                                              json.dumps(r, ensure_ascii=False), re.I)][:6]
        for r in hits:
            det = await D.detail(D.O + r["announcementUrl"].replace("locale=en", "locale=ar"))
            print("@@DETAIL@@" + json.dumps({"s": sym, "d": r.get("PR_DATE"), "title": (det or {}).get("title"),
                                             "text": ((det or {}).get("text") or "")[:1800]}, ensure_ascii=False))


asyncio.run(main())
