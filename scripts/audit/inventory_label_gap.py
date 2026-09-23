#!/usr/bin/env python3
"""اسمُ المخزون في ملفّات «تداول» الرسمية — كما ورد (D430).

    docker exec sp_backend python /app/scripts/audit/inventory_label_gap.py

قِيس على خادم المالك: خمسَ عشرةَ ورقةً (أغلبُها سلعٌ استهلاكيةٌ دورية)
فقدت درجةَ الجودة في مسحةٍ واحدة، وسببُها المُعلَن «خبيران فقط استطاعا
الحكم»، والناقصُ بعينه **«دوران المخزون»** و«صافي الدين إلى الأرباح
التشغيلية». والمحرّكُ يطلب حقلَ `inventory`، وخريطةُ «تداول» **لا اسمَ
فيها للمخزون أصلاً** — فالمخزونُ يأتي من ياهو وحدَه، ونفدت حصّتُه
اليومية في ذلك اليوم.

فتُقرأ صفوفُ المخزون غيرُ المطابَقة في ملفّات هذه الأوراق بعينها كما
وردت، وتُرتَّب بتكرارها — فيُضاف الاسمُ بالحرف لا تخميناً. قارئٌ فقط.
"""
from __future__ import annotations

import asyncio
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

SYMS = ("1810", "1820", "1830", "4008", "4011", "4071", "4080", "4170",
        "4191", "4192", "4193", "4194", "4210", "6018", "2340", "4180")
PAT = r"inventor|stock[- ]in[- ]trade|goods for resale|merchandise"


async def main() -> int:
    try:
        from app.services import tadawul_xbrl as X
        from debt_label_gap import _unmatched
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0
    found: collections.Counter = collections.Counter()
    example: dict[str, str] = {}
    why: collections.Counter = collections.Counter()
    sem = asyncio.Semaphore(6)

    async def _one(s):
        async with sem:
            try:
                return s, *(await _unmatched(X, s))
            except Exception as e:                                # noqa: BLE001
                return s, None, type(e).__name__

    ok = 0
    for s, rows, err in await asyncio.gather(*(_one(s) for s in SYMS)):
        if not rows:
            why[str(err)] += 1
            continue
        ok += 1
        for name, val in rows:
            if re.search(PAT, name, re.I):
                found[name] += 1
                example.setdefault(name, f"{s} = {val}")
    print(f"قُرئت ملفّاتُ {ok} من {len(SYMS)}"
          + (f" · تعذّر: {dict(why)}" if why else ""))
    print(f"\nأسماءُ المخزون غيرُ المطابَقة: {len(found)}")
    for name, n in found.most_common(20):
        print(f"  {n:>3}× {name}\n       مثالٌ: {example[name]}")
    if not found:
        print("لا اسمَ للمخزون في هذه الملفّات — فالنقصُ غيابُ بندٍ لا عجزُ خريطة")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
