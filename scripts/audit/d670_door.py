#!/usr/bin/env python3
"""تحقّقُ D670 بعد النشر — قارئٌ فقط: هل بلغت إفصاحاتُ «تداول» العربيةُ المفكرةَ المعروضة، وهل تُفتح بنصّها؟"""
import asyncio, collections, re, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
AR = re.compile(r"[؀-ۿ]")


async def main():
    from app.services.content_engine import _cal_load_store, market_wide_events, clean_events
    from app.services.tadawul_disclosure import match
    store = _cal_load_store()
    td = [e for e in store.values() if e.get("source") == "تداول"]
    print(f"═ المخزن {len(store)} · «تداول» {len(td)} · بعنوانٍ عربيّ {sum(1 for e in td if AR.search(e.get('title') or ''))} "
          f"· برمز {sum(1 for e in td if e.get('symbol'))}")
    shown = clean_events(await market_wide_events())
    by = collections.Counter(e.get("source") for e in shown)
    print(f"═ المعروض {len(shown)} · بالمصدر {by.most_common(5)}")
    tds = [e for e in shown if e.get("source") == "تداول"]
    for e in tds[:6]:
        print(f"   {e.get('date')} {e.get('symbol')} {e.get('company_name')} [{e.get('type')}] · {(e.get('title') or '')[:70]}")
    ok = 0
    for e in tds[:5]:
        try:
            t = await match(e["symbol"], e["title"], e.get("date"), e.get("company_name") or "")
        except Exception as ex:                                    # noqa: BLE001
            t = None
            print(f"   تعذّر النصّ {e.get('symbol')}: {type(ex).__name__}")
        ok += bool(t and t.get("text"))
        print(f"   نصّ {e.get('symbol')}: {len((t or {}).get('text') or '')} حرفاً")
    print(f"═ بنصٍّ كامل {ok} من {min(5, len(tds))}")
    # الحدثُ الواحد من مصدرين يُعرض مرّةً
    dup = collections.Counter((e.get("symbol"), e.get("date"), " ".join((e.get("title") or "").split())) for e in shown)
    print(f"═ تكرارٌ حرفيّ في المعروض: {sum(1 for v in dup.values() if v > 1)}")


asyncio.run(main())
