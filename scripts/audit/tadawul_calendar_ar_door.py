#!/usr/bin/env python3
"""أحداثُ «تداول» في المفكرة بالعربية (D670) — قارئٌ فقط: القائمةُ كما تصل، ثمّ عناوينُها العربية من صفحات إفصاحاتها،
وكم منها يجتاز مرشِّحَ المفكرة العربيّ (D506) قبلُ وبعد."""
import asyncio, collections, re, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
AR = re.compile(r"[؀-ۿ]")


async def main():
    from app.services.tadawul_announcements import fetch_tadawul_announcements, arabic_titles
    items = await fetch_tadawul_announcements(force=True)
    print(f"═ قائمةُ «تداول»: {len(items)} · بعنوانٍ عربيّ {sum(1 for i in items if AR.search(i.get('title') or ''))}")
    print(f"   أنماطُ الروابط: {collections.Counter(re.sub(r'[0-9]+', '#', (i.get('url') or '')[:90]) for i in items).most_common(3)}")
    before = [dict(i) for i in items[:10]]
    n = await arabic_titles(items)
    print(f"   عُرّب: {n} · بعد ذلك بعنوانٍ عربيّ {sum(1 for i in items if AR.search(i.get('title') or ''))} من {len(items)}")
    for b, a in zip(before, items[:10]):
        print(f"   {b.get('date')} {b.get('symbol')} · {(b.get('title') or '')[:60]}  ←  {(a.get('title') or '')[:70]}")


asyncio.run(main())
