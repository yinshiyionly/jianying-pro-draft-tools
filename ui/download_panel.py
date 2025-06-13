#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QFormLayout, QProgressBar,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QCheckBox, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSlot, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

from models.draft_model import DraftModel
from services.draft_service import DraftService
from services.api_service import APIService
from utils.file_utils import ensure_dir, get_free_space

class DownloadWorker(QThread):
    """Worker thread for downloading drafts"""
    
    # Signals
    started = pyqtSignal(str)  # draft_uuid
    progress = pyqtSignal(str, int)  # draft_uuid, progress
    completed = pyqtSignal(str)  # draft_uuid
    failed = pyqtSignal(str, str)  # draft_uuid, error_message
    
    def __init__(self, draft_uuid, save_path, parent=None):
        """
        Initialize the download worker
        
        Args:
            draft_uuid (str): Draft UUID
            save_path (str): Path to save the draft
            parent (QObject, optional): Parent object
        """
        super().__init__(parent)
        
        self.draft_uuid = draft_uuid
        self.save_path = save_path
        self.logger = logging.getLogger(__name__)
        
        # Services
        self.draft_service = DraftService()
        self.api_service = APIService()
        
        # Flag to control thread execution
        self.is_running = True
        
    def run(self):
        """Run the download process"""
        try:
            # Emit started signal
            self.started.emit(self.draft_uuid)
            
            # Get draft details
            draft = self.draft_service.get_draft_by_uuid(self.draft_uuid)
            
            if not draft:
                self.failed.emit(self.draft_uuid, "Draft not found")
                return
                
            # Create save directory
            draft_dir = os.path.join(self.save_path, draft.name)
            if not ensure_dir(draft_dir):
                self.failed.emit(self.draft_uuid, f"Failed to create directory: {draft_dir}")
                return
                
            # Update draft status to downloading
            self.draft_service.update_draft_status(self.draft_uuid, "downloading", 0)
            
            # Get draft files
            files = self.draft_service.get_draft_files(self.draft_uuid)
            
            if not files:
                self.failed.emit(self.draft_uuid, "No files found in draft")
                return
                
            # Check disk space
            total_size = sum(file.get('size', 0) for file in files)
            free_space = get_free_space(draft_dir)
            
            if total_size > free_space:
                self.failed.emit(
                    self.draft_uuid,
                    f"Not enough disk space. Required: {total_size}, Available: {free_space}"
                )
                return
                
            # TODO: Implement actual download logic using DownloadService
            # For now, just simulate progress
            for i in range(101):
                if not self.is_running:
                    return
                    
                # Update progress
                self.progress.emit(self.draft_uuid, i)
                
                # Update draft status
                self.draft_service.update_draft_status(self.draft_uuid, "downloading", i)
                
                # Sleep to simulate download
                self.msleep(50)
                
            # Mark as completed
            self.draft_service.update_draft_status(self.draft_uuid, "completed", 100)
            
            # Emit completed signal
            self.completed.emit(self.draft_uuid)
            
        except Exception as e:
            self.logger.error("Download failed: %s", e)
            self.failed.emit(self.draft_uuid, str(e))
            
            # Update draft status to failed
            self.draft_service.update_draft_status(self.draft_uuid, "failed", 0, str(e))
            
    def stop(self):
        """Stop the download process"""
        self.is_running = False

class DownloadPanel(QWidget):
    """Panel for downloading drafts"""
    
    def __init__(self, parent=None):
        """Initialize the download panel"""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.parent = parent
        
        # Services
        self.draft_service = DraftService()
        self.api_service = APIService()
        
        # Download workers
        self.download_workers = {}  # draft_uuid -> DownloadWorker
        
        # Set up UI
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface"""
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Create input group
        input_group = QGroupBox("草稿箱信息")
        input_layout = QFormLayout(input_group)
        
        # Add UUID input
        self.uuid_input = QLineEdit()
        self.uuid_input.setPlaceholderText("输入草稿箱UUID")
        input_layout.addRow("草稿箱UUID:", self.uuid_input)
        
        # Add save path input
        save_path_layout = QHBoxLayout()
        self.save_path_input = QLineEdit()
        self.save_path_input.setPlaceholderText("选择保存路径")
        self.save_path_input.setText(os.path.expanduser("~/Downloads"))
        save_path_layout.addWidget(self.save_path_input)
        
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_save_path)
        save_path_layout.addWidget(self.browse_button)
        
        input_layout.addRow("保存路径:", save_path_layout)
        
        # Add download button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.download_button = QPushButton("下载草稿箱")
        self.download_button.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_button)
        
        input_layout.addRow("", button_layout)
        
        # Add input group to main layout
        layout.addWidget(input_group)
        
        # Create download list group
        list_group = QGroupBox("下载列表")
        list_layout = QVBoxLayout(list_group)
        
        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["草稿箱名称", "状态", "进度", "操作", "UUID"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnHidden(4, True)  # Hide UUID column
        
        list_layout.addWidget(self.table)
        
        # Add list group to main layout
        layout.addWidget(list_group)
        
    def browse_save_path(self):
        """Open file dialog to select save path"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择保存路径",
            self.save_path_input.text()
        )
        
        if directory:
            self.save_path_input.setText(directory)
            
    def start_download(self):
        """Start downloading the draft"""
        # Get UUID and save path
        uuid = self.uuid_input.text().strip()
        save_path = self.save_path_input.text().strip()
        
        if not uuid:
            self.show_message("请输入草稿箱UUID", "warning")
            return
            
        if not save_path:
            self.show_message("请选择保存路径", "warning")
            return
            
        # Check if save path exists
        if not os.path.exists(save_path):
            try:
                os.makedirs(save_path)
            except Exception as e:
                self.show_message(f"无法创建保存路径: {e}", "error")
                return
                
        try:
            # Get draft details
            draft = self.draft_service.get_draft_by_uuid(uuid)
            
            if not draft:
                self.show_message("未找到草稿箱，请检查UUID是否正确", "error")
                return
                
            # Check if draft is already in the table
            for row in range(self.table.rowCount()):
                if self.table.item(row, 4).text() == uuid:
                    self.show_message("草稿箱已在下载列表中", "warning")
                    return
                    
            # Add to table
            self.add_draft_to_table(draft)
            
            # Start download
            self.download_draft(draft, save_path)
            
            # Clear UUID input
            self.uuid_input.clear()
            
        except Exception as e:
            self.logger.error("Failed to start download: %s", e)
            self.show_message(f"下载失败: {e}", "error")
            
    def add_draft_to_table(self, draft):
        """
        Add a draft to the table
        
        Args:
            draft (DraftModel): Draft model
        """
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Set name
        name_item = QTableWidgetItem(draft.name)
        self.table.setItem(row, 0, name_item)
        
        # Set status
        status_item = QTableWidgetItem(draft.get_status_display())
        self.table.setItem(row, 1, status_item)
        
        # Set progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        self.table.setCellWidget(row, 2, progress_bar)
        
        # Set action button
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        
        cancel_button = QPushButton("取消")
        cancel_button.setFixedWidth(60)
        cancel_button.clicked.connect(lambda: self.cancel_download(draft.uuid))
        action_layout.addWidget(cancel_button)
        
        self.table.setCellWidget(row, 3, action_widget)
        
        # Set UUID (hidden)
        uuid_item = QTableWidgetItem(draft.uuid)
        self.table.setItem(row, 4, uuid_item)
        
    def download_draft(self, draft, save_path):
        """
        Download a draft
        
        Args:
            draft (DraftModel): Draft model
            save_path (str): Path to save the draft
        """
        # Create worker thread
        worker = DownloadWorker(draft.uuid, save_path, self)
        
        # Connect signals
        worker.started.connect(self.on_download_started)
        worker.progress.connect(self.on_download_progress)
        worker.completed.connect(self.on_download_completed)
        worker.failed.connect(self.on_download_failed)
        
        # Store worker
        self.download_workers[draft.uuid] = worker
        
        # Start worker
        worker.start()
        
    def cancel_download(self, uuid):
        """
        Cancel a download
        
        Args:
            uuid (str): Draft UUID
        """
        if uuid in self.download_workers:
            # Stop worker
            self.download_workers[uuid].stop()
            self.download_workers[uuid].wait()
            del self.download_workers[uuid]
            
            # Update draft status
            try:
                self.draft_service.update_draft_status(uuid, "pending", 0)
            except Exception as e:
                self.logger.error("Failed to update draft status: %s", e)
                
            # Remove from table
            for row in range(self.table.rowCount()):
                if self.table.item(row, 4).text() == uuid:
                    self.table.removeRow(row)
                    break
                    
            self.show_message("下载已取消", "info")
            
    @pyqtSlot(str)
    def on_download_started(self, uuid):
        """
        Handle download started
        
        Args:
            uuid (str): Draft UUID
        """
        # Update status in table
        for row in range(self.table.rowCount()):
            if self.table.item(row, 4).text() == uuid:
                self.table.item(row, 1).setText("下载中")
                break
                
        self.show_message(f"开始下载草稿箱: {uuid}", "info")
        
    @pyqtSlot(str, int)
    def on_download_progress(self, uuid, progress):
        """
        Handle download progress
        
        Args:
            uuid (str): Draft UUID
            progress (int): Progress percentage
        """
        # Update progress in table
        for row in range(self.table.rowCount()):
            if self.table.item(row, 4).text() == uuid:
                progress_bar = self.table.cellWidget(row, 2)
                if progress_bar:
                    progress_bar.setValue(progress)
                break
                
    @pyqtSlot(str)
    def on_download_completed(self, uuid):
        """
        Handle download completed
        
        Args:
            uuid (str): Draft UUID
        """
        # Update status in table
        for row in range(self.table.rowCount()):
            if self.table.item(row, 4).text() == uuid:
                self.table.item(row, 1).setText("已完成")
                
                # Change action button
                action_widget = self.table.cellWidget(row, 3)
                if action_widget:
                    # Clear layout
                    while action_widget.layout().count():
                        item = action_widget.layout().takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()
                            
                    # Add open button
                    open_button = QPushButton("打开")
                    open_button.setFixedWidth(60)
                    open_button.clicked.connect(lambda: self.open_draft(uuid))
                    action_widget.layout().addWidget(open_button)
                break
                
        # Remove worker
        if uuid in self.download_workers:
            del self.download_workers[uuid]
            
        self.show_message(f"草稿箱下载完成: {uuid}", "success")
        
    @pyqtSlot(str, str)
    def on_download_failed(self, uuid, error_message):
        """
        Handle download failed
        
        Args:
            uuid (str): Draft UUID
            error_message (str): Error message
        """
        # Update status in table
        for row in range(self.table.rowCount()):
            if self.table.item(row, 4).text() == uuid:
                self.table.item(row, 1).setText("失败")
                
                # Change action button
                action_widget = self.table.cellWidget(row, 3)
                if action_widget:
                    # Clear layout
                    while action_widget.layout().count():
                        item = action_widget.layout().takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()
                            
                    # Add retry button
                    retry_button = QPushButton("重试")
                    retry_button.setFixedWidth(60)
                    retry_button.clicked.connect(lambda: self.retry_download(uuid))
                    action_widget.layout().addWidget(retry_button)
                break
                
        # Remove worker
        if uuid in self.download_workers:
            del self.download_workers[uuid]
            
        self.show_message(f"草稿箱下载失败: {error_message}", "error")
        
    def open_draft(self, uuid):
        """
        Open the downloaded draft
        
        Args:
            uuid (str): Draft UUID
        """
        try:
            # Get draft details
            draft = self.draft_service.get_draft_by_uuid(uuid)
            
            if not draft:
                self.show_message("未找到草稿箱", "error")
                return
                
            # Open folder
            path = os.path.join(self.save_path_input.text(), draft.name)
            if os.path.exists(path):
                os.startfile(path)
            else:
                self.show_message("草稿箱文件夹不存在", "error")
                
        except Exception as e:
            self.logger.error("Failed to open draft: %s", e)
            self.show_message(f"打开失败: {e}", "error")
            
    def retry_download(self, uuid):
        """
        Retry downloading a draft
        
        Args:
            uuid (str): Draft UUID
        """
        try:
            # Get draft details
            draft = self.draft_service.get_draft_by_uuid(uuid)
            
            if not draft:
                self.show_message("未找到草稿箱", "error")
                return
                
            # Start download
            self.download_draft(draft, self.save_path_input.text())
            
        except Exception as e:
            self.logger.error("Failed to retry download: %s", e)
            self.show_message(f"重试失败: {e}", "error")
            
    def show_message(self, message, message_type="info"):
        """
        Show a message
        
        Args:
            message (str): Message to display
            message_type (str): Type of message (info, success, warning, error)
        """
        if hasattr(self.parent, 'show_message'):
            self.parent.show_message(message, message_type) 