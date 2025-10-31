#!/usr/bin/env python3
"""
Script to create users in the SQLite database
Usage: python create_user.py <username> <password> [email] [role]
"""

import sys
import os
import argparse
from pathlib import Path

# Add current directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from database_sqlite import init_db
from auth import create_user
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description='Create a new user in the ELK service database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_user.py admin mypassword
  python create_user.py user1 password123 user1@example.com
  python create_user.py admin secret123 admin@example.com admin
        """
    )
    
    parser.add_argument('username', help='Username for the new user')
    parser.add_argument('password', help='Password for the new user (max 72 characters)')
    parser.add_argument('email', nargs='?', default=None, help='Email address (optional)')
    parser.add_argument('--role', default='user', help='User role (default: user)')
    parser.add_argument('--force', action='store_true', help='Force creation even if user exists')
    
    args = parser.parse_args()
    
    # Validate password length (bcrypt limit is 72 bytes)
    if len(args.password.encode('utf-8')) > 72:
        print(f"✗ Error: Password is too long (max 72 bytes)")
        print(f"  Your password is {len(args.password.encode('utf-8'))} bytes long")
        print(f"  Password: '{args.password}'")
        sys.exit(1)
    
    # Warn if password is long in characters (some UTF-8 chars use multiple bytes)
    if len(args.password) > 50:
        print(f"⚠ Warning: Password is {len(args.password)} characters long")
        print(f"  Bcrypt limit is 72 bytes - some characters may use multiple bytes")
    
    # Initialize database
    try:
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)
    
    # Create user
    try:
        user = create_user(
            username=args.username,
            password=args.password,
            email=args.email,
            role=args.role
        )
        
        print(f"\n✓ User created successfully!")
        print(f"  ID: {user['id']}")
        print(f"  Username: {user['username']}")
        print(f"  Email: {user['email'] or '(not set)'}")
        print(f"  Role: {user['role']}")
        print(f"\nYou can now login with:")
        print(f"  POST /api/auth/login")
        print(f"  {{'username': '{user['username']}', 'password': '{args.password}'}}")
        
    except Exception as e:
        error_msg = str(e)
        if 'UNIQUE constraint failed' in error_msg or 'unique' in error_msg.lower():
            print(f"✗ Error: Username '{args.username}' already exists")
            if args.force:
                print("  Use --force flag to update existing user (not implemented)")
            sys.exit(1)
        else:
            print(f"✗ Error creating user: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()

