#!/usr/bin/env python3
"""أوّلُ صفحةٍ في سجلّ التحقّق (‏D638) — تُكتب الآن فلا يضيع يومُ التجميد. يكتب مرّةً في اليوم (لا تكرار)، ويطبع ما كُتب."""
import sys
sys.path.insert(0, "/app")
from app.services.engine_ledger import snapshot, load, _dir
n = snapshot()
rows = load()
print(f"كُتب اليوم {n} صفّاً · السجلُّ كلُّه {len(rows)} · الأيام {sorted({r['d'] for r in rows})} · المجلّد {_dir()}")
print("عيّنة:", rows[:2])
