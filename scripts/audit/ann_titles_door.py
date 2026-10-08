#!/usr/bin/env python3
"""تشخيص: عناوينُ إفصاحات «تداول» كما تصل (لثلاث شركات) — لماذا صنّف التعدادُ صفراً. قارئٌ فقط."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services.tadawul_disclosure import list_for, detail

async def main():
    for s in ("2320", "1303", "7203"):
        rows = await list_for(s, 60)
        print(f"══ {s} · {len(rows)}")
        for a in rows[:14]:
            print(f"  {a.get('date')} · [{a.get('title')!r}] · {a.get('url','')[-60:]}")
        if rows:
            d = await detail(rows[0]["url"]) or {}
            print("  نصُّ الأوّل:", repr((d.get("title") or ""))[:120], "|", (d.get("text") or "")[:300].replace("\n", " ⏎ "))
asyncio.run(main())
