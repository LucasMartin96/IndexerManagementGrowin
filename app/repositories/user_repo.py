"""
User repository - Data access layer for users
"""

import logging
from typing import Optional, Dict
from app.db.sqlite import execute_query, get_connection

logger = logging.getLogger(__name__)


def create_user(username: str, password_hash: str, email: Optional[str] = None,
                role: str = 'user') -> Dict:
    """
    Create a new user
    
    Args:
        username: Username
        password_hash: Hashed password
        email: Optional email
        role: User role (default: 'user')
        
    Returns:
        dict: User info (without password)
    """
    query = """
        INSERT INTO users (username, password_hash, email, role)
        VALUES (?, ?, ?, ?)
    """
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (username, password_hash, email, role))
        user_id = cursor.lastrowid
        conn.commit()
    
    logger.info(f"Created user: {username}")
    
    return {
        'id': user_id,
        'username': username,
        'email': email,
        'role': role
    }


def get_user(user_id: int) -> Optional[Dict]:
    """
    Get user by ID
    
    Args:
        user_id: User ID
        
    Returns:
        dict: User info or None
    """
    query = """
        SELECT id, username, email, role, created_at, is_active
        FROM users
        WHERE id = ?
    """
    
    return execute_query(query, (user_id,), fetch_one=True)


def get_user_by_username(username: str) -> Optional[Dict]:
    """
    Get user by username
    
    Args:
        username: Username
        
    Returns:
        dict: User info with password_hash or None
    """
    query = """
        SELECT id, username, password_hash, email, role, is_active
        FROM users
        WHERE username = ?
    """
    
    return execute_query(query, (username,), fetch_one=True)


def get_user_with_password(username: str) -> Optional[Dict]:
    """
    Get user by username with password hash for authentication
    
    Args:
        username: Username
        
    Returns:
        dict: User info with password_hash or None
    """
    query = """
        SELECT id, username, password_hash, email, role, is_active
        FROM users
        WHERE username = ? AND is_active = 1
    """
    
    return execute_query(query, (username,), fetch_one=True)

