"""
Data Access Layer (Repositories)
"""

from app.repositories.param_repo import (
    create_param,
    get_param,
    update_param,
    delete_param,
    list_params,
    search_params,
    get_params_by_category,
    get_categories,
)

from app.repositories.user_repo import (
    create_user,
    get_user,
    get_user_by_username,
    get_user_with_password,
)

from app.repositories.api_key_repo import (
    create_api_key,
    get_api_key_by_hash,
    update_api_key_last_used,
    list_api_keys,
    revoke_api_key,
    delete_api_key,
)

from app.repositories.process_repo import (
    create_process,
    get_process,
    update_process_status,
    update_process_progress,
    list_processes,
    get_process_status,
    mark_process_stopped,
)

__all__ = [
    # Param repo
    "create_param",
    "get_param",
    "update_param",
    "delete_param",
    "list_params",
    "search_params",
    "get_params_by_category",
    "get_categories",
    # User repo
    "create_user",
    "get_user",
    "get_user_by_username",
    "get_user_with_password",
    # API Key repo
    "create_api_key",
    "get_api_key_by_hash",
    "update_api_key_last_used",
    "list_api_keys",
    "revoke_api_key",
    "delete_api_key",
    # Process repo
    "create_process",
    "get_process",
    "update_process_status",
    "update_process_progress",
    "list_processes",
    "get_process_status",
    "mark_process_stopped",
]
