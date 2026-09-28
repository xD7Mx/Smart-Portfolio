"""كاشفٌ للقراءة فقط (D505): هل تحمل لقطةُ «تداول» التغيّرَ اليوميّ؟

    docker exec sp_backend python /app/scripts/audit/tadawul_change_door.py
"""
import sys
sys.path.insert(0, "/app")
from app.services import tadawul_market as TM  # noqa: E402
from app.services import cache, lastgood       # noqa: E402

rec = cache.get(TM.STORE_KEY) or lastgood.load(TM.STORE_KEY, max_age_seconds=10 * 86400)
rows = (rec or {}).get("rows") or {}
print("عمرُ اللقطة (ث):", TM.age_seconds(), "· صفوفُ المخزَّن:", len(rows), "· snapshot():", len(TM.snapshot() or {}))
with_chg = [k for k, v in rows.items() if isinstance(v, dict) and v.get("change_pct") is not None]
print("صفوفٌ بتغيّر:", len(with_chg))
for k in list(rows)[:2]:
    print("  ", k, sorted(rows[k].keys()))
raw = (rec or {}).get("raw_keys")
print("مفاتيحُ الصفّ الخام إن حُفظت:", raw)
