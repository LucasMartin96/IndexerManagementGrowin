"""
Indexer process management models
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class StartIndexerRequest(BaseModel):
    """Request to start an indexer process"""
    type: str = Field(..., description="Type: index-licitacion, index-scraper-publications, index-bulk, sync-since")
    params: Dict[str, Any] = Field(..., description="Parameters for the indexer (varies by type)")


class IndexerProgress(BaseModel):
    """Progress information for an indexer process"""
    current: Optional[int] = None
    total: Optional[int] = None
    indexed: Optional[int] = None
    failed: Optional[int] = None
    message: Optional[str] = None


class IndexerProcessResponse(BaseModel):
    """Indexer process response"""
    id: int
    type: str
    status: str  # running, completed, failed, stopped
    params: Optional[Dict[str, Any]] = None
    started_at: str
    completed_at: Optional[str] = None
    progress: Optional[IndexerProgress] = None
    error_message: Optional[str] = None
    user_id: Optional[int] = None


class IndexerLogEntry(BaseModel):
    """Single log entry"""
    timestamp: str
    level: str
    message: str


class IndexerLogResponse(BaseModel):
    """Indexer logs response"""
    logs: List[IndexerLogEntry]
    last_timestamp: Optional[str] = None
    has_more: bool = False

