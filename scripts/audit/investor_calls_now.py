"""يملأ أرشيفَ مؤتمرات المحلّلين الآن ويطبع عيّنةً وتغطية (D559).

    docker exec sp_backend python /app/scripts/audit/investor_calls_now.py
"""
import asyncio
import collections
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import investor_calls as C
    for _ in range(6):
        rep = await C.refresh(pages=7, max_details=60)
        print("@@REFRESH@@", rep)
        if not rep.get("new"):
            break
    calls = list((C.load().get("calls") or {}).values())
    st = collections.Counter(c.get("status") for c in calls)
    per = sum(1 for c in calls if c.get("period"))
    dated = sum(1 for c in calls if c.get("date"))
    print("@@COVER@@", len(calls), dict(st), "بفترة", per, "بتاريخ", dated,
          "شركات", len({c.get("symbol") for c in calls}),
          "برابط عرض", sum(1 for c in calls if c.get("deck")), "برابط حضور", sum(1 for c in calls if c.get("join")))
    for c in sorted(calls, key=lambda c: c.get("date") or "", reverse=True)[:12]:
        print("   ", json.dumps({k: c.get(k) for k in ("symbol", "date", "time", "status", "period", "join", "deck")}, ensure_ascii=False))
    print("@@UPCOMING@@", [(c["symbol"], c["date"]) for c in C.upcoming()][:15])
    for s in ("1120", "7010", "2222", "4340"):
        print("@@LINES@@", s, C.lines(s))


asyncio.run(main())
