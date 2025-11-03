"""
Create user script - Command line utility to create users
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db import init_db as init_sqlite_db
from app.services.user_service import create_user

# Configure logging
setup_logging()
import logging

logger = logging.getLogger(__name__)


def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Usage: python create_user.py <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    # Validate password length (bcrypt limit is 72 bytes)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        print("ERROR: Password cannot be longer than 72 bytes")
        print(f"Your password is {len(password_bytes)} bytes long")
        print("Please use a shorter password or truncate it manually")
        sys.exit(1)
    
    # Warn if password is very long
    if len(password) > 50:
        print(f"WARNING: Password is {len(password)} characters long (bcrypt limit is 72 bytes)")
        print("Consider using a shorter password")
    
    try:
        # Initialize database
        init_sqlite_db()
        print("✓ Database initialized")
        
        # Create user
        user = create_user(
            username=username,
            password=password,
            email=None,
            role='user'
        )
        
        print(f"✓ User '{username}' created successfully")
        print(f"  User ID: {user['id']}")
        print(f"  Role: {user['role']}")
        
    except Exception as e:
        print(f"✗ Error creating user: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

