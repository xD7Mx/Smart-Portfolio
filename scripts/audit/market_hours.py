#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D215 — أطوارُ الجلسة تُقاس بالدقيقة، والنسختان لا تفترقان.
#
# رأى المالكُ «السوق مغلق» والسوقُ يعمل. وكانت الجلسةُ محسوبةً ‎10:00–14:30
# والإغلاقُ ‎15:00 — بينما «تداول» تُتِمّ التداولَ المستمرَّ ‎15:00 ثمّ مزادَ
# الإغلاق وسعرَه حتى ‎15:20. والقاعدةُ منسوخةٌ في الخادم والواجهة معاً،
# فإصلاحُ إحداهما وحدَها يُبقي العطبَ حيث لا يُنظَر.
#
# فيُقاس السلوكُ عند الحدود بالدقيقة الواحدة، ويُشترط أن تحمل نسخةُ
# الواجهة الحدودَ نفسَها — فحصُ بنيةٍ واحدٌ لا غنى عنه، لأنّ الواجهة
# تُصرَّف في المتصفّح لا هنا.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

from app.services.market_phase import market_phase  # noqa: E402

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


SUN = 0
CASES = [
    (SUN,  9 * 60 + 29, "closed",   "قبل مزاد الافتتاح بدقيقة"),
    (SUN,  9 * 60 + 30, "pre",      "أوّلُ دقيقةٍ في مزاد الافتتاح"),
    (SUN,  9 * 60 + 59, "pre",      "آخرُ دقيقةٍ فيه"),
    (SUN, 10 * 60,      "open",     "جرسُ الافتتاح"),
    (SUN, 14 * 60 + 30, "open",     "الجلسةُ قائمةٌ في الثانية والنصف"),
    (SUN, 14 * 60 + 59, "open",     "آخرُ دقيقةٍ من التداول المستمرّ"),
    (SUN, 15 * 60,      "preclose", "مزادُ الإغلاق يبدأ"),
    (SUN, 15 * 60 + 19, "preclose", "آخرُ دقيقةٍ من سعر الإغلاق"),
    (SUN, 15 * 60 + 20, "closed",   "انتهى كلُّ تداول"),
]
for dow, mins, want, why in CASES:
    got = market_phase(dow, mins)
    check(got == want, f"{mins // 60:02d}:{mins % 60:02d} ⇐ {want} — {why}", got)

check(market_phase(5, 12 * 60) == "closed", "الجمعةُ مغلقة", market_phase(5, 12 * 60))
check(market_phase(6, 12 * 60) == "closed", "السبتُ مغلق", market_phase(6, 12 * 60))
check(market_phase(4, 12 * 60) == "open", "الخميسُ يومُ تداول", market_phase(4, 12 * 60))

# ── نسخةُ الواجهة تحمل الحدودَ نفسَها ────────────────────────────────
ts = (ROOT / "frontend/src/utils/marketHours.ts").read_text(encoding="utf-8")
seg = ts[ts.index("export function tasiPhase"):]
seg = seg[:seg.index("\n}")]
want_open_end = "mins < 15 * 60"
want_close_end = "15 * 60 + 20"
ok = want_open_end in seg and want_close_end in seg and "14 * 60 + 30" not in seg
check(ok, "نسخةُ الواجهة بحدود الخادم نفسِها",
      "مطابِقة" if ok else "ما زالت على الحدود القديمة")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
