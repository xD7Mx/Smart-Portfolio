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
    from app.services import research_paper as RP
    for pid in rep:
        r = RD.load_report(pid)
        m = r["market"]
        t, b, tech, fin = m["tasi"], m["breadth"], m["tech"], m.get("fin") or {}
        print(f"  محفظة {pid} — {RP.day_label(r['date'])}: {r.get('headline')}")
        print(f"    تاسي {t.get('close')} ({t.get('pct')}) · قيمة {b.get('value')} · ↑{b.get('up')} ↓{b.get('down')} · نظرتنا {tech.get('view')}"
              f" · محور {round(tech['piv']['p'])} · منذ بداية العام {tech.get('ytd')}")
        print(f"    مالية: مكرّر {fin.get('pe')} · دفترية {fin.get('pb')} · عائد {fin.get('dy')} · حقوق {fin.get('roe')} · تغطية {fin.get('cover')}")
        print(f"    قطاعات {len(m.get('sectors') or [])} · أعلى {[x['name'] for x in (m.get('gainers') or [])[:3]]} · أكبر {[x['name'] for x in (m.get('heavy') or [])[:3]]}"
              f" · جلسة {len(m.get('intraday') or [])} · عالمي {len(m.get('global') or [])} · سلع {len(m.get('commodities') or [])}"
              f" · عملات {len(m.get('fx') or [])} · فائدة {len(m.get('rates') or [])} · إجراءات {len(m.get('actions') or [])}")
        print(f"    إقليمي {len((r.get('regional') or {}).get('rows') or [])} · سايبور {len(r.get('saibor') or [])} · معدّل5 {(r['averages'].get('value') or {}).get('a5')}"
              f" · محليّ {len(r.get('local') or [])} · عالميّ {len(r.get('global') or [])} · مراكز {[(x['symbol'], x['view']) for x in r.get('positions') or []][:6]}")
        print(f"    اختيارات {[(k['symbol'], k['buy'], k['target'], k['stop']) for k in r.get('picks') or []]} · {r.get('no_pick_reason') or ''}")
        for x in (r.get("local") or [])[:2]:
            print("    •", x["text"][:140])
        html = RP.render(r, "all")
        data = await RP.pdf(r)
        print(f"    الورقة {len(html)} حرفاً · PDF {len(data) if data else 'تعذّر'} بايت")
    print("المعرفة:", RD.stats())


asyncio.run(main())
