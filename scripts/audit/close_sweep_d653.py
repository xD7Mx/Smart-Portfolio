#!/usr/bin/env python3
"""حارسُ D653: مسحةُ الإقفال (17:30) تقيس الآن — لا تقرأ ما حسبته مسحةٌ سابقةٌ في اليوم نفسِه.

العطب (قِيس عند نشر المرشَّح ٤): مسحةُ النشر حسبت السوقَ ثمّ جاءت المسحةُ التالية في 0.3 ثانية — قرأت حسابَ الأولى من
الكاش، لأنّ مفتاحَ المسحة بيومها (D649). ففي يوم تداولٍ يُنشر فيه صباحاً، تكتب مسحةُ الإقفال رقماً بسعر منتصف الجلسة."""
import os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import cache   # noqa: E402
fresh = "analysis:1010.SR:r1:v1:fresh:2026-10-11"
page = "analysis:1010.SR:r1:v1:official:2026-10-10"
cache.set(fresh, {"fair_value": 25.0}, 24 * 3600)
cache.set(page, {"fair_value": 24.9}, 24 * 3600)
n = cache.expire_containing(":fresh:")
check(n >= 1 and cache.get(fresh) is None, "١ حسابُ المسحة السابق اليومَ يُبطَل فتُعاد المسحةُ بسعر الآن", f"أُبطل {n}")
check(cache.get(page) == {"fair_value": 24.9}, "٢ وتحليلُ الصفحة لا يُمسّ — يتجدّد بتاريخ المسحة الجديدة وحده")
src = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
job = src[src.index("async def job_valuation_sweep"):src.index("async def job_valuation_sweep") + 1400]
i_exp, i_sw = job.find('cache.expire_containing(":fresh:")'), job.find("rep = await sweep()")
check(0 < i_exp < i_sw, "٣ مسحةُ الإقفال المجدولة تُبطل حساباتِ اليوم قبل أن تبدأ")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
