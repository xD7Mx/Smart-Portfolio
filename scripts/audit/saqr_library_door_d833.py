#!/usr/bin/env python3
"""كاشفُ D833 على الخادم — هل درس صقرٌ كتبَ المكتبة؟ (قراءةٌ لا تكتب شيئاً، وبالأعداد وحدها — لا عناوينَ ولا مبادئَ في السجلّ)

  ١ الكتب: كم كتاباً في المكتبة، وكم جاهزاً بنصّه.
  ٢ الدراسة: كم كتاباً درسه صقرٌ بعين المتداول (‏lib:saqr) وكم للطيار (‏lib:wisdom)، وعددُ المبادئ وأصنافُها.
  ٣ ما يصل صقراً في حكمه: عددُ أسطر علمه في التوجيه وبصمتُه — أو أنّه فارغٌ بعد (فلم يُدرس شيء).

    docker exec sp_backend python /app/scripts/audit/saqr_library_door_d833.py
"""
import asyncio
import os
import sys
import time
from collections import Counter

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()
sys.path.insert(0, "/app")


async def books() -> tuple[int, int]:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.market import LibraryBook
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(LibraryBook).execution_options(skip_portfolio_scope=True))).scalars().all()
    return len(rows), sum(1 for b in rows if b.ready and b.has_text)


def main():
    from app.services import lastgood
    from app.services import library_wisdom as LW
    try:
        n, ready = asyncio.run(books())
        print(f"١ الكتب: {n} في المكتبة · جاهزٌ بنصّه {ready}")
    except Exception as e:                                        # noqa: BLE001
        print(f"١ الكتب: تعذّرت القراءة ({type(e).__name__})")
    for pre, lbl in (("lib:saqr:", "صقر (بعين المتداول)"), ("lib:wisdom:", "الطيار (مبادئُ المحفظة)")):
        recs = [lastgood.load(k) or {} for k in lastgood.keys_with_prefix(pre)]
        recs = [r for r in recs if r.get("principles")]
        kinds = Counter(p.get("kind") or "—" for r in recs for p in r["principles"])
        print(f"٢ {lbl}: كتبٌ مدروسة {len(recs)} · مبادئ {sum(len(r['principles']) for r in recs)} · مصوّرةٌ {sum(1 for r in recs if r.get('visual'))} · "
              f"أصناف {dict(kinds)}")
    txt, v = LW.saqr_block()
    print(f"٣ ما يصل صقراً في حكمه: {txt.count('•')} مبدأً · بصمة {v or '—'}" + ("" if txt else " — فارغ: لم يُدرس كتابٌ بعد"))


main()
