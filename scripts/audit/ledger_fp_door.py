#!/usr/bin/env python3
"""كاشفُ D647 على الإنتاج — قارئٌ فقط: بصمةُ الشيفرة العاملة داخل الحاوية، وما سيختم به السجلُّ يومَه القادم، وبصماتُ الأيّام المسجَّلة."""
import collections, json, sys
sys.path.insert(0, "/app")
from app.services.engine_identity import fingerprint
from app.services import engine_ledger as L
base = json.load(open("/app/scripts/audit/engine_baseline.json", encoding="utf-8")).get("fingerprint")
print(f"بصمةُ الشيفرة العاملة: {fingerprint()} · بصمةُ الأساس المجمَّد: {base} · يختم السجلُّ القادم: {L._fingerprint()}")
by = collections.Counter((r.get("d"), r.get("fp")) for r in L.load())
for (d, fp), n in sorted(by.items()):
    print(f"  {d} · {fp} · {n} صفّاً")
