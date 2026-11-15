#!/usr/bin/env python3
"""كاتبُ أرشيف التقارير (‏D749): يكتب تقريرَ كلِّ جلسةٍ من آخر ستّين بلا تقرير كما يفعل المجدولُ ليلاً، ويطبع ما كتب.
يكتب في ذاكرة قسم الأبحاث وحدها — لا يمسّ المحفظةَ ولا أرقامَها، ولا يرسل شيئاً."""
import asyncio, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


async def main():
    from app.services import research_desk as RD
    print("الأرشيف:", await RD.backfill(60))
    ds = RD.report_dates(1)
    print("أيامُ المحفظة 1:", len(ds), ds[:6], "…", ds[-3:])
    for d in ds[:3] + ds[-2:]:
        r = RD.load_report(1, d)
        m = r["market"]
        print(f"  {d}: تاسي {m['tasi'].get('close')} ({m['tasi'].get('pct') and round(m['tasi']['pct'], 2)}) · ↑{m['breadth'].get('up')} ↓{m['breadth'].get('down')}"
              f" · قطاعات {len(m.get('sectors') or [])} · محليّ {len(r.get('local') or [])} · أرشيف {bool(r.get('backfill'))} · {(r.get('headline') or '')[:70]}")


asyncio.run(main())
