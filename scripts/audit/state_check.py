"""ثباتُ الحصّة والذاكرة عبر الإقلاع — حارسُ D146.

يُشغّل عمليتين منفصلتين: الأولى تعدّ وتخزّن، والثانية تقرأ. والعمليةُ
الثانية هي الحاويةُ بعد إعادتها. فإن عاد العدّادُ صفراً أو ضاعت مكتبةُ
الثلاثين يوماً، رجع النزفُ الذي كلّفنا مئةَ نداءٍ في يوم.

    python scripts/audit/state_check.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_BE = os.path.join(_ROOT, "backend")

_WRITE = """
import sys; sys.path.insert(0, %r)
from app.services import cache, usage_tracker as ut
for _ in range(37):
    ut.record("sahmak")
cache.set("lib:companies", {"n": 273}, cache.LIBRARY_TTL)
cache.set("price:2222", {"p": 30.1}, cache.PRICE_TTL)
cache.flush()
"""

_READ = """
import sys, json; sys.path.insert(0, %r)
from app.services import cache, usage_tracker as ut
print(json.dumps({
    "count": ut.usage("sahmak")["daily_used"],
    "library": cache.get("lib:companies"),
    "price": cache.get("price:2222"),
    "day": ut._today_ast(),
}))
"""


def _run(code: str, state: str) -> str:
    env = dict(os.environ, SP_STATE_DIR=state)
    r = subprocess.run([sys.executable, "-c", code % _BE], env=env,
                       capture_output=True, text=True)
    return (r.stdout or "").strip().splitlines()[-1] if r.stdout else r.stderr


def main() -> int:
    T: list[tuple[str, bool, str]] = []
    with tempfile.TemporaryDirectory() as state:
        _run(_WRITE, state)
        got = json.loads(_run(_READ, state))
        T.append(("١ العدّادُ يعبر الإقلاع", got["count"] == 37,
                  f"‏37 نداءً → {got['count']} بعد عمليةٍ جديدة"))
        T.append(("٢ مكتبةُ الثلاثين يوماً تعبر", got["library"] == {"n": 273},
                  f"{got['library']}"))
        T.append(("٣ القصيرُ لا يُثقل القرص", got["price"] is None,
                  "سعرٌ عمرُه ربعُ ساعة لا يُحفظ"))

        # يومٌ مضى: لا يُعتدّ به
        with open(os.path.join(state, "usage_counts.json"), "w") as fh:
            json.dump({"day": "2020-01-01", "counts": {"sahmak": 99}}, fh)
        old = json.loads(_run(_READ, state))
        T.append(("٤ عدُّ الأمس لا يُحمَل على اليوم", old["count"] == 0,
                  f"ملفُّ ‎2020-01-01 → {old['count']}"))

        # ملفٌّ تالف: لا يُسقط شيئاً
        with open(os.path.join(state, "usage_counts.json"), "w") as fh:
            fh.write("{{ تالف")
        bad = json.loads(_run(_READ, state))
        T.append(("٥ ملفٌّ تالف لا يُسقط التطبيق", bad["count"] == 0,
                  "يُبدأ من الصفر بلا انهيار"))

    print("═" * 58)
    print("  ثباتُ الحصّة والذاكرة عبر الإقلاع")
    print("═" * 58)
    for n, ok, d in T:
        print(f"  {'PASS' if ok else 'FAIL'}  {n:34} {d}")
    bad_n = [n for n, ok, _ in T if not ok]
    print("═" * 58)
    print("  ✔ الحصّةُ لا تنزف بالإقلاع." if not bad_n
          else f"  ✖ أخفق {len(bad_n)}")
    return 0 if not bad_n else 1


if __name__ == "__main__":
    sys.exit(main())
