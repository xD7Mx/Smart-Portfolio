"""يبني «نجوم تاسي» الآن (D538): فرزٌ كاملٌ بعائد 12 شهراً ثمّ سلّةٌ مثبَّتة.

    docker exec sp_backend python /app/scripts/audit/stars_now.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services.market_screener import compute_screener
    from app.services import tasi_stars as S
    rows = await compute_screener() or []
    print("صفوفُ الفرز:", len(rows), "· لها عائد 12ش:", sum(1 for r in rows if r.get("ret_12m") is not None))
    rec = await S.build(force=True)
    print("تاسي 12ش:", rec.get("tasi_ret_12m"), "· السلّة:", len(rec.get("members") or []), rec.get("error") or "")
    for m in rec.get("members") or []:
        print(f"  #{m.get('rank')} {m['symbol']} {m.get('name')} · عادل {m['upside']}% · 12ش {m['ret_12m']}% ({m['excess']:+}) · درجة {m['finance_score']} · {m.get('confidence')} · {m['score']}")
    print("تحت المراقبة:", " ".join(f"#{m.get('rank')} {m['symbol']}" for m in rec.get("watch") or []))


asyncio.run(main())
