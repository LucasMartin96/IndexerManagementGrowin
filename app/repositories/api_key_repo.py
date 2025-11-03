"""
API Key repository - Data access layer for API keys
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime
from app.db.sqlite import execute_query, get_connection

logger = logging.getLogger(__name__)


def create_api_key(key_hash: str, name: str, user_id: Optional[int] = None,
                   permissions: Optional[str] = None,
                   expires_at: Optional[str] = None) -> Dict:
    """
    Create a new API key
    
    Args:
        key_hash: Hashed API key
        name: Name/description for the key
        user_id: Optional user ID to associate with
        permissions: Optional permissions JSON string
        expires_at: Optional expiration timestamp
        
    Returns:
        dict: Created API key info
    """
    query = """
        INSERT INTO api_keys (key_hash, name, user_id, permissions, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (key_hash, name, user_id, permissions, expires_at))
        key_id = cursor.lastrowid
        conn.commit()
    
    logger.info(f"Created API key: {name} (ID: {key_id})")
    
    return {
        'key_id': key_id,
        'name': name,
        'user_id': user_id,
        'permissions': permissions,
        'expires_at': expires_at
    }


def get_api_key_by_hash(key_hash: str) -> Optional[Dict]:
    """
    Get API key by hash
    
    Args:
        key_hash: Hashed API key
        
    Returns:
        dict: API key info or None
    """
    query = """
        SELECT * FROM api_keys
        WHERE key_hash = ? AND is_active = 1
    """
    
    return execute_query(query, (key_hash,), fetch_one=True)


def update_api_key_last_used(key_id: int):
    """
    Update API key last used timestamp
    
    Args:
        key_id: API key ID
    """
    query = """
        UPDATE api_keys
        SET last_used_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """
    execute_query(query, (key_id,))


def list_api_keys(user_id: Optional[int] = None) -> List[Dict]:
    """
    List all API keys (without plaintext keys)
    
    Args:
        user_id: Optional filter by user ID
        
    Returns:
        list: List of API key info (without plaintext)
    """
    if user_id:
        query = """
            SELECT id, name, user_id, permissions, expires_at, 
                   last_used_at, created_at, is_active
            FROM api_keys
            WHERE user_id = ?
            ORDER BY created_at DESC
        """
        return execute_query(query, (user_id,), fetch_all=True)
    else:
        query = """
            SELECT id, name, user_id, permissions, expires_at, 
                   last_used_at, created_at, is_active
            FROM api_keys
            ORDER BY created_at DESC
        """
        return execute_query(query, fetch_all=True)


def revoke_api_key(key_id: int) -> bool:
    """
    Revoke an API key (soft delete)
    
    Args:
        key_id: ID of the key to revoke
        
    Returns:
        bool: True if revoked successfully
    """
    query = """
        UPDATE api_keys
        SET is_active = 0
        WHERE id = ?
    """
    
    result = execute_query(query, (key_id,))
    logger.info(f"Revoked API key ID: {key_id}")
    return result > 0


def delete_api_key(key_id: int) -> bool:
    """
    Permanently delete an API key
    
    Args:
        key_id: ID of the key to delete
        
    Returns:
        bool: True if deleted successfully
    """
    query = "DELETE FROM api_keys WHERE id = ?"
    result = execute_query(query, (key_id,))
    logger.info(f"Deleted API key ID: {key_id}")
    return result > 0

