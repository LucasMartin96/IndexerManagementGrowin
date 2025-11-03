"""
Indexer service - Business logic for indexing publications
"""

import logging
from typing import Optional, Dict, List
from app.utils.denormalize import (
    denormalize_publication,
    get_publications_from_scraper,
    get_publications_since,
    get_all_publication_ids
)
from app.db import get_es_client
from app.core.config import settings

logger = logging.getLogger(__name__)


def index_publication(publicacion_id: int, es_client=None) -> bool:
    """
    Index a single publication
    
    Args:
        publicacion_id: Publication ID
        es_client: Optional Elasticsearch client (uses global if not provided)
        
    Returns:
        bool: True if indexed successfully
    """
    if es_client is None:
        es_client = get_es_client()
    
    try:
        doc = denormalize_publication(publicacion_id)
        if not doc:
            logger.warning(f"Publication {publicacion_id} not found")
            return False
        
        es_client.index(index=settings.ELASTICSEARCH_INDEX, id=publicacion_id, document=doc)
        logger.info(f"Indexed publication {publicacion_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to index publication {publicacion_id}: {str(e)}")
        raise


def index_scraper_publications(scraper_id: int, since: str, es_client=None, 
                                process_id: Optional[int] = None,
                                on_progress=None) -> Dict:
    """
    Index all publications from a scraper since given time
    
    Args:
        scraper_id: Scraper ID
        since: Datetime string (YYYY-MM-DD HH:MM:SS)
        es_client: Optional Elasticsearch client
        process_id: Optional process ID for tracking
        on_progress: Optional callback for progress updates
        
    Returns:
        dict: Results with indexed and failed counts
    """
    if es_client is None:
        es_client = get_es_client()
    
    publication_ids = get_publications_from_scraper(scraper_id, since, limit=1000)
    total = len(publication_ids)
    
    indexed = 0
    failed = 0
    
    for i, pub_id in enumerate(publication_ids):
        try:
            doc = denormalize_publication(pub_id)
            if doc:
                es_client.index(index=settings.ELASTICSEARCH_INDEX, id=pub_id, document=doc)
                indexed += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed to index publication {pub_id}: {str(e)}")
        
        # Report progress if callback provided
        if on_progress and (i + 1) % 10 == 0:
            on_progress(i + 1, total, indexed, failed)
    
    logger.info(f"Indexed {indexed} publications from scraper {scraper_id} since {since}")
    
    return {
        'indexed': indexed,
        'failed': failed,
        'total': total
    }


def sync_since(since: str, es_client=None, process_id: Optional[int] = None,
               on_progress=None) -> Dict:
    """
    Sync publications updated since given date
    
    Args:
        since: Datetime string (YYYY-MM-DD HH:MM:SS)
        es_client: Optional Elasticsearch client
        process_id: Optional process ID for tracking
        on_progress: Optional callback for progress updates
        
    Returns:
        dict: Results with indexed and failed counts
    """
    if es_client is None:
        es_client = get_es_client()
    
    publication_ids = get_publications_since(since, limit=5000)
    total = len(publication_ids)
    
    indexed = 0
    failed = 0
    
    for i, pub_id in enumerate(publication_ids):
        try:
            doc = denormalize_publication(pub_id)
            if doc:
                es_client.index(index=settings.ELASTICSEARCH_INDEX, id=pub_id, document=doc)
                indexed += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed to index publication {pub_id}: {str(e)}")
        
        # Report progress if callback provided
        if on_progress and (i + 1) % 50 == 0:
            on_progress(i + 1, total, indexed, failed)
    
    logger.info(f"Sync completed since {since}: {indexed} indexed, {failed} failed")
    
    return {
        'indexed': indexed,
        'failed': failed,
        'total': total
    }


def index_bulk(es_client=None, process_id: Optional[int] = None,
                on_progress=None) -> Dict:
    """
    Bulk index all publications
    
    Args:
        es_client: Optional Elasticsearch client
        process_id: Optional process ID for tracking
        on_progress: Optional callback for progress updates
        
    Returns:
        dict: Results with indexed and failed counts
    """
    if es_client is None:
        es_client = get_es_client()
    
    from elasticsearch.helpers import streaming_bulk
    
    batch_size = 1000
    offset = 0
    total_indexed = 0
    total_failed = 0
    
    # Count total first
    total_count = 0
    temp_offset = 0
    while True:
        batch = get_all_publication_ids(batch_size, temp_offset)
        if not batch:
            break
        total_count += len(batch)
        temp_offset += batch_size
    
    # Index in batches
    while True:
        publication_ids = get_all_publication_ids(batch_size, offset)
        
        if not publication_ids:
            break
        
        # Build bulk actions
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
                logger.error(f"Failed to denormalize publication {pub_id}: {str(e)}")
        
        # Bulk insert
        if actions:
            try:
                success_count = 0
                for ok, response in streaming_bulk(es_client, actions, chunk_size=500):
                    if ok:
                        success_count += 1
                    else:
                        total_failed += 1
                total_indexed += success_count
            except Exception as e:
                logger.error(f"Bulk insert failed: {str(e)}")
                total_failed += len(actions)
        
        offset += batch_size
        
        # Report progress
        if on_progress:
            on_progress(offset, total_count, total_indexed, total_failed)
        
        logger.info(f"Bulk indexing progress: {offset} processed, {total_indexed} indexed")
    
    logger.info(f"Bulk indexing completed: {total_indexed} indexed, {total_failed} failed")
    
    return {
        'indexed': total_indexed,
        'failed': total_failed,
        'total': total_count
    }

