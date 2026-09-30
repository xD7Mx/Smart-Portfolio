"""كاشفٌ (قراءةٌ فقط): ما تعيده قائمةُ إفصاحات «تداول» للراجحي ريت — نقطةُ البيانات والعناوين (D555).

    docker exec sp_backend python /app/scripts/audit/reit_list_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import cache
    from app.services import tadawul_disclosure as D
    print("@@EP_CACHED@@", cache.get("tadawul:annlist:ep"))
    ep = await D._endpoint()
    print("@@EP@@", ep)
    from app.services.tadawul_http import smart_fetch
    form = {"annoucmentType": "1_-1", "symbol": "4340", "sectorDpId": "", "searchType": "", "fromDate": "",
            "toDate": "", "datePeriod": "", "productType": "", "advisorsList": "", "textSearch": "",
            "pageNumberDb": "1", "pageSize": "20"}
    if ep:
        try:
            st, raw = await smart_fetch(ep, method="POST", data=form, referer=D.PAGE, warm=D.PAGE,
                                        headers={"X-Requested-With": "XMLHttpRequest"})
            print("@@RAW@@", st, len(raw or ""), (raw or "")[:600])
            rows = (json.loads(raw) or {}).get("announcementList") or []
            print("@@ROWS@@", len(rows), json.dumps([{k: r.get(k) for k in ("SYMBOL", "TITLE", "PR_DATE", "announcementUrl")}
                                                      for r in rows[:6]], ensure_ascii=False)[:2000])
        except Exception as e:                                    # noqa: BLE001
            print("@@ERR@@", repr(e))
    items = await D.list_for("4340", 80)
    print("@@LIST@@", len(items), json.dumps(items[:5], ensure_ascii=False)[:1500])


asyncio.run(main())
