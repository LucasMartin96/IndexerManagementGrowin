"""
SQLite database module for authentication and params storage
"""

import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

# Database file path
DB_PATH = settings.SQLITE_DB_PATH

def init_db():
    """
    Initialize SQLite database with required tables
    """
    try:
        # Ensure directory exists
        db_dir = Path(DB_PATH).parent
        if db_dir and str(db_dir) != '.' and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table for authentication
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            # Params table for key-value storage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS params (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    description TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # API Keys table for authentication
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    user_id INTEGER,
                    permissions TEXT,
                    expires_at TIMESTAMP,
                    last_used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Indexer processes table for tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS indexer_processes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'running',
                    params TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    progress TEXT,
                    error_message TEXT,
                    user_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_params_key ON params(key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_params_category ON params(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_indexer_processes_type ON indexer_processes(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_indexer_processes_status ON indexer_processes(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_indexer_processes_started_at ON indexer_processes(started_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_indexer_processes_user_id ON indexer_processes(user_id)")
            
            conn.commit()
            logger.info(f"SQLite database initialized at {DB_PATH}")
            
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database: {str(e)}")
        raise

@contextmanager
def get_connection():
    """
    Get SQLite connection context manager
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"SQLite connection error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    Execute SQLite query
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch_one: Return single row
        fetch_all: Return all rows
        
    Returns:
        Result based on fetch_one/fetch_all flags
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        
        if query.strip().upper().startswith('SELECT'):
            if fetch_one:
                row = cursor.fetchone()
                return dict(row) if row else None
            elif fetch_all:
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                return cursor.fetchone()
        else:
            conn.commit()
            return cursor.rowcount


def vacuum_database():
    """
    Optimize SQLite database by running VACUUM
    This reclaims space after deleting old records
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            conn.commit()
        logger.info("Database VACUUM completed successfully")
    except Exception as e:
        logger.error(f"Failed to run VACUUM: {str(e)}")
        raise

