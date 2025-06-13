#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from config.settings import get_setting

def setup_logger():
    """
    Setup application logger with file and console handlers
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Get log configuration from environment
    log_level_name = get_setting('LOG_LEVEL', 'INFO')
    log_file = get_setting('LOG_FILE', 'app.log')
    log_max_size = get_setting('ERROR_LOG_MAX_SIZE', '10MB')
    log_backup_count = int(get_setting('ERROR_LOG_BACKUP_COUNT', 5))
    
    # Convert log level string to logging constant
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Convert max size string to bytes
    if log_max_size.endswith('MB'):
        max_bytes = int(log_max_size[:-2]) * 1024 * 1024
    elif log_max_size.endswith('KB'):
        max_bytes = int(log_max_size[:-2]) * 1024
    else:
        max_bytes = int(log_max_size)
    
    # Create logs directory if it doesn't exist
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    log_file_path = logs_dir / log_file
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create file handler for rotating log files
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=log_backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info("Logger initialized with level %s", log_level_name)
    return logger

def get_logger(name):
    """
    Get a named logger for a specific module
    
    Args:
        name (str): Name of the logger, typically __name__
        
    Returns:
        logging.Logger: Named logger instance
    """
    return logging.getLogger(name) 