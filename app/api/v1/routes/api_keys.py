"""
API Key management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.models.api_key import CreateAPIKeyRequest, APIKeyResponse
from app.services.api_key_service import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
    delete_api_key
)
from app.api.deps import require_full_access

router = APIRouter()


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    request: CreateAPIKeyRequest,
    current_user: dict = Depends(require_full_access)
) -> APIKeyResponse:
    """
    Create a new API key
    Returns the plaintext key only once - save it!
    Access: JWT token only (full access required)
    """
    # If user_id not provided, use current user
    user_id = request.user_id or current_user.get('id')
    
    key_data = create_api_key(
        name=request.name,
        user_id=user_id,
        permissions=request.permissions,
        expires_days=request.expires_days
    )
    
    return APIKeyResponse(**key_data)


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys_endpoint(
    user_id: Optional[int] = None,
    current_user: dict = Depends(require_full_access)
) -> List[APIKeyResponse]:
    """
    List all API keys (without plaintext keys)
    Access: JWT token only (full access required)
    """
    # If user_id not provided, filter by current user
    if not user_id:
        user_id = current_user.get('id')
    
    keys = list_api_keys(user_id=user_id)
    return [APIKeyResponse(**key) for key in keys]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key_endpoint(
    key_id: int,
    current_user: dict = Depends(require_full_access)
) -> dict:
    """
    Revoke an API key
    Access: JWT token only (full access required)
    """
    success = revoke_api_key(key_id)
    if success:
        return {"status": "revoked", "key_id": key_id}
    raise HTTPException(status_code=404, detail="API key not found")

