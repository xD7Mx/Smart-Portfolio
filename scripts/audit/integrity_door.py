#!/usr/bin/env python3
"""كاشفُ فحص السلامة (ملاحظةُ المالك 2026-11-14: «فحصُ السلامة يظهر إنذاراً قبيحاً») — قارئٌ فقط: أيُّ فحصٍ لم يمرّ ولماذا."""
import asyncio, os, sys, time
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")


async def main():
    from app.core.database import AsyncSessionLocal
    from app.services.integrity import run_integrity_check
    async with AsyncSessionLocal() as db:
        r = await run_integrity_check(db)
    for c in (r or {}).get("checks") or []:
        print(("✔" if c.get("ok") else "✘"), c.get("name"), "—", str(c.get("detail") or "")[:300])


asyncio.run(main())
