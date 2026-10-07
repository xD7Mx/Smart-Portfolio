#!/usr/bin/env python3
"""معايرةُ الثقة على القيم الممزوجة: وسيطُ |القيمة÷هدف المحلّلين − 1| لكلّ شريحةٍ من مكوّنات `confidence_of`. قارئٌ فقط."""
import asyncio, collections, statistics, sys
sys.path.insert(0, "/app")
from app.services.content_engine import fund_store_load
from app.services.market_screener import get_cached_screener
from app.services.fair_value_models import for_symbol
from app.services.analysis import confidence_of

st = fund_store_load()
rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}

async def main():
    g = collections.defaultdict(list)
    far = collections.defaultdict(lambda: [0, 0])
    for s, v in st.items():
        fv, at, px = v.get("fair_value"), (rows.get(s) or {}).get("analyst_target"), (rows.get(s) or {}).get("price")
        if not isinstance(fv, (int, float)) or not fv:
            continue
        m = await for_symbol(s) or {}
        ms = [x.get("value") for x in m.get("models") or [] if isinstance(x.get("value"), (int, float)) and x["value"] > 0]
        notes = " ".join(map(str, m.get("notes") or []))
        loser = "خاسر" in notes or "خسارة" in notes
        if len(ms) >= 3:
            med = statistics.median(ms); d = statistics.median([abs(x / med - 1) for x in ms])
        else:
            d = None
        db = "n<3" if d is None else ("≤14" if d <= .14 else "≤30" if d <= .30 else "≤45" if d <= .45 else ">45")
        keys = [f"تشتّت {db}", f"خاسرة {loser}", f"عدمُ يقين {m.get('uncertainty')}", f"عددُ النماذج {min(len(ms),5)}",
                f"الحكمُ {confidence_of(m)}", f"خاسرة={loser} · تشتّت {db}"]
        for k in keys:
            if isinstance(px, (int, float)) and px:
                far[k][0] += abs(fv / px - 1) > .6; far[k][1] += 1
            if isinstance(at, (int, float)) and at > 0:
                g[k].append(abs(fv / at - 1))
    for k in sorted(set(g) | set(far)):
        e = g.get(k) or []
        print(f"{k:<34} n_مرجع={len(e):>3} · وسيطُ الخطأ {statistics.median(e) if e else float('nan'):.0%} · "
              f"ضمن 20٪ {sum(x <= .2 for x in e) / len(e) if e else 0:.0%} · بعيدةٌ >60٪ {far[k][0]}/{far[k][1]}")
asyncio.run(main())
