#!/usr/bin/env python3
"""كاشفُ قسم الأبحاث على الخادم (‏D745): يشغّل القسمَ مرّةً كما يشغّله المجدول — يقرأ ثلاثةَ تقاريرَ جديدةٍ ثمّ يكتب تقريرَ كلّ محفظة
بلا إرسالٍ إلى تلغرام — ويطبع ما قرأ وما كتب. يكتب في ذاكرة القسم وحدها (‏research_desk/) — لا يمسّ المحفظةَ ولا أرقامَها."""
import asyncio, os, sys, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


async def main():
    from app.services import research_desk as RD
    items = await RD._all_items()
    by = {}
    for it in items:
        by.setdefault(it.get("source"), {}).setdefault(it.get("kind"), 0)
        by[it.get("source")][it.get("kind")] += 1
    print("المنشور:", len(items), by)
    got = await RD.ingest(budget=3, days=10)
    print("القراءة:", got)
    k = RD.knowledge()
    for n in k["notes"][-3:]:
        print(f"  • {n.get('date')} {n.get('source')} «{n.get('title')}»: {n.get('headline')} · نقاط {len(n.get('points') or [])} · شركات {len(n.get('companies') or [])}")
    bad = [v for v in k["read"].values() if not v.get("ok")]
    if bad:
        print("  تعذّرت:", [(b.get("source"), b.get("title")) for b in bad[-3:]])
    rep = await RD.compose_all(send=False)
    print("التقارير:", rep)
    for pid in rep:
        r = RD.load_report(pid)
        print(f"  محفظة {pid}: {r.get('headline')}")
        print(f"    السوق {len(r['market'].get('points') or [])} · محليّ {len(r.get('local') or [])} · عالميّ {len(r.get('global') or [])} · قطاعات {len(r.get('sectors') or [])}"
              f" · مراكز {len(r.get('portfolio') or [])} · متابعة {len(r.get('watch') or [])} · توصيات {len(r.get('recommendations') or [])} · مصادر {len(r.get('sources') or [])}")
        for x in (r.get("recommendations") or []):
            print(f"    توصية: {x['action']} {x['name']} — {x['why'][:120]}")
        if r.get("no_rec_reason"):
            print("    لا توصية:", r["no_rec_reason"][:160])
    print("المعرفة:", RD.stats())


asyncio.run(main())
