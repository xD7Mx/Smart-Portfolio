"""كاشف (قراءةٌ فقط · D596): ما حُفظ فعلاً من جدول «المعلومات المالية» — في عمليةٍ جديدة تقرأ القرص.

    docker exec sp_backend python /app/scripts/audit/tfin_census.py
"""
import sys

sys.path.insert(0, "/app")
from app.services import lastgood
from app.services.tadawul_xbrl import for_symbol, _xbrl_for

keys = lastgood.keys_with_prefix("tfin2:")
lat, gain = {}, 0
for k in keys:
    r = lastgood.load(k) or {}
    q = [p["as_of"] for p in (r.get("quarterly") or []) + (r.get("annual") or [])]
    m = max(q)[:7] if q else "none"
    lat[m] = lat.get(m, 0) + 1
    s = k.split(":", 1)[1]
    xb = [p["as_of"] for p in _xbrl_for(s, "quarterly") + _xbrl_for(s, "annual")]
    mg = [p["as_of"] for p in for_symbol(s, "quarterly") + for_symbol(s, "annual")]
    if mg and (not xb or max(mg) > max(xb)):
        gain += 1
print("@@KEYS@@", len(keys), flush=True)
print("@@LATEST@@", dict(sorted(lat.items(), reverse=True)), flush=True)
print("@@NEWER_THAN_XBRL@@", gain, flush=True)
for s in ("8010", "8250", "8050", "2222", "1120"):
    q = for_symbol(s, "quarterly")
    print(f"@@{s}@@", [(p["as_of"], p.get("source", "xbrl")[:6], p.get("net_income"), p.get("equity")) for p in q[-3:]], flush=True)
