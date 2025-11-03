"""
API Key service - Business logic for API keys
"""

import hashlib
import secrets
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from app.repositories import api_key_repo

logger = logging.getLogger(__name__)


def generate_api_key() -> str:
    """
    Generate a new API key
    
    Returns:
        str: New API key (plaintext)
    """
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """
    Hash an API key for storage
    
    Args:
        key: Plaintext API key
        
    Returns:
        str: Hashed API key
    """
    return hashlib.sha256(key.encode()).hexdigest()


def create_api_key(name: str, user_id: Optional[int] = None,
                   permissions: Optional[str] = None,
                   expires_days: Optional[int] = None) -> Dict:
    """
    Create a new API key
    
    Args:
        name: Name/description for the key
        user_id: Optional user ID to associate with
        permissions: Optional permissions JSON string
        expires_days: Optional expiration in days
        
    Returns:
        dict: Contains 'key' (plaintext) and 'key_id'
    """
    # Generate key
    plain_key = generate_api_key()
    key_hash = hash_api_key(plain_key)
    
    # Calculate expiration
    expires_at = None
    if expires_days:
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
    
    # Create via repository
    key_data = api_key_repo.create_api_key(key_hash, name, user_id, permissions, expires_at)
    
    # Return with plaintext key (only returned once!)
    return {
        'key_id': key_data['key_id'],
        'key': plain_key,
        'name': key_data['name'],
        'user_id': key_data['user_id'],
        'permissions': key_data['permissions'],
        'expires_at': key_data['expires_at'],
        'created_at': key_data.get('created_at'),
        'is_active': True
    }


def verify_api_key(api_key: str) -> Optional[Dict]:
    """
    Verify an API key and return key info if valid
    
    Args:
        api_key: Plaintext API key to verify
        
    Returns:
        dict: Key information if valid, None otherwise
    """
    key_hash = hash_api_key(api_key)
    
    key_data = api_key_repo.get_api_key_by_hash(key_hash)
    
    if not key_data:
        return None
    
    # Check expiration
    if key_data.get('expires_at'):
        expires_at = datetime.fromisoformat(key_data['expires_at'])
        if datetime.now() > expires_at:
            logger.warning(f"API key expired: {key_data.get('name')}")
            return None
    
    # Update last used
    api_key_repo.update_api_key_last_used(key_data['id'])
    
    return key_data


def list_api_keys(user_id: Optional[int] = None) -> List[Dict]:
    """List all API keys (without plaintext keys)"""
    return api_key_repo.list_api_keys(user_id)


def revoke_api_key(key_id: int) -> bool:
    """Revoke an API key"""
    return api_key_repo.revoke_api_key(key_id)


def delete_api_key(key_id: int) -> bool:
    """Permanently delete an API key"""
    return api_key_repo.delete_api_key(key_id)

