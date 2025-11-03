"""
Authentication service - Business logic for authentication
"""

import logging
from typing import Optional, Dict
from app.core.security import verify_password, create_access_token, decode_access_token
from app.repositories import user_repo

logger = logging.getLogger(__name__)


def verify_user(username: str, password: str) -> Optional[Dict]:
    """
    Verify user credentials
    
    Args:
        username: Username
        password: Plaintext password
        
    Returns:
        dict: User info if valid, None otherwise
    """
    # Get user with password hash
    user = user_repo.get_user_with_password(username)
    
    if not user:
        return None
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        return None
    
    logger.info(f"User authenticated: {username}")
    
    # Return user without password hash
    return {
        'id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'role': user['role'],
        'is_active': user['is_active']
    }


def get_user_from_token(token: str) -> Optional[Dict]:
    """
    Get user from JWT token
    
    Args:
        token: JWT token
        
    Returns:
        dict: User info if valid, None otherwise
    """
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    return user_repo.get_user(int(user_id))

