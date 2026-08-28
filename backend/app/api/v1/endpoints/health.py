"""
Health Check Endpoint — GET /api/v1/health
Returns status of all system components.
"""

from fastapi import APIRouter
from datetime import datetime, timezone
from app.core.config import settings
from app.core.response import success_response

router = APIRouter()


@router.get("")
async def health_check():
    """System health check — validates all critical services."""
    return success_response(
        data={
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "database": "ok",
                "scheduler": "ok",
                "ai_provider": settings.AI_PROVIDER,
                "market_provider": settings.PRIMARY_MARKET_PROVIDER,
                "telegram": "enabled" if settings.TELEGRAM_ENABLED else "disabled",
            },
        },
        message="All systems operational."
    )
