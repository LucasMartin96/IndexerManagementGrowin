"""
Parameter service - Business logic for parameters
"""

import logging
from typing import Optional, List, Dict
from app.repositories import param_repo

logger = logging.getLogger(__name__)


def create_param(key: str, value: str, description: Optional[str] = None,
                 category: Optional[str] = None) -> Dict:
    """Create a new parameter"""
    return param_repo.create_param(key, value, description, category)


def get_param(key: str) -> Optional[Dict]:
    """Get parameter by key"""
    return param_repo.get_param(key)


def update_param(key: str, value: Optional[str] = None,
                 description: Optional[str] = None,
                 category: Optional[str] = None) -> bool:
    """Update parameter by key"""
    return param_repo.update_param(key, value, description, category)


def delete_param(key: str) -> bool:
    """Delete parameter by key"""
    return param_repo.delete_param(key)


def list_params(category: Optional[str] = None) -> List[Dict]:
    """List all parameters"""
    return param_repo.list_params(category)


def search_params(search_term: str) -> List[Dict]:
    """Search parameters"""
    return param_repo.search_params(search_term)


def get_params_by_category(category: str) -> List[Dict]:
    """Get parameters by category"""
    return param_repo.get_params_by_category(category)


def get_categories() -> List[str]:
    """Get all categories"""
    return param_repo.get_categories()

