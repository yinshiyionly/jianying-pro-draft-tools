#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import mysql.connector
from mysql.connector import pooling
import logging
from config.settings import get_setting

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