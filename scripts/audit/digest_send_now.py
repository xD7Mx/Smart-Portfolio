"""إجراءٌ محصور (D604): يُرسل ملخّصَ الإغلاق الآن مرّةً للتحقّق — ويطبع أسطرَه.

    docker exec sp_backend python /app/scripts/audit/digest_send_now.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services.market_close_digest import send
    print("@@DIGEST@@", await send(force=True), flush=True)
    from app.services import lastgood
    lastgood.flush()

asyncio.run(main())
