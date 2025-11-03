"""
Process repository - Data access layer for indexer processes
"""

import json
import logging
from typing import Optional, List, Dict
from datetime import datetime
from app.db.sqlite import execute_query, get_connection

logger = logging.getLogger(__name__)


def create_process(type: str, params: Dict, user_id: Optional[int] = None) -> int:
    """
    Create a new process record
    
    Args:
        type: Process type
        params: Parameters dict
        user_id: Optional user ID
        
    Returns:
        int: Process ID
    """
    query = """
        INSERT INTO indexer_processes (type, status, params, user_id)
        VALUES (?, ?, ?, ?)
    """
    
    params_json = json.dumps(params)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (type, 'running', params_json, user_id))
        process_id = cursor.lastrowid
        conn.commit()
    
    logger.info(f"Created process {process_id}: type={type}")
    
    return process_id


def get_process(process_id: int) -> Optional[Dict]:
    """
    Get process information
    
    Args:
        process_id: Process ID
        
    Returns:
        dict: Process info or None
    """
    query = """
        SELECT * FROM indexer_processes
        WHERE id = ?
    """
    
    return execute_query(query, (process_id,), fetch_one=True)


def update_process_status(process_id: int, status: str, error_message: Optional[str] = None):
    """
    Update process status
    
    Args:
        process_id: Process ID
        status: New status
        error_message: Optional error message
    """
    query = """
        UPDATE indexer_processes
        SET status = ?, completed_at = ?, error_message = ?
        WHERE id = ?
    """
    
    completed_at = datetime.now().isoformat() if status in ('completed', 'failed', 'stopped') else None
    
    execute_query(query, (status, completed_at, error_message, process_id))


def update_process_progress(process_id: int, progress: Dict):
    """
    Update process progress
    
    Args:
        process_id: Process ID
        progress: Progress dict
    """
    query = """
        UPDATE indexer_processes
        SET progress = ?
        WHERE id = ?
    """
    
    progress_json = json.dumps(progress)
    execute_query(query, (progress_json, process_id))


def list_processes(
    status: Optional[str] = None,
    type: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """
    List processes with optional filters
    
    Args:
        status: Filter by status
        type: Filter by type
        user_id: Filter by user ID
        limit: Maximum results
        offset: Offset for pagination
        
    Returns:
        list: List of processes
    """
    conditions = []
    params = []
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    if type:
        conditions.append("type = ?")
        params.append(type)
    
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    query = f"""
        SELECT * FROM indexer_processes
        {where_clause}
        ORDER BY started_at DESC
        LIMIT ? OFFSET ?
    """
    
    params.extend([limit, offset])
    
    return execute_query(query, tuple(params), fetch_all=True)


def get_process_status(process_id: int) -> Optional[str]:
    """
    Get process status
    
    Args:
        process_id: Process ID
        
    Returns:
        str: Process status or None
    """
    query = "SELECT status FROM indexer_processes WHERE id = ?"
    result = execute_query(query, (process_id,), fetch_one=True)
    
    return result['status'] if result else None


def mark_process_stopped(process_id: int):
    """
    Mark process as stopped
    
    Args:
        process_id: Process ID
    """
    query = """
        UPDATE indexer_processes
        SET status = 'stopped', completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """
    execute_query(query, (process_id,))


def delete_old_processes(retention_days: int) -> int:
    """
    Delete processes older than retention_days with status completed, failed, or stopped
    
    Args:
        retention_days: Number of days to retain processes
        
    Returns:
        int: Number of deleted processes
    """
    query = """
        DELETE FROM indexer_processes
        WHERE status IN ('completed', 'failed', 'stopped')
        AND (
            (completed_at IS NOT NULL AND datetime(completed_at) < datetime('now', '-' || ? || ' days'))
            OR (completed_at IS NULL AND datetime(started_at) < datetime('now', '-' || ? || ' days'))
        )
    """
    
    result = execute_query(query, (str(retention_days), str(retention_days)))
    logger.info(f"Deleted {result} old processes (retention: {retention_days} days)")
    return result


def get_all_process_ids() -> List[int]:
    """
    Get all existing process IDs from database
    
    Returns:
        List[int]: List of process IDs
    """
    query = "SELECT id FROM indexer_processes"
    results = execute_query(query, fetch_all=True)
    return [row['id'] for row in results] if results else []

