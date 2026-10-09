#!/usr/bin/env python3
"""حارسُ D650: قياسُ المرشَّح لا يمسّ الإنتاج — لا كاشَ يُحفظ إلى القرص المشترك، ولا لقطةَ «آخر سليم» تُكتب.

العطب: `candidate_gate.py` يحسب السوقَ بشيفرة المرشَّح في عمليّةٍ على الخادم، وكاشُها الطويل (‏fvm 6 ساعات · التحليل
24) يُكتب إلى ملفٍّ يشاركه الخادم ويمتصّ منه ما انتهاؤه أبعد (D582) — فقيمةُ مرشَّحٍ تحت مفتاحٍ لم يتغيّر تُخدَم
للمستخدم ساعات قبل اعتماده؛ و`lastgood.save("analysis:…")` يكتب تحليلَ المرشَّح لقطةً احتياطيةً للإنتاج."""
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

src = (ROOT / "scripts/audit/candidate_gate.py").read_text(encoding="utf-8")
i_cap = src.find("_cache.set = lambda key, value, ttl: _set0(key, value, min(ttl, _cache._PERSIST_MIN_TTL - 60))")
i_lg = src.find("_lg.save = lambda *a, **k: None")
i_one = src.find("from app.services.market_valuation_sweep import _one")
check(0 < i_cap < i_one, "١ الكاشُ يُقصَّر دون عتبة الحفظ قبل أن يُستورد شيءٌ من المحرّك")
check(0 < i_lg < i_one, "٢ ولقطاتُ «آخر سليم» لا تُكتب")

from app.services import cache   # noqa: E402
_set0 = cache.set
cache.set = lambda key, value, ttl: _set0(key, value, min(ttl, cache._PERSIST_MIN_TTL - 60))
cache._dirty = False
cache.set("fvm:v38:9999", {"value": 1.0}, 6 * 60 * 60)
check(cache.get("fvm:v38:9999") == {"value": 1.0}, "٣ والكاشُ يعمل داخل العمليّة — القياسُ لا يُبطَّأ")
check(cache._dirty is False, "٤ ولا يُعلَّم للحفظ: لا يصل القرصَ المشترك ولا يمتصّه الخادم")
for g in ("parity_gate.py", "parity_shift_gate.py", "readiness_door.py"):
    s = (ROOT / "scripts/audit" / g).read_text(encoding="utf-8")
    check("cache.set = lambda *a, **k: None" in s and "lastgood.save = lambda *a, **k: None" in s,
          f"٥ وكاشفُ الصفحات ({g}) لا يكتب كاشاً ولا لقطة")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
