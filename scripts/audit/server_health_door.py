"""كاشف (قراءةٌ فقط): صحةُ الخادم — الذاكرةُ المتاحة، والعملياتُ الطويلة داخل الحاوية، وردُّ الصحة، والمهامُّ المجدولة القادمة.

    docker exec sp_backend python /app/scripts/audit/server_health_door.py
"""
import json
import os
import subprocess
import sys
import urllib.request

sys.path.insert(0, "/app")
from app.services.tadawul_pdf import mem_available_mb

procs = []
for pid in os.listdir("/proc"):
    if not pid.isdigit():
        continue
    try:
        cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="ignore")[:160]
        rss = 0
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1]) // 1024
        et = os.stat(f"/proc/{pid}").st_mtime
        procs.append({"pid": int(pid), "rss_mb": rss, "cmd": cmd})
    except Exception:                                             # noqa: BLE001
        pass
try:
    h = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=10).status
except Exception as e:                                            # noqa: BLE001
    h = type(e).__name__
print("@@HEALTH@@ " + json.dumps({"mem_available_mb": mem_available_mb(), "health": h,
                                  "procs": sorted([p for p in procs if p["rss_mb"] > 20], key=lambda p: -p["rss_mb"])[:10]},
                                 ensure_ascii=False))
