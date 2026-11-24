#!/usr/bin/env python3
"""حارسُ D793 — لقطةُ «تداول» قبل أوّل صفقةٍ في اليوم لا تفقد السعر.

قِيس على الخادم 2026-11-24 الساعة 09:47 بتوقيت مكّة (مرحلةُ ما قبل الافتتاح، كاشفُ tadawul_preopen_door.py):
‏lastTradePrice صفرٌ في 273 من 273 — والافتتاحُ والكمّيةُ والأعلى والأدنى والتغيّرُ أصفار — والإغلاقُ السابق موجبٌ في 273
(أرامكو: ‏0.0 · ‏26.14). فكانت اللقطةُ «حيّةً بلا سعر»: كلُّ مستعمِلٍ يسقط إلى مزوّدٍ بحصّة (ياهو بنصابٍ يوميّ، وسهمك بلا مفتاح
على الخادم)، ومسحةُ التقييم في نشرٍ ذلك الوقت كتبت 196 سعراً عادلاً لا 260، وحُفظ «آخرُ إغلاقٍ» بلا سعرٍ في 396 من 396.

  ١ صفُّ ما قبل الافتتاح: السعرُ هو الإغلاقُ السابق من الصفّ نفسِه، مسمّى الأساس (‏price_basis = prev_close)، والتغيّرُ صفر،
    ولا كمّيةَ ولا أعلى ولا أدنى مختلَقة.
  ٢ صفٌّ تداولَ اليوم: سعرُه آخرُ صفقة، بلا أساسٍ مسمّى (لا يتغيّر شيء).
  ٣ صفٌّ بلا آخرِ صفقةٍ ولا إغلاقٍ سابق: بلا سعر — لا رقمَ مصنوع.
  ٤ سعرُ الشركة من الطبقة الأولى (‏MarketDataService._tadawul_price) قبل الافتتاح: الإغلاقُ السابق بتغيّرٍ صفر ومصدرُه «تداول» —
    لا سقوطَ إلى مزوّد.

    python3 scripts/audit/tadawul_preopen_d793.py
"""
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp_d793_")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import tadawul_market as TM  # noqa: E402

# صفوفٌ على شكل مخرَج «تداول» كما قيست على الخادم في المرحلتين
PRE = {"companyRef": 2222, "lastTradePrice": 0.0, "previousClosePrice": 26.14, "todayOpen": 0.0, "precentChange": 0.0,
       "bidPrice": 26.1, "askPrice": 0.0, "volumeTraded": 0.0, "highPrice": 0.0, "lowPrice": 0.0}
LIVE = {"companyRef": 1120, "lastTradePrice": 61.4, "previousClosePrice": 60.0, "todayOpen": 60.2, "precentChange": 2.33,
        "bidPrice": 61.3, "askPrice": 61.4, "volumeTraded": 125000.0, "highPrice": 61.6, "lowPrice": 60.1}
EMPTY = {"companyRef": 4190, "lastTradePrice": 0.0, "previousClosePrice": 0.0, "precentChange": 0.0}

rows = TM.normalize([PRE, LIVE, EMPTY])
pre, live, empty = rows.get("2222", {}), rows.get("1120", {}), rows.get("4190", {})

check(pre.get("price") == 26.14 and pre.get("price_basis") == "prev_close" and pre.get("prev_close") == 26.14
      and pre.get("change_pct") == 0.0 and not any(k in pre for k in ("volume", "day_high", "day_low", "day_open")),
      "١ قبل أوّل صفقة: السعرُ هو الإغلاقُ السابق من الصفّ نفسِه، مسمّى الأساس، والتغيّرُ صفر — ولا كمّيةَ ولا أعلى ولا أدنى مختلَقة",
      str(pre))
check(live.get("price") == 61.4 and "price_basis" not in live and live.get("prev_close") == 60.0 and live.get("volume") == 125000.0,
      "٢ صفٌّ تداولَ اليوم: سعرُه آخرُ صفقة بلا أساسٍ مسمّى — لا يتغيّر شيء", str(live))
check("price" not in empty and "price_basis" not in empty,
      "٣ بلا آخرِ صفقةٍ ولا إغلاقٍ سابق: بلا سعر — لا رقمَ مصنوع", str(empty))

# الطبقةُ الأولى لسعر الشركة: تقرأ صفَّ اللقطة — فتُعطى صفَّ ما قبل الافتتاح
from app.services.market_data import MarketDataService  # noqa: E402

TM.row_for = lambda symbol: rows.get(str(symbol).replace(".SR", ""), {})  # noqa: E731
q = MarketDataService._tadawul_price("2222")
check(bool(q) and q.get("price") == 26.14 and q.get("change") == 0.0 and q.get("change_pct") == 0.0 and q.get("source") == "تداول",
      "٤ سعرُ الشركة قبل الافتتاح من «تداول» نفسِها: الإغلاقُ السابق بتغيّرٍ صفر — لا سقوطَ إلى مزوّدٍ بحصّة", str(q))

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
