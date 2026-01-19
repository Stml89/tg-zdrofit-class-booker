"""Logging configuration module."""

import logging
import os
from pathlib import Path
from config.config import LOG_LEVEL, LOG_DIR

# Create logs directory if it doesn't exist
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

# Configure logging
def get_logger(name: str) -> logging.Logger:
    """Get configured logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Avoid duplicate handlers
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, LOG_LEVEL))
        
        # File handler
        file_handler = logging.FileHandler(
            os.path.join(LOG_DIR, "zdrofit_bot.log")
        )
        file_handler.setLevel(getattr(logging, LOG_LEVEL))
        
        # Formatter with user_id tracking
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] '
            '[user_id:%(user_id)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            defaults={'user_id': 'system'}
        )
        
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger
