#!/usr/bin/env python3
"""حداثةُ القوائم المحفوظة للسوق الرئيسية: آخرُ سنةٍ لكلّ ورقة ومصدرُها. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/statements_freshness.py
"""
import collections, sys
from datetime import date
sys.path.insert(0, "/app")

from app.services import tadawul_xbrl as X
from app.services.tadawul_market import usable_rows
try:
    from app.data.universe import is_main
except Exception:                                                  # noqa: BLE001
    is_main = lambda s: not s.startswith("9")                      # noqa: E731
rows = usable_rows()[0] or {}
st = X._store()
cut = date.today().year - 1
by_year, by_sec, late = collections.Counter(), collections.defaultdict(collections.Counter), []
for k, r in sorted(rows.items()):
    s = str(k).replace(".SR", "")
    if not is_main(s):
        continue
    an = (st.get(s) or {}).get("annual") or []
    last = an[-1] if an else {}
    y = last.get("year") or 0
    by_year[y] += 1
    sec = (r or {}).get("sector_en") or "?"
    by_sec[sec]["حديثة" if y >= cut else "متأخّرة"] += 1
    if y < cut:
        late.append((sec, s, y))
    if s.startswith("80") or s in ("8210", "8230", "8313"):
        print(f"  {s} {y} · {last.get('source', 'XBRL')} · إيراد {last.get('revenue')} · ربح {last.get('net_income')} · حقوق {last.get('equity')} · ربحيةُ سهم {last.get('eps')}")
print("\nآخرُ سنةٍ في السوق الرئيسية:", dict(sorted(by_year.items())))
print("\nلكلّ قطاع:")
for sec, c in sorted(by_sec.items(), key=lambda kv: -kv[1]["متأخّرة"]):
    print(f"  {sec[:40]:42} حديثة {c['حديثة']:3} · متأخّرة {c['متأخّرة']:3}")
print("\nالمتأخّرة:", " ".join(f"{s}({y})" for _, s, y in sorted(late)))
