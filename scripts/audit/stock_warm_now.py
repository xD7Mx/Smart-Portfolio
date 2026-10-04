"""كاشفٌ يكتب المخزَّنَ وحده: يُجهّز صفحاتِ أسهم المحافظ والمراقبة الآن ويقيس زمنَه — D581.

    docker exec sp_backend python /app/scripts/audit/stock_warm_now.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.core.portfolio_scope import install_scope_listeners
    try:
        install_scope_listeners()
    except Exception:                                             # noqa: BLE001
        pass
    from app.services.stock_warm import warm
    print("@@WARM@@ " + json.dumps(await warm(), ensure_ascii=False)[:3000])

asyncio.run(main())
