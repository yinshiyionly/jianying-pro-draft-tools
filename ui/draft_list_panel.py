#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMenu, QComboBox, QCheckBox,
    QSpinBox, QSizePolicy, QToolButton, QDialog, QTextEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSlot, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QAction

from models.draft_model import DraftModel
from services.draft_service import DraftService
from services.api_service import APIService

class DraftListWorker(QThread):
    """Worker thread for loading drafts"""
    
    # Signals
    loaded = pyqtSignal(list)  # List of DraftModel
    failed = pyqtSignal(str)  # Error message
    
    def __init__(self, page=1, page_size=20, status=None, search_term=None, parent=None):
        """
        Initialize the draft list worker
        
        Args:
            page (int, optional): Page number
            page_size (int, optional): Number of items per page
            status (str, optional): Filter by status
            search_term (str, optional): Search term
            parent (QObject, optional): Parent object
        """
        super().__init__(parent)
        
        self.page = page
        self.page_size = page_size
        self.status = status
        self.search_term = search_term
        self.logger = logging.getLogger(__name__)
        
        # Services
        self.draft_service = DraftService()
        
    def run(self):
        """Run the loading process"""
        try:
            # Load drafts
            if self.search_term:
                # Search drafts
                drafts = self.draft_service.search_drafts(
                    self.search_term,
                    self.page,
                    self.page_size
                )
            else:
                # Get drafts
                drafts = self.draft_service.get_drafts(
                    self.page,
                    self.page_size,
                    self.status
                )
                
            # Emit loaded signal
            self.loaded.emit(drafts)
            
        except Exception as e:
            self.logger.error("Failed to load drafts: %s", e)
            self.failed.emit(str(e))

class DraftDetailsDialog(QDialog):
    """Dialog for displaying draft details"""
    
    def __init__(self, draft, parent=None):
        """
        Initialize the draft details dialog
        
        Args:
            draft (DraftModel): Draft model
            parent (QWidget, optional): Parent widget
        """
        super().__init__(parent)
        
        self.draft = draft
        self.logger = logging.getLogger(__name__)
        
        # Set up UI
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface"""
        # Set window properties
        self.setWindowTitle(f"草稿箱详情: {self.draft.name}")
        self.resize(600, 400)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create form layout for details
        form_layout = QFormLayout()
        
        # Add details
        form_layout.addRow("UUID:", QLabel(self.draft.uuid))
        form_layout.addRow("名称:", QLabel(self.draft.name))
        form_layout.addRow("描述:", QLabel(self.draft.description))
        form_layout.addRow("文件数量:", QLabel(str(self.draft.file_count)))
        form_layout.addRow("总大小:", QLabel(self.draft.get_formatted_size()))
        form_layout.addRow("状态:", QLabel(self.draft.get_status_display()))
        form_layout.addRow("创建时间:", QLabel(self.draft.created_at.strftime("%Y-%m-%d %H:%M:%S")))
        form_layout.addRow("更新时间:", QLabel(self.draft.updated_at.strftime("%Y-%m-%d %H:%M:%S")))
        form_layout.addRow("设备名称:", QLabel(self.draft.machine_name))
        form_layout.addRow("本地路径:", QLabel(self.draft.local_path))
        
        if self.draft.error_message:
            form_layout.addRow("错误信息:", QLabel(self.draft.error_message))
            
        # Add form layout to main layout
        layout.addLayout(form_layout)
        
        # Add remote URLs
        if self.draft.remote_urls:
            urls_group = QGroupBox("远程URL")
            urls_layout = QVBoxLayout(urls_group)
            
            urls_text = QTextEdit()
            urls_text.setReadOnly(True)
            urls_text.setText("\n".join(self.draft.remote_urls))
            urls_layout.addWidget(urls_text)
            
            layout.addWidget(urls_group)
            
        # Add button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

class DraftListPanel(QWidget):
    """Panel for displaying and managing drafts"""
    
    def __init__(self, parent=None):
        """Initialize the draft list panel"""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.parent = parent
        
        # Current page
        self.current_page = 1
        self.page_size = 20
        self.total_pages = 1
        
        # Services
        self.draft_service = DraftService()
        
        # Worker thread
        self.worker = None
        
        # Set up UI
        self.setup_ui()
        
        # Load drafts
        self.load_drafts()
        
        # Set up auto refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_drafts)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
    def setup_ui(self):
        """Set up the user interface"""
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Create search and filter group
        filter_group = QGroupBox("搜索和筛选")
        filter_layout = QHBoxLayout(filter_group)
        
        # Add search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索草稿箱...")
        self.search_input.returnPressed.connect(self.search_drafts)
        filter_layout.addWidget(self.search_input)
        
        # Add search button
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.search_drafts)
        filter_layout.addWidget(self.search_button)
        
        # Add status filter
        self.status_filter = QComboBox()
        self.status_filter.addItem("所有状态", "")
        self.status_filter.addItem("等待中", "pending")
        self.status_filter.addItem("下载中", "downloading")
        self.status_filter.addItem("已完成", "completed")
        self.status_filter.addItem("失败", "failed")
        self.status_filter.currentIndexChanged.connect(self.filter_drafts)
        filter_layout.addWidget(self.status_filter)
        
        # Add refresh button
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.load_drafts)
        filter_layout.addWidget(self.refresh_button)
        
        # Add filter group to main layout
        layout.addWidget(filter_group)
        
        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["名称", "描述", "文件数量", "大小", "状态", "创建时间", "操作"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Add table to main layout
        layout.addWidget(self.table)
        
        # Create pagination layout
        pagination_layout = QHBoxLayout()
        
        # Add page navigation buttons
        self.prev_button = QPushButton("上一页")
        self.prev_button.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_button)
        
        self.page_label = QLabel("第 1 页 / 共 1 页")
        pagination_layout.addWidget(self.page_label)
        
        self.next_button = QPushButton("下一页")
        self.next_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_button)
        
        # Add page size selector
        pagination_layout.addStretch()
        pagination_layout.addWidget(QLabel("每页显示:"))
        
        self.page_size_selector = QComboBox()
        self.page_size_selector.addItem("10", 10)
        self.page_size_selector.addItem("20", 20)
        self.page_size_selector.addItem("50", 50)
        self.page_size_selector.addItem("100", 100)
        self.page_size_selector.setCurrentIndex(1)  # Default to 20
        self.page_size_selector.currentIndexChanged.connect(self.change_page_size)
        pagination_layout.addWidget(self.page_size_selector)
        
        # Add pagination layout to main layout
        layout.addLayout(pagination_layout)
        
    def load_drafts(self):
        """Load drafts from the service"""
        # Disable UI elements
        self.setEnabled(False)
        
        # Get filter status
        status = self.status_filter.currentData()
        
        # Create worker thread
        self.worker = DraftListWorker(
            self.current_page,
            self.page_size,
            status,
            None,
            self
        )
        
        # Connect signals
        self.worker.loaded.connect(self.on_drafts_loaded)
        self.worker.failed.connect(self.on_drafts_load_failed)
        
        # Start worker
        self.worker.start()
        
    def search_drafts(self):
        """Search drafts by term"""
        # Get search term
        search_term = self.search_input.text().strip()
        
        if not search_term:
            self.load_drafts()
            return
            
        # Disable UI elements
        self.setEnabled(False)
        
        # Reset to first page
        self.current_page = 1
        
        # Create worker thread
        self.worker = DraftListWorker(
            self.current_page,
            self.page_size,
            None,
            search_term,
            self
        )
        
        # Connect signals
        self.worker.loaded.connect(self.on_drafts_loaded)
        self.worker.failed.connect(self.on_drafts_load_failed)
        
        # Start worker
        self.worker.start()
        
    def filter_drafts(self):
        """Filter drafts by status"""
        # Reset to first page
        self.current_page = 1
        
        # Reload drafts
        self.load_drafts()
        
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_drafts()
            
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_drafts()
            
    def change_page_size(self):
        """Change the number of items per page"""
        self.page_size = self.page_size_selector.currentData()
        self.current_page = 1
        self.load_drafts()
        
    def on_drafts_loaded(self, drafts):
        """
        Handle drafts loaded
        
        Args:
            drafts (List[DraftModel]): List of draft models
        """
        # Clear table
        self.table.setRowCount(0)
        
        # Add drafts to table
        for draft in drafts:
            self.add_draft_to_table(draft)
            
        # Update pagination
        self.update_pagination()
        
        # Enable UI elements
        self.setEnabled(True)
        
    def on_drafts_load_failed(self, error_message):
        """
        Handle drafts load failed
        
        Args:
            error_message (str): Error message
        """
        # Show error message
        self.show_message(f"加载草稿箱列表失败: {error_message}", "error")
        
        # Enable UI elements
        self.setEnabled(True)
        
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
        name_item.setData(Qt.ItemDataRole.UserRole, draft.uuid)
        self.table.setItem(row, 0, name_item)
        
        # Set description
        description_item = QTableWidgetItem(draft.description)
        self.table.setItem(row, 1, description_item)
        
        # Set file count
        file_count_item = QTableWidgetItem(str(draft.file_count))
        self.table.setItem(row, 2, file_count_item)
        
        # Set size
        size_item = QTableWidgetItem(draft.get_formatted_size())
        self.table.setItem(row, 3, size_item)
        
        # Set status
        status_item = QTableWidgetItem(draft.get_status_display())
        self.table.setItem(row, 4, status_item)
        
        # Set created time
        created_time_item = QTableWidgetItem(draft.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        self.table.setItem(row, 5, created_time_item)
        
        # Set actions
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add details button
        details_button = QToolButton()
        details_button.setText("详情")
        details_button.clicked.connect(lambda: self.show_draft_details(draft))
        action_layout.addWidget(details_button)
        
        # Add open button if completed
        if draft.status == "completed" and draft.local_path:
            open_button = QToolButton()
            open_button.setText("打开")
            open_button.clicked.connect(lambda: self.open_draft(draft))
            action_layout.addWidget(open_button)
            
        # Add delete button
        delete_button = QToolButton()
        delete_button.setText("删除")
        delete_button.clicked.connect(lambda: self.delete_draft(draft.uuid))
        action_layout.addWidget(delete_button)
        
        self.table.setCellWidget(row, 6, action_widget)
        
    def update_pagination(self):
        """Update pagination controls"""
        # TODO: Get total count from API
        # For now, just estimate based on current page and items
        if self.table.rowCount() < self.page_size:
            self.total_pages = self.current_page
        else:
            self.total_pages = self.current_page + 1
            
        # Update page label
        self.page_label.setText(f"第 {self.current_page} 页 / 共 {self.total_pages} 页")
        
        # Enable/disable navigation buttons
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)
        
    def show_context_menu(self, position):
        """
        Show context menu for table item
        
        Args:
            position (QPoint): Position where the context menu should be shown
        """
        # Get selected row
        row = self.table.rowAt(position.y())
        if row < 0:
            return
            
        # Get draft UUID
        uuid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        # Create menu
        menu = QMenu(self)
        
        # Add actions
        details_action = QAction("查看详情", self)
        details_action.triggered.connect(lambda: self.show_draft_details_by_uuid(uuid))
        menu.addAction(details_action)
        
        # Add open action if completed
        status = self.table.item(row, 4).text()
        if status == "已完成":
            open_action = QAction("打开文件夹", self)
            open_action.triggered.connect(lambda: self.open_draft_by_uuid(uuid))
            menu.addAction(open_action)
            
        menu.addSeparator()
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_draft(uuid))
        menu.addAction(delete_action)
        
        # Show menu
        menu.exec(self.table.viewport().mapToGlobal(position))
        
    def show_draft_details(self, draft):
        """
        Show draft details dialog
        
        Args:
            draft (DraftModel): Draft model
        """
        dialog = DraftDetailsDialog(draft, self)
        dialog.exec()
        
    def show_draft_details_by_uuid(self, uuid):
        """
        Show draft details dialog by UUID
        
        Args:
            uuid (str): Draft UUID
        """
        try:
            draft = self.draft_service.get_draft_by_uuid(uuid)
            if draft:
                self.show_draft_details(draft)
            else:
                self.show_message("未找到草稿箱", "error")
        except Exception as e:
            self.logger.error("Failed to get draft details: %s", e)
            self.show_message(f"获取草稿箱详情失败: {e}", "error")
            
    def open_draft(self, draft):
        """
        Open draft folder
        
        Args:
            draft (DraftModel): Draft model
        """
        try:
            if draft.local_path and os.path.exists(draft.local_path):
                os.startfile(draft.local_path)
            else:
                self.show_message("草稿箱文件夹不存在", "error")
        except Exception as e:
            self.logger.error("Failed to open draft: %s", e)
            self.show_message(f"打开草稿箱失败: {e}", "error")
            
    def open_draft_by_uuid(self, uuid):
        """
        Open draft folder by UUID
        
        Args:
            uuid (str): Draft UUID
        """
        try:
            draft = self.draft_service.get_draft_by_uuid(uuid)
            if draft:
                self.open_draft(draft)
            else:
                self.show_message("未找到草稿箱", "error")
        except Exception as e:
            self.logger.error("Failed to open draft: %s", e)
            self.show_message(f"打开草稿箱失败: {e}", "error")
            
    def delete_draft(self, uuid):
        """
        Delete a draft
        
        Args:
            uuid (str): Draft UUID
        """
        try:
            # Delete from database
            self.draft_service.delete_draft(uuid)
            
            # Remove from table
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) == uuid:
                    self.table.removeRow(row)
                    break
                    
            self.show_message("草稿箱已删除", "success")
        except Exception as e:
            self.logger.error("Failed to delete draft: %s", e)
            self.show_message(f"删除草稿箱失败: {e}", "error")
            
    def show_message(self, message, message_type="info"):
        """
        Show a message
        
        Args:
            message (str): Message to display
            message_type (str): Type of message (info, success, warning, error)
        """
        if hasattr(self.parent, 'show_message'):
            self.parent.show_message(message, message_type) 