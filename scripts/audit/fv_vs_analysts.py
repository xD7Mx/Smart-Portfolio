#!/usr/bin/env python3
"""محرّكُنا مقابل أهداف المحلّلين — على كلّ ورقةٍ لها الاثنان. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fv_vs_analysts.py

قال المالك: «أريده يقارع المحللين وينافسهم». فيُقاس: وسيطُ نسبة تقديرنا
إلى هدفهم، ونسبةُ ما يقع ضمن ±25٪ منه، والانحيازُ بالنمط.
"""
import collections, statistics, sys
sys.path.insert(0, "/app")
from app.services.market_screener import get_cached_screener
from app.services.statement_merge import archetype_of
rows = get_cached_screener() or []
pairs = [(r["symbol"], r["fair_value"], r["analyst_target"], r.get("price")) for r in rows
         if isinstance(r.get("fair_value"), (int, float)) and isinstance(r.get("analyst_target"), (int, float))
         and r["analyst_target"] > 0]
print(f"صفوف={len(rows)} · لها الاثنان={len(pairs)}")
if pairs:
    q = [fv / at for _, fv, at, _ in pairs]
    print(f"وسيطُ تقديرنا÷هدفهم = {statistics.median(q):.3f} · ضمن ±25٪ = {sum(0.75 <= x <= 1.25 for x in q)}/{len(q)}"
          f" · ضمن ±15٪ = {sum(0.85 <= x <= 1.15 for x in q)}/{len(q)}")
    by = collections.defaultdict(list)
    for (s, fv, at, _), x in zip(pairs, q):
        by[archetype_of(s)].append(x)
    for a, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"   {a:<20} n={len(xs):>3} · وسيط={statistics.median(xs):.2f}")
    for s, fv, at, px in sorted(pairs, key=lambda p: p[1] / p[2])[:8] + sorted(pairs, key=lambda p: p[1] / p[2])[-5:]:
        print(f"   {s} · تقديرنا {fv} · هدفهم {at} · سعر {px} · نسبة {fv/at:.2f}")
