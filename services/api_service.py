#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import json
import time
import socket
import requests
from requests.exceptions import RequestException
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

from config.settings import get_setting, get_int_setting

class APIService:
    """Service for interacting with the backend API"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(APIService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the API service"""
        if self._initialized:
            return
            
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        
        # Get API configuration from environment variables
        self.base_url = get_setting('API_BASE_URL', 'https://api.example.com')
        self.timeout = get_int_setting('API_TIMEOUT', 30)
        self.retry_count = get_int_setting('API_RETRY_COUNT', 3)
        
        # Create a session for connection pooling
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': f'DraftBoxManager/{get_setting("APP_VERSION", "1.0.0")}'
        })
        
        self.logger.info("API service initialized with base URL: %s", self.base_url)
        
    def _get_machine_name(self):
        """
        Get the current machine name
        
        Returns:
            str: Machine name
        """
        return socket.gethostname()
        
    def _make_request(self, method, endpoint, params=None, data=None, headers=None, retry=0):
        """
        Make an HTTP request to the API
        
        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            endpoint (str): API endpoint
            params (dict, optional): Query parameters
            data (dict, optional): Request body
            headers (dict, optional): Additional headers
            retry (int, optional): Current retry count
            
        Returns:
            dict: Response data
            
        Raises:
            RequestException: If the request fails
        """
        url = urljoin(self.base_url, endpoint)
        
        # Merge headers
        request_headers = {}
        if headers:
            request_headers.update(headers)
            
        # Convert data to JSON if it's a dict
        json_data = None
        if data and isinstance(data, dict):
            json_data = data
            
        try:
            self.logger.debug("Making %s request to %s", method, url)
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=request_headers,
                timeout=self.timeout
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse JSON response
            if response.content:
                return response.json()
            return {}
            
        except RequestException as e:
            self.logger.error("API request failed: %s", e)
            
            # Retry if we haven't reached the maximum retry count
            if retry < self.retry_count:
                # Exponential backoff
                wait_time = 2 ** retry
                self.logger.info("Retrying in %s seconds (retry %s/%s)", wait_time, retry + 1, self.retry_count)
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, data, headers, retry + 1)
                
            # If we've reached the maximum retry count, re-raise the exception
            raise
            
    def get_draft_by_uuid(self, uuid: str) -> Dict[str, Any]:
        """
        Get a draft by UUID
        
        Args:
            uuid (str): Draft UUID
            
        Returns:
            dict: Draft data
            
        Raises:
            RequestException: If the request fails
        """
        endpoint = f'/drafts/{uuid}'
        return self._make_request('GET', endpoint)
        
    def get_drafts(self, page: int = 1, page_size: int = 20, status: str = None) -> Dict[str, Any]:
        """
        Get a list of drafts
        
        Args:
            page (int, optional): Page number
            page_size (int, optional): Number of items per page
            status (str, optional): Filter by status
            
        Returns:
            dict: List of drafts and pagination info
            
        Raises:
            RequestException: If the request fails
        """
        endpoint = '/drafts'
        params = {
            'page': page,
            'page_size': page_size
        }
        
        if status:
            params['status'] = status
            
        return self._make_request('GET', endpoint, params=params)
        
    def save_draft(self, uuid: str, folder_path: str) -> Dict[str, Any]:
        """
        Save a draft to the local machine
        
        Args:
            uuid (str): Draft UUID
            folder_path (str): Local folder path
            
        Returns:
            dict: Result of the operation
            
        Raises:
            RequestException: If the request fails
        """
        endpoint = '/drafts/save'
        data = {
            'uuid': uuid,
            'machine_name': self._get_machine_name(),
            'local_path': folder_path
        }
        
        return self._make_request('POST', endpoint, data=data)
        
    def update_draft_status(self, uuid: str, status: str, progress: int = None, error_message: str = None) -> Dict[str, Any]:
        """
        Update the status of a draft
        
        Args:
            uuid (str): Draft UUID
            status (str): New status
            progress (int, optional): Download progress (0-100)
            error_message (str, optional): Error message if status is 'failed'
            
        Returns:
            dict: Result of the operation
            
        Raises:
            RequestException: If the request fails
        """
        endpoint = f'/drafts/{uuid}/status'
        data = {
            'status': status,
            'machine_name': self._get_machine_name()
        }
        
        if progress is not None:
            data['progress'] = progress
            
        if error_message:
            data['error_message'] = error_message
            
        return self._make_request('PUT', endpoint, data=data)
        
    def get_draft_files(self, uuid: str) -> List[Dict[str, Any]]:
        """
        Get the list of files in a draft
        
        Args:
            uuid (str): Draft UUID
            
        Returns:
            list: List of file data
            
        Raises:
            RequestException: If the request fails
        """
        endpoint = f'/drafts/{uuid}/files'
        response = self._make_request('GET', endpoint)
        return response.get('files', [])
        
    def get_file_download_url(self, uuid: str, file_path: str) -> str:
        """
        Get the download URL for a file
        
        Args:
            uuid (str): Draft UUID
            file_path (str): Path of the file within the draft
            
        Returns:
            str: Download URL
            
        Raises:
            RequestException: If the request fails
        """
        endpoint = f'/drafts/{uuid}/files/download'
        params = {
            'file_path': file_path
        }
        
        response = self._make_request('GET', endpoint, params=params)
        return response.get('download_url', '') 