"""
Database connection modules for MySQL and Elasticsearch
"""

import os
import pymysql
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import logging
from queue import Queue
import threading

load_dotenv()

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
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', '3306')),
                user=os.getenv('DB_USERNAME', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_DATABASE', 'growin_db'),
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
_connection_pool = None

def init_connection_pool(max_connections=5):
    """Initialize the MySQL connection pool"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = MySQLConnectionPool(max_connections)
        logger.info(f"MySQL connection pool initialized (max: {max_connections})")
    return _connection_pool

def get_connection_pool():
    """Get the global connection pool"""
    if _connection_pool is None:
        init_connection_pool()
    return _connection_pool

def mysql_connection():
    """
    Get MySQL connection from pool (for backward compatibility)
    """
    pool = get_connection_pool()
    return pool.get_connection()

def mysql_query(query, params=None, conn=None):
    """
    Execute MySQL query and return results
    Uses connection pool if no connection provided
    """
    should_return_conn = False
    if conn is None:
        pool = get_connection_pool()
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
            pool = get_connection_pool()
            pool.return_connection(conn)

# ========================================
# Elasticsearch Connection
# ========================================

def es_client_init():
    """
    Initialize Elasticsearch client
    Returns Elasticsearch client object
    """
    try:
        es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        es_port = int(os.getenv('ELASTICSEARCH_PORT', '9200'))
        
        es = Elasticsearch(
            [f"http://{es_host}:{es_port}"],
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        
        # Test connection
        if es.ping():
            logger.info(f"Elasticsearch connection established: {es_host}:{es_port}")
            return es
        else:
            raise Exception("Failed to ping Elasticsearch")
            
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {str(e)}")
        raise

def es_create_index(es_client, index_name, mapping=None):
    """
    Create Elasticsearch index with mapping if it doesn't exist
    """
    try:
        if not es_client.indices.exists(index=index_name):
            if mapping:
                es_client.indices.create(index=index_name, body=mapping)
            else:
                es_client.indices.create(index=index_name)
            logger.info(f"Created Elasticsearch index: {index_name}")
        else:
            logger.info(f"Elasticsearch index already exists: {index_name}")
    except Exception as e:
        logger.error(f"Failed to create Elasticsearch index: {str(e)}")
        raise

