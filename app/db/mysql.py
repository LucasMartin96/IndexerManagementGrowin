"""
MySQL database connection pool
"""

import logging
import pymysql
import pymysql.cursors
from queue import Queue
import threading
from app.core.config import settings

logger = logging.getLogger(__name__)

# ========================================
# MySQL Connection Pool
# ========================================

class MySQLConnectionPool:
    """Simple connection pool for MySQL connections"""
    def __init__(self, max_connections=5):
        self.max_connections = max_connections
        self.pool = Queue(maxsize=max_connections)
        self._created = 0
        self._lock = threading.Lock()
    
    def _create_connection(self):
        """Create a new MySQL connection"""
        try:
            conn = pymysql.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USERNAME,
                password=settings.DB_PASSWORD,
                database=settings.DB_DATABASE,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
                connect_timeout=5
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to create MySQL connection: {str(e)}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            # Try to get from pool with timeout
            conn = self.pool.get(timeout=1)
            # Check if connection is alive
            try:
                conn.ping(reconnect=True)
            except:
                # Connection is dead, create new one
                conn = self._create_connection()
            return conn
        except:
            # Pool is empty, create new connection if under limit
            with self._lock:
                if self._created < self.max_connections:
                    self._created += 1
                    return self._create_connection()
            # Pool is full, wait for connection or create new one
            return self.pool.get(timeout=5)
    
    def return_connection(self, conn):
        """Return connection to pool"""
        try:
            self.pool.put_nowait(conn)
        except:
            # Pool is full, close connection
            try:
                conn.close()
                with self._lock:
                    self._created -= 1
            except:
                pass

# Global connection pool
connection_pool = None

def init_connection_pool(max_connections: int = 5):
    """Initialize MySQL connection pool"""
    global connection_pool
    connection_pool = MySQLConnectionPool(max_connections=max_connections)

def mysql_connection():
    """
    Get MySQL connection from pool (context manager)
    
    Usage:
        with mysql_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ...")
            results = cursor.fetchall()
    """
    if connection_pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_connection_pool() first.")
    
    conn = connection_pool.get_connection()
    
    class ConnectionContext:
        def __init__(self, connection):
            self.connection = connection
        
        def __enter__(self):
            return self.connection
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                connection_pool.return_connection(self.connection)
            else:
                # On error, close connection instead of returning to pool
                try:
                    self.connection.rollback()
                    self.connection.close()
                except:
                    pass
                with connection_pool._lock:
                    if hasattr(connection_pool, '_created'):
                        connection_pool._created -= 1
    
    return ConnectionContext(conn)


def mysql_query(query, params=None, conn=None):
    """
    Execute MySQL query and return results
    Uses connection pool if no connection provided
    """
    should_return_conn = False
    if conn is None:
        pool = connection_pool
        if pool is None:
            raise RuntimeError("Connection pool not initialized. Call init_connection_pool() first.")
        conn = pool.get_connection()
        should_return_conn = True
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                return results
            else:
                conn.commit()
                return cursor.rowcount
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"MySQL query failed: {str(e)}")
        raise
    finally:
        if should_return_conn and conn:
            pool = connection_pool
            pool.return_connection(conn)

