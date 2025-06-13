#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import time
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from config.settings import get_int_setting
from models.download_task import DownloadTask
from services.api_service import APIService
from utils.file_utils import ensure_dir, get_free_space

class DownloadService(QObject):
    """Service for managing file downloads"""
    
    # Signals
    task_progress = pyqtSignal(str, int)  # task_id, progress
    task_started = pyqtSignal(str)  # task_id
    task_completed = pyqtSignal(str)  # task_id
    task_failed = pyqtSignal(str, str)  # task_id, error_message
    task_paused = pyqtSignal(str)  # task_id
    all_tasks_completed = pyqtSignal()
    
    # Status constants
    STATUS_QUEUED = 'queued'
    STATUS_DOWNLOADING = 'downloading'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_PAUSED = 'paused'
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(DownloadService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the download service"""
        if self._initialized:
            return
            
        super().__init__()
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        
        # Get download configuration from environment variables
        self.concurrent_count = get_int_setting('DOWNLOAD_CONCURRENT_COUNT', 5)
        self.chunk_size = get_int_setting('DOWNLOAD_CHUNK_SIZE', 8192)
        self.timeout = get_int_setting('DOWNLOAD_TIMEOUT', 300)
        
        # Initialize task storage
        self.tasks = {}  # task_id -> DownloadTask
        self.active_tasks = set()  # Set of active task IDs
        self.queued_tasks = []  # List of queued task IDs
        self.completed_tasks = []  # List of completed task IDs
        self.failed_tasks = []  # List of failed task IDs
        self.paused_tasks = []  # List of paused task IDs
        
        # Create thread pool
        self.executor = ThreadPoolExecutor(max_workers=self.concurrent_count)
        self.futures = {}  # task_id -> Future
        
        # API service
        self.api_service = APIService()
        
        self.logger.info("Download service initialized with %s concurrent downloads", self.concurrent_count)
        
    def add_task(self, task: DownloadTask) -> str:
        """
        Add a download task
        
        Args:
            task (DownloadTask): Download task
            
        Returns:
            str: Task ID
        """
        self.logger.debug("Adding download task: %s", task.task_id)
        
        # Store the task
        self.tasks[task.task_id] = task
        
        # Add to queued tasks
        if task.status == self.STATUS_QUEUED:
            self.queued_tasks.append(task.task_id)
            
        # Start the task if we have capacity
        if len(self.active_tasks) < self.concurrent_count and task.status == self.STATUS_QUEUED:
            self._start_task(task.task_id)
            
        return task.task_id
        
    def add_tasks(self, tasks: List[DownloadTask]) -> List[str]:
        """
        Add multiple download tasks
        
        Args:
            tasks (List[DownloadTask]): List of download tasks
            
        Returns:
            List[str]: List of task IDs
        """
        task_ids = []
        for task in tasks:
            task_id = self.add_task(task)
            task_ids.append(task_id)
            
        return task_ids
        
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """
        Get a download task
        
        Args:
            task_id (str): Task ID
            
        Returns:
            DownloadTask: Download task, or None if not found
        """
        return self.tasks.get(task_id)
        
    def get_tasks_by_draft(self, draft_uuid: str) -> List[DownloadTask]:
        """
        Get all download tasks for a draft
        
        Args:
            draft_uuid (str): Draft UUID
            
        Returns:
            List[DownloadTask]: List of download tasks
        """
        return [task for task in self.tasks.values() if task.draft_uuid == draft_uuid]
        
    def get_all_tasks(self) -> List[DownloadTask]:
        """
        Get all download tasks
        
        Returns:
            List[DownloadTask]: List of all download tasks
        """
        return list(self.tasks.values())
        
    def pause_task(self, task_id: str) -> bool:
        """
        Pause a download task
        
        Args:
            task_id (str): Task ID
            
        Returns:
            bool: True if the task was paused, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            self.logger.warning("Cannot pause task %s: Task not found", task_id)
            return False
            
        # Can only pause active tasks
        if task_id not in self.active_tasks:
            self.logger.warning("Cannot pause task %s: Task is not active", task_id)
            return False
            
        # Cancel the future
        if task_id in self.futures:
            self.futures[task_id].cancel()
            del self.futures[task_id]
            
        # Update task status
        task.status = self.STATUS_PAUSED
        self.active_tasks.remove(task_id)
        self.paused_tasks.append(task_id)
        
        # Emit signal
        self.task_paused.emit(task_id)
        
        # Start next task if there are queued tasks
        if self.queued_tasks:
            next_task_id = self.queued_tasks[0]
            self._start_task(next_task_id)
            
        return True
        
    def resume_task(self, task_id: str) -> bool:
        """
        Resume a paused download task
        
        Args:
            task_id (str): Task ID
            
        Returns:
            bool: True if the task was resumed, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            self.logger.warning("Cannot resume task %s: Task not found", task_id)
            return False
            
        # Can only resume paused tasks
        if task.status != self.STATUS_PAUSED:
            self.logger.warning("Cannot resume task %s: Task is not paused", task_id)
            return False
            
        # Update task status
        task.status = self.STATUS_QUEUED
        self.paused_tasks.remove(task_id)
        self.queued_tasks.append(task_id)
        
        # Start the task if we have capacity
        if len(self.active_tasks) < self.concurrent_count:
            self._start_task(task_id)
            
        return True
        
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a download task
        
        Args:
            task_id (str): Task ID
            
        Returns:
            bool: True if the task was cancelled, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            self.logger.warning("Cannot cancel task %s: Task not found", task_id)
            return False
            
        # Cancel the future if the task is active
        if task_id in self.active_tasks and task_id in self.futures:
            self.futures[task_id].cancel()
            del self.futures[task_id]
            self.active_tasks.remove(task_id)
            
        # Remove from queued/paused tasks
        if task_id in self.queued_tasks:
            self.queued_tasks.remove(task_id)
        if task_id in self.paused_tasks:
            self.paused_tasks.remove(task_id)
            
        # Delete the task
        del self.tasks[task_id]
        
        # Start next task if there are queued tasks
        if len(self.active_tasks) < self.concurrent_count and self.queued_tasks:
            next_task_id = self.queued_tasks[0]
            self._start_task(next_task_id)
            
        return True
        
    def retry_task(self, task_id: str) -> bool:
        """
        Retry a failed download task
        
        Args:
            task_id (str): Task ID
            
        Returns:
            bool: True if the task was retried, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            self.logger.warning("Cannot retry task %s: Task not found", task_id)
            return False
            
        # Can only retry failed tasks
        if task.status != self.STATUS_FAILED:
            self.logger.warning("Cannot retry task %s: Task is not failed", task_id)
            return False
            
        # Check if the task can be retried
        if not task.can_retry():
            self.logger.warning("Cannot retry task %s: Maximum retry count reached", task_id)
            return False
            
        # Update task status
        task.retry()
        self.failed_tasks.remove(task_id)
        self.queued_tasks.append(task_id)
        
        # Start the task if we have capacity
        if len(self.active_tasks) < self.concurrent_count:
            self._start_task(task_id)
            
        return True
        
    def _start_task(self, task_id: str) -> bool:
        """
        Start a download task
        
        Args:
            task_id (str): Task ID
            
        Returns:
            bool: True if the task was started, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            self.logger.warning("Cannot start task %s: Task not found", task_id)
            return False
            
        # Check if the task is queued
        if task.status != self.STATUS_QUEUED:
            self.logger.warning("Cannot start task %s: Task is not queued", task_id)
            return False
            
        # Check if we have capacity
        if len(self.active_tasks) >= self.concurrent_count:
            self.logger.warning("Cannot start task %s: Maximum concurrent downloads reached", task_id)
            return False
            
        # Update task status
        task.status = self.STATUS_DOWNLOADING
        self.queued_tasks.remove(task_id)
        self.active_tasks.add(task_id)
        
        # Emit signal
        self.task_started.emit(task_id)
        
        # Submit task to thread pool
        future = self.executor.submit(self._download_file, task)
        self.futures[task_id] = future
        
        return True
        
    def _download_file(self, task: DownloadTask) -> bool:
        """
        Download a file
        
        Args:
            task (DownloadTask): Download task
            
        Returns:
            bool: True if the download was successful, False otherwise
        """
        self.logger.info("Downloading file: %s", task.file_url)
        
        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(task.local_path)
            ensure_dir(directory)
            
            # Check disk space
            file_size = task.file_size
            free_space = get_free_space(directory)
            
            if file_size > free_space:
                error_msg = f"Not enough disk space. Required: {file_size}, Available: {free_space}"
                self._handle_task_failure(task, error_msg)
                return False
                
            # Start download
            with open(task.local_path, 'wb') as f:
                # Make request
                with self.api_service.session.get(
                    task.file_url,
                    stream=True,
                    timeout=self.timeout
                ) as response:
                    response.raise_for_status()
                    
                    # Get content length if not provided
                    if task.file_size <= 0 and 'content-length' in response.headers:
                        task.file_size = int(response.headers['content-length'])
                        
                    # Download the file in chunks
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                            task.downloaded_size += len(chunk)
                            
                            # Update progress
                            progress = task.get_progress()
                            self.task_progress.emit(task.task_id, progress)
                            
            # Mark task as completed
            task.mark_completed()
            self.active_tasks.remove(task.task_id)
            self.completed_tasks.append(task.task_id)
            
            # Emit signal
            self.task_completed.emit(task.task_id)
            
            # Start next task if there are queued tasks
            if self.queued_tasks:
                next_task_id = self.queued_tasks[0]
                self._start_task(next_task_id)
                
            # Check if all tasks are completed
            if not self.active_tasks and not self.queued_tasks:
                self.all_tasks_completed.emit()
                
            return True
                
        except Exception as e:
            self._handle_task_failure(task, str(e))
            return False
            
    def _handle_task_failure(self, task: DownloadTask, error_message: str):
        """
        Handle task failure
        
        Args:
            task (DownloadTask): Download task
            error_message (str): Error message
        """
        self.logger.error("Download task %s failed: %s", task.task_id, error_message)
        
        # Mark task as failed
        task.mark_failed(error_message)
        
        # Update task lists
        self.active_tasks.remove(task.task_id)
        self.failed_tasks.append(task.task_id)
        
        # Emit signal
        self.task_failed.emit(task.task_id, error_message)
        
        # Start next task if there are queued tasks
        if self.queued_tasks:
            next_task_id = self.queued_tasks[0]
            self._start_task(next_task_id)
            
    def create_tasks_for_draft(self, draft_uuid: str, files: List[Dict[str, Any]], base_path: str) -> List[str]:
        """
        Create download tasks for all files in a draft
        
        Args:
            draft_uuid (str): Draft UUID
            files (List[Dict[str, Any]]): List of file data
            base_path (str): Base path for saving files
            
        Returns:
            List[str]: List of task IDs
        """
        tasks = []
        
        for file_data in files:
            file_path = file_data.get('path', '')
            file_url = file_data.get('url', '')
            file_size = file_data.get('size', 0)
            
            if not file_url:
                self.logger.warning("Skipping file with no URL: %s", file_path)
                continue
                
            # Create local path
            local_path = os.path.join(base_path, file_path)
            
            # Create task
            task = DownloadTask.create(
                draft_uuid=draft_uuid,
                file_url=file_url,
                local_path=local_path,
                file_size=file_size
            )
            
            tasks.append(task)
            
        # Add tasks
        task_ids = self.add_tasks(tasks)
        
        return task_ids
        
    def get_draft_progress(self, draft_uuid: str) -> int:
        """
        Get the overall progress for a draft
        
        Args:
            draft_uuid (str): Draft UUID
            
        Returns:
            int: Progress percentage (0-100)
        """
        tasks = self.get_tasks_by_draft(draft_uuid)
        
        if not tasks:
            return 0
            
        total_size = sum(task.file_size for task in tasks)
        downloaded_size = sum(task.downloaded_size for task in tasks)
        
        if total_size <= 0:
            return 0
            
        progress = (downloaded_size / total_size) * 100
        return min(int(progress), 100)
        
    def get_draft_status(self, draft_uuid: str) -> str:
        """
        Get the overall status for a draft
        
        Args:
            draft_uuid (str): Draft UUID
            
        Returns:
            str: Status (queued, downloading, completed, failed, paused)
        """
        tasks = self.get_tasks_by_draft(draft_uuid)
        
        if not tasks:
            return self.STATUS_COMPLETED
            
        # If any task is downloading, the draft is downloading
        if any(task.status == self.STATUS_DOWNLOADING for task in tasks):
            return self.STATUS_DOWNLOADING
            
        # If any task is queued, the draft is queued
        if any(task.status == self.STATUS_QUEUED for task in tasks):
            return self.STATUS_QUEUED
            
        # If any task is paused, the draft is paused
        if any(task.status == self.STATUS_PAUSED for task in tasks):
            return self.STATUS_PAUSED
            
        # If any task is failed, the draft is failed
        if any(task.status == self.STATUS_FAILED for task in tasks):
            return self.STATUS_FAILED
            
        # If all tasks are completed, the draft is completed
        return self.STATUS_COMPLETED 