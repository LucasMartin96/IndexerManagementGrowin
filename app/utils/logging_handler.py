"""
Custom logging handler for indexer processes
Stores logs in memory buffers per process_id for real-time retrieval
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
import threading

logger = logging.getLogger(__name__)

# Global log buffers: {process_id: deque of log entries}
_log_buffers: Dict[int, deque] = {}
_buffer_lock = threading.Lock()
MAX_LOG_BUFFER_SIZE = 1000  # Max logs per process

class ProcessLogHandler(logging.Handler):
    """
    Custom logging handler that stores logs in memory buffers
    """
    
    def __init__(self, process_id: int):
        super().__init__()
        self.process_id = process_id
        
        # Initialize buffer for this process
        with _buffer_lock:
            if process_id not in _log_buffers:
                _log_buffers[process_id] = deque(maxlen=MAX_LOG_BUFFER_SIZE)
                logger.info(f"Initialized log buffer for process {process_id}")
    
    def emit(self, record):
        """Emit a log record to the buffer"""
        try:
            # Format log entry - message is already formatted by the formatter
            message = record.getMessage()
            if record.exc_info:
                # Include exception info if present
                import traceback
                message += "\n" + "".join(traceback.format_exception(*record.exc_info))
            
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'message': message,
                'process_id': self.process_id
            }
            
            # Add to buffer
            with _buffer_lock:
                if self.process_id not in _log_buffers:
                    _log_buffers[self.process_id] = deque(maxlen=MAX_LOG_BUFFER_SIZE)
                _log_buffers[self.process_id].append(log_entry)
                # Debug: log to root logger that we captured a log
                logger.info(f"[DEBUG] ProcessLogHandler captured log for process {self.process_id}: {message[:50]}...")
        except Exception as e:
            # Don't let logging errors break the app
            logger.error(f"Error in ProcessLogHandler.emit: {e}")

def get_process_logs(process_id: int, since_timestamp: Optional[str] = None) -> List[Dict]:
    """
    Get logs for a process since given timestamp
    
    Args:
        process_id: Process ID
        since_timestamp: Optional ISO timestamp to filter logs (returns logs after this time)
        
    Returns:
        list: List of log entries
    """
    with _buffer_lock:
        if process_id not in _log_buffers:
            return []
        
        logs = list(_log_buffers[process_id])
    
    # Filter by timestamp if provided
    if since_timestamp:
        try:
            since_dt = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
            filtered_logs = []
            for log in logs:
                log_dt = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                if log_dt > since_dt:
                    filtered_logs.append(log)
            return filtered_logs
        except Exception as e:
            logger.warning(f"Error filtering logs by timestamp: {e}")
            return logs
    
    return logs

def clear_process_logs(process_id: int):
    """Clear logs for a process"""
    with _buffer_lock:
        if process_id in _log_buffers:
            _log_buffers[process_id].clear()

def remove_process_logs(process_id: int):
    """Remove log buffer for a process (cleanup)"""
    with _buffer_lock:
        if process_id in _log_buffers:
            del _log_buffers[process_id]


def get_all_buffer_process_ids() -> List[int]:
    """
    Get list of all process IDs that have active log buffers
    
    Returns:
        List[int]: List of process IDs with active buffers
    """
    with _buffer_lock:
        return list(_log_buffers.keys())

