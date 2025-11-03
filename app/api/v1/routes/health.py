"""
Health check endpoint
"""

from fastapi import APIRouter
from datetime import datetime
from app.models.common import HealthResponse

router = APIRouter()

# Global scheduler reference (set from main app)
_scheduler = None


def set_scheduler(sched):
    """Set scheduler reference"""
    global _scheduler
    _scheduler = sched


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check endpoint
    """
    scheduler_running = _scheduler.running if _scheduler else False
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
        scheduler_running=scheduler_running
    )

