"""
User service - Business logic for users
"""

import logging
from typing import Optional, Dict
from app.core.security import hash_password
from app.repositories import user_repo

logger = logging.getLogger(__name__)


def create_user(username: str, password: str, email: Optional[str] = None,
                role: str = 'user') -> Dict:
    """
    Create a new user
    
    Args:
        username: Username
        password: Plaintext password
        email: Optional email
        role: User role
        
    Returns:
        dict: User info (without password)
    """
    # Hash password
    password_hash = hash_password(password)
    
    # Create user via repository
    return user_repo.create_user(username, password_hash, email, role)


def get_user(user_id: int) -> Optional[Dict]:
    """Get user by ID"""
    return user_repo.get_user(user_id)


def get_user_by_username(username: str) -> Optional[Dict]:
    """Get user by username (without password)"""
    return user_repo.get_user_by_username(username)

