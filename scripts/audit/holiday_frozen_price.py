#!/usr/bin/env python3
"""العطلةُ من مؤشّرٍ لا يتحرّك داخل الجلسة — لا من «الوقتِ الحاليّ» (D426).

    python3 scripts/audit/holiday_frozen_price.py

قِيس على خادم المالك يومَ **اليوم الوطنيّ** (‏23 سبتمبر) — أوّلُ عطلةٍ
حقيقيةٍ يُختبر عليها الكشف: ‎78 مشاهدةً طوالَ اليوم، ورمزُ «تداول» ‎3
في كلّ الأطوار، و«زمنُ التغذية» تغيّر **‎32 مرّةً داخل ساعات الجلسة**.
فالشاهدُ الذي بُني عليه الكشفُ («تغذيةٌ متجمّدة») لم يتجمّد، وقال
التطبيقُ «السوق مفتوح» طوالَ جلسةِ يومِ عطلة — وهي الشكوى الأولى نفسُها.

والسببُ في سطرٍ واحد: `"as_of": d.get("currentTime")` — الحقلُ هو
**الوقتُ الحاليُّ للخادم** كما يقول اسمُه، لا زمنُ آخرِ صفقة. فلا يتجمّد
أبداً، ولن يحكم بعطلةٍ مهما كانت.

والشاهدُ الذي يتجمّد فعلاً حين لا تداول هو **قيمةُ المؤشّر**: في جلسةٍ
حيّةٍ تتحرّك كلَّ دقيقة، وفي العطلة تبقى ثابتةً. فالفحصُ يقيس:

  ١· مؤشّرٌ ثابتٌ ‎25 دقيقةً فأكثرَ في طور «مفتوح» ⇒ عطلة.
  ٢· مؤشّرٌ يتحرّك ⇒ ليست عطلة — لا إنذارَ كاذب.
  ٣· ثباتٌ أقصرُ من النافذة لا يكفي — لا حكمَ على عشر دقائق.
  ٤· «الوقتُ الحاليّ» يتحرّك والمؤشّرُ ثابت ⇒ عطلة: الحكمُ لا يقرأ ذلك الحقل.
  ٥· بعد الجرس في يومِ عطلةٍ مُثبَتة: «عطلة» لا «مغلق»؛ وفي يومِ تداول: «مغلق».
  ٦· مشاهداتُ الأمس لا تحكم على اليوم.
"""
from __future__ import annotations

import pathlib
import sys
from datetime import datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


try:
    from app.services import market_state as MS
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)

verdict = getattr(MS, "frozen_index_verdict", None)
check(callable(verdict),
      "٠ حكمُ العطلة دالّةٌ تقرأ المشاهداتِ لا «الوقتَ الحاليّ»")
if not callable(verdict):
    print("FAIL D426 — العطلةُ من مؤشّرٍ لا يتحرّك داخل الجلسة")
    sys.exit(1)

DAY = datetime(2026, 9, 23)


def _obs(start_min: int, n: int, step: int, prices, phase="open",
         day: datetime = DAY, feed_moves=True):
    out = []
    for i in range(n):
        t = day + timedelta(hours=10, minutes=start_min + i * step)
        out.append({
            "at": t.isoformat(timespec="minutes"),
            "clock_phase": phase,
            "price": prices(i),
            "feed_at": (t.strftime("%I:%M %p") if feed_moves else "12:39 PM"),
            "code": 3,
        })
    return out


# ١ · مؤشّرٌ ثابتٌ أربعين دقيقةً في طور «مفتوح»
_h = _obs(5, 9, 5, lambda i: 10787.98)
_now = DAY + timedelta(hours=10, minutes=45)
v = verdict(_h, _now, "open")
check((v or {}).get("status") == "holiday",
      "١ مؤشّرٌ ثابتٌ ‎40 دقيقةً داخل الجلسة ⇒ عطلة", str(v)[:120])
check(bool((v or {}).get("evidence")),
      "١ب ومعها دليلُها بالأرقام", str((v or {}).get("evidence"))[:100])

# ٢ · مؤشّرٌ يتحرّك
_t = _obs(5, 9, 5, lambda i: 10787.98 + i * 1.37)
v = verdict(_t, _now, "open")
check((v or {}).get("status") != "holiday",
      "٢ مؤشّرٌ يتحرّك ⇒ ليست عطلة", str(v)[:80])

# ٣ · ثباتٌ عشرَ دقائقَ فقط
_s = _obs(30, 3, 5, lambda i: 10787.98)
v = verdict(_s, DAY + timedelta(hours=10, minutes=42), "open")
check((v or {}).get("status") != "holiday",
      "٣ ثباتٌ أقصرُ من النافذة لا يُحكم به", str(v)[:80])

# ٤ · «الوقتُ الحاليّ» يتحرّك (كما قِيس يومَ العطلة) والمؤشّرُ ثابت
_m = _obs(5, 9, 5, lambda i: 10787.98, feed_moves=True)
v = verdict(_m, _now, "open")
check((v or {}).get("status") == "holiday",
      "٤ زمنُ الردّ يتحرّك والمؤشّرُ ثابت ⇒ عطلة — الحكمُ لا يقرأ currentTime")

# ٥ · بعد الجرس
_after = DAY + timedelta(hours=16)
v = verdict(_h, _after, "closed")
check((v or {}).get("status") == "holiday",
      "٥ بعد الجرس في يومِ عطلةٍ مُثبَتة ⇒ «عطلة» لا «مغلق»", str(v)[:80])
v = verdict(_t, _after, "closed")
check((v or {}).get("status") != "holiday",
      "٥ب وفي يومِ تداولٍ ⇒ لا «عطلة»", str(v)[:80])

# ٦ · الأمسُ لا يحكم على اليوم
_y = _obs(5, 9, 5, lambda i: 10787.98, day=DAY - timedelta(days=1))
v = verdict(_y, _now, "open")
check((v or {}).get("status") != "holiday",
      "٦ ثباتُ الأمس لا يجعل اليومَ عطلة", str(v)[:80])

# ٧ · وما لا سعرَ فيه لا يشهد
_np = _obs(5, 9, 5, lambda i: None)
v = verdict(_np, _now, "open")
check((v or {}).get("status") != "holiday",
      "٧ مشاهداتٌ بلا قيمةِ مؤشّرٍ لا تشهد بعطلة")

print(("FAIL" if fail else "PASS")
      + " D426 — العطلةُ من مؤشّرٍ لا يتحرّك داخل الجلسة")
sys.exit(fail)
