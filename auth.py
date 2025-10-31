"""
Authentication module for API keys and users
Supports two authentication methods:
- JWT Tokens for users (full access)
- API Keys for services (limited access)
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from database_sqlite import execute_query, get_connection
import os

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ========================================
# API Key Management
# ========================================

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
    
    # Insert into database
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
        'key': plain_key,  # Only returned once!
        'name': name,
        'expires_at': expires_at
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
    
    query = """
        SELECT * FROM api_keys
        WHERE key_hash = ? AND is_active = 1
    """
    
    key_data = execute_query(query, (key_hash,), fetch_one=True)
    
    if not key_data:
        return None
    
    # Check expiration
    if key_data.get('expires_at'):
        expires_at = datetime.fromisoformat(key_data['expires_at'])
        if datetime.now() > expires_at:
            logger.warning(f"API key expired: {key_data.get('name')}")
            return None
    
    # Update last used
    query = """
        UPDATE api_keys
        SET last_used_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """
    execute_query(query, (key_data['id'],))
    
    return key_data

def list_api_keys(user_id: Optional[int] = None) -> list:
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
    Revoke an API key
    
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

# ========================================
# User Management (Basic)
# ========================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plaintext password (will be truncated to 72 bytes if longer)
        
    Returns:
        str: Hashed password
    """
    # Bcrypt has a 72-byte limit
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        logger.warning(f"Password too long ({len(password_bytes)} bytes), truncating to 72 bytes")
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    
    Args:
        plain_password: Plaintext password (will be truncated to 72 bytes if longer)
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches
    """
    # Truncate password to 72 bytes to match hashing behavior
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        plain_password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    return pwd_context.verify(plain_password, hashed_password)

def create_user(username: str, password: str, email: Optional[str] = None,
                role: str = 'user') -> Dict:
    """
    Create a new user
    
    Args:
        username: Username
        password: Plaintext password
        email: Optional email
        role: User role (default: 'user')
        
    Returns:
        dict: User info (without password)
    """
    password_hash = hash_password(password)
    
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

def verify_user(username: str, password: str) -> Optional[Dict]:
    """
    Verify user credentials
    
    Args:
        username: Username
        password: Plaintext password
        
    Returns:
        dict: User info if valid, None otherwise
    """
    query = """
        SELECT id, username, password_hash, email, role, is_active
        FROM users
        WHERE username = ? AND is_active = 1
    """
    
    user = execute_query(query, (username,), fetch_one=True)
    
    if not user:
        return None
    
    # Verify password using bcrypt
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

# ========================================
# JWT Token Management
# ========================================

def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time
        
    Returns:
        str: JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict]:
    """
    Verify JWT token and return payload
    
    Args:
        token: JWT token
        
    Returns:
        dict: Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_user_from_token(token: str) -> Optional[Dict]:
    """
    Get user from JWT token
    
    Args:
        token: JWT token
        
    Returns:
        dict: User info if valid, None otherwise
    """
    payload = verify_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    return get_user(int(user_id))

