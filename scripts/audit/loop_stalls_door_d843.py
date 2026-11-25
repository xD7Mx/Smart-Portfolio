#!/usr/bin/env python3
"""كاشفُ D843 (٣) — ما سجّله رقيبُ الحلقة في العملية الحيّة: كلُّ حبسٍ فوق 400ms بمدّته ومكانه في الشيفرة، مجمَّعاً بالمكان. قراءةٌ فقط.

    docker exec sp_backend python /app/scripts/audit/loop_stalls_door_d843.py
"""
import json
import os
from collections import defaultdict

p = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "perf", "loop_stalls.json")
try:
    rows = json.load(open(p, encoding="utf-8"))
except Exception as e:                                           # noqa: BLE001
    print("لا سجلّ بعد:", type(e).__name__)
    raise SystemExit(0)
print(f"حبساتٌ مسجّلة: {len(rows)} · من {rows[0]['at'] if rows else '—'} إلى {rows[-1]['at'] if rows else '—'}")
by = defaultdict(lambda: [0, 0, 0])
for r in rows:
    k = " ← ".join((r.get("where") or ["?"])[:3])
    by[k][0] += 1
    by[k][1] += r.get("ms") or 0
    by[k][2] = max(by[k][2], r.get("ms") or 0)
print("\nمجمَّعةً بالمكان (المجموع ms · العدد · الأطول):")
for k, (n, tot, mx) in sorted(by.items(), key=lambda kv: -kv[1][1])[:15]:
    print(f"  {tot:7}ms · {n:3}× · أطولُها {mx:6}ms · {k}")
print("\nآخرُ عشرة:")
for r in rows[-10:]:
    print(f"  {r['at']} · {r.get('ms')}ms · {' ← '.join((r.get('where') or [])[:4])}" + (f"\n      ثمّ: {' ← '.join(r['where2'][:4])}" if r.get("where2") else ""))
