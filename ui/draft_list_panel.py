#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMenu, QDialog, QTextEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSlot, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QAction

from qfluentwidgets import (
    LineEdit, PushButton, ComboBox, CheckBox, SpinBox,
    CardWidget, TableWidget, FluentIcon, InfoBar,
    InfoBarPosition, StrongBodyLabel, BodyLabel,
    SearchLineEdit, MessageBox
)

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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Create details card
        details_card = CardWidget(self)
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(20, 20, 20, 20)
        details_layout.setSpacing(10)
        
        # Add card title
        title_label = StrongBodyLabel("草稿箱信息", details_card)
        details_layout.addWidget(title_label)
        
        # Create form layout for details
        form_widget = QWidget(details_card)
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(8)
        
        # Add details with label/value pairs
        detail_pairs = [
            ("UUID:", self.draft.uuid),
            ("名称:", self.draft.name),
            ("描述:", self.draft.description),
            ("文件数量:", str(self.draft.file_count)),
            ("总大小:", self.draft.get_formatted_size()),
            ("状态:", self.draft.get_status_display()),
            ("创建时间:", self.draft.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("更新时间:", self.draft.updated_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("设备名称:", self.draft.machine_name),
            ("本地路径:", self.draft.local_path)
        ]
        
        if self.draft.error_message:
            detail_pairs.append(("错误信息:", self.draft.error_message))
        
        for label_text, value_text in detail_pairs:
            item_layout = QHBoxLayout()
            
            label = BodyLabel(label_text, form_widget)
            label.setMinimumWidth(100)
            item_layout.addWidget(label)
            
            value = BodyLabel(value_text, form_widget)
            value.setWordWrap(True)
            item_layout.addWidget(value, 1)
            
            form_layout.addLayout(item_layout)
        
        details_layout.addWidget(form_widget)
        layout.addWidget(details_card)
        
        # Add remote URLs if available
        if self.draft.remote_urls:
            urls_card = CardWidget(self)
            urls_layout = QVBoxLayout(urls_card)
            urls_layout.setContentsMargins(20, 20, 20, 20)
            urls_layout.setSpacing(10)
            
            urls_title = StrongBodyLabel("远程URL", urls_card)
            urls_layout.addWidget(urls_title)
            
            urls_text = QTextEdit(urls_card)
            urls_text.setReadOnly(True)
            urls_text.setText("\n".join(self.draft.remote_urls))
            urls_layout.addWidget(urls_text)
            
            layout.addWidget(urls_card)
            
        # Add button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Create search and filter card
        filter_card = CardWidget(self)
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setContentsMargins(20, 20, 20, 20)
        filter_layout.setSpacing(16)
        
        # Add card title
        filter_title = StrongBodyLabel("搜索和筛选", filter_card)
        filter_layout.addWidget(filter_title)
        
        # Add search and filter controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        # Add search input
        self.search_input = SearchLineEdit(filter_card)
        self.search_input.setPlaceholderText("搜索草稿箱...")
        self.search_input.textChanged.connect(self.search_drafts)
        controls_layout.addWidget(self.search_input, 1)
        
        # Add status filter
        self.status_filter = ComboBox(filter_card)
        self.status_filter.addItem("所有状态", "")
        self.status_filter.addItem("等待中", "pending")
        self.status_filter.addItem("下载中", "downloading")
        self.status_filter.addItem("已完成", "completed")
        self.status_filter.addItem("失败", "failed")
        self.status_filter.currentIndexChanged.connect(self.filter_drafts)
        controls_layout.addWidget(self.status_filter)
        
        # Add refresh button
        self.refresh_button = PushButton("刷新", filter_card)
        self.refresh_button.setIcon(FluentIcon.SYNC)
        self.refresh_button.clicked.connect(self.load_drafts)
        controls_layout.addWidget(self.refresh_button)
        
        filter_layout.addLayout(controls_layout)
        
        # Add filter card to main layout
        layout.addWidget(filter_card)
        
        # Create drafts list card
        list_card = CardWidget(self)
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(20, 20, 20, 20)
        list_layout.setSpacing(16)
        
        # Add card title
        list_title = StrongBodyLabel("草稿箱列表", list_card)
        list_layout.addWidget(list_title)
        
        # Create table widget
        self.table = TableWidget(list_card)
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
        
        list_layout.addWidget(self.table)
        
        # Create pagination layout
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)
        
        # Add page navigation buttons
        self.prev_button = PushButton("上一页", list_card)
        self.prev_button.setIcon(FluentIcon.CHEVRON_LEFT)
        self.prev_button.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_button)
        
        self.page_label = BodyLabel("第 1 页 / 共 1 页", list_card)
        pagination_layout.addWidget(self.page_label)
        
        self.next_button = PushButton("下一页", list_card)
        self.next_button.setIcon(FluentIcon.CHEVRON_RIGHT)
        self.next_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_button)
        
        # Add page size selector
        pagination_layout.addStretch()
        pagination_layout.addWidget(BodyLabel("每页显示:", list_card))
        
        self.page_size_selector = ComboBox(list_card)
        self.page_size_selector.addItem("10", 10)
        self.page_size_selector.addItem("20", 20)
        self.page_size_selector.addItem("50", 50)
        self.page_size_selector.addItem("100", 100)
        self.page_size_selector.setCurrentIndex(1)  # Default to 20
        self.page_size_selector.currentIndexChanged.connect(self.change_page_size)
        pagination_layout.addWidget(self.page_size_selector)
        
        list_layout.addLayout(pagination_layout)
        
        # Add list card to main layout
        layout.addWidget(list_card)
        
    def load_drafts(self):
        """Load drafts from service"""
        # Disable controls
        self.setEnabled(False)
        
        # Get search term and status filter
        search_term = self.search_input.text().strip()
        status = self.status_filter.currentData()
        
        # Create worker thread
        self.worker = DraftListWorker(
            self.current_page,
            self.page_size,
            status,
            search_term,
            self
        )
        
        # Connect signals
        self.worker.loaded.connect(self.on_drafts_loaded)
        self.worker.failed.connect(self.on_drafts_load_failed)
        
        # Start worker
        self.worker.start()
        
    def search_drafts(self):
        """Search drafts by term"""
        # Reset to first page
        self.current_page = 1
        
        # Load drafts with search term
        self.load_drafts()
        
    def filter_drafts(self):
        """Filter drafts by status"""
        # Reset to first page
        self.current_page = 1
        
        # Load drafts with filter
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
        """Change number of items per page"""
        self.page_size = self.page_size_selector.currentData()
        self.current_page = 1
        self.load_drafts()
        
    def on_drafts_loaded(self, drafts):
        """
        Handle drafts loaded
        
        Args:
            drafts (list): List of DraftModel objects
        """
        # Clear table
        self.table.setRowCount(0)
        
        # Add drafts to table
        for draft in drafts:
            self.add_draft_to_table(draft)
            
        # Update pagination
        self.update_pagination()
        
        # Enable controls
        self.setEnabled(True)
        
        # Clean up worker
        self.worker = None
        
    def on_drafts_load_failed(self, error_message):
        """
        Handle drafts load failed
        
        Args:
            error_message (str): Error message
        """
        # Show error message
        self.show_message(f"加载草稿箱失败: {error_message}", "error")
        
        # Enable controls
        self.setEnabled(True)
        
        # Clean up worker
        self.worker = None
        
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
        
        # Set name
        name_item = QTableWidgetItem(draft.name)
        name_item.setData(Qt.ItemDataRole.UserRole, draft.uuid)
        self.table.setItem(row, 0, name_item)
        
        # Set description
        description_item = QTableWidgetItem(draft.description)
        self.table.setItem(row, 1, description_item)
        
        # Set file count
        file_count_item = QTableWidgetItem(str(draft.file_count))
        file_count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 2, file_count_item)
        
        # Set size
        size_item = QTableWidgetItem(draft.get_formatted_size())
        size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 3, size_item)
        
        # Set status
        status_item = QTableWidgetItem(draft.get_status_display())
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 4, status_item)
        
        # Set created at
        created_at_item = QTableWidgetItem(draft.created_at.strftime("%Y-%m-%d %H:%M"))
        created_at_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 5, created_at_item)
        
        # Create action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(5, 2, 5, 2)
        action_layout.setSpacing(4)
        
        details_button = PushButton("详情", action_widget)
        details_button.setIcon(FluentIcon.INFO)
        details_button.clicked.connect(lambda: self.show_draft_details_by_uuid(draft.uuid))
        action_layout.addWidget(details_button)
        
        open_button = PushButton("打开", action_widget)
        open_button.setIcon(FluentIcon.FOLDER)
        open_button.clicked.connect(lambda: self.open_draft_by_uuid(draft.uuid))
        open_button.setEnabled(draft.status == "completed")
        action_layout.addWidget(open_button)
        
        delete_button = PushButton("删除", action_widget)
        delete_button.setIcon(FluentIcon.DELETE)
        delete_button.clicked.connect(lambda: self.delete_draft(draft.uuid))
        action_layout.addWidget(delete_button)
        
        self.table.setCellWidget(row, 6, action_widget)
        
    def update_pagination(self):
        """Update pagination controls"""
        # Calculate total pages
        total_drafts = self.draft_service.get_total_drafts_count()
        self.total_pages = (total_drafts + self.page_size - 1) // self.page_size
        
        # Update page label
        self.page_label.setText(f"第 {self.current_page} 页 / 共 {self.total_pages} 页")
        
        # Update button states
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)
        
    def show_context_menu(self, position):
        """
        Show context menu for draft
        
        Args:
            position (QPoint): Position where to show the menu
        """
        # Get selected item
        row = self.table.rowAt(position.y())
        if row < 0:
            return
            
        # Get draft UUID
        uuid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not uuid:
            return
            
        # Create menu
        menu = QMenu(self)
        
        # Add actions
        details_action = QAction("查看详情", self)
        details_action.triggered.connect(lambda: self.show_draft_details_by_uuid(uuid))
        menu.addAction(details_action)
        
        # Get draft to check status
        draft = self.draft_service.get_draft_by_uuid(uuid)
        if draft and draft.status == "completed":
            open_action = QAction("打开草稿箱", self)
            open_action.triggered.connect(lambda: self.open_draft_by_uuid(uuid))
            menu.addAction(open_action)
            
        menu.addSeparator()
        
        delete_action = QAction("删除草稿箱", self)
        delete_action.triggered.connect(lambda: self.delete_draft(uuid))
        menu.addAction(delete_action)
        
        # Show menu
        menu.exec(self.table.mapToGlobal(position))
        
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
        # Get draft
        draft = self.draft_service.get_draft_by_uuid(uuid)
        
        if not draft:
            self.show_message("找不到草稿箱", "error")
            return
            
        # Show details
        self.show_draft_details(draft)
        
    def open_draft(self, draft):
        """
        Open draft in file explorer
        
        Args:
            draft (DraftModel): Draft model
        """
        if not draft.local_path or not os.path.exists(draft.local_path):
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
            
    def open_draft_by_uuid(self, uuid):
        """
        Open draft in file explorer by UUID
        
        Args:
            uuid (str): Draft UUID
        """
        # Get draft
        draft = self.draft_service.get_draft_by_uuid(uuid)
        
        if not draft:
            self.show_message("找不到草稿箱", "error")
            return
            
        # Open draft
        self.open_draft(draft)
        
    def delete_draft(self, uuid):
        """
        Delete draft
        
        Args:
            uuid (str): Draft UUID
        """
        # Get draft
        draft = self.draft_service.get_draft_by_uuid(uuid)
        
        if not draft:
            self.show_message("找不到草稿箱", "error")
            return
            
        # Confirm deletion
        ok = MessageBox(
            "确认删除",
            f"确定要删除草稿箱 \"{draft.name}\" 吗？\n\n此操作不可撤销。",
            self
        ).exec()
        
        if not ok:
            return
            
        try:
            # Delete draft
            self.draft_service.delete_draft(uuid)
            
            # Reload drafts
            self.load_drafts()
            
            # Show success message
            self.show_message(f"草稿箱 \"{draft.name}\" 已删除", "success")
            
        except Exception as e:
            self.logger.error("Failed to delete draft: %s", e)
            self.show_message(f"删除草稿箱失败: {e}", "error")
            
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