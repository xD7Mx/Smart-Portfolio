"""ثباتُ الحصّة والذاكرة — حارسا D146 و D161.

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


def _plan_block_check() -> tuple[str, bool, str]:
    """يُشغَّل في عمليةٍ منفصلة: يزيّف مصدراً يردّ ‎403 دائماً، ويعدّ
    النداءاتِ الفعلية لخمسٍ وعشرين شركة. الصوابُ نداءٌ واحد."""
    import json as _j
    code = """
import sys, os, asyncio, tempfile, json
sb = tempfile.mkdtemp()
os.environ["SP_STATE_DIR"] = sb
os.environ["LASTGOOD_PATH"] = os.path.join(sb, "lg.json")
sys.path.insert(0, %r)
from app.core.config import settings
settings.SAHMAK_API_KEY = "TEST"
from app.services import sahmak_library as s, usage_tracker as ut
n = {"c": 0}
class R:
    status_code = 403
    headers = {"content-type": "application/json"}
    text = '{"error":{"code":"PLAN_LIMIT"}}'
class C:
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def get(self, *a, **k):
        n["c"] += 1
        return R()
s.httpx.AsyncClient = lambda *a, **k: C()
async def m():
    for i in range(25):
        await s.fundamentals(str(1000 + i))
    before = n["c"]
    await s.company_profile("2222")
    print(json.dumps({"calls": n["c"] - 1, "quota": ut.usage("sahmak")["daily_used"],
                      "other_family": n["c"] - before}))
asyncio.run(m())
""" % _BE
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    try:
        got = _j.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:                                             # noqa: BLE001
        return ("٦ الخطّةُ الرافضة لا تُنادى ثانيةً", False,
                f"تعذّر القياس: {(r.stderr or '')[-90:]}")
    # الشرطُ على **عائلة القوائم** وحدها: نداءٌ واحدٌ لخمسٍ وعشرين
    # شركة. والحصّةُ الكلّية ‎2 لأنّ الاختبار ينادي عائلةً ثانيةً عمداً،
    # ليثبت أنّ الحبسَ لا يتعدّى عائلتَه.
    ok = got["calls"] == 1 and got["other_family"] == 1
    return ("٦ الخطّةُ الرافضة لا تُنادى ثانيةً", ok,
            f"‏25 شركة → نداءٌ {got['calls']} · وعائلةٌ أخرى تُنادى "
            f"{got['other_family']}")


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

    # ══ ٦ — نقطةٌ ترفضها الخطّةُ لا تُنادى ثانيةً ══ (D161)
    # الحصّةُ تُحجز قبل الطلب، فردُّ ‎403 يستهلك خانةً بلا عائد. ونقطةٌ
    # ترفضها الخطّةُ ترفضها لكلّ شركة — فمحاولتُها لكلٍّ منها تحرق اليومَ
    # كلَّه. قِيس ذلك: العدّادُ ‎90/90 وصفرُ ملفٍّ مخزَّن.
    T.append(_plan_block_check())

    print("═" * 58)
    print("  ثباتُ الحصّة والذاكرة")
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
