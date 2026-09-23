#!/usr/bin/env python3
"""حصّةُ ياهو: احتياطٌ للمستخدم لا تبلغه المهامُّ الخلفية (D436).

    python3 scripts/audit/yahoo_reserve.py

قِيس على خادم المالك بكاشف `yahoo_budget_sites.py`: **10,000 من 10,000**
مستهلكةٌ في يومٍ واحد — `get_history` ‏29٪ · `get_company_info` ‏28٪ ·
`get_ownership` ‏22٪ · `get_price` ‏12٪ — وأكثرُها مسحاتٌ وبناءُ جداولَ في
الخلفية. فلمّا نفدت أظلم أوّلاً ما يراه المستخدم: رقمُ برنت، ورسما
المؤشّرين، ودرجاتٌ تنتظر شاهدَ ياهو.

فالشرط: المهامُّ الخلفيةُ تقف عند 90٪ من الحصّة، والطلبُ الآتي من شاشةٍ
يبلغ الحصّةَ كاملة. ويُقاس سلوكياً بعدّادٍ مُصطنَع عند 92٪.
"""
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

import pathlib
import sys

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
    from app.services import usage_tracker as U
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)

bg = getattr(U, "background", None)
check(callable(bg), "٠ للمهامّ الخلفية وسمٌ يُعرّفها للحصّة")
if not callable(bg):
    print("FAIL D436 — احتياطٌ للمستخدم في حصّة ياهو")
    sys.exit(1)

lim = U.limit_for("yahoo")
U._reset_if_new_day()
U._counts["yahoo"] = int(lim * 0.92)

check(U.can_call("yahoo") is True,
      "١ طلبُ الشاشة يُجاب عند 92٪ — الاحتياطُ له", f"{U._counts['yahoo']}/{lim}")
with bg():
    check(U.can_call("yahoo") is False,
          "٢ والمهمّةُ الخلفيةُ تقف عند 90٪ فلا تأكل الاحتياط")
check(U.can_call("yahoo") is True, "٣ والوسمُ لا يتسرّب بعد خروج المهمّة")

U._counts["yahoo"] = int(lim * 0.5)
with bg():
    check(U.can_call("yahoo") is True, "٤ ودون 90٪ تعمل الخلفيةُ كما كانت")

U._counts["yahoo"] = lim
check(U.can_call("yahoo") is False, "٥ وعند 100٪ يقف الجميع — الحصّةُ حدٌّ لا اقتراح")

# ── ٦ · والمهامُّ الثقيلةُ الثلاث موسومةٌ خلفية ─────────────────────
try:
    from app.services import market_valuation_sweep as _sw
    from app.services import market_screener as _sc
    from app.services import governance as _gv
    _mk = {"مسحةُ التقييم": _sw.sweep, "بناءُ جدول السوق": _sc.compute_screener,
           "مسحُ حوكمة السوق": _gv.get_market_governance}
    _un = [n for n, f in _mk.items() if not getattr(f, "__sp_background__", False)]
    check(not _un, "٦ المهامُّ الثقيلةُ الثلاث موسومةٌ خلفية", ", ".join(_un))
except ModuleNotFoundError as e:
    print(f"⚠ ٦ لم يُقَس ({e.name})")

print(("FAIL" if fail else "PASS") + " D436 — احتياطٌ للمستخدم في حصّة ياهو")
sys.exit(fail)
