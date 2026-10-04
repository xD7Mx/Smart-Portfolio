"""إجراءٌ إصلاحيّ محصور: يوقف مسحةَ التقييم اليتيمة (من نشرٍ أُلغي عند مهلته) داخل الحاوية — ولا يمسّ الخادمَ (pid 1).
يطابق سطرَ الأمر حرفاً، ويطبع ما أوقفه، ثمّ يقيس ردَّ الصحة.

    docker exec sp_backend python /app/scripts/audit/stop_orphan_sweep.py
"""
import json
import os
import signal
import time
import urllib.request

me = os.getpid()
stopped = []
for pid in os.listdir("/proc"):
    if not pid.isdigit() or int(pid) in (1, me):
        continue
    try:
        cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="ignore")
    except OSError:
        continue
    if "market_valuation_sweep import sweep" in cmd:
        os.kill(int(pid), signal.SIGTERM)
        stopped.append(int(pid))
time.sleep(5)
for pid in stopped:
    if os.path.exists(f"/proc/{pid}"):
        os.kill(pid, signal.SIGKILL)
time.sleep(5)
t0 = time.time()
try:
    h = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=30).status
except Exception as e:                                            # noqa: BLE001
    h = type(e).__name__
print("@@STOP@@ " + json.dumps({"stopped": stopped, "health": h, "health_s": round(time.time() - t0, 2)}))
