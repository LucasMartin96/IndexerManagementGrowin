"""
Common models (health, error)
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    scheduler_running: bool


class ErrorResponse(BaseModel):
    """Error response"""
    status: str = "error"
    message: str

