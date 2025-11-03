"""
Business Logic Services
"""

from app.services.param_service import (
    create_param,
    get_param,
    update_param,
    delete_param,
    list_params,
    search_params,
    get_params_by_category,
    get_categories,
)

from app.services.user_service import (
    create_user,
    get_user,
    get_user_by_username,
)

from app.services.api_key_service import (
    create_api_key,
    verify_api_key,
    list_api_keys,
    revoke_api_key,
    delete_api_key,
)

from app.services.auth_service import (
    verify_user,
    get_user_from_token,
)

from app.services.indexer_service import (
    index_publication,
    index_scraper_publications,
    sync_since,
    index_bulk,
)

from app.services.search_service import (
    search_publications,
)

from app.services.process_service import (
    start_indexer,
    stop_indexer,
    register_process,
    update_status,
    update_progress,
    get_process,
    list_processes,
    check_process_stopped,
    get_logs,
)

__all__ = [
    # Param service
    "create_param",
    "get_param",
    "update_param",
    "delete_param",
    "list_params",
    "search_params",
    "get_params_by_category",
    "get_categories",
    # User service
    "create_user",
    "get_user",
    "get_user_by_username",
    # API Key service
    "create_api_key",
    "verify_api_key",
    "list_api_keys",
    "revoke_api_key",
    "delete_api_key",
    # Auth service
    "verify_user",
    "get_user_from_token",
    # Indexer service
    "index_publication",
    "index_scraper_publications",
    "sync_since",
    "index_bulk",
    # Search service
    "search_publications",
    # Process service
    "start_indexer",
    "stop_indexer",
    "register_process",
    "update_status",
    "update_progress",
    "get_process",
    "list_processes",
    "check_process_stopped",
    "get_logs",
]
