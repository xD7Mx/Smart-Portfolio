#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D229 — «سُئل ولم يوجد» ليست «لم يُسأل».
#
# بلغ ياهو سقفَه فأضاف المالكُ خمسةَ آلافٍ إليه. ثمّ أُضيف إسنادُ العدّاد
# فقال بعد يومين أيُّ مسارٍ ينفقها:
#
#     981  get_price · 599 get_ownership · 576 get_history · 561 get_company_info
#
# وهيكلةُ الملكية بيانٌ **يتغيّر ربعياً** — فـ‎599 نداءً في يومٍ واحد رقمٌ لا
# يفسّره إلا عطب. والعطب: حين لا تنشر ياهو هيكلةً لشركة — وهو حالُ أكثر
# الشركات الصغيرة — تعود الدالّةُ `None` **بلا تخزينٍ**، فيُعاد السؤالُ في
# كلّ تحليلٍ أبداً. والمدّةُ ثلاثون يوماً لكنها لا تُطبَّق إلا على النجاح.
#
# فالقاعدة: **الغيابُ نتيجةٌ تُخزَّن كما تُخزَّن النتيجة.** ومدّتُه أقصر من
# مدّة الحضور لأنه قد يكون نقصاً مؤقّتاً عند المزوّد.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

from app.services.market_data import YahooFinanceAdapter          # noqa: E402
from app.services import cache                                    # noqa: E402

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


def _adapter(payload):
    a = YahooFinanceAdapter()
    n = {"calls": 0}

    async def fake(sym, mod):
        n["calls"] += 1
        return payload

    a._quote_summary = fake
    return a, n


# ── ١ · شركةٌ بلا هيكلةِ ملكية: نداءٌ واحدٌ لا خمسة ──────────────────
a, n = _adapter({"majorHoldersBreakdown": {}})
res = [asyncio.run(a.get_ownership("1111.SR")) for _ in range(5)]
check(n["calls"] == 1, "١ خمسُ محاولاتٍ لشركةٍ بلا هيكلةٍ ⇒ نداءٌ واحد",
      f"{n['calls']} نداءً")

# ── ٢ · والجوابُ يبقى «غير متوفّر» لا علامةً داخلية ─────────────────
# الاتّجاه المعاكس للعطب المحتمل في العلاج: أن تتسرّب علامةُ التخزين إلى
# المستدعي فيقرأها هيكلةَ ملكيةٍ فيها مفتاحٌ غريب.
check(all(r is None for r in res), "٢ والجوابُ `None` في كلّ مرّة", str(res[:2]))

# ── ٣ · والحضورُ يُخزَّن ويُعاد كما هو ──────────────────────────────
b, m = _adapter({"majorHoldersBreakdown": {
    "insidersPercentHeld": {"raw": 0.42},
    "institutionsPercentHeld": {"raw": 0.11}}})
got = [asyncio.run(b.get_ownership("2222.SR")) for _ in range(3)]
check(m["calls"] == 1 and got[0] and got[0]["insiders"] == 42.0
      and got[0]["public"] == 47.0,
      "٣ والحضورُ يُخزَّن مرّةً ويُعاد صحيحاً", str(got[0]))

# ── ٤ · ومدّةُ الغياب أقصرُ من مدّة الحضور ──────────────────────────
# غيابٌ يُؤبَّد شهراً قد يُخفي بياناً وصل المزوّدَ بعد أسبوع. ويُقاس
# بالتقاط مدّةِ التخزين الفعلية لا بقراءة النصّ حولها — فقراءةُ النصّ
# تُصيب وتُخطئ بحسب ما جاورَه.
_ttls: dict[str, int] = {}
_real_set = cache.set


def _spy(key, value, ttl=None):
    if str(key).startswith("own:yahoo:"):
        _ttls["absent" if isinstance(value, dict) and value.get("_absent")
              else "present"] = ttl
    return _real_set(key, value, ttl)


cache.set = _spy
c, _ = _adapter({"majorHoldersBreakdown": {}})
asyncio.run(c.get_ownership("3333.SR"))
d, _ = _adapter({"majorHoldersBreakdown": {
    "insidersPercentHeld": {"raw": 0.30},
    "institutionsPercentHeld": {"raw": 0.20}}})
asyncio.run(d.get_ownership("4444.SR"))
cache.set = _real_set
ok4 = (_ttls.get("absent") is not None and _ttls.get("present") is not None
       and _ttls["absent"] < _ttls["present"])
check(ok4, "٤ مدّةُ الغياب أقصرُ من مدّة الحضور",
      f"غياب {_ttls.get('absent')} ثانية · حضور {_ttls.get('present')} ثانية")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
