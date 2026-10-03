"""كاشف (قراءةٌ فقط): إحصاءُ قرارات السوق من المخزن العميق — كم «بيانات غير كافية» ولماذا.

    docker exec sp_backend python /app/scripts/audit/abstain_census_door.py
"""
import json
import sys
from collections import Counter

sys.path.insert(0, "/app")
from app.services import lastgood
from app.services.market_screener import get_cached_screener

rows = get_cached_screener() or []
c = Counter(str(r.get("decision")) for r in rows)
ab = [r.get("symbol") for r in rows if "غير كافية" in str(r.get("decision"))]
deep = lastgood.load("governance:deep") or {}
reasons = Counter()
for s in ab:
    d = (deep.get(str(s).replace(".SR", "")) or {}).get("decision")
    reasons[(d or {}).get("reason", "")[:70] if isinstance(d, dict) else "لا حكمَ عميق"] += 1
print("@@CENSUS@@ " + json.dumps({"rows": len(rows), "decisions": c.most_common(), "abstain": ab[:60],
                                   "reasons": reasons.most_common(8)}, ensure_ascii=False))
