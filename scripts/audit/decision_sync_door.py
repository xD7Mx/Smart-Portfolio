"""كاشف D575 (قراءةٌ فقط): كم شركةً يخالف قرارُها في الفرز آخرَ حكمٍ لصفحتها — قبل المزامنة وبعدها.

    docker exec sp_backend python /app/scripts/audit/decision_sync_door.py
"""
import json
import sys

sys.path.insert(0, "/app")
from app.services import lastgood
from app.services.market_screener import with_live_decisions, _label

raw = lastgood.load("market:screener") or []
deep = lastgood.load("governance:deep") or {}
def diff(rows):
    out = []
    for r in rows:
        d = deep.get(str(r.get("symbol")).replace(".SR", ""))
        if isinstance(d, dict) and d.get("decision") is not None and _label(d["decision"]) != r.get("decision"):
            out.append((r.get("symbol"), r.get("decision"), _label(d["decision"])))
    return out
b, a = diff(raw), diff(with_live_decisions(raw))
print("@@SYNC@@ " + json.dumps({"rows": len(raw), "deep": len(deep), "before": len(b), "after": len(a),
                                "sample": b[:12], "4340": [x for x in b if str(x[0]).startswith("4340")]}, ensure_ascii=False))
