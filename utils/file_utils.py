#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import logging
import hashlib
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

def ensure_dir(directory: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary
    
    Args:
        directory (str): Directory path
        
    Returns:
        bool: True if the directory exists or was created, False otherwise
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error("Failed to create directory %s: %s", directory, e)
        return False

def get_free_space(path: str) -> int:
    """
    Get the free space on the disk containing the path
    
    Args:
        path (str): Path to check
        
    Returns:
        int: Free space in bytes
    """
    try:
        if os.path.isdir(path):
            directory = path
        else:
            directory = os.path.dirname(path)
            
        if not os.path.exists(directory):
            # Try to get the free space of the parent directory
            parent = os.path.dirname(directory)
            if not parent or parent == directory:
                # We've reached the root directory
                return 0
            return get_free_space(parent)
            
        return shutil.disk_usage(directory).free
    except Exception as e:
        logger.error("Failed to get free space for %s: %s", path, e)
        return 0

def get_file_size(file_path: str) -> int:
    """
    Get the size of a file
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        int: File size in bytes, or 0 if the file doesn't exist
    """
    try:
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return 0
    except Exception as e:
        logger.error("Failed to get file size for %s: %s", file_path, e)
        return 0

def calculate_file_hash(file_path: str, hash_type: str = 'md5', chunk_size: int = 8192) -> Optional[str]:
    """
    Calculate the hash of a file
    
    Args:
        file_path (str): Path to the file
        hash_type (str): Hash algorithm to use (md5, sha1, sha256)
        chunk_size (int): Size of chunks to read
        
    Returns:
        str: File hash, or None if the file doesn't exist or an error occurred
    """
    try:
        if not os.path.exists(file_path):
            logger.warning("File does not exist: %s", file_path)
            return None
            
        hash_func = None
        if hash_type.lower() == 'md5':
            hash_func = hashlib.md5()
        elif hash_type.lower() == 'sha1':
            hash_func = hashlib.sha1()
        elif hash_type.lower() == 'sha256':
            hash_func = hashlib.sha256()
        else:
            logger.error("Unsupported hash type: %s", hash_type)
            return None
            
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hash_func.update(chunk)
                
        return hash_func.hexdigest()
    except Exception as e:
        logger.error("Failed to calculate hash for %s: %s", file_path, e)
        return None

def is_path_writable(path: str) -> bool:
    """
    Check if a path is writable
    
    Args:
        path (str): Path to check
        
    Returns:
        bool: True if the path is writable, False otherwise
    """
    try:
        if os.path.exists(path):
            # Path exists, check if it's writable
            return os.access(path, os.W_OK)
        else:
            # Path doesn't exist, check if the parent directory is writable
            parent = os.path.dirname(path)
            if not parent:
                # We've reached the root directory
                return False
            return is_path_writable(parent)
    except Exception as e:
        logger.error("Failed to check if path is writable %s: %s", path, e)
        return False

def clean_directory(directory: str, exclude_patterns: List[str] = None) -> Tuple[int, int]:
    """
    Clean a directory by removing all files and subdirectories
    
    Args:
        directory (str): Directory to clean
        exclude_patterns (List[str], optional): List of patterns to exclude
        
    Returns:
        Tuple[int, int]: Number of files and directories removed
    """
    if exclude_patterns is None:
        exclude_patterns = []
        
    files_removed = 0
    dirs_removed = 0
    
    try:
        if not os.path.exists(directory):
            logger.warning("Directory does not exist: %s", directory)
            return files_removed, dirs_removed
            
        for root, dirs, files in os.walk(directory, topdown=False):
            # Remove files
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if the file should be excluded
                exclude = False
                for pattern in exclude_patterns:
                    if pattern in file_path:
                        exclude = True
                        break
                        
                if not exclude:
                    try:
                        os.remove(file_path)
                        files_removed += 1
                    except Exception as e:
                        logger.error("Failed to remove file %s: %s", file_path, e)
                        
            # Remove directories
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                
                # Check if the directory should be excluded
                exclude = False
                for pattern in exclude_patterns:
                    if pattern in dir_path:
                        exclude = True
                        break
                        
                if not exclude:
                    try:
                        os.rmdir(dir_path)
                        dirs_removed += 1
                    except Exception as e:
                        logger.error("Failed to remove directory %s: %s", dir_path, e)
                        
        return files_removed, dirs_removed
    except Exception as e:
        logger.error("Failed to clean directory %s: %s", directory, e)
        return files_removed, dirs_removed 