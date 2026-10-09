#!/usr/bin/env python3
"""تنظيفُ أصفار الأحداث المحفوظة قبل D656 — يكتب الكاشَ فقط (لا رقمَ ولا قرار).

قبل D656 كان صفرُ تعذّرٍ لحظيٍّ يُحفظ يوماً في كاش العرض والمستخرِج، فبقيت بطاقةُ «الغاز» فارغةً بعد الإصلاح. فيُبطَل كلُّ صفرٍ
محفوظ، ويُعاد حسابُ تلك الشركات بمنطق D656 (ما وصل يُحفظ · الصفرُ دقائق)، ويُطبع قبلُ وبعد."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market, is_nomu
from app.services import cache
from app.services.events_view import for_display

uni = [s for s in main_market(MARKET_UNIVERSE) if not is_nomu(s)]


async def main():
    empty = []
    for s in uni:
        for k in (f"events:view:v2:{s}", f"events:v1:{s}"):
            v = cache.get(k)
            if isinstance(v, dict) and not (v.get("events") or []):
                empty.append((s, k))
    syms = sorted({s for s, _ in empty})
    print(f"أصفارٌ محفوظة: {len(empty)} مفتاحاً في {len(syms)} شركة")
    cache.expire_keys([k for _, k in empty])                    # شاهدٌ طويلُ العمر يغلب القديمَ في الدمج (D619)
    sem = asyncio.Semaphore(3)

    async def one(s):
        async with sem:
            try:
                return s, len((await for_display(s)).get("events") or [])
            except Exception as e:                                 # noqa: BLE001
                return s, f"✘ {type(e).__name__}"
    res = await asyncio.gather(*(one(s) for s in syms))
    got = [(s, n) for s, n in res if isinstance(n, int) and n > 0]
    print(f"بعد إعادة الحساب: {len(got)} شركةً عادت لها أحداثٌ · والباقيةُ بلا أحداثٍ في سنتها أو تعذّر جلبُها الآن")
    for s, n in got[:30]:
        print(f"  {s}: {n}")
    cache.flush()


asyncio.run(main())
