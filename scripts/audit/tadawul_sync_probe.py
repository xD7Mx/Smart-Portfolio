#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D242 — مسبارُ مزامنة الدليل: يُقرأ قبل أن يُكتب.
#
# مضيفُ «تداول» محجوبٌ عن بيئة التطوير، فبنيةُ صفحته لا تُخمَّن. وهذا
# المسبارُ يُشغَّل **على الخادم** فيجلب ويفهم ويطبع الخطّةَ — ولا يكتب:
#
#   docker exec sp_backend python /app/scripts/audit/tadawul_sync_probe.py
#   docker exec sp_backend python /app/scripts/audit/tadawul_sync_probe.py --apply
#
# فإن قال «فُهم ‎N رمزاً» وN معقولٌ وأسماؤه عربيةٌ صحيحة، فالبنيةُ ثابتةٌ
# ويُؤذَن بالكتابة. وإن قال «فُهم 3» فالصفحةُ تغيّرت أو الحمايةُ ردّت —
# ولا يُوسَم أحدٌ موقوفاً على أساسٍ كهذا (حدُّ MIN_LISTED يمنعه).
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import json
import sys

for _p in ("/app", "backend", "."):
    if _p not in sys.path:
        sys.path.insert(0, _p)

APPLY = "--apply" in sys.argv


async def main() -> int:
    from app.services.tadawul_sync import MIN_LISTED, fetch_listed, plan, apply_plan

    listed, why = await fetch_listed()
    if not listed:
        print(f"✘ تعذّر الجلب أو الفهم: {why}")
        print(f"   الحدُّ الأدنى للقبول {MIN_LISTED} رمزاً — ولا يُكتب شيءٌ دونه.")
        return 1
    print(f"✔ فُهم {len(listed)} رمزاً من «تداول».")
    for s, r in list(sorted(listed.items()))[:5]:
        print(f"   {s} · {r.get('name')} · {r.get('sector') or '—'}")

    p = plan(listed)
    print()
    print(f"الخطّة: جديد {len(p['added'])} · تسمية {len(p['renamed'])} · "
          f"موقوف {len(p['suspended'])} · غائبٌ مرّةً "
          f"{len(p.get('absent_once') or [])} · عائد {len(p['resumed'])}")
    print("‏(التسميةُ تُسجَّل ولا تُكتب إلا حيث لا اسمَ عندنا · "
          "والوسمُ لا يُكتب إلا بعد غيابين متتاليين)")
    for label, key in (("جديد", "added"), ("تسمية", "renamed"),
                       ("موقوف", "suspended"), ("غائبٌ مرّةً", "absent_once"),
                       ("عائد", "resumed")):
        for row in (p.get(key) or [])[:10]:
            print(f"   [{label}] {json.dumps(row, ensure_ascii=False)}")

    if not APPLY:
        print()
        print("… لم يُكتب شيء (مسبار). أضف --apply للكتابة في الطبقة.")
        return 0
    print()
    print("طُبِّق:", json.dumps(apply_plan(p), ensure_ascii=False))
    return 0


raise SystemExit(asyncio.run(main()))
