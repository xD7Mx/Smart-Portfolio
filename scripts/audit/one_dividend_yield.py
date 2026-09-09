#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D223 — عائدُ التوزيعات رقمٌ واحدٌ في كلّ شاشة.
#
# رأى المالك ‎2.44٪ في فرز السوق و‎2.56٪ في صفحة السهم لبوبا. ولم يكن
# الفرقُ تقريباً بل **تعريفين**: الصفحةُ تعرض رقمَ المزوّد، والفرزُ يسقط —
# متى غاب الرقمُ من كاشه — إلى حسابٍ خاصّ (توزيعُ ١٢ شهراً ÷ السعر).
#
# وأوّلُ علاجٍ جرّبتُه كان ناقصاً: تثبيتُ رقم المزوّد في المخزن الدائم
# صحيحٌ لكنه **يتأخّر** — المخزنُ لا يمتلئ إلا بجلبٍ جديد، ولقطةُ الفرز
# تُبنى مرّةً في اليوم. فالاختلافُ يبقى ظاهراً أياماً، ولم يُقَل ذلك.
#
# فالعلاجُ الجذريّ: **سلسلةٌ واحدةٌ يقرأ منها الطرفان** — فيستحيل اختلافُهما
# مهما كانت حالُ الكاش، ويعود المصدرُ مع الرقم.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

from app.services.dividend_yield import resolve  # noqa: E402

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


PROVIDER = 2.56
STORE = {"dividend_yield": PROVIDER, "dps_ttm": 3.84}

# ── ١ · الكاشُ حاضر ⇒ رقمُ المزوّد ────────────────────────────────────
v, src = resolve("8210", 157.10, {"dividend_yield": PROVIDER}, STORE)
check(v == PROVIDER and src == "المزوّد", "١ الكاشُ حاضرٌ ⇒ رقمُ المزوّد", f"{v} · {src}")

# ── ٢ · الاتّجاه المعاكس: الكاشُ فارغٌ والمخزنُ حاضر ⇒ **الرقمُ نفسُه** ──
# هذه هي الحالةُ التي أنتجت الاختلاف: الفرزُ كان يسقط هنا إلى تعريفٍ آخر
# بينما تبقى الصفحةُ على رقم المزوّد.
v2, src2 = resolve("8210", 157.20, {}, STORE)
check(v2 == PROVIDER and src2 == "المزوّد",
      "٢ الكاشُ فارغٌ والمخزنُ حاضرٌ ⇒ الرقمُ نفسُه لا تعريفٌ آخر", f"{v2} · {src2}")
check(v == v2, "٣ فلا يختلف الفرزُ عن صفحة السهم بحال الكاش", f"{v} ⇐ {v2}")

# ── ٤ · وإن غاب المزوّدُ تماماً، فاحتياطٌ **مُسمّى** لا مجهول ──────────
v3, src3 = resolve("8210", 157.20, {}, {"dps_ttm": 3.84})
check(v3 is not None and src3 and "المزوّد" not in src3,
      "٤ الاحتياطُ يعود بمصدره لا تحت اسم المزوّد", f"{v3} · {src3}")

# ── ٥ · ولا يُختلق رقمٌ من عدم ────────────────────────────────────────
v4, src4 = resolve("8210", 157.20, {}, {})
check(v4 is None and src4 is None, "٥ بلا مصدرٍ ⇒ «غير متوفّر» لا صفر", f"{v4}")

# ── ٦ · وسعرٌ معدومٌ لا يُنتج قسمةً على صفر ──────────────────────────
v5, _ = resolve("8210", 0, {}, {"dps_ttm": 3.84})
check(v5 is None, "٦ سعرٌ معدومٌ لا يُنتج رقماً", f"{v5}")

# ── ٧ · والطرفان يستدعيان الدالّةَ نفسَها ────────────────────────────
scr = (ROOT / "backend/app/services/market_screener.py").read_text(encoding="utf-8")
mkt = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
both = "dividend_yield import resolve" in scr and "dividend_yield import resolve" in mkt
check(both, "٧ الفرزُ وصفحةُ السهم يستدعيان المُنتِجَ الواحد",
      "المصدر واحد" if both else "أحدهما يحسب لنفسه")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
