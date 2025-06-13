#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from dotenv import load_dotenv
from pathlib import Path

def load_settings():
    """
    Load environment settings from .env file.
    If .env file doesn't exist, create one with default values.
    """
    # Get the root directory of the project
    root_dir = Path(__file__).parent.parent
    env_path = root_dir / '.env'
    
    # Check if .env file exists
    if not env_path.exists():
        create_default_env(env_path)
        
    # Load environment variables from .env file
    load_dotenv(env_path)
    
    # Log settings loaded
    logging.info("Settings loaded from %s", env_path)
    
def create_default_env(env_path):
    """
    Create a default .env file with basic settings.
    
    Args:
        env_path (Path): Path to the .env file
    """
    default_env = """# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=draft_box

# API配置
API_BASE_URL=https://api.example.com
API_TIMEOUT=30
API_RETRY_COUNT=3

# 下载配置
DOWNLOAD_CONCURRENT_COUNT=5
DOWNLOAD_CHUNK_SIZE=8192
DOWNLOAD_TIMEOUT=300

# 同步配置
SYNC_INTERVAL_SECONDS=10
SYNC_RETRY_COUNT=3

# 应用配置
APP_NAME=草稿箱管理系统
APP_VERSION=1.0.0
LOG_LEVEL=INFO
LOG_FILE=app.log

# 界面配置
WINDOW_WIDTH=1200
WINDOW_HEIGHT=800
WINDOW_MIN_WIDTH=800
WINDOW_MIN_HEIGHT=600
THEME=light
AUTO_SAVE_WINDOW_STATE=true

# 异常处理配置
SHOW_DETAILED_ERRORS=true
AUTO_REPORT_ERRORS=false
ERROR_LOG_MAX_SIZE=10MB
ERROR_LOG_BACKUP_COUNT=5

# 用户体验配置
ENABLE_SOUND_NOTIFICATIONS=true
ENABLE_SYSTEM_TRAY=true
MINIMIZE_TO_TRAY=true
CONFIRM_EXIT=true
AUTO_CHECK_UPDATES=false
"""
    # Write default settings to .env file
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(default_env)
    
    logging.info("Created default .env file at %s", env_path)

def get_setting(key, default=None):
    """
    Get a setting from environment variables.
    
    Args:
        key (str): The environment variable key
        default: Default value if key doesn't exist
        
    Returns:
        The value of the environment variable or the default value
    """
    return os.getenv(key, default)

def get_int_setting(key, default=0):
    """
    Get an integer setting from environment variables.
    
    Args:
        key (str): The environment variable key
        default (int): Default value if key doesn't exist or isn't an integer
        
    Returns:
        int: The value of the environment variable as an integer or the default value
    """
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default

def get_bool_setting(key, default=False):
    """
    Get a boolean setting from environment variables.
    
    Args:
        key (str): The environment variable key
        default (bool): Default value if key doesn't exist
        
    Returns:
        bool: The value of the environment variable as a boolean or the default value
    """
    value = os.getenv(key, str(default)).lower()
    return value in ('true', 'yes', '1', 'y', 't') 