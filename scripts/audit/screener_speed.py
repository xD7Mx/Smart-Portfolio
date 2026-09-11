#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D243 — الفرزُ يُفتح بسرعة: يُقاس بالزمن لا بالانطباع.
#
# قال المالك: «فرزُ السوق للأسهم يواجه صعوبة، اجعلها سلسة ويفتح بسرعة».
# والثقلُ من عملي: إنعاشُ الحقول (‏D226 · D236 · D239 · D240) يجري **مع
# كلّ طلب** على ‎270 صفّاً، وفيه لكلّ صفٍّ تشغيلُ محرّك الحوكمة وقراءةُ
# كاشٍ ومائدةُ قطاعات. وهو حسابٌ بلا شبكة — و«بلا شبكة» ليست «بلا وقت».
#
# فطبقتان من الحفظ: مخرَجُ الإنعاش تسعين ثانية (أقصرُ من عمر أيّ مدخلٍ
# يقرؤه فلا يشيخ عن صفحة السهم)، ودرجةُ الحوكمة لكلّ رمزٍ ساعةً (القوائمُ
# لا تتغيّر في ساعة).
#
# ويُقاس بالزمن: الفتحةُ الثانية دون عشرِ ملّي ثانية، وبلا تشغيلٍ واحدٍ
# للمحرّك. والاتّجاه المعاكس: تغيّرُ الصفوف لا يُخدَم من محفوظٍ قديم.
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
import time  # noqa: E402

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
from app.data import company_sectors as cs  # noqa: E402
from app.data import universe as uni  # noqa: E402
from app.services import content_engine as ce  # noqa: E402

N = 270
STORE = {f"{1000 + i}": {"pe_ratio": 10 + i % 20, "price_to_book": 1 + i % 5,
                         "book_value": 20.0, "eps": 2.0} for i in range(N)}
ce.fund_store_load = lambda: dict(STORE)                         # type: ignore[assignment]
cs.SYMBOL_TO_SECTOR_AR = {s: "الطاقة" for s in STORE}            # type: ignore[assignment]
uni.main_market = lambda _u: {s: {} for s in STORE}              # type: ignore[assignment]

calls = {"n": 0}


async def _gov(ysym, sector):
    calls["n"] += 1
    await asyncio.sleep(0.004)      # كلفةُ المحرّك الحقيقية تقريباً
    return 70.0


ms._governance_score = _gov                                      # type: ignore[assignment]
ms.cache.get = ms.cache.get                                      # الكاشُ الحقيقيّ

ROWS = [{"symbol": s, "sector": "الطاقة", "price": 50.0, "sma50": 48.0,
         "high_52w": 60.0, "low_52w": 40.0, "fair_value": None} for s in STORE]

t0 = time.perf_counter()
asyncio.run(ms.refresh_derived_cached([dict(r) for r in ROWS]))
first = (time.perf_counter() - t0) * 1000
first_calls = calls["n"]

calls["n"] = 0
t1 = time.perf_counter()
again = asyncio.run(ms.refresh_derived_cached([dict(r) for r in ROWS]))
second = (time.perf_counter() - t1) * 1000

check(len(again) == N, "١ الفتحةُ الثانية تُعيد الصفوفَ كلَّها", f"{len(again)} صفّاً")
check(second < 10, "٢ ودون عشرِ ملّي ثانية",
      f"الأولى {first:.0f} ms · الثانية {second:.1f} ms")
check(calls["n"] == 0, "٣ وبلا تشغيلٍ واحدٍ لمحرّك الحوكمة",
      f"الأولى {first_calls} تشغيلاً · الثانية {calls['n']}")

# ── ٤ · والاتّجاه المعاكس: لا يُخدَم عددٌ مختلفٌ من محفوظٍ قديم ─────────
half = asyncio.run(ms.refresh_derived_cached([dict(r) for r in ROWS[:5]]))
check(len(half) == 5, "٤ وصفوفٌ مختلفةُ العدد لا تُخدَم من المحفوظ",
      f"{len(half)} صفّاً")

# ── ٥ · ودرجةُ الحوكمة نفسُها محفوظةٌ لساعة (‏الطبقةُ الثانية) ──────────
src = (ROOT / "backend/app/services/market_screener.py").read_text(encoding="utf-8")
# صار الامتناعُ يُحفظ بعلامةٍ صريحةٍ ("-") تُفرّغ العمود (‏D247)، فالفحصُ
# يسأل عن **الحفظ ساعةً** لا عن سطرٍ بعينه.
check('screener:gov:' in src and 'cache.set(sk, "-", 3600)' in src
      and 'cache.set(sk, out, 3600)' in src,
      "٥ ودرجةُ الحوكمة لكلّ رمزٍ محفوظةٌ ساعةً — والامتناعُ يُحفظ كالحضور")

# ── ٦ · وما خرج عن الشاشة لا يُرسَم — وحدُّ الصفوف اتّسع للسوق ──────────
css = (ROOT / "frontend/src/styles/globals.css").read_text(encoding="utf-8")
page = (ROOT / "frontend/src/pages/MarketPage.tsx").read_text(encoding="utf-8")
check("content-visibility: auto" in css and "scr-row" in page,
      "٦ وصفوفُ الجدول لا تُرسَم خارج الشاشة")
check("const ROW_CAP = 500" in page,
      "٧ وحدُّ العرض يتّسع للسوق كلِّه — لا سبعين شركةً محجوبةً للأداء")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
