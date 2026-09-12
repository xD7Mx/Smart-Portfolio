"""
Health Check Endpoint — GET /api/v1/health
Returns status of all system components.
"""

from fastapi import APIRouter
from datetime import datetime, timezone
from app.core.config import settings
from app.core.response import success_response

router = APIRouter()


async def _db_state() -> str:
    """حالُ القاعدة **مقيسةً** — لا مكتوبةً (D271).

    كانت حالُ القاعدة نصّاً ثابتاً في الشيفرة: تقول «سليم» وقاعدةُ البيانات
    ميّتة، فيصير الفحصُ نفسُه مصدرَ تضليلٍ في اللحظة التي يُحتاج فيها.
    فتُسأل القاعدةُ سؤالاً حقيقياً بمهلةٍ قصيرة، ويُقال ما رُدّ.
    """
    import asyncio

    from sqlalchemy import text
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=4)
        return "ok"
    except Exception as e:                                        # noqa: BLE001
        return f"غير متاحة — {type(e).__name__}"


def _sched_state() -> str:
    try:
        import main
        st = main.SCHED_BOOT
    except Exception:                                             # noqa: BLE001
        return "غير معروف"
    if st.get("ok"):
        return "ok"
    return "متوقّفة" if st.get("ok") is False else "لم تبدأ بعد"


@router.get("")
async def health_check():
    """System health check — validates all critical services."""
    db = await _db_state()
    sched = _sched_state()
    healthy = db == "ok" and sched == "ok"
    return success_response(
        data={
            "status": "healthy" if healthy else "degraded",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "database": db,
                "scheduler": sched,
                "ai_provider": settings.AI_PROVIDER,
                "market_provider": settings.PRIMARY_MARKET_PROVIDER,
                "telegram": "enabled" if settings.TELEGRAM_ENABLED else "disabled",
            },
        },
        message=("All systems operational." if healthy
                 else f"خللٌ معلَن — القاعدة: {db} · الجدولة: {sched}")
    )
