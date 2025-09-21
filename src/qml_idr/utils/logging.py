"""Logging utilities for the QML-IDR project."""

import logging
import sys
from pathlib import Path
from typing import Optional
from .config import get_config


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        format_string: Log message format
        
    Returns:
        Configured logger
    """
    config = get_config()
    
    # Use config defaults if not provided
    level = level or config.logging.level
    log_file = log_file or config.logging.file
    format_string = format_string or config.logging.format
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file) if log_file else logging.NullHandler(),
        ]
    )
    
    # Create project logger
    logger = logging.getLogger("qml_idr")
    logger.info(f"Logging initialized at level {level}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"qml_idr.{name}")


# Progress tracking utilities
class ProgressLogger:
    """Logger with progress tracking capabilities."""
    
    def __init__(self, logger: logging.Logger, total_steps: int):
        self.logger = logger
        self.total_steps = total_steps
        self.current_step = 0
    
    def step(self, message: str = "") -> None:
        """Log progress step."""
        self.current_step += 1
        progress = (self.current_step / self.total_steps) * 100
        
        log_msg = f"Progress: {self.current_step}/{self.total_steps} ({progress:.1f}%)"
        if message:
            log_msg += f" - {message}"
        
        self.logger.info(log_msg)
    
    def reset(self) -> None:
        """Reset progress counter."""
        self.current_step = 0