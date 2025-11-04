"""
Elasticsearch client initialization
"""

import json
import logging
from pathlib import Path
from elasticsearch import Elasticsearch
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global ES client
es_client = None


def es_client_init() -> Elasticsearch | None:
    """
    Initialize Elasticsearch client
    
    Returns:
        Elasticsearch: Initialized ES client, or None if connection fails
    """
    global es_client
    
    # Build connection parameters
    # Support both http:// and https:// URLs, or host:port format
    if settings.ELASTICSEARCH_HOST.startswith(('http://', 'https://')):
        # Full URL provided (e.g., https://my-cluster.es.amazonaws.com)
        es_url = settings.ELASTICSEARCH_HOST
        if settings.ELASTICSEARCH_PORT and settings.ELASTICSEARCH_PORT not in [80, 443]:
            # Port is specified and not default, add it to URL
            es_url = f"{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"
    else:
        # Host:port format (e.g., localhost:9200 or elasticsearch:9200)
        scheme = "https" if settings.ELASTICSEARCH_PORT == 443 else "http"
        es_url = f"{scheme}://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"
    
    es_config = {
        "hosts": [es_url],
        "request_timeout": 30,
        "max_retries": 3
    }
    
    # Add authentication - API key takes precedence over username/password
    if settings.ELASTICSEARCH_API_KEY:
        es_config["api_key"] = settings.ELASTICSEARCH_API_KEY
        logger.info("Using Elasticsearch API key authentication")
    elif settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
        es_config["basic_auth"] = (
            settings.ELASTICSEARCH_USERNAME,
            settings.ELASTICSEARCH_PASSWORD
        )
        logger.info("Using Elasticsearch username/password authentication")
    
    try:
        client = Elasticsearch(**es_config)
        # Test connection with timeout
        if not client.ping(request_timeout=5):
            logger.warning(f"Elasticsearch ping failed at {es_url}")
            return None
        
        logger.info(f"Elasticsearch connection established: {es_url}")
        return client
    except Exception as e:
        logger.warning(f"Failed to connect to Elasticsearch at {es_url}: {str(e)}")
        logger.info("FastAPI will continue without Elasticsearch. Endpoints requiring Elasticsearch will return errors.")
        return None


def es_create_index(client: Elasticsearch, index_name: str, mapping: dict = None):
    """
    Create Elasticsearch index if it doesn't exist
    
    Args:
        client: Elasticsearch client
        index_name: Name of the index
        mapping: Optional index mapping
    """
    try:
        # Check if index exists
        if client.indices.exists(index=index_name):
            logger.info(f"Index {index_name} already exists")
            return
        
        # Create index
        body = {}
        if mapping:
            body["mappings"] = mapping
        
        client.indices.create(index=index_name, body=body)
        logger.info(f"Created index {index_name}")
    except Exception as e:
        logger.error(f"Failed to create index {index_name}: {str(e)}")
        raise


def load_es_mapping(mapping_file: str = "es_mapping.json") -> dict:
    """
    Load Elasticsearch mapping from file
    
    Args:
        mapping_file: Path to mapping file
        
    Returns:
        dict: Mapping configuration
    """
    try:
        mapping_path = Path(mapping_file)
        if not mapping_path.exists():
            logger.warning(f"Mapping file {mapping_file} not found")
            return None
        
        with open(mapping_path, 'r') as f:
            mapping = json.load(f)
        
        logger.info(f"Loaded mapping from {mapping_file}")
        return mapping
    except Exception as e:
        logger.error(f"Failed to load mapping file {mapping_file}: {str(e)}")
        return None


def get_es_client() -> Elasticsearch | None:
    """
    Get global Elasticsearch client
    
    Returns:
        Elasticsearch: ES client instance, or None if not available
    """
    global es_client
    if es_client is None:
        es_client = es_client_init()
    return es_client


def initialize_elasticsearch(mapping_file: str = "es_mapping.json") -> Elasticsearch | None:
    """
    Initialize Elasticsearch with mapping
    
    Args:
        mapping_file: Path to mapping file
        
    Returns:
        Elasticsearch: Initialized ES client, or None if connection fails
    """
    client = es_client_init()
    
    if client is None:
        logger.warning("Cannot initialize Elasticsearch index - client not available")
        return None
    
    # Load and apply mapping
    mapping = load_es_mapping(mapping_file)
    if mapping:
        es_create_index(client, settings.ELASTICSEARCH_INDEX, mapping)
    else:
        es_create_index(client, settings.ELASTICSEARCH_INDEX)
    
    return client

