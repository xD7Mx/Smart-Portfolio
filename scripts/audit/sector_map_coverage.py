#!/usr/bin/env python3
"""تغطيةُ درجات الحوكمة في خريطة القطاعات — قطاعاً قطاعاً (D432).

    docker exec sp_backend python /app/scripts/audit/sector_map_coverage.py

يُنادي `get_sector_map` الحقيقيّةَ على قاعدة الخادم ومخازنه، ويطبع لكلّ
قطاعٍ عددَ شركاته وكم منها له درجة، ثمّ المجموع. قارئٌ فقط.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")


async def main() -> int:
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.governance import get_sector_map
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0
    async with AsyncSessionLocal() as db:
        out = await get_sector_map(db)
    secs = (out or {}).get("sectors") or []
    tot = sum(s["count"] for s in secs)
    sc = sum(s.get("scored_count") or 0 for s in secs)
    for s in sorted(secs, key=lambda x: x["sector"]):
        miss = [c["symbol"] for c in s["companies"] if c["finance_score"] is None]
        print(f"  {s['sector']:32s} {s.get('scored_count', 0):>3}/{s['count']:<3}"
              + (f"  بلا درجة: {miss[:8]}" if miss else ""))
    print(f"\nالقطاعات: {len(secs)} · الشركات: {tot} · لها درجة: **{sc}**")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
