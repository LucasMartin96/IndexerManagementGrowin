"""
Pydantic Models (Schemas)
"""

# Indexer models
from app.models.indexer import (
    IndexLicitacionRequest,
    IndexScraperRequest,
    SyncSinceRequest,
    IndexResponse,
)

# Search models
from app.models.search import (
    SearchLicitacionesRequest,
    TagModel,
    PublicationModel,
    SearchResponse,
)

# Auth models
from app.models.auth import (
    LoginRequest,
    TokenResponse,
)

# User models
from app.models.user import (
    CreateUserRequest,
    UserResponse,
)

# API Key models
from app.models.api_key import (
    CreateAPIKeyRequest,
    APIKeyResponse,
)

# Parameter models
from app.models.param import (
    CreateParamRequest,
    UpdateParamRequest,
    ParamResponse,
)

# Process models
from app.models.process import (
    StartIndexerRequest,
    IndexerProgress,
    IndexerProcessResponse,
    IndexerLogEntry,
    IndexerLogResponse,
)

# Common models
from app.models.common import (
    HealthResponse,
    ErrorResponse,
)

__all__ = [
    # Indexer
    "IndexLicitacionRequest",
    "IndexScraperRequest",
    "SyncSinceRequest",
    "IndexResponse",
    # Search
    "SearchLicitacionesRequest",
    "TagModel",
    "PublicationModel",
    "SearchResponse",
    # Auth
    "LoginRequest",
    "TokenResponse",
    # User
    "CreateUserRequest",
    "UserResponse",
    # API Key
    "CreateAPIKeyRequest",
    "APIKeyResponse",
    # Parameter
    "CreateParamRequest",
    "UpdateParamRequest",
    "ParamResponse",
    # Process
    "StartIndexerRequest",
    "IndexerProgress",
    "IndexerProcessResponse",
    "IndexerLogEntry",
    "IndexerLogResponse",
    # Common
    "HealthResponse",
    "ErrorResponse",
]
