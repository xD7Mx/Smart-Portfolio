#!/usr/bin/env python3
"""حارسُ D597: حفظٌ يقع **أثناء** كتابة المخزن إلى القرص لا يضيع.
قِيس: قراءةُ جدول المعلومات المالية للسوق نجحت في 252 ورقة وحُفظ منها 158 — والباقي مُحي بصمت.

    python3 scripts/audit/lastgood_race_d597.py
"""
import os, sys, json, tempfile, pathlib, subprocess, textwrap
ROOT = pathlib.Path(__file__).resolve().parents[2]
SB = tempfile.mkdtemp(prefix="sp-lg-")
code = textwrap.dedent("""
    import threading, time, json, os
    from app.services import lastgood as L
    real_dump = json.dump
    hit = {"n": 0}
    def slow_dump(obj, f, **kw):
        # أثناء الكتابة: عمليةٌ أخرى في العملية نفسِها تحفظ مفاتيحَ جديدة
        if hit["n"] == 0:
            hit["n"] = 1
            t = threading.Thread(target=lambda: [L.save(f"race:{i}", {"v": i}) for i in range(50)])
            t.start(); t.join()
        return real_dump(obj, f, **kw)
    L.save("first", {"v": 1})
    json.dump = slow_dump
    L.flush()
    json.dump = real_dump
    L.flush()
    disk = json.load(open(L._PATH))
    print(json.dumps({"disk": sum(1 for k in disk if k.startswith("race:")), "first": "first" in disk}))
""")
env = {**os.environ, "LASTGOOD_PATH": os.path.join(SB, "lg.json"), "PYTHONPATH": str(ROOT / "backend")}
r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=60)
out = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1] or "{}")
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))
if r.returncode:
    print(r.stderr[-600:])
check(out.get("first") is True, "١ المفتاحُ المحفوظُ قبل الكتابة على القرص")
check(out.get("disk") == 50, "٢ والخمسون المحفوظةُ أثناء الكتابة كلُّها على القرص بعد الإفراغ التالي", str(out.get("disk")))
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
