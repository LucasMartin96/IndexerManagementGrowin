"""
Process service - Business logic for indexer process management
"""

import logging
from typing import Optional, Dict, List
from concurrent.futures import Future
from app.utils.process_manager import (
    start_indexer_process,
    stop_indexer_process,
    update_process_status,
    update_process_progress,
    register_active_process,
    is_process_stopped,
    get_process as get_process_util,
    list_processes as list_processes_util
)
from app.utils.logging_handler import get_process_logs

logger = logging.getLogger(__name__)


def start_indexer(type: str, params: Dict, user_id: Optional[int] = None) -> int:
    """
    Start an indexer process
    
    Args:
        type: Indexer type
        params: Parameters dict
        user_id: Optional user ID
        
    Returns:
        int: Process ID
    """
    return start_indexer_process(type, params, user_id)


def stop_indexer(process_id: int) -> bool:
    """Stop an indexer process"""
    return stop_indexer_process(process_id)


def register_process(process_id: int, future: Future):
    """Register an active process"""
    register_active_process(process_id, future)


def update_status(process_id: int, status: str, error_message: Optional[str] = None):
    """Update process status"""
    update_process_status(process_id, status, error_message)


def update_progress(process_id: int, progress: Dict):
    """Update process progress"""
    update_process_progress(process_id, progress)


def get_process(process_id: int) -> Optional[Dict]:
    """Get process information"""
    return get_process_util(process_id)


def list_processes(
    status: Optional[str] = None,
    type: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """List processes with filters"""
    return list_processes_util(status, type, user_id, limit, offset)


def check_process_stopped(process_id: int) -> bool:
    """Check if process is stopped"""
    return is_process_stopped(process_id)


def get_logs(process_id: int, since_timestamp: Optional[str] = None) -> List[Dict]:
    """Get process logs"""
    return get_process_logs(process_id, since_timestamp)

