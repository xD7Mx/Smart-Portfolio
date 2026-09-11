#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D244 — سلسلةُ مصادرَ واحدةٌ لحقول العرض.
#
# بعد توحيد المائدة (‏D240) بقي في مسبار الأعمدة خلافان على أربعين شركة:
#   · مضاعفُ الدفترية — 1213: ‎63.31 في الفرز و‎11.78 في الصفحة
#   · عائدُ التوزيعات — 1304: ‎1.36 في الفرز و«غير متوفّر» في الصفحة
#
# والسببُ ليس حساباً مختلفاً بل **ترتيبَ مصادرَ مختلفاً**: كلُّ مسارٍ كتب
# سلسلتَه بيده. فصار `valuation_fields.resolve_display` هو السلسلة، وكلا
# المسارَين ينزل إليها.
#
# ويُقاس سلوكاً: المسارانِ على مدخلاتٍ واحدةٍ يُخرجان الأرقامَ نفسَها،
# والمكرّرُ دالّةُ سعرٍ يُعاد حسابُها، وما خرج عن المدى لا يُنشَر في
# **الشاشتين معاً** — لا في واحدةٍ وتُخفيه الأخرى.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

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


from app.services.valuation_fields import resolve_display as disp  # noqa: E402

PX = 60.0
FUND = {"eps": 3.0, "book_value": 12.0, "target_mean_price": 72.0,
        "week52_high": 65.0, "week52_low": 40.0}
STORE = {"eps": 2.0, "book_value": 6.0, "dps_ttm": 1.2}

# ── ١ · دالّتا السعر تُحسبان من السعر الحاضر ─────────────────────────────
# ── المنشورُ أوّلاً (‏D246): هو ما تعرضه الصفحة، فلا تختلف الشاشتان ──
d0 = disp("1213", PX, fund={**FUND, "pe_ratio": 18.5}, store_row=STORE)
check(d0.get("pe_ratio") == 18.5,
      "١ رقمُ المزوّد المنشور يُقدَّم — هو ما تعرضه الصفحة",
      f"منشور 18.5 ⇒ {d0.get('pe_ratio')}")
d = disp("1213", PX, fund=FUND, store_row=STORE)
check(d.get("pe_ratio") == 20.0 and d.get("price_to_book") == 5.0,
      "١ب وحيث لا منشورَ يُحسب من السعر الحاضر ومقياسِ الشركة",
      f"‏60÷3={d.get('pe_ratio')} · 60÷12={d.get('price_to_book')}")

# ── ٢ · والكاشُ يتقدّم المخزنَ — سلسلةٌ واحدةٌ معلَنة ────────────────────
d2 = disp("1213", PX, fund={}, store_row=STORE)
check(d2.get("pe_ratio") == 30.0,
      "٢ وحين لا كاشَ يُقرأ المخزن", f"‏60÷2={d2.get('pe_ratio')}")

# ── ٣ · وما خرج عن المدى لا يُنشَر (عطبُ 1213 بعينه) ─────────────────────
# ══ مدى المحرّك ليس مدى العرض ══ (D247)
# قِيس على عيّنة ‎120: خمسُ شركاتٍ مكرّرُها ‎136–1172 تعرضه الصفحةُ
# ويُخفيه الفرز، لأنّي طبّقتُ مدى عيّنةِ النظائر على العرض. والمكرّرُ
# المرتفعُ **خبرٌ حقيقيٌّ** عن ربحٍ كاد ينعدم — ومن يُصفّي به يجب أن
# يجد الشركة. فالعرضُ يقبل كلَّ موجب، والمحرّكُ يبقى على مداه.
d3 = disp("2330", PX, fund={"pe_ratio": 1172.5}, store_row={})
check(d3.get("pe_ratio") == 1172.5,
      "٣ مكرّرٌ مرتفعٌ حقيقيٌّ يُعرض ولا يُقصّ بمدى المحرّك",
      f"{d3.get('pe_ratio')}")
from app.services.relative_value import PE_RANGE as _PER  # noqa: E402
check(_PER[1] == 100.0,
      "٣ب ومدى المحرّك باقٍ في عيّنته — لا يُوسَّع لأجل العرض",
      f"حدُّ العيّنة {_PER[1]}")
# والفرقُ بين الرفض والجهل: بلا مدخَلٍ يُحجَب المفتاحُ فلا يُفرَّغ عمود.
# ودالّةُ السعر تُكتب دائماً: بلا مقياسٍ ولا منشورٍ ⇒ `None` صريحة،
# فلا يبقى في الجدول رقمُ بناءٍ محسوبٌ بسعرِ أمس (عطبُ 1213 بعينه).
d3c = disp("1213", PX, fund={}, store_row={})
check("price_to_book" in d3c and d3c["price_to_book"] is None,
      "٣ج وبلا منشورٍ ولا مقياسٍ تُكتب None — لا رقمَ من سعرٍ آخر",
      f"{d3c.get('price_to_book')} (المفتاحُ مكتوب)")
# ولا يُقبَل سالبٌ ولا صفر: خسارةٌ ليست مكرّراً.
d3d = disp("1213", PX, fund={"pe_ratio": -8.0}, store_row={})
check(d3d.get("pe_ratio") is None,
      "٣د ومكرّرٌ سالبٌ (خسارة) لا يُعرض مكرّراً", f"{d3d.get('pe_ratio')}")

# ── ٤ · وحدّا العام يتّسعان لسعر اليوم ───────────────────────────────────
d4 = disp("1213", 70.0, fund=FUND, store_row={})
check(d4.get("high_52w") == 70.0 and d4.get("low_52w") == 40.0,
      "٤ وقمّةُ العام تتّسع للسعر إن تجاوزها",
      f"قمّة {d4.get('high_52w')} · قاع {d4.get('low_52w')}")

# ── ٥ · والعائدُ من المُنتِج الواحد ولو غاب رقمُ المزوّد (عطبُ 1304) ─────
d5 = disp("1304", 60.0, fund={}, store_row={"dps_ttm": 1.2})
check(d5.get("dividend_yield") is not None and d5.get("dividend_yield_source"),
      "٥ والعائدُ يُشتقّ حين يغيب رقمُ المزوّد — ومصدرُه معلَن",
      f"{d5.get('dividend_yield')}٪ · {d5.get('dividend_yield_source')}")

# ── ٦ · والمساران ينزلان إليها ──────────────────────────────────────────
scr = (ROOT / "backend/app/services/market_screener.py").read_text(encoding="utf-8")
ana = (ROOT / "backend/app/services/analysis.py").read_text(encoding="utf-8")
check("resolve_display" in scr, "٦ الفرزُ ينزل إلى السلسلة الواحدة")
check("resolve_display" in ana, "٧ وصفحةُ السهم كذلك")
check("_disp(_base2, _px2" in ana and 'info.get(k) is None' in ana,
      "٨ والسلسلةُ تُكمل ولا تُبدّل ما جاء من المزوّد صريحاً")

# ── ٩ · ولا حسابَ مضاعفٍ بقي في المسارين خارجها ─────────────────────────
# الاتّجاه المعاكس: لو أعاد أحدُهما كتابةَ القسمة عندَه، عاد الخلافُ.
for name, src in (("الفرز", scr), ("صفحة السهم", ana)):
    bad = [ln.strip() for ln in src.splitlines()
           if 'r["pe_ratio"] = round(' in ln or '_add["pe_ratio"]' in ln]
    check(not bad, f"٩ لا قسمةَ مكرّرٍ مكتوبةً في {name} خارج السلسلة",
          " · ".join(bad[:2]))

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
