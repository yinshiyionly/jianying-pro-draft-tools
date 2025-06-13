#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QStatusBar, QMessageBox, QSystemTrayIcon,
    QMenu, QApplication
)
from PyQt6.QtCore import Qt, QSize, QTimer, QSettings
from PyQt6.QtGui import QIcon, QAction

from config.settings import get_setting, get_int_setting, get_bool_setting
from ui.sidebar import Sidebar
from ui.download_panel import DownloadPanel
from ui.draft_list_panel import DraftListPanel
from handlers.message_handler import MessageHandler

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        """Initialize the main window"""
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self.settings = QSettings("JianYingPro", "DraftTools")
        
        # Initialize UI components
        self.message_handler = MessageHandler(self)
        self.setup_ui()
        
        # Load window state
        self.load_window_state()
        
        # Set up system tray if enabled
        if get_bool_setting('ENABLE_SYSTEM_TRAY', True):
            self.setup_system_tray()
            
        self.logger.info("Main window initialized")
        
    def setup_ui(self):
        """Set up the user interface"""
        # Set window properties
        self.setWindowTitle(get_setting('APP_NAME', '草稿箱管理系统'))
        self.setMinimumSize(
            get_int_setting('WINDOW_MIN_WIDTH', 800),
            get_int_setting('WINDOW_MIN_HEIGHT', 600)
        )
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = Sidebar(self)
        main_layout.addWidget(self.sidebar)
        
        # Create content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setMovable(True)
        
        # Create download panel
        self.download_panel = DownloadPanel(self)
        self.tab_widget.addTab(self.download_panel, "下载草稿箱")
        
        # Create draft list panel
        self.draft_list_panel = DraftListPanel(self)
        self.tab_widget.addTab(self.draft_list_panel, "草稿箱列表")
        
        # Add tab widget to content layout
        content_layout.addWidget(self.tab_widget)
        
        # Add content widget to main layout
        main_layout.addWidget(content_widget)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Show initial status
        self.status_bar.showMessage("就绪")
        
    def setup_system_tray(self):
        """Set up system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip(get_setting('APP_NAME', '草稿箱管理系统'))
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Add actions to menu
        show_action = QAction("显示", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("隐藏", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        tray_menu.addAction(exit_action)
        
        # Set tray icon and menu
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Show tray icon
        self.tray_icon.show()
        
    def tray_icon_activated(self, reason):
        """
        Handle tray icon activation
        
        Args:
            reason (QSystemTrayIcon.ActivationReason): Activation reason
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
                
    def save_window_state(self):
        """Save window state to settings"""
        if get_bool_setting('AUTO_SAVE_WINDOW_STATE', True):
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())
            self.settings.setValue("maximized", self.isMaximized())
            
    def load_window_state(self):
        """Load window state from settings"""
        if get_bool_setting('AUTO_SAVE_WINDOW_STATE', True):
            # Restore window geometry
            if self.settings.contains("geometry"):
                self.restoreGeometry(self.settings.value("geometry"))
            else:
                # Set default size
                self.resize(
                    get_int_setting('WINDOW_WIDTH', 1200),
                    get_int_setting('WINDOW_HEIGHT', 800)
                )
                
            # Restore window state
            if self.settings.contains("windowState"):
                self.restoreState(self.settings.value("windowState"))
                
            # Restore maximized state
            if self.settings.contains("maximized") and self.settings.value("maximized", type=bool):
                self.showMaximized()
                
    def closeEvent(self, event):
        """
        Handle window close event
        
        Args:
            event (QCloseEvent): Close event
        """
        # Check if confirmation is required
        if get_bool_setting('CONFIRM_EXIT', True):
            # Ask for confirmation
            reply = QMessageBox.question(
                self,
                "确认退出",
                "确定要退出应用程序吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
                
        # Save window state
        self.save_window_state()
        
        # Hide system tray icon
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
            
        # Accept the event
        event.accept()
        
    def show_message(self, message, message_type="info", duration=3000):
        """
        Show a message in the status bar and as a toast notification
        
        Args:
            message (str): Message to display
            message_type (str): Type of message (info, success, warning, error)
            duration (int): Duration in milliseconds
        """
        # Show in status bar
        self.status_bar.showMessage(message, duration)
        
        # Show as toast notification
        if message_type == "info":
            self.message_handler.show_info(message, duration)
        elif message_type == "success":
            self.message_handler.show_success(message, duration)
        elif message_type == "warning":
            self.message_handler.show_warning(message, duration)
        elif message_type == "error":
            self.message_handler.show_error(message, duration) 