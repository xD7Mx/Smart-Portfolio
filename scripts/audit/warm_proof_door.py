"""كاشف (قراءةٌ فقط): هل جهّز الخادمُ الحيُّ صفحاتِ الأسهم بعد إقلاعه؟ — D581.

المخزَّنُ الطويلُ يُكتب إلى القرص بزمن انقضائه؛ فزمنُ الإنشاء = الانقضاءُ − العمر. إن أُنشئت مفاتيحُ شركات المحافظ
بعد الإقلاع بدقائق، فالتجهيزُ جرى داخل الخادم.

    docker exec sp_backend python /app/scripts/audit/warm_proof_door.py
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/app")


async def main():
    from app.services.stock_warm import targets
    path = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "cache_store.json")
    raw = json.load(open(path, encoding="utf-8"))
    up = None
    try:
        up = os.stat("/proc/1").st_mtime          # إقلاعُ الحاوية تقريباً
    except OSError:
        pass
    ttl = {"health:v5:": 86400, "fvm:v40:": 6 * 3600, "argaam:recs:": 7 * 86400}
    rows = {}
    for sym, _n in (await targets())[:12]:
        r = {}
        for pre, t in ttl.items():
            item = raw.get(pre + sym)
            if item:
                created = item[0] - t
                r[pre.rstrip(":")] = datetime.fromtimestamp(created, timezone.utc).strftime("%H:%M:%S") if created > time.time() - 86400 * 7 else "old"
        rows[sym] = r
    print("@@PROOF@@ " + json.dumps({"now": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                                     "container_start": datetime.fromtimestamp(up, timezone.utc).strftime("%H:%M:%S") if up else None,
                                     "file_mtime": datetime.fromtimestamp(os.stat(path).st_mtime, timezone.utc).strftime("%H:%M:%S"),
                                     "rows": rows}, ensure_ascii=False)[:3500])

asyncio.run(main())
