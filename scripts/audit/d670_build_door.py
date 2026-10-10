#!/usr/bin/env python3
"""D670 بعد النشر: المخزنُ لم يتغيّر بعد دورة «تداول» — فيُشخَّص القارئُ ثمّ يُبنى مرّةً كما يبنيه المجدوِل.

قارئٌ أوّلاً (بلا كتابة): هل تُرجع `market_list` إفصاحاتٍ عربيةً في هذه العملية؟ ثمّ — إن أرجعت — تُنفَّذ دورةُ البنّاء نفسُها
التي ينفّذها المجدوِلُ كلَّ نصف ساعة (`build_market_calendar_tadawul`)، فتُكتب في مخزن المفكرة كما يكتبها هو. مخزنُ المفكرة
ليس من أرقام المحفظة."""
import asyncio, collections, re, sys
sys.path.insert(0, "/app")
AR = re.compile(r"[؀-ۿ]")


async def main():
    from app.services import tadawul_disclosure as D
    from app.services.content_engine import build_market_calendar_tadawul, _cal_load_store, market_wide_events, clean_events
    ep = await D._endpoint()
    print(f"═ نقطةُ الخدمة: {'وُجدت' if ep else 'تعذّرت'}")
    items = await D.market_list()
    print(f"═ market_list: {len(items)} · عربيّ {sum(1 for i in items if AR.search(i.get('title') or ''))}")
    for it in items[:3]:
        print(f"   {it['date']} {it['symbol']} · {it['title'][:70]}")
    if not items:
        return
    added = await build_market_calendar_tadawul()
    store = _cal_load_store()
    td = [e for e in store.values() if e.get("source") == "تداول"]
    print(f"═ البنّاء: +{added} · «تداول» في المخزن {len(td)} · بعنوانٍ عربيّ {sum(1 for e in td if AR.search(e.get('title') or ''))}")
    shown = clean_events(await market_wide_events())
    print(f"═ المعروض {len(shown)} · {collections.Counter(e.get('source') for e in shown).most_common(4)}")


asyncio.run(main())
