#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSlot, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

from qfluentwidgets import (
    LineEdit, PushButton, ProgressBar, ComboBox, 
    FluentIcon, CardWidget, SpinBox, CheckBox,
    StrongBodyLabel, BodyLabel, CaptionLabel,
    InfoBar, InfoBarPosition, TableWidget
)

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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Create input card
        input_card = CardWidget(self)
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(16)
        
        # Add card title
        title_label = StrongBodyLabel("草稿箱信息", input_card)
        input_layout.addWidget(title_label)
        
        # Add UUID input with label
        uuid_layout = QVBoxLayout()
        uuid_layout.setSpacing(6)
        
        uuid_label = BodyLabel("草稿箱UUID:", input_card)
        uuid_layout.addWidget(uuid_label)
        
        self.uuid_input = LineEdit(input_card)
        self.uuid_input.setPlaceholderText("输入草稿箱UUID")
        uuid_layout.addWidget(self.uuid_input)
        
        input_layout.addLayout(uuid_layout)
        
        # Add save path input with label
        path_layout = QVBoxLayout()
        path_layout.setSpacing(6)
        
        path_label = BodyLabel("保存路径:", input_card)
        path_layout.addWidget(path_label)
        
        save_path_layout = QHBoxLayout()
        save_path_layout.setSpacing(8)
        
        self.save_path_input = LineEdit(input_card)
        self.save_path_input.setPlaceholderText("选择保存路径")
        self.save_path_input.setText(os.path.expanduser("~/Downloads"))
        save_path_layout.addWidget(self.save_path_input)
        
        self.browse_button = PushButton("浏览...", input_card)
        self.browse_button.setIcon(FluentIcon.FOLDER)
        self.browse_button.clicked.connect(self.browse_save_path)
        save_path_layout.addWidget(self.browse_button)
        
        path_layout.addLayout(save_path_layout)
        input_layout.addLayout(path_layout)
        
        # Add download button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.download_button = PushButton("下载草稿箱", input_card)
        self.download_button.setIcon(FluentIcon.DOWNLOAD)
        self.download_button.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_button)
        
        input_layout.addLayout(button_layout)
        
        # Add input card to main layout
        layout.addWidget(input_card)
        
        # Create download list card
        list_card = CardWidget(self)
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(20, 20, 20, 20)
        list_layout.setSpacing(16)
        
        # Add card title
        list_title = StrongBodyLabel("下载列表", list_card)
        list_layout.addWidget(list_title)
        
        # Create table widget
        self.table = TableWidget(list_card)
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
        
        # Add list card to main layout
        layout.addWidget(list_card)
        
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
                    
            # Add draft to table
            self.add_draft_to_table(draft)
            
            # Start download
            self.download_draft(draft, save_path)
            
            # Clear input field
            self.uuid_input.clear()
            
            # Show success message
            self.show_message(f"开始下载草稿箱: {draft.name}", "success")
            
        except Exception as e:
            self.logger.error("Failed to start download: %s", e)
            self.show_message(f"下载失败: {e}", "error")
            
    def add_draft_to_table(self, draft):
        """
        Add draft to table
        
        Args:
            draft (DraftModel): Draft model
        """
        # Get current row count
        row = self.table.rowCount()
        
        # Insert new row
        self.table.insertRow(row)
        
        # Set draft name
        name_item = QTableWidgetItem(draft.name)
        self.table.setItem(row, 0, name_item)
        
        # Set status
        status_item = QTableWidgetItem(draft.get_status_display())
        self.table.setItem(row, 1, status_item)
        
        # Create progress bar
        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setContentsMargins(5, 2, 5, 2)
        
        progress_bar = ProgressBar(progress_widget)
        progress_bar.setValue(draft.progress)
        progress_layout.addWidget(progress_bar)
        
        self.table.setCellWidget(row, 2, progress_widget)
        
        # Create action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(5, 2, 5, 2)
        action_layout.setSpacing(4)
        
        cancel_button = PushButton("取消", action_widget)
        cancel_button.setIcon(FluentIcon.CANCEL)
        cancel_button.clicked.connect(lambda: self.cancel_download(draft.uuid))
        action_layout.addWidget(cancel_button)
        
        open_button = PushButton("打开", action_widget)
        open_button.setIcon(FluentIcon.FOLDER)
        open_button.clicked.connect(lambda: self.open_draft(draft.uuid))
        open_button.setEnabled(draft.status == "completed")
        action_layout.addWidget(open_button)
        
        retry_button = PushButton("重试", action_widget)
        retry_button.setIcon(FluentIcon.SYNC)
        retry_button.clicked.connect(lambda: self.retry_download(draft.uuid))
        retry_button.setEnabled(draft.status == "failed")
        action_layout.addWidget(retry_button)
        
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
        # Create download worker
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
        # Get worker
        worker = self.download_workers.get(uuid)
        
        if worker:
            # Stop worker
            worker.stop()
            
            # Wait for worker to finish
            worker.wait()
            
            # Remove worker
            del self.download_workers[uuid]
            
            # Update draft status
            self.draft_service.update_draft_status(uuid, "pending", 0)
            
            # Update table
            for row in range(self.table.rowCount()):
                if self.table.item(row, 4).text() == uuid:
                    # Update status
                    self.table.item(row, 1).setText("已取消")
                    
                    # Update progress bar
                    progress_widget = self.table.cellWidget(row, 2)
                    progress_bar = progress_widget.layout().itemAt(0).widget()
                    progress_bar.setValue(0)
                    
                    # Update action buttons
                    action_widget = self.table.cellWidget(row, 3)
                    layout = action_widget.layout()
                    
                    # Enable retry button
                    retry_button = layout.itemAt(2).widget()
                    retry_button.setEnabled(True)
                    
                    break
                    
            # Show message
            self.show_message(f"已取消下载", "info")
            
    @pyqtSlot(str)
    def on_download_started(self, uuid):
        """
        Handle download started
        
        Args:
            uuid (str): Draft UUID
        """
        # Update table
        for row in range(self.table.rowCount()):
            if self.table.item(row, 4).text() == uuid:
                # Update status
                self.table.item(row, 1).setText("下载中")
                break
                
    @pyqtSlot(str, int)
    def on_download_progress(self, uuid, progress):
        """
        Handle download progress
        
        Args:
            uuid (str): Draft UUID
            progress (int): Progress percentage
        """
        # Update table
        for row in range(self.table.rowCount()):
            if self.table.item(row, 4).text() == uuid:
                # Update progress bar
                progress_widget = self.table.cellWidget(row, 2)
                progress_bar = progress_widget.layout().itemAt(0).widget()
                progress_bar.setValue(progress)
                break
                
    @pyqtSlot(str)
    def on_download_completed(self, uuid):
        """
        Handle download completed
        
        Args:
            uuid (str): Draft UUID
        """
        # Remove worker
        if uuid in self.download_workers:
            del self.download_workers[uuid]
            
        # Get draft
        draft = self.draft_service.get_draft_by_uuid(uuid)
        
        if not draft:
            return
            
        # Update table
        for row in range(self.table.rowCount()):
            if self.table.item(row, 4).text() == uuid:
                # Update status
                self.table.item(row, 1).setText("已完成")
                
                # Update progress bar
                progress_widget = self.table.cellWidget(row, 2)
                progress_bar = progress_widget.layout().itemAt(0).widget()
                progress_bar.setValue(100)
                
                # Update action buttons
                action_widget = self.table.cellWidget(row, 3)
                layout = action_widget.layout()
                
                # Enable open button
                open_button = layout.itemAt(1).widget()
                open_button.setEnabled(True)
                
                # Disable retry button
                retry_button = layout.itemAt(2).widget()
                retry_button.setEnabled(False)
                
                break
                
        # Show message
        self.show_message(f"草稿箱 {draft.name} 下载完成", "success")
        
    @pyqtSlot(str, str)
    def on_download_failed(self, uuid, error_message):
        """
        Handle download failed
        
        Args:
            uuid (str): Draft UUID
            error_message (str): Error message
        """
        # Remove worker
        if uuid in self.download_workers:
            del self.download_workers[uuid]
            
        # Get draft
        draft = self.draft_service.get_draft_by_uuid(uuid)
        
        if not draft:
            return
            
        # Update table
        for row in range(self.table.rowCount()):
            if self.table.item(row, 4).text() == uuid:
                # Update status
                self.table.item(row, 1).setText("失败")
                
                # Update action buttons
                action_widget = self.table.cellWidget(row, 3)
                layout = action_widget.layout()
                
                # Enable retry button
                retry_button = layout.itemAt(2).widget()
                retry_button.setEnabled(True)
                
                break
                
        # Show message
        self.show_message(f"草稿箱 {draft.name} 下载失败: {error_message}", "error")
        
    def open_draft(self, uuid):
        """
        Open a draft
        
        Args:
            uuid (str): Draft UUID
        """
        # Get draft
        draft = self.draft_service.get_draft_by_uuid(uuid)
        
        if not draft or not draft.local_path:
            self.show_message("找不到草稿箱本地路径", "error")
            return
            
        # Check if path exists
        if not os.path.exists(draft.local_path):
            self.show_message("草稿箱本地路径不存在", "error")
            return
            
        try:
            # Open folder
            if os.name == 'nt':  # Windows
                os.startfile(draft.local_path)
            elif os.name == 'posix':  # macOS, Linux
                import subprocess
                subprocess.Popen(['xdg-open', draft.local_path])
                
        except Exception as e:
            self.logger.error("Failed to open draft: %s", e)
            self.show_message(f"无法打开草稿箱: {e}", "error")
            
    def retry_download(self, uuid):
        """
        Retry downloading a draft
        
        Args:
            uuid (str): Draft UUID
        """
        # Get draft
        draft = self.draft_service.get_draft_by_uuid(uuid)
        
        if not draft:
            self.show_message("找不到草稿箱", "error")
            return
            
        # Get save path
        save_path = self.save_path_input.text().strip()
        
        if not save_path:
            self.show_message("请选择保存路径", "warning")
            return
            
        # Start download
        self.download_draft(draft, save_path)
        
        # Show message
        self.show_message(f"重新下载草稿箱: {draft.name}", "info")
        
    def show_message(self, message, message_type="info"):
        """
        Show a message in the main window
        
        Args:
            message (str): Message to display
            message_type (str): Type of message (info, success, warning, error)
        """
        if hasattr(self.parent, 'show_message'):
            self.parent.show_message(message, message_type)
        else:
            # Create InfoBar if parent doesn't have show_message
            icon = None
            title = "信息"
            
            if message_type == "info":
                title = "信息"
                icon = FluentIcon.INFORMATION
            elif message_type == "success":
                title = "成功"
                icon = FluentIcon.COMPLETED
            elif message_type == "warning":
                title = "警告"
                icon = FluentIcon.WARNING
            elif message_type == "error":
                title = "错误" 
                icon = FluentIcon.ERROR
            
            # Show InfoBar directly
            InfoBar.success(
                title=title,
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            ) 