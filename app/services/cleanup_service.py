"""
Cleanup service for old processes and orphaned logs
"""

import logging
from typing import List
from app.repositories.process_repo import delete_old_processes, get_all_process_ids
from app.db.sqlite import vacuum_database
from app.utils.logging_handler import remove_process_logs, get_all_buffer_process_ids
from app.core.config import settings

logger = logging.getLogger(__name__)


def cleanup_old_processes(retention_days: int = None) -> int:
    """
    Clean up old processes from database
    
    Args:
        retention_days: Number of days to retain processes (defaults to settings.PROCESS_RETENTION_DAYS)
        
    Returns:
        int: Number of deleted processes
    """
    if retention_days is None:
        retention_days = settings.PROCESS_RETENTION_DAYS
    
    try:
        deleted_count = delete_old_processes(retention_days)
        logger.info(f"Cleanup: Deleted {deleted_count} old processes (retention: {retention_days} days)")
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to cleanup old processes: {str(e)}")
        raise


def cleanup_orphaned_logs() -> int:
    """
    Clean up log buffers in memory for processes that no longer exist in database
    
    Returns:
        int: Number of orphaned log buffers removed
    """
    try:
        # Get all existing process IDs from database
        existing_process_ids = set(get_all_process_ids())
        
        # Get all process IDs that have active log buffers
        buffer_process_ids = set(get_all_buffer_process_ids())
        
        # Find orphaned buffers (buffers for processes that no longer exist in DB)
        orphaned_process_ids = buffer_process_ids - existing_process_ids
        
        # Remove orphaned buffers
        for process_id in orphaned_process_ids:
            remove_process_logs(process_id)
        
        if orphaned_process_ids:
            logger.info(f"Cleanup: Removed {len(orphaned_process_ids)} orphaned log buffers")
        
        return len(orphaned_process_ids)
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned logs: {str(e)}")
        return 0


def run_cleanup():
    """
    Run full cleanup: old processes, orphaned logs, and database optimization
    """
    try:
        logger.info("Starting cleanup process...")
        
        # Clean up old processes
        deleted_processes = cleanup_old_processes()
        
        # Clean up orphaned logs (basic version)
        removed_logs = cleanup_orphaned_logs()
        
        # Optimize database
        vacuum_database()
        
        logger.info(f"Cleanup completed: {deleted_processes} processes deleted, {removed_logs} orphaned log buffers removed")
        
    except Exception as e:
        logger.error(f"Cleanup process failed: {str(e)}")
        raise

