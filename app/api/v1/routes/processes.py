"""
Indexer process management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.models.process import (
    StartIndexerRequest,
    IndexerProcessResponse,
    IndexerProgress,
    IndexerLogResponse,
    IndexerLogEntry
)
from app.services.process_service import (
    start_indexer as start_indexer_service,
    stop_indexer as stop_indexer_service,
    register_process,
    update_status,
    update_progress,
    get_process as get_process_service,
    list_processes as list_processes_service,
    check_process_stopped,
    get_logs as get_logs_service
)
from app.api.deps import require_full_access
from app.api.v1.routes.indexer import (
    _index_publication_sync,
    _index_scraper_publications_sync,
    _sync_since_sync,
    _index_bulk_sync,
    set_executor as set_indexer_executor
)
from app.db import get_es_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global executor (set from main app)
_executor: Optional[ThreadPoolExecutor] = None


def set_process_executor(exec: ThreadPoolExecutor):
    """Set the global executor for processes"""
    global _executor
    _executor = exec
    set_indexer_executor(exec)  # Also set in indexer routes (imported with alias)


@router.post("/start", response_model=IndexerProcessResponse)
async def start_indexer_endpoint(
    request: StartIndexerRequest,
    current_user: dict = Depends(require_full_access)
) -> IndexerProcessResponse:
    """
    Start an indexer process
    Access: JWT token only (full access required)
    """
    if not _executor:
        raise HTTPException(status_code=503, detail="Executor not initialized")
    
    es_client = get_es_client()
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    # Validate indexer type
    valid_types = ['index-licitacion', 'index-scraper-publications', 'index-bulk', 'sync-since']
    if request.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid indexer type. Must be one of: {valid_types}")
    
    # Validate params based on type
    if request.type == 'index-licitacion':
        if 'publicacion_id' not in request.params:
            raise HTTPException(status_code=400, detail="Missing required param: publicacion_id")
    elif request.type == 'index-scraper-publications':
        if 'scraper_id' not in request.params or 'since' not in request.params:
            raise HTTPException(status_code=400, detail="Missing required params: scraper_id, since")
    elif request.type == 'sync-since':
        if 'since' not in request.params:
            raise HTTPException(status_code=400, detail="Missing required param: since")
    elif request.type == 'index-bulk':
        # No params needed for bulk
        pass
    
    # Start process in DB
    user_id = current_user.get('id')
    process_id = start_indexer_service(request.type, request.params, user_id)
    
    # Create wrapper function that calls the appropriate sync function
    def run_indexer():
        try:
            if request.type == 'index-licitacion':
                _index_publication_sync(request.params['publicacion_id'], process_id)
            elif request.type == 'index-scraper-publications':
                _index_scraper_publications_sync(request.params['scraper_id'], request.params['since'], process_id)
            elif request.type == 'sync-since':
                _sync_since_sync(request.params['since'], process_id)
            elif request.type == 'index-bulk':
                _index_bulk_sync(process_id)
        except Exception as e:
            logger.error(f"Indexer process {process_id} failed: {str(e)}")
            update_status(process_id, 'failed', str(e))
    
    # Submit to executor
    future = _executor.submit(run_indexer)
    register_process(process_id, future)
    
    # Get process info
    process = get_process_service(process_id)
    if not process:
        raise HTTPException(status_code=500, detail="Failed to create process")
    
    # Parse JSON fields
    process_dict = dict(process)
    if process_dict.get('params'):
        process_dict['params'] = json.loads(process_dict['params'])
    if process_dict.get('progress'):
        progress_data = json.loads(process_dict['progress'])
        process_dict['progress'] = IndexerProgress(**progress_data) if progress_data else None
    
    return IndexerProcessResponse(**process_dict)


@router.get("", response_model=List[IndexerProcessResponse])
async def list_indexers(
    status: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(require_full_access)
) -> List[IndexerProcessResponse]:
    """
    List indexer processes
    Access: JWT token only (full access required)
    """
    processes = list_processes_service(status=status, type=type, limit=limit, offset=offset)
    
    # Parse JSON fields
    results = []
    for process in processes:
        process_dict = dict(process)
        if process_dict.get('params'):
            process_dict['params'] = json.loads(process_dict['params'])
        if process_dict.get('progress'):
            progress_data = json.loads(process_dict['progress'])
            process_dict['progress'] = IndexerProgress(**progress_data) if progress_data else None
        
        results.append(IndexerProcessResponse(**process_dict))
    
    return results


@router.get("/{process_id}", response_model=IndexerProcessResponse)
async def get_indexer(
    process_id: int,
    current_user: dict = Depends(require_full_access)
) -> IndexerProcessResponse:
    """
    Get indexer process details
    Access: JWT token only (full access required)
    """
    process = get_process_service(process_id)
    if not process:
        raise HTTPException(status_code=404, detail=f"Process {process_id} not found")
    
    # Parse JSON fields
    process_dict = dict(process)
    if process_dict.get('params'):
        process_dict['params'] = json.loads(process_dict['params'])
    if process_dict.get('progress'):
        progress_data = json.loads(process_dict['progress'])
        process_dict['progress'] = IndexerProgress(**progress_data) if progress_data else None
    
    return IndexerProcessResponse(**process_dict)


@router.post("/{process_id}/stop")
async def stop_indexer_endpoint(
    process_id: int,
    current_user: dict = Depends(require_full_access)
) -> dict:
    """
    Stop an indexer process
    Access: JWT token only (full access required)
    """
    success = stop_indexer_service(process_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Process {process_id} not found or cannot be stopped")
    
    return {"status": "stopped", "process_id": process_id}


@router.get("/{process_id}/logs", response_model=IndexerLogResponse)
async def get_indexer_logs(
    process_id: int,
    since: Optional[str] = None,
    current_user: dict = Depends(require_full_access)
) -> IndexerLogResponse:
    """
    Get logs for an indexer process (polling endpoint)
    Access: JWT token only (full access required)
    """
    # Verify process exists
    process = get_process_service(process_id)
    if not process:
        raise HTTPException(status_code=404, detail=f"Process {process_id} not found")
    
    # Get logs
    logs = get_logs_service(process_id, since_timestamp=since)
    
    # Convert to response model
    log_entries = [IndexerLogEntry(**log) for log in logs]
    
    # Get last timestamp
    last_timestamp = None
    if logs:
        last_timestamp = logs[-1]['timestamp']
    
    return IndexerLogResponse(
        logs=log_entries,
        last_timestamp=last_timestamp,
        has_more=False  # For now, always return all available logs
    )

