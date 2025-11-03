"""
API Version 1 Router - Main router that includes all sub-routers
"""

from fastapi import APIRouter, Depends
from app.api.v1.routes import (
    health,
    search,
    indexer,
    auth,
    api_keys,
    params,
    processes
)
from app.api.deps import require_full_access

# Main API router
api_router = APIRouter()

# Include all sub-routers with proper prefixes
# Note: Routes maintain backward compatibility with /api/* paths
api_router.include_router(health.router, tags=["Health"])  # /api/health
api_router.include_router(search.router, tags=["Search"])  # /api/search-licitaciones
api_router.include_router(indexer.router, tags=["Indexer"])  # /api/index-licitacion, /api/index-scraper-publications
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])  # /api/auth/login, /api/auth/users
api_router.include_router(api_keys.router, prefix="/auth", tags=["API Keys"])  # /api/auth/api-keys
api_router.include_router(params.router, prefix="/params", tags=["Params"])  # /api/params/*
api_router.include_router(processes.router, prefix="/indexers", tags=["Processes"])  # /api/indexers/*

# Apply dependency to create_user endpoint
# Note: We'll apply this in the app factory instead

