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


def es_client_init() -> Elasticsearch:
    """
    Initialize Elasticsearch client
    
    Returns:
        Elasticsearch: Initialized ES client
    """
    global es_client
    
    # Build connection parameters
    # Elasticsearch needs full URL with scheme (http:// or https://)
    es_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"
    es_config = {
        "hosts": [es_url]
    }
    
    # Add authentication if provided
    if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
        es_config["basic_auth"] = (
            settings.ELASTICSEARCH_USERNAME,
            settings.ELASTICSEARCH_PASSWORD
        )
    
    try:
        client = Elasticsearch(**es_config)
        # Test connection
        if not client.ping():
            raise ConnectionError("Failed to ping Elasticsearch")
        
        logger.info(f"Elasticsearch connection established: {settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch: {str(e)}")
        raise


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


def get_es_client() -> Elasticsearch:
    """
    Get global Elasticsearch client
    
    Returns:
        Elasticsearch: ES client instance
    """
    global es_client
    if es_client is None:
        es_client = es_client_init()
    return es_client


def initialize_elasticsearch(mapping_file: str = "es_mapping.json") -> Elasticsearch:
    """
    Initialize Elasticsearch with mapping
    
    Args:
        mapping_file: Path to mapping file
        
    Returns:
        Elasticsearch: Initialized ES client
    """
    client = es_client_init()
    
    # Load and apply mapping
    mapping = load_es_mapping(mapping_file)
    if mapping:
        es_create_index(client, settings.ELASTICSEARCH_INDEX, mapping)
    else:
        es_create_index(client, settings.ELASTICSEARCH_INDEX)
    
    return client

