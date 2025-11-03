"""
Elasticsearch query builder for PHP query parameters
Translates PHP query params to ES queries
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def build_es_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Elasticsearch query from PHP query parameters
    
    Args:
        params: Query parameters from PHP (same format as current POST data)
        
    Returns:
        dict: Elasticsearch query DSL
    """
    must_clauses = []
    filter_clauses = []
    should_clauses = []
    
    # General search (multi-field text search)
    search = params.get('search')
    if search and search.strip():
        search_terms = search.strip()
        should_clauses.append({
            "wildcard": {"objeto": f"*{search_terms}*"}
        })
        should_clauses.append({
            "wildcard": {"agencia": f"*{search_terms}*"}
        })
        should_clauses.append({
            "wildcard": {"oficina": f"*{search_terms}*"}
        })
        should_clauses.append({
            "wildcard": {"referencia": f"*{search_terms}*"}
        })
    
    # Object filter
    objeto = params.get('objeto')
    if objeto and objeto.strip():
        must_clauses.append({
            "wildcard": {"objeto": f"*{objeto.strip()}*"}
        })
    
    # Agency filter
    agencia = params.get('agencia')
    if agencia and agencia.strip():
        must_clauses.append({
            "wildcard": {"agencia": f"*{agencia.strip()}*"}
        })
    
    # Country filter
    pais = params.get('pais')
    if pais and pais != 'all':
        try:
            pais_id = int(pais)
            filter_clauses.append({"term": {"pais_id": pais_id}})
        except (ValueError, TypeError):
            # If pais is not numeric, try matching by pais_nombre
            filter_clauses.append({"term": {"pais_nombre": str(pais)}})
    
    # Tag/rubro filter
    rubro = params.get('rubro')
    if rubro and rubro != 'all':
        try:
            tag_id = int(rubro)
            filter_clauses.append({"term": {"tag_ids": tag_id}})
        except (ValueError, TypeError):
            pass
    
    # User tag filtering (PHP sends if filtering by user tags)
    user_tag_ids = params.get('user_tag_ids')
    filter_mode = params.get('filter_mode', 'all')
    if user_tag_ids and isinstance(user_tag_ids, list) and len(user_tag_ids) > 0 and filter_mode == 'user_tags':
        # Filter by user's selected tags
        filter_clauses.append({"terms": {"tag_ids": user_tag_ids}})
    
    # Date range filters
    apertura_fr = params.get('apertura_fr')
    apertura_to = params.get('apertura_to')
    
    if apertura_fr or apertura_to:
        date_range = {}
        if apertura_fr:
            try:
                # Parse date format d/m/Y to Y-m-d
                date_obj = datetime.strptime(apertura_fr, '%d/%m/%Y')
                date_range["gte"] = date_obj.strftime('%Y-%m-%d') + " 00:00:00"
            except ValueError:
                # Try Y-m-d format
                date_range["gte"] = apertura_fr + " 00:00:00"
        if apertura_to:
            try:
                date_obj = datetime.strptime(apertura_to, '%d/%m/%Y')
                date_range["lte"] = date_obj.strftime('%Y-%m-%d') + " 23:59:59"
            except ValueError:
                date_range["lte"] = apertura_to + " 23:59:59"
        
        if date_range:
            filter_clauses.append({"range": {"apertura": date_range}})
    
    # Vigente filter
    incluirVencidos = params.get('incluirVencidos')
    soloVigentes = params.get('soloVigentes')
    
    if incluirVencidos == '0' or soloVigentes == '1':
        # Only show vigente publications
        filter_clauses.append({"term": {"vigente": True}})
    elif incluirVencidos == '1':
        # Show all (no filter)
        pass
    
    # Visible filter (always show only visible)
    filter_clauses.append({"term": {"visible": True}})
    
    # Build bool query
    bool_query = {}
    
    if must_clauses:
        bool_query["must"] = must_clauses
    
    if filter_clauses:
        bool_query["filter"] = filter_clauses
    
    if should_clauses:
        bool_query["should"] = should_clauses
        bool_query["minimum_should_match"] = 1
    
    query = {
        "bool": bool_query
    } if bool_query else {"match_all": {}}
    
    return query

def format_es_results(es_response: Dict, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format Elasticsearch response to match MySQL response format
    
    Args:
        es_response: Raw Elasticsearch search response
        params: Original query parameters
        
    Returns:
        dict: Formatted response matching PHP MySQL format
    """
    hits = es_response.get('hits', {})
    total = hits.get('total', {})
    
    # Handle ES 7.x vs 8.x total format
    if isinstance(total, dict):
        total_value = total.get('value', 0)
    else:
        total_value = total
    
    publications = []
    for hit in hits.get('hits', []):
        source = hit['_source']
        # Ensure format matches MySQL result structure
        publications.append(source)
    
    page = int(params.get('page', 1))
    page_size = int(params.get('page_size', 15))
    paginas = (total_value + page_size - 1) // page_size if total_value > 0 else 1
    
    return {
        "publicaciones": publications,
        "total": total_value,
        "pagina": page,
        "paginas": paginas
    }

