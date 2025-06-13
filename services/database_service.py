#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import mysql.connector
from mysql.connector import pooling
from typing import List, Dict, Any, Optional, Tuple

from config.settings import get_setting, get_int_setting

class DatabasePool:
    """Database connection pool manager"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(DatabasePool, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the database connection pool"""
        if self._initialized:
            return
            
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        
        # Get database configuration from environment variables
        self.db_config = {
            'host': get_setting('DB_HOST', 'localhost'),
            'port': int(get_setting('DB_PORT', 3306)),
            'user': get_setting('DB_USER', 'root'),
            'password': get_setting('DB_PASSWORD', ''),
            'database': get_setting('DB_NAME', 'draft_box'),
            'use_pure': True,
            'autocommit': True,
            'pool_size': 5
        }
        
        try:
            # Create connection pool
            self.pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="draft_box_pool",
                **self.db_config
            )
            self.logger.info("Database connection pool initialized")
            
            # Initialize database schema if needed
            self._initialize_schema()
        except mysql.connector.Error as err:
            self.logger.error("Failed to create database connection pool: %s", err)
            self.pool = None
    
    def get_connection(self):
        """
        Get a connection from the pool
        
        Returns:
            mysql.connector.connection.MySQLConnection: Database connection
        
        Raises:
            mysql.connector.Error: If connection cannot be established
        """
        if self.pool is None:
            self.logger.error("Connection pool is not initialized")
            raise mysql.connector.Error("Database connection pool is not initialized")
            
        try:
            connection = self.pool.get_connection()
            return connection
        except mysql.connector.Error as err:
            self.logger.error("Failed to get connection from pool: %s", err)
            raise
    
    def execute_query(self, query, params=None, fetch=True):
        """
        Execute a SQL query and return the results
        
        Args:
            query (str): SQL query to execute
            params (tuple, optional): Parameters for the query
            fetch (bool, optional): Whether to fetch results
            
        Returns:
            list: Query results if fetch is True, else None
            
        Raises:
            mysql.connector.Error: If query execution fails
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            
            if fetch:
                return cursor.fetchall()
            return None
        except mysql.connector.Error as err:
            self.logger.error("Failed to execute query: %s", err)
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def execute_many(self, query, params_list):
        """
        Execute a SQL query with multiple parameter sets
        
        Args:
            query (str): SQL query to execute
            params_list (list): List of parameter tuples
            
        Raises:
            mysql.connector.Error: If query execution fails
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.executemany(query, params_list)
            connection.commit()
        except mysql.connector.Error as err:
            self.logger.error("Failed to execute batch query: %s", err)
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
                
    def test_connection(self):
        """
        Test the database connection
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            self.logger.error("Database connection test failed: %s", e)
            return False
            
    def _initialize_schema(self):
        """
        Initialize database schema if needed
        """
        try:
            # Create drafts table
            drafts_table_query = """
                CREATE TABLE IF NOT EXISTS drafts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    file_count INT NOT NULL DEFAULT 0,
                    total_size BIGINT NOT NULL DEFAULT 0,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    machine_name VARCHAR(255) NOT NULL,
                    local_path VARCHAR(255) NOT NULL,
                    error_message TEXT,
                    progress INT NOT NULL DEFAULT 0,
                    INDEX idx_uuid (uuid),
                    INDEX idx_status (status),
                    INDEX idx_machine_name (machine_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            self.execute_query(drafts_table_query, fetch=False)
            
            # Create draft_files table
            draft_files_table_query = """
                CREATE TABLE IF NOT EXISTS draft_files (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    draft_uuid VARCHAR(36) NOT NULL,
                    file_path VARCHAR(255) NOT NULL,
                    file_url VARCHAR(255) NOT NULL,
                    file_size BIGINT NOT NULL DEFAULT 0,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    FOREIGN KEY (draft_uuid) REFERENCES drafts(uuid) ON DELETE CASCADE,
                    INDEX idx_draft_uuid (draft_uuid)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            self.execute_query(draft_files_table_query, fetch=False)
            
            # Create download_tasks table
            download_tasks_table_query = """
                CREATE TABLE IF NOT EXISTS download_tasks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    task_id VARCHAR(36) NOT NULL UNIQUE,
                    draft_uuid VARCHAR(36) NOT NULL,
                    file_url VARCHAR(255) NOT NULL,
                    local_path VARCHAR(255) NOT NULL,
                    file_size BIGINT NOT NULL DEFAULT 0,
                    downloaded_size BIGINT NOT NULL DEFAULT 0,
                    status VARCHAR(50) NOT NULL DEFAULT 'queued',
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    error_message TEXT,
                    retries INT NOT NULL DEFAULT 0,
                    max_retries INT NOT NULL DEFAULT 3,
                    FOREIGN KEY (draft_uuid) REFERENCES drafts(uuid) ON DELETE CASCADE,
                    INDEX idx_task_id (task_id),
                    INDEX idx_draft_uuid (draft_uuid),
                    INDEX idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            self.execute_query(download_tasks_table_query, fetch=False)
            
            self.logger.info("Database schema initialized")
        except mysql.connector.Error as err:
            self.logger.error("Failed to initialize database schema: %s", err)
            raise 