"""كاشف (قراءةٌ فقط): آخرُ تجهيزٍ لصفحات الأسهم — متى، وفي أيّ عملية، وكم استغرق — D581.

    docker exec sp_backend python /app/scripts/audit/stock_warm_status.py
"""
import json
import os
import sys

sys.path.insert(0, "/app")
from app.services import lastgood

r = lastgood.load("stock_warm:_last") or {}
print("@@WARM_STATUS@@ " + json.dumps({**r, "probe_pid": os.getpid()}, ensure_ascii=False)[:3000])
