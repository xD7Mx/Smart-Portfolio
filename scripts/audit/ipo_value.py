#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D231 — حاسبةُ الاكتتاب تقيس بالمسطرة نفسِها.
#
# بأمر المالك: شاشةٌ في «الحاسبات» تُدخل فيها مدخلاتُ نشرة الإصدار فتقرأ
# موضعَ سعر الطرح من نظائر القطاع. وخطرُها بيّنٌ: أداةٌ جديدةٌ تُغري بنسخ
# الحساب — مسطرةٌ ثانيةٌ تنحرف عن السوق فيقرأ المالكُ رقمين لقياسٍ واحد،
# وهو العطبُ الذي تكرّر في هذا التطبيق أكثرَ من غيره (‏D147 · D174 · D223).
#
# فيُقاس السلوكُ: تُشغَّل الشاشةُ والمحرّكُ على مدخلاتٍ متكافئةٍ ويُشترط
# **تطابقُ الرقم**. ثم ثلاثةٌ خاصّةٌ بالاكتتاب:
#   · الشركةُ غيرُ المدرَجة لا تُنزَع من عيّنة قطاعها (ليست فيها)
#   · الخسارةُ تُسقط مسارَ المكرّر ولا تُسقط التقييم — ولا تبلغ ثقةً مرتفعة
#   · وسعرُ الطرح يُعاد موضعاً ورقماً، وبلا سعرٍ لا يُختلق فرق
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import statistics  # noqa: E402
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


# ── مخزنٌ محكوم: قطاعٌ من عشرٍ متقارب، وآخرُ من ثلاثٍ (دون الحدّ) ────────
SEC, THIN = "الطاقة", "قطاعٌ نحيل"
STORE = {f"1{i:03d}": {"pe_ratio": 10 + i * 0.3, "price_to_book": 1 + i * 0.03}
         for i in range(10)}
STORE.update({f"2{i:03d}": {"pe_ratio": 12.0, "price_to_book": 1.5} for i in range(3)})
SECTORS = {k: (SEC if k.startswith("1") else THIN) for k in STORE}

from app.services import content_engine as _ce  # noqa: E402
from app.data import company_sectors as _cs  # noqa: E402
from app.services.relative_value import SectorTable, relative_value  # noqa: E402

_ce.fund_store_load = lambda: dict(STORE)                        # type: ignore[assignment]
_cs.SYMBOL_TO_SECTOR_AR = dict(SECTORS)                          # type: ignore[assignment]

from app.api.v1.endpoints import market as mk  # noqa: E402


def ipo(**kw) -> dict:
    r = asyncio.run(mk.get_ipo_value(**kw))
    body = r.body if hasattr(r, "body") else r
    if isinstance(body, (bytes, bytearray)):
        import json
        body = json.loads(body)
    return (body or {}).get("data") or {}


# ── ١ · المسطرةُ واحدة: الشاشةُ والمحرّكُ يُخرجان الرقمَ نفسَه ───────────
EPS, BVPS, SHARES = 3.20, 22.0, 1_000_000.0
screen = ipo(sector=SEC, net_profit=EPS * SHARES, equity=BVPS * SHARES,
             shares=SHARES)
PRICE = 44.0
engine = relative_value(sector=SEC, price=PRICE, pe=PRICE / EPS,
                        pb=PRICE / BVPS, book_value=BVPS,
                        table=SectorTable({"sector": SECTORS[s],
                                           "pe": v["pe_ratio"],
                                           "pb": v["price_to_book"]}
                                          for s, v in STORE.items()))
check(screen.get("value") is not None and engine["value"] is not None
      and abs(screen["value"] - round(engine["value"], 2)) < 0.02,
      "١ الشاشةُ والمحرّكُ يقيسان بمسطرةٍ واحدة",
      f"الشاشة {screen.get('value')} · المحرّك {round(engine['value'] or 0, 2)}")

# ── ٢ · والرياضياتُ مكشوفة: وسيطُ القطاع × مقياسِ الشركة ────────────────
med_pe = statistics.median(v["pe_ratio"] for s, v in STORE.items() if SECTORS[s] == SEC)
check(abs(screen["paths"]["مكرر الربحية"]["value"] - med_pe * EPS) < 0.02,
      "٢ مسارُ المكرّر = وسيطُ القطاع × ربحيةِ السهم",
      f"{med_pe} × {EPS} = {round(med_pe * EPS, 2)} · الشاشة {screen['paths']['مكرر الربحية']['value']}")
check(abs(screen["eps"] - EPS) < 1e-6 and abs(screen["bvps"] - BVPS) < 1e-6,
      "٣ والمقياسانِ مشتقّانِ من النشرة لا من سعرٍ لا وجودَ له",
      f"ربحية {screen['eps']} · دفترية {screen['bvps']}")

# ── ٤ · الشركةُ غيرُ المدرَجة ليست في عيّنة قطاعها فلا يُنزَع لها شيء ────
check(screen["paths"]["مكرر الربحية"]["peers"] == 10,
      "٤ عشرُ نظائرَ كاملةً — لا نزعَ لشركةٍ ليست في العيّنة",
      f"نظائر {screen['paths']['مكرر الربحية']['peers']}")

# ── ٥ · الخسارةُ تُسقط المكرّرَ لا التقييم، ولا تبلغ ثقةً مرتفعة ─────────
loss = ipo(sector=SEC, net_profit=-5_000_000.0, equity=BVPS * SHARES, shares=SHARES)
check(loss.get("value") is not None and "مكرر الربحية" not in (loss.get("paths") or {})
      and loss.get("confidence") != "مرتفعة",
      "٥ الخاسرةُ تُقيَّم بالدفترية وحدَها وثقتُها دون المرتفعة",
      f"قيمة {loss.get('value')} · مسارات {list((loss.get('paths') or {}))} · ثقة {loss.get('confidence')}")

# ── ٦ · قطاعٌ نظائرُه دون الحدّ: امتناعٌ مُعلَّلٌ لا رقمٌ ضعيف ────────────
thin = ipo(sector=THIN, net_profit=EPS * SHARES, equity=BVPS * SHARES, shares=SHARES)
check(thin.get("value") is None and bool(thin.get("why")),
      "٦ قطاعٌ بثلاثِ نظائرَ يمتنع ويقول سببَه", str(thin.get("why")))

# ── ٧ · سعرُ الطرح: موضعٌ وفرقٌ محسوبان بالاتّجاه الصحيح ────────────────
hi = ipo(sector=SEC, net_profit=EPS * SHARES, equity=BVPS * SHARES,
         shares=SHARES, offer_price=screen["high"] + 10)
check(hi.get("offer_in_range") is False and (hi.get("offer_gap_pct") or 0) < 0,
      "٧ سعرُ طرحٍ فوق النطاق: خارجَه وفرقُه سالب",
      f"داخل={hi.get('offer_in_range')} · فرق {hi.get('offer_gap_pct')}%")
mid = ipo(sector=SEC, net_profit=EPS * SHARES, equity=BVPS * SHARES,
          shares=SHARES, offer_price=screen["value"])
_gap = mid.get("offer_gap_pct")
check(mid.get("offer_in_range") is True and _gap is not None and abs(_gap) < 0.1,
      "٨ وسعرٌ عند القيمة: داخلَ النطاق وفرقُه صفر",
      f"داخل={mid.get('offer_in_range')} · فرق {mid.get('offer_gap_pct')}%")

# ── ٩ · وبلا سعرٍ لا يُختلق فرقٌ ولا موضع ───────────────────────────────
check(screen.get("offer_gap_pct") is None and screen.get("offer_in_range") is None,
      "٩ بلا سعرِ طرحٍ لا فرقَ ولا موضعَ — لا رقمَ من فراغ")

# ── ١٠ · عددُ أسهمٍ غيرُ موجبٍ يُرفَض ولا يُقسَم على صفر ────────────────
from fastapi import HTTPException  # noqa: E402
try:
    ipo(sector=SEC, net_profit=1.0, equity=1.0, shares=0)
    ok10 = False
except HTTPException as e:
    ok10 = e.status_code == 400
check(ok10, "١٠ عددُ أسهمٍ صفرٌ يُرفَض بجوابٍ صريحٍ لا بانهيار")

# ── ١١ · والشاشةُ موصولةٌ فعلاً بهذا المسار ─────────────────────────────
page = (ROOT / "frontend/src/pages/CalculatorsPage.tsx").read_text(encoding="utf-8")
check("IpoValueCalc" in page and "marketApi.ipoValue" in page
      and "<IpoValueCalc />" in page,
      "١١ حاسبةُ الاكتتاب في قسم الحاسبات وموصولةٌ بالخادم")
check("offer_in_range" in page and "confidence_why" in page,
      "١٢ وتعرض موضعَ السعر وقيودَ الثقة — لا رقماً مغلقاً")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
