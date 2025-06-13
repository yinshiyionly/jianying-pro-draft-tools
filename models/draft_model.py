#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class DraftModel:
    """
    Data model for a draft box
    """
    id: int
    uuid: str
    name: str
    description: str
    file_count: int
    total_size: int
    status: str  # pending, downloading, completed, failed
    created_at: datetime
    updated_at: datetime
    machine_name: str
    local_path: str
    remote_urls: List[str]
    
    # Optional fields
    error_message: Optional[str] = None
    progress: Optional[int] = 0  # 0-100
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a DraftModel from a dictionary
        
        Args:
            data (dict): Dictionary containing draft data
            
        Returns:
            DraftModel: New DraftModel instance
        """
        # Convert string dates to datetime objects
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        else:
            created_at = datetime.now()
            
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        else:
            updated_at = datetime.now()
            
        # Extract remote URLs
        remote_urls = data.get('remote_urls', [])
        if isinstance(remote_urls, str):
            # Convert comma-separated string to list
            remote_urls = [url.strip() for url in remote_urls.split(',') if url.strip()]
            
        return cls(
            id=data.get('id', 0),
            uuid=data.get('uuid', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            file_count=data.get('file_count', 0),
            total_size=data.get('total_size', 0),
            status=data.get('status', 'pending'),
            created_at=created_at,
            updated_at=updated_at,
            machine_name=data.get('machine_name', ''),
            local_path=data.get('local_path', ''),
            remote_urls=remote_urls,
            error_message=data.get('error_message'),
            progress=data.get('progress', 0)
        )
        
    def to_dict(self):
        """
        Convert the model to a dictionary
        
        Returns:
            dict: Dictionary representation of the model
        """
        return {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'description': self.description,
            'file_count': self.file_count,
            'total_size': self.total_size,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'machine_name': self.machine_name,
            'local_path': self.local_path,
            'remote_urls': self.remote_urls,
            'error_message': self.error_message,
            'progress': self.progress
        }
        
    def get_status_display(self):
        """
        Get a display-friendly status string
        
        Returns:
            str: Status string in Chinese
        """
        status_map = {
            'pending': '等待中',
            'downloading': '下载中',
            'completed': '已完成',
            'failed': '失败'
        }
        return status_map.get(self.status, self.status)
        
    def get_formatted_size(self):
        """
        Get a formatted size string
        
        Returns:
            str: Formatted size string (e.g. "1.2 MB")
        """
        size = self.total_size
        
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB" 