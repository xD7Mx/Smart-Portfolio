#!/usr/bin/env python3
"""حارسُ D724 — الكاشُ لا يحتفظ بالمنتهي في الذاكرة.

سؤالُ المالك: «ألا يمكن توسيعُ الذاكرة بتنظيفها؟». قِيس (مهمّةُ memory · run 38637273470): الخادمُ وحدُه ‎236‎ م.ب مقيمة و‎268‎ في
المبادلة على خادمٍ ‎909‎ م.ب. وكان `cache.get` يتجاهل المنتهيَ ولا يحذفه، فتنمو الذاكرةُ ما دام الخادمُ قائماً. فالحارسُ:
  · المنتهي يُحذف من الذاكرة دوريّاً، والحيُّ يبقى، وشاهدُ القبر (قيمةٌ فارغةٌ طويلةُ العمر · D619) يبقى.

    python3 scripts/audit/cache_purge_d724.py
"""
import os, sys, tempfile, time
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["SP_STATE_DIR"] = _SB
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend"))
from app.services import cache as C                                    # noqa: E402
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


C._flush = lambda *a, **k: None
C._store.clear()
t0 = time.time()
real = time.time
C.set("short:a", 1, 60); C.set("short:b", 2, 60); C.set("live:c", 3, 86400); C.set("tomb:d", None, 7 * 86400)
time.time = lambda: real() + 3600                                       # بعد ساعة
try:
    C._purged_at = 0.0
    C.set("new:e", 5, 60)
    keys = set(C._store)
finally:
    time.time = real
check("short:a" not in keys and "short:b" not in keys, "١ المنتهي يُحذف من الذاكرة — لا يبقى بعد أن تجاهلته القراءة", str(sorted(keys)))
check({"live:c", "tomb:d", "new:e"} <= keys, "٢ والحيُّ يبقى، وشاهدُ القبر الطويلُ العمر يبقى")
src = open(C.__file__, encoding="utf-8").read()
check("_PURGE_EVERY = 300" in src and "_purge_expired(now)" in src.split("def set(")[1][:400],
      "٣ والحذفُ دوريٌّ في `set` (كلَّ خمس دقائق) — لا في كلّ نداءٍ فيُبطئ")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
