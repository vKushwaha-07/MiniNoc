"""
Logging Configuration for Mini NOC.
Provides structured logging for all monitoring operations.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import settings, BASE_DIR


# Log directory
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    Create a configured logger instance.
    
    Args:
        name: Logger name (usually module name)
        log_file: Optional log file name
        level: Logging level
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_path = LOG_DIR / log_file
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Pre-configured loggers for different modules
main_logger = setup_logger("mini_noc", "mini_noc.log")
scan_logger = setup_logger("scanner", "scanner.log")
alert_logger = setup_logger("alerts", "alerts.log")
api_logger = setup_logger("api", "api.log")
