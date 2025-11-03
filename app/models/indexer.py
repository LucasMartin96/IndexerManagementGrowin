"""
Indexer request and response models
"""

from pydantic import BaseModel, Field
from typing import Optional


class IndexLicitacionRequest(BaseModel):
    """Request to index a single publication"""
    publicacion_id: int = Field(..., description="ID of the publication to index")


class IndexScraperRequest(BaseModel):
    """Request to index publications from a scraper"""
    scraper_id: int = Field(..., description="ID of the scraper")
    since: str = Field(..., description="Datetime in format YYYY-MM-DD HH:MM:SS")


class SyncSinceRequest(BaseModel):
    """Request to sync publications since a given date"""
    since: str = Field(..., description="Datetime in format YYYY-MM-DD HH:MM:SS")


class IndexResponse(BaseModel):
    """Response for indexing operations"""
    status: str
    id: Optional[int] = None
    scraper_id: Optional[int] = None
    since: Optional[str] = None
    indexed: Optional[int] = None
    total: Optional[int] = None
    failed: Optional[int] = None
    total_indexed: Optional[int] = None
    total_failed: Optional[int] = None
    timestamp: Optional[str] = None

