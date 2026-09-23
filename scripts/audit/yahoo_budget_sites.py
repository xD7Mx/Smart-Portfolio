#!/usr/bin/env python3
"""مَن يستهلك حصّةَ ياهو اليوم — موضعاً موضعاً (D436).

    docker exec sp_backend python /app/scripts/audit/yahoo_budget_sites.py

حصّةُ ياهو الداخليةُ واحدةٌ يتقاسمها كلُّ شيء، ونفادُها اليوم أخلى برنت
ورسمَي المؤشّرين وحبس درجاتٍ في محرّك الجودة. ولا تُقسَم الحصّةُ قبل أن
يُعرف مستهلكُها: يُقرأ عدّادُ اليوم ومواضعُ النداء كما يسجّلها المتتبِّع.
قارئٌ فقط.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

try:
    from app.services import usage_tracker as U
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    raise SystemExit(0)

print("الاستهلاكُ اليوم:", U.usage("yahoo"))
st = U.sites("yahoo") or {}
tot = sum(st.values()) or 1
for k, v in sorted(st.items(), key=lambda x: -x[1])[:20]:
    print(f"  {v:>6}  {v * 100 / tot:5.1f}%  {k}")
