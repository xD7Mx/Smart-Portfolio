#!/usr/bin/env python3
"""حارسُ D582: ملفُّ المخزَّن مشتركٌ بين عملياتٍ (الخادمُ والمسحةُ والكواشف) — لا تمحو كتابةُ عمليةٍ ما كتبته أخرى،
والمسحُ الكلّيُّ المقصود وحده يُفرغه.

    python3 scripts/audit/cache_merge_d582.py
"""
import os, sys, json, tempfile, pathlib, subprocess, textwrap
ROOT = pathlib.Path(__file__).resolve().parents[2]
SB = tempfile.mkdtemp(prefix="sp-cache-")
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

def run(code: str) -> str:
    env = {**os.environ, "SP_STATE_DIR": SB, "PYTHONPATH": str(ROOT / "backend")}
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], env=env, capture_output=True, text=True, timeout=60)
    if r.returncode:
        print(r.stderr[-800:])
    return r.stdout.strip()

# «الخادم» يُقلع ويقرأ الملفّ (فارغاً)، ثمّ «مسحةٌ» في عمليةٍ أخرى تكتب، ثمّ «الخادم» يكتب — كما في النشر تماماً
code_server = """
import time, sys
from app.services import cache
open(sys.argv[0] if False else '/dev/null')
cache.set('server:key', 's', 7200)            # يُكتب (أكثر من ساعة)
cache.flush()
import subprocess, os
"""
run("""
from app.services import cache
cache.set('server:old', 1, 7200); cache.flush()
""")
# العمليتان متزامنتان: الخادمُ حمّل الملفّ قبل أن تكتب المسحة
out = run("""
import subprocess, sys, os, time
from app.services import cache            # «الخادم» يحمّل الآن
sweep = subprocess.run([sys.executable, '-c',
    "from app.services import cache; cache.set('sweep:key', 'w', 7200); cache.flush()"], env=os.environ)
time.sleep(0.05)
cache.set('server:new', 'n', 7200)         # الخادمُ يكتب بعد المسحة
cache.flush()
print('absorbed' if cache.get('sweep:key') == 'w' else 'not-absorbed')
""")
disk = json.load(open(os.path.join(SB, "cache_store.json"), encoding="utf-8"))
check({"server:old", "sweep:key", "server:new"} <= set(disk), "١ كتابةُ الخادم بعد المسحة لا تمحو ما كتبته المسحة", str(sorted(disk)))
check(out == "absorbed", "٢ والخادمُ يستوعب ما حسبته المسحةُ في ذاكرته", out)
run("""
from app.services import cache
cache.set('short:key', 1, 60); cache.flush()
""")
disk = json.load(open(os.path.join(SB, "cache_store.json"), encoding="utf-8"))
check("short:key" not in disk, "٣ ما عمرُه دون ساعةٍ لا يُكتب (كما كان)")
run("""
from app.services import cache
cache.clear()
""")
disk = json.load(open(os.path.join(SB, "cache_store.json"), encoding="utf-8"))
check(disk == {}, "٤ المسحُ الكلّيُّ المقصود يُفرغ الملفّ ولا يُدمج ما عليه", str(disk)[:80])
# ‏D592: الكتابةُ لا تقع في مسار الطلب — ملفٌّ ضخمٌ كتبته عمليةٌ أخرى لا يُبطئ `set`
big = {f"k{i}": [__import__("time").time() + 7200, {"v": "x" * 400}] for i in range(40000)}
json.dump(big, open(os.path.join(SB, "cache_store.json"), "w"))
out = run("""
import time, os, json
from app.services import cache
cache.set('warm', 1, 7200); cache.flush()                  # الملفُّ الآن ملفُّنا
p = os.path.join(os.environ['SP_STATE_DIR'], 'cache_store.json')
d = json.load(open(p)); d.update({f'z{i}': [time.time() + 7200, 'y' * 400] for i in range(40000)})
json.dump(d, open(p, 'w'))                                  # «المسحة» كتبت ملفّاً ضخماً
time.sleep(6)                                               # بعد نافذة التجميع: الكتابةُ التالية كانت تدمج داخل الطلب
dt = 0.0
for i in range(50):
    t0 = time.perf_counter()
    cache.set(f'n{i}', i, 7200)
    dt = max(dt, (time.perf_counter() - t0) * 1000)
time.sleep(12)                                              # الكاتبُ الخلفيّ يدمج ويكتب
d2 = json.load(open(p))
print(round(dt, 1), 'z1' in d2 and 'n49' in d2)
""")
ms, merged = out.split()
check(float(ms) < 50, f"٥ أبطأُ كتابةٍ في المخزّن {ms}ms — لا تنتظر القرصَ ولو كتب غيرُنا ملفّاً ضخماً", ms)
check(merged == "True", "٦ والكاتبُ الخلفيّ يدمج الملفَّين بعدها")
sys.exit(fail)
