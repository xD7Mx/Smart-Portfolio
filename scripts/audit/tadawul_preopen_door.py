#!/usr/bin/env python3
"""كاشفُ لقطة «تداول» في كلّ مرحلة (قراءةٌ لا تكتب شيئاً).

قِيس في نشر 2026-11-24 الساعة 09:38 بتوقيت مكّة (مرحلة ما قبل الافتتاح): سلسلةُ المعلومة «اللقطةُ الحيّة — رئيسيّ=273 · له
سعرٌ=0 · حيّة=True»، ومسحةُ التقييم في النشر نفسِه 196 سعراً عادلاً لا 260. فما الذي تحمله الصفوفُ في هذه المرحلة؟

  ١ المرحلةُ الآن بالحاكم الواحد (‏market_phase) وزمنُ الخادم.
  ٢ صفوفُ المصدر كما وصلت: لكلّ حقلٍ سعريٍّ كم صفّاً موجبٌ وكم صفرٌ وكم فارغ — ومثالُ أرامكو.
  ٣ ما يُعطيه ‏usable_rows للمستعمِلين: أحيّةٌ هي، وكم صفّاً بسعرٍ وبإغلاقٍ سابق.
  ٤ آخرُ إغلاقٍ محفوظ (‏lastgood): زمنُه وكم صفّاً فيه بسعر.

    docker exec sp_backend python /app/scripts/audit/tadawul_preopen_door.py
"""
import asyncio
import os
import sys
import time
from datetime import datetime

# بتوقيت مكّة قبل الاستيراد كخادم التطبيق — عمليةُ docker exec لا تمرّ بـmain.py فساعتُها UTC (طريقةُ الجلب ٧)
os.environ["TZ"] = "Asia/Riyadh"
if hasattr(time, "tzset"):
    time.tzset()

sys.path.insert(0, "/app")

FIELDS = ("lastTradePrice", "previousClosePrice", "todayOpen", "precentChange", "bidPrice", "askPrice",
          "volumeTraded", "highPrice", "lowPrice")


async def main():
    from app.services import lastgood
    from app.services import tadawul_market as TM
    from app.services.market_phase import market_phase

    now = datetime.now()
    print(f"══ ١ المرحلة: {market_phase((now.weekday() + 1) % 7, now.hour * 60 + now.minute)} · زمنُ الخادم {now.isoformat(timespec='seconds')}")

    rows, why = await TM.fetch_rows()
    rows = [r for r in rows if isinstance(r, dict)]
    print(f"══ ٢ صفوفُ المصدر: {len(rows)}" + (f" · تعذّر: {why}" if why else ""))
    for k in FIELDS:
        vals = [r.get(k) for r in rows]
        pos = sum(1 for v in vals if TM._pos(v) is not None)
        zero = sum(1 for v in vals if TM._num(v) == 0)
        empty = sum(1 for v in vals if v in (None, ""))
        print(f"  {k}: موجب {pos} · صفر {zero} · فارغ {empty}")
    aramco = next((r for r in rows if "2222" in str(r.get("companyRef") or r.get("symbol") or "")), None)
    if aramco:
        print("  أرامكو كما وصلت:", {k: aramco.get(k) for k in FIELDS})

    got, live, at = TM.usable_rows()
    print(f"══ ٣ ما يُعطاه المستعمِلون: صفوف {len(got)} · حيّة {live} · زمنُها {at}"
          f" · بسعر {sum(1 for r in got.values() if r.get('price'))} · منها الإغلاقُ السابق قبل أوّل صفقة (D793)"
          f" {sum(1 for r in got.values() if r.get('price_basis') == 'prev_close')} · بإغلاقٍ سابق {sum(1 for r in got.values() if r.get('prev_close'))}")

    rec = lastgood.load(TM.STORE_KEY, max_age_seconds=TM.CLOSE_MAX_DAYS * 86400)
    if isinstance(rec, dict) and isinstance(rec.get("rows"), dict):
        print(f"══ ٤ آخرُ إغلاقٍ محفوظ: {rec.get('at')} · صفوف {len(rec['rows'])} · بسعر {sum(1 for r in rec['rows'].values() if r.get('price'))}")
    else:
        print("══ ٤ آخرُ إغلاقٍ محفوظ: لا شيء")


asyncio.run(main())
