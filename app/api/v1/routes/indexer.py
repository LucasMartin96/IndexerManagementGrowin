"""
Indexer endpoints - Index publications
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from app.models.indexer import IndexLicitacionRequest, IndexScraperRequest, SyncSinceRequest, IndexResponse
from app.api.deps import allow_api_key, require_full_access
from app.utils.denormalize import (
    denormalize_publication,
    get_publications_from_scraper,
    get_publications_since,
    get_all_publication_ids
)
from app.utils.logging_handler import ProcessLogHandler
from app.utils.process_manager import (
    update_process_progress,
    update_process_status,
    is_process_stopped
)
from app.db import get_es_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Global executor (will be initialized in main app)
executor: Optional[ThreadPoolExecutor] = None


def set_executor(exec: ThreadPoolExecutor):
    """Set the global executor"""
    global executor
    executor = exec


def _index_publication_sync(publicacion_id: int, process_id: Optional[int] = None):
    """Synchronous function to index a publication (runs in background thread)"""
    process_logger = logger
    if process_id:
        # Set up process-specific logger
        handler = ProcessLogHandler(process_id)
        handler.setFormatter(logging.Formatter('%(message)s'))
        process_logger = logging.getLogger(f'process_{process_id}')
        process_logger.setLevel(logging.INFO)
        process_logger.propagate = False  # Don't propagate to root logger
        process_logger.handlers = []  # Clear existing handlers
        process_logger.addHandler(handler)
        process_logger.info(f"Process {process_id} started: index-licitacion, publicacion_id={publicacion_id}")
    
    try:
        if process_id:
            update_process_progress(process_id, {'message': 'Starting index...', 'current': 0, 'total': 1})
            process_logger.info("Starting index...")
        
        es_client = get_es_client()
        if not es_client:
            error_msg = f"Elasticsearch not available for publication {publicacion_id}"
            process_logger.warning(error_msg)
            if process_id:
                update_process_status(process_id, 'failed', error_msg)
            return
        
        # Check if stopped
        if process_id and is_process_stopped(process_id):
            process_logger.info("Process was stopped")
            return
        
        if process_id:
            update_process_progress(process_id, {'message': 'Denormalizing publication...', 'current': 1, 'total': 2})
            process_logger.info("Denormalizing publication...")
        
        doc = denormalize_publication(publicacion_id)
        if not doc:
            error_msg = f"Publication {publicacion_id} not found"
            process_logger.warning(error_msg)
            if process_id:
                update_process_status(process_id, 'failed', error_msg)
            return
        
        # Check if stopped
        if process_id and is_process_stopped(process_id):
            process_logger.info("Process was stopped")
            return
        
        if process_id:
            update_process_progress(process_id, {'message': 'Indexing to Elasticsearch...', 'current': 2, 'total': 2})
            process_logger.info("Indexing to Elasticsearch...")
        
        es_client.index(index=settings.ELASTICSEARCH_INDEX, id=publicacion_id, document=doc)
        process_logger.info(f"Successfully indexed publication {publicacion_id}")
        
        if process_id:
            update_process_status(process_id, 'completed')
            update_process_progress(process_id, {'message': 'Completed', 'indexed': 1, 'failed': 0, 'current': 2, 'total': 2})
    except Exception as e:
        error_msg = f"Failed to index publication {publicacion_id}: {str(e)}"
        process_logger.error(error_msg)
        if process_id:
            update_process_status(process_id, 'failed', error_msg)


def _index_scraper_publications_sync(scraper_id: int, since: str, process_id: Optional[int] = None):
    """Synchronous function to index scraper publications (runs in background thread)"""
    process_logger = logger
    if process_id:
        handler = ProcessLogHandler(process_id)
        handler.setFormatter(logging.Formatter('%(message)s'))
        handler.setLevel(logging.DEBUG)  # Set handler level to catch all logs
        process_logger = logging.getLogger(f'process_{process_id}')
        process_logger.setLevel(logging.DEBUG)  # Set logger level to DEBUG to catch all
        process_logger.propagate = False  # Don't propagate to root logger
        process_logger.handlers = []  # Clear existing handlers
        process_logger.addHandler(handler)
        # Force immediate flush/test
        process_logger.info(f"Process {process_id} started: index-scraper-publications, scraper_id={scraper_id}, since={since}")
    
    try:
        if process_id:
            update_process_progress(process_id, {'message': 'Starting scraper indexing...', 'current': 0, 'total': 0})
            process_logger.info("Starting scraper indexing...")
        
        es_client = get_es_client()
        if not es_client:
            error_msg = "Elasticsearch not available - skipping indexing"
            process_logger.warning(error_msg)
            if process_id:
                update_process_status(process_id, 'failed', error_msg)
            return
        
        # Check if stopped
        if process_id and is_process_stopped(process_id):
            process_logger.info("Process was stopped")
            return
        
        if process_id:
            update_process_progress(process_id, {'message': 'Fetching publications from scraper...', 'current': 0, 'total': 0})
        
        publication_ids = get_publications_from_scraper(scraper_id, since, limit=1000)
        total = len(publication_ids)
        
        if process_id:
            update_process_progress(process_id, {'message': f'Found {total} publications to index', 'current': 0, 'total': total})
            process_logger.info(f"Found {total} publications to index")
        
        indexed = 0
        failed = 0
        
        for i, pub_id in enumerate(publication_ids):
            # Check if stopped
            if process_id and is_process_stopped(process_id):
                process_logger.info("Process was stopped")
                return
            
            try:
                doc = denormalize_publication(pub_id)
                if doc:
                    es_client.index(index=settings.ELASTICSEARCH_INDEX, id=pub_id, document=doc)
                    indexed += 1
                
                if process_id and (i + 1) % 10 == 0:
                    update_process_progress(process_id, {
                        'message': f'Indexing... {i+1}/{total}',
                        'current': i + 1,
                        'total': total,
                        'indexed': indexed,
                        'failed': failed
                    })
                    process_logger.info(f"Progress: {i+1}/{total} indexed, {failed} failed")
            except Exception as e:
                failed += 1
                process_logger.error(f"Failed to index publication {pub_id}: {str(e)}")
        
        if process_id:
            process_logger.info(f"Completed: Indexed {indexed} publications from scraper {scraper_id} since {since}, {failed} failed")
        
        if process_id:
            update_process_status(process_id, 'completed')
            update_process_progress(process_id, {
                'message': 'Completed',
                'current': total,
                'total': total,
                'indexed': indexed,
                'failed': failed
            })
    except Exception as e:
        error_msg = f"Failed to index scraper publications: {str(e)}"
        process_logger.error(error_msg)
        if process_id:
            update_process_status(process_id, 'failed', error_msg)


@router.post("/index-licitacion", response_model=IndexResponse)  # Full path: /api/index-licitacion
async def index_licitacion(
    request: IndexLicitacionRequest,
    current_auth: dict = Depends(allow_api_key)
) -> IndexResponse:
    """
    Index single publication by ID - webhook style (returns immediately, processes in background)
    Access: JWT token or API key
    """
    if not executor:
        raise HTTPException(status_code=503, detail="Executor not initialized")
    
    es_client = get_es_client()
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    # Schedule background task
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _index_publication_sync, request.publicacion_id, None)
    
    # Return immediately
    return IndexResponse(
        status="queued",
        id=request.publicacion_id,
        timestamp=datetime.now().isoformat()
    )


@router.post("/index-scraper-publications", response_model=IndexResponse)  # Full path: /api/index-scraper-publications
async def index_scraper_publications(
    request: IndexScraperRequest,
    current_auth: dict = Depends(allow_api_key)
) -> IndexResponse:
    """
    Index all publications from a scraper since given time - webhook style
    Access: JWT token or API key
    """
    if not executor:
        raise HTTPException(status_code=503, detail="Executor not initialized")
    
    es_client = get_es_client()
    if not es_client:
        logger.warning("Elasticsearch not available - skipping indexing")
        return IndexResponse(status="error", message="Elasticsearch not available")
    
    # Schedule background task
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _index_scraper_publications_sync, request.scraper_id, request.since, None)
    
    # Return immediately
    return IndexResponse(
        status="queued",
        scraper_id=request.scraper_id,
        since=request.since,
        timestamp=datetime.now().isoformat()
    )


def _sync_since_sync(since: str, process_id: Optional[int] = None):
    """Synchronous function to sync publications since date (runs in background thread)"""
    process_logger = logger
    if process_id:
        handler = ProcessLogHandler(process_id)
        handler.setFormatter(logging.Formatter('%(message)s'))
        process_logger = logging.getLogger(f'process_{process_id}')
        process_logger.setLevel(logging.INFO)
        process_logger.propagate = False  # Don't propagate to root logger
        process_logger.handlers = []  # Clear existing handlers
        process_logger.addHandler(handler)
    
    try:
        if process_id:
            update_process_progress(process_id, {'message': 'Starting sync...', 'current': 0, 'total': 0})
        
        es_client = get_es_client()
        if not es_client:
            error_msg = "Elasticsearch not available - skipping sync"
            process_logger.warning(error_msg)
            if process_id:
                update_process_status(process_id, 'failed', error_msg)
            return
        
        # Check if stopped
        if process_id and is_process_stopped(process_id):
            process_logger.info("Process was stopped")
            return
        
        if process_id:
            update_process_progress(process_id, {'message': 'Fetching publications...', 'current': 0, 'total': 0})
        
        publication_ids = get_publications_since(since, limit=5000)
        total = len(publication_ids)
        
        if process_id:
            update_process_progress(process_id, {'message': f'Found {total} publications to sync', 'current': 0, 'total': total})
        
        indexed = 0
        failed = 0
        
        for i, pub_id in enumerate(publication_ids):
            # Check if stopped
            if process_id and is_process_stopped(process_id):
                process_logger.info("Process was stopped")
                return
            
            try:
                doc = denormalize_publication(pub_id)
                if doc:
                    es_client.index(index=settings.ELASTICSEARCH_INDEX, id=pub_id, document=doc)
                    indexed += 1
                
                if process_id and (i + 1) % 50 == 0:
                    update_process_progress(process_id, {
                        'message': f'Syncing... {i+1}/{total}',
                        'current': i + 1,
                        'total': total,
                        'indexed': indexed,
                        'failed': failed
                    })
            except Exception as e:
                failed += 1
                process_logger.error(f"Failed to index publication {pub_id}: {str(e)}")
        
        process_logger.info(f"Sync completed since {since}: {indexed} indexed, {failed} failed")
        
        if process_id:
            update_process_status(process_id, 'completed')
            update_process_progress(process_id, {
                'message': 'Completed',
                'current': total,
                'total': total,
                'indexed': indexed,
                'failed': failed
            })
    except Exception as e:
        error_msg = f"Sync failed: {str(e)}"
        process_logger.error(error_msg)
        if process_id:
            update_process_status(process_id, 'failed', error_msg)


def _index_bulk_sync(process_id: Optional[int] = None):
    """Synchronous function to bulk index all publications (runs in background thread)"""
    process_logger = logger
    if process_id:
        handler = ProcessLogHandler(process_id)
        handler.setFormatter(logging.Formatter('%(message)s'))
        process_logger = logging.getLogger(f'process_{process_id}')
        process_logger.setLevel(logging.INFO)
        process_logger.propagate = False  # Don't propagate to root logger
        process_logger.handlers = []  # Clear existing handlers
        process_logger.addHandler(handler)
    
    try:
        if process_id:
            update_process_progress(process_id, {'message': 'Starting bulk indexing...', 'current': 0, 'total': 0})
        
        es_client = get_es_client()
        if not es_client:
            error_msg = "Elasticsearch not available"
            process_logger.warning(error_msg)
            if process_id:
                update_process_status(process_id, 'failed', error_msg)
            return
        
        # Check if stopped
        if process_id and is_process_stopped(process_id):
            process_logger.info("Process was stopped")
            return
        
        batch_size = 1000
        offset = 0
        total_indexed = 0
        total_failed = 0
        
        process_logger.info("Starting bulk indexing...")
        
        # First pass: count total
        total_count = 0
        temp_offset = 0
        while True:
            batch = get_all_publication_ids(batch_size, temp_offset)
            if not batch:
                break
            total_count += len(batch)
            temp_offset += batch_size
        
        if process_id:
            update_process_progress(process_id, {'message': f'Found {total_count} publications to index', 'current': 0, 'total': total_count})
        
        # Second pass: index
        while True:
            # Check if stopped
            if process_id and is_process_stopped(process_id):
                process_logger.info("Process was stopped")
                return
            
            publication_ids = get_all_publication_ids(batch_size, offset)
            
            if not publication_ids:
                break
            
            # Bulk index this batch
            actions = []
            
            for pub_id in publication_ids:
                try:
                    doc = denormalize_publication(pub_id)
                    if doc:
                        actions.append({
                            "_index": settings.ELASTICSEARCH_INDEX,
                            "_id": pub_id,
                            "_source": doc
                        })
                except Exception as e:
                    total_failed += 1
                    process_logger.error(f"Failed to denormalize publication {pub_id}: {str(e)}")
            
            # Bulk insert
            if actions:
                try:
                    from elasticsearch.helpers import streaming_bulk
                    success_count = 0
                    for ok, response in streaming_bulk(es_client, actions, chunk_size=500):
                        if ok:
                            success_count += 1
                        else:
                            total_failed += 1
                    total_indexed += success_count
                except Exception as e:
                    process_logger.error(f"Bulk insert failed: {str(e)}")
                    total_failed += len(actions)
            
            offset += batch_size
            
            if process_id:
                update_process_progress(process_id, {
                    'message': f'Bulk indexing... {offset}/{total_count}',
                    'current': offset,
                    'total': total_count,
                    'indexed': total_indexed,
                    'failed': total_failed
                })
            
            process_logger.info(f"Bulk indexing progress: {offset} processed, {total_indexed} indexed")
        
        process_logger.info(f"Bulk indexing completed: {total_indexed} indexed, {total_failed} failed")
        
        if process_id:
            update_process_status(process_id, 'completed')
            update_process_progress(process_id, {
                'message': 'Completed',
                'current': total_count,
                'total': total_count,
                'indexed': total_indexed,
                'failed': total_failed
            })
    except Exception as e:
        error_msg = f"Bulk indexing failed: {str(e)}"
        process_logger.error(error_msg)
        if process_id:
            update_process_status(process_id, 'failed', error_msg)
