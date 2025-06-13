#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from models.draft_model import DraftModel
from services.api_service import APIService
from services.database_service import DatabasePool
from services.download_service import DownloadService
from utils.file_utils import ensure_dir

class DraftService:
    """服务类，用于管理剪映专业版草稿箱"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(DraftService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化草稿箱服务"""
        if self._initialized:
            return
            
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        
        # 服务依赖
        self.db_pool = DatabasePool()
        self.api_service = APIService()
        self.download_service = DownloadService()
        
        self.logger.info("草稿箱服务初始化完成")
        
    def get_draft_by_uuid(self, uuid: str) -> Optional[DraftModel]:
        """
        通过UUID获取草稿箱
        
        Args:
            uuid (str): 草稿箱UUID
            
        Returns:
            DraftModel: 草稿箱模型，如果未找到则返回None
        """
        try:
            # 首先尝试从本地数据库获取
            query = "SELECT * FROM drafts WHERE uuid = %s"
            results = self.db_pool.execute_query(query, (uuid,))
            
            if results and len(results) > 0:
                return DraftModel.from_dict(results[0])
                
            # 如果本地没有，则从API获取
            draft_data = self.api_service.get_draft_by_uuid(uuid)
            
            if draft_data:
                return DraftModel.from_dict(draft_data)
                
            return None
            
        except Exception as e:
            self.logger.error("获取草稿箱失败: %s", e)
            return None
            
    def get_drafts(self, page: int = 1, page_size: int = 20, status: str = None) -> List[DraftModel]:
        """
        获取草稿箱列表
        
        Args:
            page (int, optional): 页码
            page_size (int, optional): 每页数量
            status (str, optional): 按状态筛选
            
        Returns:
            List[DraftModel]: 草稿箱列表
        """
        try:
            query = "SELECT * FROM drafts"
            params = []
            
            if status:
                query += " WHERE status = %s"
                params.append(status)
                
            query += " ORDER BY updated_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, (page - 1) * page_size])
            
            results = self.db_pool.execute_query(query, tuple(params))
            
            drafts = []
            for row in results:
                drafts.append(DraftModel.from_dict(row))
                
            return drafts
            
        except Exception as e:
            self.logger.error("获取草稿箱列表失败: %s", e)
            return []
            
    def save_draft(self, uuid: str, folder_path: str) -> bool:
        """
        保存草稿箱到本地
        
        Args:
            uuid (str): 草稿箱UUID
            folder_path (str): 本地文件夹路径
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取草稿箱信息
            draft = self.get_draft_by_uuid(uuid)
            
            if not draft:
                self.logger.error("未找到草稿箱: %s", uuid)
                return False
                
            # 确保文件夹存在
            ensure_dir(folder_path)
            
            # 创建草稿箱文件夹
            draft_folder = os.path.join(folder_path, draft.name)
            ensure_dir(draft_folder)
            
            # 获取草稿箱文件列表
            files = self.api_service.get_draft_files(uuid)
            
            if not files:
                self.logger.warning("草稿箱没有文件: %s", uuid)
                
            # 创建下载任务
            self.download_service.create_tasks_for_draft(uuid, files, draft_folder)
            
            # 更新草稿箱状态
            draft.status = 'downloading'
            draft.local_path = draft_folder
            self.update_draft(draft)
            
            return True
            
        except Exception as e:
            self.logger.error("保存草稿箱失败: %s", e)
            return False
            
    def update_draft_status(self, uuid: str, status: str, progress: int = None, error_message: str = None) -> bool:
        """
        更新草稿箱状态
        
        Args:
            uuid (str): 草稿箱UUID
            status (str): 新状态
            progress (int, optional): 下载进度(0-100)
            error_message (str, optional): 如果状态为'failed'，则为错误消息
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取草稿箱
            draft = self.get_draft_by_uuid(uuid)
            
            if not draft:
                self.logger.error("未找到草稿箱: %s", uuid)
                return False
                
            # 更新状态
            draft.status = status
            
            if progress is not None:
                draft.progress = progress
                
            if error_message:
                draft.error_message = error_message
                
            # 保存到数据库
            return self.update_draft(draft)
            
        except Exception as e:
            self.logger.error("更新草稿箱状态失败: %s", e)
            return False
            
    def update_draft(self, draft: DraftModel) -> bool:
        """
        更新草稿箱
        
        Args:
            draft (DraftModel): 草稿箱模型
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 更新时间
            draft.updated_at = datetime.now()
            
            # 检查草稿箱是否存在
            query = "SELECT id FROM drafts WHERE uuid = %s"
            results = self.db_pool.execute_query(query, (draft.uuid,))
            
            if results and len(results) > 0:
                # 更新现有草稿箱
                query = """
                    UPDATE drafts SET
                    name = %s,
                    description = %s,
                    file_count = %s,
                    total_size = %s,
                    status = %s,
                    updated_at = %s,
                    machine_name = %s,
                    local_path = %s,
                    error_message = %s,
                    progress = %s
                    WHERE uuid = %s
                """
                params = (
                    draft.name,
                    draft.description,
                    draft.file_count,
                    draft.total_size,
                    draft.status,
                    draft.updated_at,
                    draft.machine_name,
                    draft.local_path,
                    draft.error_message,
                    draft.progress,
                    draft.uuid
                )
            else:
                # 插入新草稿箱
                query = """
                    INSERT INTO drafts (
                    uuid, name, description, file_count, total_size,
                    status, created_at, updated_at, machine_name,
                    local_path, error_message, progress
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    draft.uuid,
                    draft.name,
                    draft.description,
                    draft.file_count,
                    draft.total_size,
                    draft.status,
                    draft.created_at,
                    draft.updated_at,
                    draft.machine_name,
                    draft.local_path,
                    draft.error_message,
                    draft.progress
                )
                
            self.db_pool.execute_query(query, params, fetch=False)
            
            # 同时更新API服务器上的状态
            self.api_service.update_draft_status(
                draft.uuid,
                draft.status,
                draft.progress,
                draft.error_message
            )
            
            return True
            
        except Exception as e:
            self.logger.error("更新草稿箱失败: %s", e)
            return False
            
    def delete_draft(self, uuid: str, delete_files: bool = False) -> bool:
        """
        删除草稿箱
        
        Args:
            uuid (str): 草稿箱UUID
            delete_files (bool, optional): 是否同时删除本地文件
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取草稿箱
            draft = self.get_draft_by_uuid(uuid)
            
            if not draft:
                self.logger.error("未找到草稿箱: %s", uuid)
                return False
                
            # 如果需要，删除本地文件
            if delete_files and draft.local_path and os.path.exists(draft.local_path):
                try:
                    import shutil
                    shutil.rmtree(draft.local_path)
                except Exception as e:
                    self.logger.error("删除本地文件失败: %s", e)
                    
            # 从数据库中删除
            query = "DELETE FROM drafts WHERE uuid = %s"
            self.db_pool.execute_query(query, (uuid,), fetch=False)
            
            return True
            
        except Exception as e:
            self.logger.error("删除草稿箱失败: %s", e)
            return False
            
    def count_drafts(self, status: str = None) -> int:
        """
        统计草稿箱数量
        
        Args:
            status (str, optional): 按状态筛选
            
        Returns:
            int: 草稿箱数量
        """
        try:
            query = "SELECT COUNT(*) as count FROM drafts"
            params = []
            
            if status:
                query += " WHERE status = %s"
                params.append(status)
                
            results = self.db_pool.execute_query(query, tuple(params) if params else None)
            
            if results and len(results) > 0:
                return results[0]['count']
                
            return 0
            
        except Exception as e:
            self.logger.error("统计草稿箱数量失败: %s", e)
            return 0
            
    def search_drafts(self, keyword: str, page: int = 1, page_size: int = 20) -> List[DraftModel]:
        """
        搜索草稿箱
        
        Args:
            keyword (str): 搜索关键词
            page (int, optional): 页码
            page_size (int, optional): 每页数量
            
        Returns:
            List[DraftModel]: 草稿箱列表
        """
        try:
            query = """
                SELECT * FROM drafts
                WHERE name LIKE %s OR description LIKE %s OR uuid LIKE %s
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
            """
            
            keyword_param = f"%{keyword}%"
            params = (keyword_param, keyword_param, keyword_param, page_size, (page - 1) * page_size)
            
            results = self.db_pool.execute_query(query, params)
            
            drafts = []
            for row in results:
                drafts.append(DraftModel.from_dict(row))
                
            return drafts
            
        except Exception as e:
            self.logger.error("搜索草稿箱失败: %s", e)
            return [] 