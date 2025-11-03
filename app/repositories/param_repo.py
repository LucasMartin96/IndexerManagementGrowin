"""
Parameter repository - Data access layer for params
"""

import logging
from typing import Optional, List, Dict
from app.db.sqlite import execute_query, get_connection

logger = logging.getLogger(__name__)


def create_param(key: str, value: str, description: Optional[str] = None,
                 category: Optional[str] = None) -> Dict:
    """
    Create a new parameter
    
    Args:
        key: Parameter key (unique)
        value: Parameter value
        description: Optional description
        category: Optional category for grouping
        
    Returns:
        dict: Created parameter info
    """
    query = """
        INSERT INTO params (key, value, description, category)
        VALUES (?, ?, ?, ?)
    """
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (key, value, description, category))
        param_id = cursor.lastrowid
        conn.commit()
    
    logger.info(f"Created param: {key}")
    
    return {
        'id': param_id,
        'key': key,
        'value': value,
        'description': description,
        'category': category
    }


def get_param(key: str) -> Optional[Dict]:
    """
    Get parameter by key
    
    Args:
        key: Parameter key
        
    Returns:
        dict: Parameter info or None
    """
    query = """
        SELECT * FROM params
        WHERE key = ?
    """
    
    return execute_query(query, (key,), fetch_one=True)


def update_param(key: str, value: Optional[str] = None,
                 description: Optional[str] = None,
                 category: Optional[str] = None) -> bool:
    """
    Update parameter by key
    
    Args:
        key: Parameter key
        value: New value (optional)
        description: New description (optional)
        category: New category (optional)
        
    Returns:
        bool: True if updated successfully
    """
    # Build dynamic update query
    updates = []
    params = []
    
    if value is not None:
        updates.append("value = ?")
        params.append(value)
    
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    
    if not updates:
        return False
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(key)
    
    query = f"""
        UPDATE params
        SET {', '.join(updates)}
        WHERE key = ?
    """
    
    result = execute_query(query, tuple(params))
    logger.info(f"Updated param: {key}")
    return result > 0


def delete_param(key: str) -> bool:
    """
    Delete parameter by key
    
    Args:
        key: Parameter key
        
    Returns:
        bool: True if deleted successfully
    """
    query = "DELETE FROM params WHERE key = ?"
    result = execute_query(query, (key,))
    logger.info(f"Deleted param: {key}")
    return result > 0


def list_params(category: Optional[str] = None) -> List[Dict]:
    """
    List all parameters
    
    Args:
        category: Optional filter by category
        
    Returns:
        list: List of parameter dictionaries
    """
    if category:
        query = """
            SELECT * FROM params
            WHERE category = ?
            ORDER BY key ASC
        """
        return execute_query(query, (category,), fetch_all=True)
    else:
        query = """
            SELECT * FROM params
            ORDER BY category ASC, key ASC
        """
        return execute_query(query, fetch_all=True)


def search_params(search_term: str) -> List[Dict]:
    """
    Search parameters by key or description
    
    Args:
        search_term: Search term
        
    Returns:
        list: List of matching parameters
    """
    query = """
        SELECT * FROM params
        WHERE key LIKE ? OR description LIKE ?
        ORDER BY key ASC
    """
    
    search_pattern = f"%{search_term}%"
    return execute_query(query, (search_pattern, search_pattern), fetch_all=True)


def get_params_by_category(category: str) -> List[Dict]:
    """
    Get all parameters in a category
    
    Args:
        category: Category name
        
    Returns:
        list: List of parameters in category
    """
    return list_params(category=category)


def get_categories() -> List[str]:
    """
    Get all unique categories
    
    Returns:
        list: List of category names
    """
    query = """
        SELECT DISTINCT category
        FROM params
        WHERE category IS NOT NULL
        ORDER BY category ASC
    """
    
    results = execute_query(query, fetch_all=True)
    return [row['category'] for row in results if row['category']]

