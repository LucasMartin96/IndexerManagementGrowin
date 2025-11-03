"""
User models
"""

from pydantic import BaseModel
from typing import Optional


class CreateUserRequest(BaseModel):
    """Request to create user"""
    username: str
    password: str
    email: Optional[str] = None
    role: str = "user"


class UserResponse(BaseModel):
    """User response"""
    id: int
    username: str
    email: Optional[str] = None
    role: str
    created_at: Optional[str] = None
    is_active: Optional[bool] = True

