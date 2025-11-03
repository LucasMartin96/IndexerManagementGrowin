"""
Process manager for indexer processes
Handles tracking, starting, stopping, and monitoring indexer processes
"""

import json
import logging
import threading
from datetime import datetime
from typing import Dict, Optional, List
from concurrent.futures import Future, ThreadPoolExecutor
from app.db.sqlite import execute_query, get_connection
from app.utils.logging_handler import ProcessLogHandler, get_process_logs, remove_process_logs
from app.repositories.process_repo import (
    create_process,
    get_process as get_process_repo,
    update_process_status as update_process_status_repo,
    update_process_progress as update_process_progress_repo,
    list_processes as list_processes_repo,
    get_process_status,
    mark_process_stopped
)

logger = logging.getLogger(__name__)

# Registry of active processes: {process_id: Future}
_active_processes: Dict[int, Future] = {}
_process_lock = threading.Lock()

def start_indexer_process(type: str, params: Dict, user_id: Optional[int] = None, executor: ThreadPoolExecutor = None) -> int:
    """
    Start an indexer process and register it in the database
    
    Args:
        type: Indexer type (index-licitacion, index-scraper-publications, index-bulk, sync-since)
        params: Parameters dict (varies by type)
        user_id: Optional user ID who started the process
        executor: ThreadPoolExecutor to submit the task to
        
    Returns:
        int: Process ID
    """
    # Use repository to create process
    process_id = create_process(type, params, user_id)
    logger.info(f"Started indexer process {process_id}: type={type}, params={params}")
    return process_id

def stop_indexer_process(process_id: int) -> bool:
    """
    Stop an indexer process
    
    Args:
        process_id: Process ID to stop
        
    Returns:
        bool: True if stopped successfully
    """
    with _process_lock:
        future = _active_processes.get(process_id)
        
        if not future:
            # Process might have already completed
            # Check if it's still running in DB
            query = "SELECT status FROM indexer_processes WHERE id = ?"
            result = execute_query(query, (process_id,), fetch_one=True)
            
            if not result or result['status'] != 'running':
                return False
            
            # Update status to stopped
            query = """
                UPDATE indexer_processes
                SET status = 'stopped', completed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'running'
            """
            execute_query(query, (process_id,))
            logger.info(f"Marked process {process_id} as stopped (was already completed)")
            return True
        
        # Try to cancel the future
        cancelled = future.cancel()
        
        if cancelled:
            # Update status in DB
            mark_process_stopped(process_id)
            
            # Remove from active processes
            del _active_processes[process_id]
            
            logger.info(f"Cancelled process {process_id}")
            return True
        else:
            # Process is already running, mark as stopped
            # The process will check cancellation flag and stop itself
            update_process_status_repo(process_id, 'stopped')
            
            # Note: We don't remove from _active_processes here
            # The process will clean up when it checks the status
            
            logger.info(f"Marked process {process_id} for stopping (was already running)")
            return True

def register_active_process(process_id: int, future: Future):
    """Register an active process future"""
    with _process_lock:
        _active_processes[process_id] = future

def unregister_active_process(process_id: int):
    """Unregister an active process"""
    with _process_lock:
        _active_processes.pop(process_id, None)

def update_process_status(process_id: int, status: str, error_message: Optional[str] = None):
    """
    Update process status in database
    
    Args:
        process_id: Process ID
        status: New status (running, completed, failed, stopped)
        error_message: Optional error message if failed
    """
    update_process_status_repo(process_id, status, error_message)
    
    if status in ('completed', 'failed', 'stopped'):
        unregister_active_process(process_id)

def update_process_progress(process_id: int, progress: Dict):
    """
    Update process progress in database
    
    Args:
        process_id: Process ID
        progress: Progress dict with current, total, indexed, failed, etc.
    """
    update_process_progress_repo(process_id, progress)

def get_process(process_id: int) -> Optional[Dict]:
    """
    Get process information
    
    Args:
        process_id: Process ID
        
    Returns:
        dict: Process info or None
    """
    return get_process_repo(process_id)

def list_processes(
    status: Optional[str] = None,
    type: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """
    List indexer processes with optional filters
    
    Args:
        status: Filter by status (running, completed, failed, stopped)
        type: Filter by type (index-licitacion, etc.)
        user_id: Filter by user ID
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        list: List of processes
    """
    return list_processes_repo(status, type, user_id, limit, offset)

def is_process_stopped(process_id: int) -> bool:
    """
    Check if a process is marked as stopped
    
    Args:
        process_id: Process ID
        
    Returns:
        bool: True if process is stopped
    """
    status = get_process_status(process_id)
    return status == 'stopped' if status else True

