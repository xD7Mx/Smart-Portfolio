"""يجمع بياناتِ اختبار النجوم منذ 2015 الآن ويطبع نتائجَه بمفاتيحَ مختلفة (D546).

    docker exec sp_backend python /app/scripts/audit/stars_bt_now.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import stars_backtest as B, tasi_stars as S
    d = await B.ensure_data(force=True)
    px = d.get("px") or {}
    firsts = sorted((v["m"][0][0] for v in px.values() if v.get("m")))
    print("أسعار:", len(px), "· أقدمُ شهر:", firsts[:1], "· منذ 2014 فأقدم:", sum(1 for f in firsts if f <= "2014-01"),
          "· تاسي:", len(d.get("tasi") or {}), min(d.get("tasi") or {"—": 0}))
    for off in ((), ("sharia",), ("large",), ("momentum",), tuple(B.FAMILY_KEYS[:2])):
        r = await B.get(set(off))
        r = r or {}
        print("@@BT@@" + json.dumps({"off": off, **{k: r.get(k) for k in ("months", "total", "tasi_total", "excess", "cagr",
                                     "tasi_cagr", "beat_pct", "max_dd", "universe", "last_pick")},
                                     "years": r.get("years")}, ensure_ascii=False))
    res = await S.get(frozenset({"sharia"}))
    print("@@LIVE_OFF@@" + json.dumps({"members": [m["symbol"] for m in res.get("members") or []],
                                        "summary": res.get("summary"), "inception": res.get("inception"),
                                        "criteria": [(c["key"], c["on"]) for c in res.get("criteria") or []]},
                                       ensure_ascii=False))


asyncio.run(main())
