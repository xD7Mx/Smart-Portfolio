"""كاشفٌ للقراءة فقط: شركاتٌ في لقطة «تداول» وليست في دليلنا (أرماح 6022 مثالاً).

    docker exec sp_backend python /app/scripts/audit/directory_gap_door.py
"""
import json
import sys

sys.path.insert(0, "/app")
from app.services import tadawul_market as TM, cache, lastgood   # noqa: E402

d = json.load(open("/app/app/data/saudi_directory.json", encoding="utf-8"))
rec = cache.get(TM.STORE_KEY) or lastgood.load(TM.STORE_KEY, max_age_seconds=10 * 86400) or {}
rows = rec.get("rows") or {}
gap = sorted(s for s in rows if s not in d)
print(f"لقطةُ تداول {len(rows)} · الدليل {len(d)} · غائبٌ عن الدليل {len(gap)}")
for s in gap:
    r = rows[s]
    print(f"   {s} · {r.get('name_ar') or '—'} · {r.get('name_en')} · {r.get('sector_en')} · {r.get('company_url')}")
