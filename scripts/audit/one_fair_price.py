#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D240 — مُنتِجٌ واحدٌ للسعر العادل: مائدةٌ واحدةٌ ومدخلاتٌ واحدة.
#
# شغّل المالكُ مسبارَ الأعمدة بعد توحيد السعر والمكرّر، فبقي عمودٌ واحدٌ
# مخالفاً: **السعرُ العادل** في ‎28 شركةٍ من ‎40 — والرقمان موجودان
# كلاهما ومختلفان (‏1111: ‎44.42 في الفرز و‎38.92 في الصفحة).
#
# والسببُ حسابانِ لا حسابٌ واحد:
#   · الصفحةُ تبني مائدةَ القطاعات من المخزن **مصفَّى على السوق الرئيسي**
#     وتقرأ مضاعفَ الشركة من المخزن وحدَه.
#   · والفرزُ يبنيها من المخزن **كلِّه** ويقرأ المضاعفَ من الكاش أوّلاً.
# فاختلف الوسيطُ واختلف المنزوعُ منه. وهذا الصنفُ لا يُعالج بتقريبِ
# حسابين بل بإلغاء أحدهما: `fields_for` هي الحسابُ، والاثنان ينزلان إليها.
#
# ويُقاس سلوكاً: المسارانِ يُشغَّلان على مخزنٍ واحدٍ وسعرٍ واحد، ويُشترط
# **تطابقُ الرقم** — لا تقاربُه.
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


SEC = "الطاقة"
# قطاعٌ من عشرٍ في السوق الرئيسي، وشركتان **خارجه** بمضاعفاتٍ شاذّة:
# لو دخلتا المائدةَ لحرّكتا الوسيطَ — وهو ما كان يفعله الفرز.
STORE = {f"1{i:03d}": {"pe_ratio": 10 + i * 0.3, "price_to_book": 1 + i * 0.03,
                       "book_value": 40.0, "eps": 3.2}
         for i in range(10)}
STORE["9999"] = {"pe_ratio": 11.0, "price_to_book": 1.1, "book_value": 40.0,
                 "eps": 3.2}
STORE["7777"] = {"pe_ratio": 95.0, "price_to_book": 19.0}   # خارج السوق الرئيسي
STORE["7778"] = {"pe_ratio": 92.0, "price_to_book": 18.0}   # خارج السوق الرئيسي

MAIN = {k: {} for k in STORE if k != "7777" and k != "7778"}

from app.data import universe as _uni  # noqa: E402
from app.data import company_sectors as _cs  # noqa: E402
from app.services import content_engine as _ce  # noqa: E402
import app.services.market_screener as ms  # noqa: E402
import app.services.relative_value as rv  # noqa: E402

_cs.SYMBOL_TO_SECTOR_AR = {k: SEC for k in STORE}                # type: ignore[assignment]
rv.__dict__["_SEC_CACHE"] = None
_uni.main_market = lambda _u: dict(MAIN)                         # type: ignore[assignment]
_ce.fund_store_load = lambda: {k: dict(v) for k, v in STORE.items()}  # type: ignore[assignment]

PRICE = 50.0
FUND = {}


async def _no_score(*_a, **_k):
    return None


ms._governance_score = _no_score                                 # type: ignore[assignment]
ms.cache.get = lambda k: (FUND if k == "fund:yahoo:9999.SR" else None)  # type: ignore[assignment]

# ── ١ · الفرزُ والصفحةُ يخرجان بالرقم نفسِه ──────────────────────────────
row = asyncio.run(ms.refresh_derived([{"symbol": "9999", "sector": SEC,
                                       "price": PRICE, "fair_value": None}]))[0]
page = rv.fields_for("9999.SR", PRICE, store=_ce.fund_store_load(), fund=FUND)
check(row.get("rel_value") is not None
      and row.get("rel_value") == page.get("rel_value"),
      "١ الفرزُ وصفحةُ السهم يخرجان بالسعر العادل نفسِه",
      f"الفرز {row.get('rel_value')} · الصفحة {page.get('rel_value')}")
check(row.get("rel_low") == page.get("rel_low")
      and row.get("rel_high") == page.get("rel_high")
      and row.get("rel_conf") == page.get("rel_conf"),
      "٢ ونطاقُهما وثقتُهما واحدة",
      f"{row.get('rel_low')}–{row.get('rel_high')} · {row.get('rel_conf')}")

# ── ٣ · والمائدةُ من السوق الرئيسيّ لا من المخزن كلِّه ───────────────────
# لو دخلت الشركتان الشاذّتان (خارج السوق) لارتفع الوسيطُ ارتفاعاً ظاهراً.
tbl_main = rv.market_table(_ce.fund_store_load())
tbl_all = rv.SectorTable({"sector": SEC, "pe": v.get("pe_ratio"),
                          "pb": v.get("price_to_book")}
                         for v in STORE.values())
med_main = tbl_main.for_sector(SEC)["pe"]["median"]
med_all = tbl_all.for_sector(SEC)["pe"]["median"]
check(med_main != med_all,
      "٣ مائدةُ السوق الرئيسيّ ليست مائدةَ المخزن كلِّه — والفرقُ ظاهر",
      f"وسيطُ الرئيسيّ {med_main:.2f} · وسيطُ الكلّ {med_all:.2f}")
# ويُحسب الوسيطُ المتوقَّعُ هنا **استقلالاً** لا يُكتَب رقماً مأخوذاً من
# المخرَج — وإلا صار الفحصُ يشهد لنفسه.
import statistics as _st  # noqa: E402
_expect = _st.median([v["pe_ratio"] for k, v in STORE.items() if k in MAIN])
check(abs(med_main - _expect) < 1e-9,
      "٤ والمُنتِجُ الواحد يستعمل الأولى — بوسيطٍ محسوبٍ استقلالاً",
      f"المُنتِج {med_main:.2f} · المحسوبُ هنا {_expect:.2f}")

# ── ٥ · والكاشُ يتقدّم المخزنَ في الاثنين معاً ───────────────────────────
FUND = {"pe_ratio": 20.0, "price_to_book": 2.0, "book_value": 25.0, "eps": 2.5}
ms.cache.get = lambda k: (FUND if k == "fund:yahoo:9999.SR" else None)  # type: ignore[assignment]
row2 = asyncio.run(ms.refresh_derived([{"symbol": "9999", "sector": SEC,
                                        "price": PRICE, "fair_value": None}]))[0]
page2 = rv.fields_for("9999.SR", PRICE, store=_ce.fund_store_load(), fund=FUND)
check(row2.get("rel_value") == page2.get("rel_value")
      and row2.get("rel_value") != row.get("rel_value"),
      "٥ ومضاعفُ الكاش يتقدّم المخزنَ في المسارين معاً",
      f"بالكاش {row2.get('rel_value')} · بالمخزن {row.get('rel_value')}")

# ── ٦ · والامتناعُ متطابقٌ أيضاً: قطاعٌ غيرُ مصنّف ───────────────────────
_cs.SYMBOL_TO_SECTOR_AR = {}                                     # type: ignore[assignment]
row3 = asyncio.run(ms.refresh_derived([{"symbol": "9999", "sector": None,
                                        "price": PRICE, "fair_value": None}]))[0]
page3 = rv.fields_for("9999.SR", PRICE, store=_ce.fund_store_load(), fund=FUND)
check(row3.get("rel_value") is None and page3.get("rel_value") is None
      and row3.get("rel_why") == page3.get("rel_why") == "القطاع غير مصنّف",
      "٦ والامتناعُ وسببُه متطابقان — لا شاشةٌ تمتنع وأخرى تحكم",
      str(row3.get("rel_why")))

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
