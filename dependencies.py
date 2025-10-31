"""
FastAPI dependencies for authentication
"""

from fastapi import Header, HTTPException, Depends
from typing import Optional
from auth import verify_api_key, get_user_from_token, verify_token

# ========================================
# Authentication Dependencies
# ========================================

def get_current_user_token(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency to verify JWT token from Authorization header
    Returns user info if token is valid
    Full access to all endpoints
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    # Verify token
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

def get_current_api_key(x_api_key: Optional[str] = Header(None)) -> dict:
    """
    Dependency to verify API key from X-API-Key header
    Returns API key info if valid
    Limited access - only for main.py endpoints (indexing/search)
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="X-API-Key header missing",
        )
    
    # Verify API key
    key_data = verify_api_key(x_api_key)
    if not key_data:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    
    return key_data

def get_current_auth(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """
    Dependency that accepts either JWT token OR API key
    - JWT token: Full access (all endpoints)
    - API key: Limited access (only main.py endpoints)
    
    Returns auth info with 'type' field indicating auth method
    """
    # Try JWT token first (full access)
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                user = get_user_from_token(token)
                if user:
                    return {
                        **user,
                        'auth_type': 'token',
                        'full_access': True
                    }
        except (ValueError, AttributeError):
            pass
    
    # Try API key (limited access)
    if x_api_key:
        key_data = verify_api_key(x_api_key)
        if key_data:
            return {
                **key_data,
                'auth_type': 'api_key',
                'full_access': False
            }
    
    # No valid authentication
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide either Bearer token or X-API-Key header"
    )

def require_full_access(current_auth: dict = Depends(get_current_auth)) -> dict:
    """
    Dependency that requires full access (JWT token only)
    Use this for auth endpoints, params CRUD, etc.
    """
    if not current_auth.get('full_access'):
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires full access. Use JWT token authentication."
        )
    return current_auth

def allow_api_key(current_auth: dict = Depends(get_current_auth)) -> dict:
    """
    Dependency that allows both API keys and tokens
    Use this for main.py endpoints (indexing/search)
    """
    return current_auth

