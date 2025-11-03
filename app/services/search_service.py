"""
Search service - Business logic for searching publications
"""

import logging
from typing import Dict
from app.utils.query_builder import build_es_query, format_es_results
from app.db import get_es_client
from app.core.config import settings

logger = logging.getLogger(__name__)


def search_publications(params: Dict, es_client=None) -> Dict:
    """
    Search publications in Elasticsearch
    
    Args:
        params: Search parameters dict
        es_client: Optional Elasticsearch client
        
    Returns:
        dict: Formatted search results
    """
    if es_client is None:
        es_client = get_es_client()
    
    # Build Elasticsearch query from PHP params
    es_query_dsl = build_es_query(params)
    
    # Pagination
    page = int(params.get('page', 1))
    page_size = int(params.get('page_size', 15))
    from_offset = (page - 1) * page_size
    
    # Sorting
    sort = [
        {"editado": {"order": "desc"}},
        {"id": {"order": "desc"}}
    ]
    
    # Execute Elasticsearch query
    es_query = {
        "query": es_query_dsl,
        "from": from_offset,
        "size": page_size,
        "sort": sort
    }
    
    results = es_client.search(index=settings.ELASTICSEARCH_INDEX, body=es_query)
    
    # Format results to match MySQL response
    formatted_results = format_es_results(results, params)
    
    return formatted_results

