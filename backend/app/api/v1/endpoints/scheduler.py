from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.response import success_response

router = APIRouter()

@router.get("")
async def get_scheduler_status():
    return success_response(data={"status": "running", "jobs": ["market_update", "ai_analysis", "daily_report", "backup"]})

@router.post("/run")
async def run_job(job_name: str):
    return success_response(message=f"Job '{job_name}' triggered manually.")
