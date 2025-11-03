"""
Database connections module
"""

from app.db.mysql import (
    mysql_connection,
    mysql_query,
    init_connection_pool,
    connection_pool
)
from app.db.sqlite import (
    get_connection,
    execute_query,
    init_db
)
from app.db.elasticsearch import (
    es_client_init,
    es_create_index,
    get_es_client,
    initialize_elasticsearch,
    es_client
)

__all__ = [
    "mysql_connection",
    "mysql_query",
    "init_connection_pool",
    "connection_pool",
    "get_connection",
    "execute_query",
    "init_db",
    "es_client_init",
    "es_create_index",
    "get_es_client",
    "initialize_elasticsearch",
    "es_client",
]
