#!/usr/bin/env python3
"""قائمةُ بحوث الراجحي المالية كاملةً بأصنافها وسنواتها (‏D733) — قارئٌ فقط: هل في موقعها تقاريرُ شركاتٍ حديثة؟"""
import asyncio, json, os, re, sys, time
from collections import Counter
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


async def main():
    from app.services import research_reports as R
    from app.services.tadawul_http import smart_flow

    def plan():
        st, page = yield {"url": R.ARC_PAGE, "timeout": 40}
        texts = [page]
        disc = R.arc_discover(texts)
        for src in re.findall(r"<script[^>]+src=[\"'](/_next/static/[^\"']+\.js)[\"']", page or ""):
            if "key" in disc:
                break
            _, js = yield {"url": R.ARC + src, "referer": R.ARC_PAGE, "timeout": 30}
            disc = {**R.arc_discover([js]), **disc}
        out, after = [], None
        for _ in range(30):
            st3, raw = yield {"url": R.ARC_GRAPH, "method": "POST", "params": {"sc_apikey": disc["key"]}, "referer": R.ARC_PAGE,
                              "data": json.dumps({"query": R.arc_query(disc.get("root") or R.ARC_ROOT_MEASURED,
                                                                       disc.get("template") or R.ARC_TEMPLATE_MEASURED, 50, after)}),
                              "headers": {"Content-Type": "application/json"}}
            got, info = R.arc_graph_items(raw)
            try:
                res = json.loads(raw)["data"]["search"]["results"]
            except Exception:                                     # noqa: BLE001
                res = []
            for r in res:
                cats = R._names(r.get("Categories"))
                out.append(((r.get("Date") or {}).get("value", "")[-15:], cats, R._names(r.get("Companies")),
                            ((r.get("title") or {}).get("value") or "")[:60]))
            after = info.get("endCursor")
            if not info.get("hasNext") or not after:
                break
        return out
    rows = await smart_flow(plan, warm=R.ARC + "/ar", timeout=40) or []
    print("البنود:", len(rows))
    yr = lambda d: (re.search(r"(20\d\d)", d) or [None, "?"])[1]
    print("بالصنف والسنة:", Counter((yr(d), ",".join(c) or "—") for d, c, _, _ in rows).most_common(40))
    comp = [r for r in rows if r[2]]
    print("بشركة:", len(comp))
    for d, c, co, t in sorted(comp, key=lambda r: (yr(r[0]), r[0]), reverse=True)[:15]:
        print("  ", d, "|", ",".join(c), "|", ",".join(co)[:40], "|", t)


asyncio.run(main())
