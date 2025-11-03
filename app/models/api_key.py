"""
API Key models
"""

from pydantic import BaseModel
from typing import Optional


class CreateAPIKeyRequest(BaseModel):
    """Request to create API key"""
    name: str
    user_id: Optional[int] = None
    permissions: Optional[str] = None
    expires_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API key response (with plaintext key only on creation)"""
    key_id: int
    key: Optional[str] = None  # Only present on creation
    name: str
    user_id: Optional[int] = None
    permissions: Optional[str] = None
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None
    is_active: Optional[bool] = True

