#!/usr/bin/env python3
"""مخزَنُ القوائم: ما حُصد وما بقي منه على القرص (D423).

    docker exec sp_backend python /app/scripts/audit/xbrl_store_census.py

قِيس على خادم المالك في دورةٍ كاملة: الحصادُ قال **«قُرئت 176»**، وفي
الحلقة الخامسة من السلسلة بعدها بدقائق: **«لها قوائمُ = 0/60»**، ومسحةُ
التقييم: **«تعذّرت 269 من 273»** و«لها سعرٌ عادل: صفر». فالرقمُ الذي
دخل ليس الرقمَ الذي بقي — والفرقُ لا يُفسَّر بالمصدر.

فيُقرأ **ما على القرص** بعينه: كم رمزاً تحت `market:xbrl`، وكم منها
يجتاز شرطَ العمر فيصل `for_symbol`، وهل الملفُّ قابلٌ للكتابة، ومتى
كُتب آخرَ مرّة. ولا يُستنتَج سببٌ قبل هذا.
"""
from __future__ import annotations

import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

try:
    from app.services import lastgood
    from app.services.tadawul_xbrl import MAX_AGE_DAYS, STORE_KEY, for_symbol
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)

path = getattr(lastgood, "_PATH", "?")
print(f"ملفُّ المخزَن: {path}")
try:
    st_ = os.stat(path)
    print(f"  حجمٌ: {st_.st_size/1e6:.2f} ميجابايت · آخرُ كتابةٍ قبل "
          f"{int(time.time() - st_.st_mtime)} ثانية")
    print(f"  قابلٌ للكتابة: {os.access(path, os.W_OK)}")
except OSError as e:
    print(f"  لا يُقرأ: {e}")

rec = lastgood.load(STORE_KEY)
rec = rec if isinstance(rec, dict) else {}
print(f"\nرموزٌ تحت `{STORE_KEY}`: **{len(rec)}**")

with_annual = sum(1 for v in rec.values()
                  if isinstance(v, dict) and (v.get("annual") or []))
print(f"  ومنها ما فيه قوائمُ سنوية: {with_annual}")

reach = sum(1 for s in rec if for_symbol(s))
print(f"  وما يصل `for_symbol` (عمرٌ ≤ {MAX_AGE_DAYS} يوماً): **{reach}**")

ages: dict[str, int] = {}
for s, v in rec.items():
    if isinstance(v, dict):
        ages[str(v.get("as_of"))] = ages.get(str(v.get("as_of")), 0) + 1
print("  توزيعُ تاريخ الإيداع: "
      + "، ".join(f"{k}:{n}" for k, n in sorted(ages.items())[-6:]))

print(f"\nمفاتيحُ المخزَن كلِّه: {len(lastgood._load())}")
