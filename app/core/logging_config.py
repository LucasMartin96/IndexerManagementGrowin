"""
Logging configuration
"""

import logging
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure application logging
    
    Args:
        level: Logging level as string (e.g., 'INFO', 'DEBUG') or None for default INFO
    """
    if level is None:
        log_level = logging.INFO
    elif isinstance(level, str):
        log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        # If it's already an integer (logging constant), use it directly
        log_level = level if isinstance(level, int) else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

