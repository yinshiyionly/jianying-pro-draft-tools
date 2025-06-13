#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid

@dataclass
class DownloadTask:
    """
    Data model for a download task
    """
    task_id: str
    draft_uuid: str
    file_url: str
    local_path: str
    file_size: int
    downloaded_size: int
    status: str  # queued, downloading, completed, failed, paused
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    
    @classmethod
    def create(cls, draft_uuid, file_url, local_path, file_size=0):
        """
        Create a new download task
        
        Args:
            draft_uuid (str): UUID of the draft
            file_url (str): URL of the file to download
            local_path (str): Local path to save the file
            file_size (int, optional): Size of the file in bytes
            
        Returns:
            DownloadTask: New download task
        """
        task_id = str(uuid.uuid4())
        return cls(
            task_id=task_id,
            draft_uuid=draft_uuid,
            file_url=file_url,
            local_path=local_path,
            file_size=file_size,
            downloaded_size=0,
            status='queued',
            start_time=datetime.now()
        )
        
    @classmethod
    def from_dict(cls, data):
        """
        Create a DownloadTask from a dictionary
        
        Args:
            data (dict): Dictionary containing task data
            
        Returns:
            DownloadTask: New DownloadTask instance
        """
        # Convert string dates to datetime objects
        start_time = data.get('start_time')
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            start_time = datetime.now()
            
        end_time = data.get('end_time')
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            end_time = None
            
        return cls(
            task_id=data.get('task_id', str(uuid.uuid4())),
            draft_uuid=data.get('draft_uuid', ''),
            file_url=data.get('file_url', ''),
            local_path=data.get('local_path', ''),
            file_size=data.get('file_size', 0),
            downloaded_size=data.get('downloaded_size', 0),
            status=data.get('status', 'queued'),
            start_time=start_time,
            end_time=end_time,
            error_message=data.get('error_message'),
            retries=data.get('retries', 0),
            max_retries=data.get('max_retries', 3)
        )
        
    def to_dict(self):
        """
        Convert the model to a dictionary
        
        Returns:
            dict: Dictionary representation of the model
        """
        result = {
            'task_id': self.task_id,
            'draft_uuid': self.draft_uuid,
            'file_url': self.file_url,
            'local_path': self.local_path,
            'file_size': self.file_size,
            'downloaded_size': self.downloaded_size,
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'retries': self.retries,
            'max_retries': self.max_retries
        }
        
        if self.end_time:
            result['end_time'] = self.end_time.isoformat()
            
        if self.error_message:
            result['error_message'] = self.error_message
            
        return result
        
    def get_progress(self):
        """
        Get the download progress as a percentage
        
        Returns:
            int: Progress percentage (0-100)
        """
        if self.file_size <= 0:
            return 0
            
        progress = (self.downloaded_size / self.file_size) * 100
        return min(int(progress), 100)
        
    def get_status_display(self):
        """
        Get a display-friendly status string
        
        Returns:
            str: Status string in Chinese
        """
        status_map = {
            'queued': '排队中',
            'downloading': '下载中',
            'completed': '已完成',
            'failed': '失败',
            'paused': '已暂停'
        }
        return status_map.get(self.status, self.status)
        
    def can_retry(self):
        """
        Check if the task can be retried
        
        Returns:
            bool: True if the task can be retried, False otherwise
        """
        return self.status == 'failed' and self.retries < self.max_retries
        
    def mark_completed(self):
        """Mark the task as completed"""
        self.status = 'completed'
        self.end_time = datetime.now()
        
    def mark_failed(self, error_message):
        """
        Mark the task as failed
        
        Args:
            error_message (str): Error message
        """
        self.status = 'failed'
        self.error_message = error_message
        self.end_time = datetime.now()
        
    def retry(self):
        """
        Retry the task
        
        Returns:
            bool: True if the task was retried, False if max retries reached
        """
        if self.retries >= self.max_retries:
            return False
            
        self.retries += 1
        self.status = 'queued'
        self.error_message = None
        return True 