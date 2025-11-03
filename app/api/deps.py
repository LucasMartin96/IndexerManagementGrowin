"""
API Dependencies - Authentication and common dependencies
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from typing import Optional, Dict
from app.services.auth_service import get_user_from_token, verify_user
from app.services.api_key_service import verify_api_key

# Security schemes
security_bearer = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    api_key: Optional[str] = Depends(api_key_header)
) -> Dict:
    """
    Get current authentication (JWT or API key)
    Returns auth info dict with 'type' (jwt/api_key) and 'user' or 'key' info
    """
    # Try JWT first
    if credentials:
        try:
            token = credentials.credentials
            user = get_user_from_token(token)
            if user:
                return {
                    'type': 'jwt',
                    'user': user,
                    'id': user.get('id')
                }
        except Exception:
            pass
    
    # Try API key
    if api_key:
        key_data = verify_api_key(api_key)
        if key_data:
            return {
                'type': 'api_key',
                'key': key_data,
                'id': key_data.get('user_id')
            }
    
    # No valid auth found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_full_access(
    current_auth: Dict = Depends(get_current_auth)
) -> Dict:
    """
    Require full access (JWT token only, not API keys)
    """
    if current_auth.get('type') != 'jwt':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="JWT token required for this endpoint"
        )
    
    return current_auth


async def allow_api_key(
    current_auth: Dict = Depends(get_current_auth)
) -> Dict:
    """
    Allow either JWT token or API key (less restrictive)
    """
    return current_auth

