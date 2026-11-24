#!/usr/bin/env python3
"""كاشفُ D800 على الخادم — قائمةُ المراقبة في ويدجت الآيفون (قراءةٌ لا تكتب شيئاً، ولا تطبع رمزاً ولا سعراً):

  ١ الطريقُ في الخادم الحيّ: ‏/widget/watchlist عامٌّ يرفض بلا رمز (‏401 برسالة الويدجت).
  ٢ لكلّ قائمةٍ (محفظتي ثمّ قوائمُ التطبيق بترتيبها): عددُ الشركات، وكم منها له سعرٌ من باب غرفة التداول، وكم له شعارٌ من بابنا،
    وزمنُ الطلب — في جلسةٍ تُلغى في آخرها (فحصُ الرمز مُعطَّلٌ داخل هذا الكاشف وحده، و«آخرُ استعمالٍ» لا يُحفظ).

    docker exec sp_backend python /app/scripts/audit/widget_list_door_d800.py
"""
import os
import time

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()

import asyncio  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, "/app")


async def main():
    import httpx
    from main import app
    from app.core.database import AsyncSessionLocal
    from app.api.v1.endpoints import widget as WG

    print("══ ١ الطريقُ في الخادم الحيّ:")
    paths = {getattr(r, "path", "") for r in app.routes}
    route = next((p for p in paths if p.endswith("/widget/watchlist")), None)
    print("   الطريق:", route or "غيرُ موجود")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t/api/v1", timeout=60) as c:
        r = await c.get("/widget/watchlist")
    print("   بلا رمز:", r.status_code, (r.json().get("detail") or "")[:60] if r.headers.get("content-type", "").startswith("application/json") else "")

    print("══ ٢ القوائم:")

    async def nocheck(db, token):
        return None
    WG._check = nocheck
    async with AsyncSessionLocal() as db:
        async def no_commit():
            await db.rollback()
        db.commit = no_commit                                    # «آخرُ استعمال» لا يُحفظ من الكاشف
        t0 = time.monotonic()
        first = await WG.widget_watchlist(None, None, db)
        d = first.get("data") or {}
        specs = [("mine", "محفظتي")] + [(x["key"], x["name"]) for x in d.get("lists", [])[1:]]
        for key, name in specs:
            t1 = time.monotonic()
            res = first if key == "mine" else await WG.widget_watchlist(key, None, db)
            items = (res.get("data") or {}).get("items") or []
            priced = sum(1 for i in items if i.get("price") is not None)
            logos = sum(1 for i in items if str(i.get("logo") or "").startswith("/market/logo/"))
            ms = (time.monotonic() - (t0 if key == "mine" else t1)) * 1000
            print(f"   «{name}»: {len(items)} شركة · لها سعر {priced} · لها شعار {logos} · {ms:.0f}ms")
        await db.rollback()
    print("══ انتهى")


asyncio.run(main())
