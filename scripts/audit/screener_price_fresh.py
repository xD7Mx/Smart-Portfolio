#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D236 — صفُّ الفرز لا يعيش في كوكبٍ آخر.
#
# قال المالك: «في جدول فرز السوق… بياناتها لا تطابق صفحة السهم سواءَ آخر
# سعرٍ وغير ذلك». والسببُ مقيسٌ لا مظنون: سعرُ الصفّ **آخرُ إغلاقٍ في
# تاريخٍ** جُلب وقتَ المسح (‏`closes[-1]`)، وصفحةُ السهم تقرأ السعرَ
# اللحظيّ من كاش الأسعار. فيختلفان طولَ اليوم — وهو زمنانِ لا رقمان.
#
# والعلاجُ بلا نداءِ شبكةٍ واحد: يُقرأ من **الكاش نفسِه** الذي تملؤه
# صفحةُ السهم. ويُقاس هنا سلوكاً:
#   ١· السعرُ يصير سعرَ الصفحة  ٢· والتغيّرُ معه
#   ٣· وكلُّ ما اشتُقّ من السعر يُعاد حسابُه (البعدُ عن المتوسّطات ·
#      حدودُ العام · الفجوةُ عن السعر العادل) — فلا يخالف الصفُّ نفسَه
#   ٤· وبلا سعرٍ في الكاش لا يُخترَع شيء: الصفُّ كما هو
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


import app.services.market_screener as ms  # noqa: E402
from app.services.market_screener import _pct  # noqa: E402
from app.services import content_engine as ce  # noqa: E402

ce.fund_store_load = lambda: {}                                  # type: ignore[assignment]


class _Px:
    """ما تقرؤه صفحةُ السهم: سعرٌ لحظيٌّ وتغيّرُه."""

    def __init__(self, price, change_pct):
        self.price, self.change_pct = price, change_pct


LIVE = _Px(30.0, 2.5)
# وما تقرؤه الصفحةُ من أساسيات المزوّد — الكاشُ نفسُه بمفتاحه نفسِه.
FUND = {"eps": 2.0, "book_value": 10.0, "target_mean_price": 36.0,
        "week52_high": 31.0, "week52_low": 21.0}
# الفحوصُ ١–٧ للسعر وحدَه (بلا أساسيات)، والفحوصُ ٨–١٠ تُدخل الأساسيات —
# فسببُ كلّ فحصٍ واحدٌ ولا يُخفي أحدُهما الآخر.
_CACHE = {"price:yahoo:9999.SR": LIVE}
ms.cache.get = lambda k: _CACHE.get(k)                           # type: ignore[assignment]


async def _no_score(*_a, **_k):
    return None


ms._governance_score = _no_score                                 # type: ignore[assignment]

STALE = {
    "symbol": "9999", "sector": "الطاقة",
    "price": 25.0,                 # إغلاقُ أمسِ وقتَ المسح
    "change_pct": -1.68,           # تغيّرُ يومٍ مضى
    "sma50": 24.0, "sma200": 20.0,
    "dist_sma50": 4.17, "dist_sma200": 25.0,
    "above_sma50": True, "above_sma200": True,
    "high_52w": 28.0, "low_52w": 22.0,
    "fair_value": 36.0, "upside_pct": 44.0,
}

out = asyncio.run(ms.refresh_derived([dict(STALE)]))[0]

check(out["price"] == 30.0, "١ سعرُ الصفّ هو سعرُ صفحة السهم",
      f"كان {STALE['price']} فصار {out['price']}")
check(out["change_pct"] == 2.5, "٢ والتغيّرُ من المصدر نفسِه",
      f"كان {STALE['change_pct']}٪ فصار {out['change_pct']}٪")
check(out["dist_sma50"] == 25.0 and out["dist_sma200"] == 50.0,
      "٣ والبعدُ عن المتوسّطات يُعاد حسابُه بالسعر الجديد",
      f"م50 {out['dist_sma50']}٪ · م200 {out['dist_sma200']}٪")
check(out["high_52w"] == 30.0 and out["low_52w"] == 22.0,
      "٤ وقمّةُ العام تتّسع للسعر إن تجاوزها — لا حدٌّ أقلُّ من الواقع",
      f"قمّة {out['high_52w']} · قاع {out['low_52w']}")
check(out["upside_pct"] == 20.0,
      "٥ والفجوةُ عن السعر العادل تُقاس من السعر الحاضر",
      f"‏(36 − 30) ÷ 30 = {out['upside_pct']}٪ — كانت {STALE['upside_pct']}٪")

# ── ٦ · الاتّجاه المعاكس: لا كاشَ ⇒ لا اختلاق ────────────────────────────
_CACHE.clear()
untouched = asyncio.run(ms.refresh_derived([dict(STALE)]))[0]
check(untouched["price"] == 25.0 and untouched["upside_pct"] == 44.0
      and untouched["dist_sma50"] == 4.17,
      "٦ وبلا سعرٍ في الكاش يبقى الصفُّ كما هو — لا رقمَ يُخترع",
      f"سعر {untouched['price']} · فجوة {untouched['upside_pct']}٪")

# ── ٧ · وسعرٌ معطوبٌ لا يُقبَل ───────────────────────────────────────────
_CACHE["price:yahoo:9999.SR"] = _Px(0, 0)
zero = asyncio.run(ms.refresh_derived([dict(STALE)]))[0]
check(zero["price"] == 25.0,
      "٧ وسعرُ صفرٍ يُرفَض ولا يُقسَم عليه", f"سعر {zero['price']}")

# ── ٨ · حقولُ التقييم من سلسلة الصفحة، والمشتقُّ من السعر يُعاد ────────
# ‏(D239) قِيس على الخادم: المكرّرُ خالف في ‎32 من ‎40، والمضاعفُ في ‎33،
# وحدّا العام في ‎39 و‎38، وهدفُ المحلّلين في ‎8. والمكرّرُ دالّةُ سعرٍ —
# فيُحسب من السعر الحاضر وربحيةِ السهم لا يُنسَخ محفوظاً.
_CACHE.clear()
_CACHE["price:yahoo:9999.SR"] = LIVE
_CACHE["fund:yahoo:9999.SR"] = FUND
fresh = asyncio.run(ms.refresh_derived([dict(STALE)]))[0]
# `.get` لا `[]`: فحصٌ ينهار بـKeyError يخرج بشيفرةٍ صحيحةٍ لكن بلا
# سطرِ FAIL يُقرأ — والعطبُ يجب أن يُسمّى لا أن يُستنتَج من انهيار.
check(fresh.get("pe_ratio") == 15.0 and fresh.get("price_to_book") == 3.0,
      "٨ المكرّرُ والمضاعفُ يُحسبان بالسعر الحاضر لا يُنسَخان",
      f"‏30 ÷ 2 = {fresh.get('pe_ratio')} · 30 ÷ 10 = {fresh.get('price_to_book')}")
check(fresh.get("high_52w") == 31.0 and fresh.get("low_52w") == 21.0,
      "٩ وحدّا العام من مصدر الصفحة نفسِه — لا تاريخٌ ومزوّدٌ معاً",
      f"قمّة {fresh.get('high_52w')} · قاع {fresh.get('low_52w')}")
check(fresh.get("fair_value") == 36.0 and fresh.get("upside_pct") == 20.0,
      "١٠ وهدفُ المحلّلين من الكاش الحيّ، وفجوتُه من السعر الحاضر",
      f"هدف {fresh.get('fair_value')} · فجوة {fresh.get('upside_pct')}٪")

# ── ١١ · ولمن لم تُفتح صفحتُه: سعرُ مسح المحرّكين ──────────────────────
# ‏(D248) كاشُ الأسعار لا يحمل إلا من فُتحت صفحتُه، فبقيت بقيّةُ السوق على
# إغلاق المسح. ومسحُ المحرّكين يجلب سعرَ كلّ شركةٍ أصلاً — فيُقرأ منه.
_CACHE.clear()
ms._movers_prices = lambda: {"9999": 28.0}                       # type: ignore[assignment]
mv = asyncio.run(ms.refresh_derived([dict(STALE)]))[0]
check(mv["price"] == 28.0 and mv.get("price_source") == "movers",
      "١١ شركةٌ لم تُفتح صفحتُها تأخذ سعرَ مسح المحرّكين",
      f"سعر {mv['price']} · مصدر {mv.get('price_source')}")
_expect50 = round((28.0 - 24.0) / 24.0 * 100, 2)
check(mv["dist_sma50"] == _expect50,
      "١٢ ومشتقّاتُه تُعاد حسابُها بالسعر نفسِه",
      f"م50 {mv['dist_sma50']}٪ · المتوقَّع {_expect50}٪")

# والأولويةُ للكاش الحيّ على لقطةِ المسح: هو أحدثُ منها.
_CACHE["price:yahoo:9999.SR"] = LIVE
pri = asyncio.run(ms.refresh_derived([dict(STALE)]))[0]
check(pri["price"] == 30.0 and pri.get("price_source") == "live",
      "١٣ والكاشُ الحيُّ يتقدّم لقطةَ المسح", f"سعر {pri['price']}")

# ══ وفوقهما: «تداول» ══ (D255 · انعكاسٌ مقصودٌ في الترتيب)
# كان الكاشُ الحيُّ (ياهو) رأسَ الترتيب يومَ لم يكن للسوق مصدرٌ مباشر.
# وقد صار لِلقطة «تداول» زمنٌ محروسٌ وتغطيةٌ كاملة، وأمرَ المالك:
# «تداول ثمّ أرقام ثمّ ياهو، كلٌّ حسب ميزته» — وميزةُ «تداول» السعرُ
# نفسُه. فيُقلَب الترتيبُ عمداً ويُقاس مقلوباً.
ms._tadawul_prices = lambda: {"9999": 27.5}                      # type: ignore[assignment]
top = asyncio.run(ms.refresh_derived([dict(STALE)]))[0]
check(top["price"] == 27.5 and top.get("price_source") == "tadawul",
      "١٤ ولقطةُ «تداول» تتقدّمهما جميعاً — المُصدِرُ قبل المزوّد",
      f"سعر {top['price']} · مصدر {top.get('price_source')}")
ms._tadawul_prices = lambda: {}                                  # type: ignore[assignment]
back = asyncio.run(ms.refresh_derived([dict(STALE)]))[0]
check(back["price"] == 30.0 and back.get("price_source") == "live",
      "١٤ب وبغيابها يعود ياهو رأسَ الترتيب — لا انكسار", f"سعر {back['price']}")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
