"""
Parameter models
"""

from pydantic import BaseModel
from typing import Optional


class CreateParamRequest(BaseModel):
    """Request to create parameter"""
    key: str
    value: str
    description: Optional[str] = None
    category: Optional[str] = None


class UpdateParamRequest(BaseModel):
    """Request to update parameter"""
    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class ParamResponse(BaseModel):
    """Parameter response"""
    id: int
    key: str
    value: str
    description: Optional[str] = None
    category: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

