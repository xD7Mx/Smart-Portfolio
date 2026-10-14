"""‏D708 — الحصادُ الأوّل لهيكل الملكية من «تداول» على الإنتاج، ثمّ ما تعرضه البطاقة.

يشغّل ‎job_ownership نفسَها (دفعةُ الليلة: أربعون من «تداول» ومتصفّحُ «أرقام» لخمسٍ ممّن لم تقرأهم) — يكتب مخازنَ الملكية وحدها
(‏tadawul_own:* · ownership:coverage)، وهو ما يكتبه الحصّادُ الليليّ نفسُه؛ لا يمسّ أرقامَ المالك. ثمّ يطبع التغطيةَ، وما يعيده بابُ
البطاقة (‏/market/ownership) لأرامكو والراجحي والحبيب: البنودَ ومصدرَها وأوّلَ صفوفها.

    docker exec sp_backend python /app/scripts/audit/ownership_harvest_door.py
"""
import asyncio
import json
import os
import sys
import time

os.environ["TZ"] = "Asia/Riyadh"                 # كخادم التطبيق (main.py) — فتعمل اللقطةُ في عمليةٍ مستقلّة
if hasattr(time, "tzset"):
    time.tzset()
sys.path.insert(0, "/app")


async def main():
    from app.scheduler.scheduler import job_ownership
    from app.services import lastgood
    from app.services.tadawul_ownership import reading
    from app.data.market_universe import MARKET_UNIVERSE as MU
    from app.data.universe import main_market
    syms = list(main_market(MU))
    before = sum(1 for s in syms if reading(s))
    t0 = time.time()
    await job_ownership()
    lastgood.flush()
    after = [s for s in syms if reading(s)]
    secs = {k: sum(1 for s in after if (reading(s) or {}).get(k)) for k in ("foreign", "board", "major_holders")}
    print(f"@@HARVEST@@ قبل {before} · بعد {len(after)} من {len(syms)} · {time.time() - t0:.0f} ثانية · البنود {secs}")
    print("@@COVER@@", lastgood.load("ownership:coverage"))
    from app.api.v1.endpoints.market import get_company_ownership
    for s in ("2222", "1120", "4013"):
        try:
            res = await get_company_ownership(s)
            body = json.loads(res.body) if hasattr(res, "body") else res
            d = (body or {}).get("data") or {}
        except Exception as e:                                     # noqa: BLE001
            print(f"\n@@CARD@@ {s} تعذّر {type(e).__name__}: {e}")
            continue
        print(f"\n@@CARD@@ {s} · المصدر {d.get('detail_source')} · بتاريخ {d.get('detail_as_of')} · "
              f"النِّسَبُ المجمّعة {[d.get(k) for k in ('institutions', 'insiders', 'public')]}")
        for k in ("major_holders", "foreign", "board"):
            rows = d.get(k) or []
            print(f"   [{k}] {len(rows)} · " + " · ".join(f"{r.get('name')} {r.get('percent')}%" + (f" ({r['position']})" if r.get("position") else "")
                                                   for r in rows[:4]))


asyncio.run(main())
