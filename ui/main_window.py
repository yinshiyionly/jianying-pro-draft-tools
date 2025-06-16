#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QApplication
)
from PyQt6.QtCore import Qt, QSize, QTimer, QSettings
from PyQt6.QtGui import QIcon, QAction

from qfluentwidgets import (
    NavigationInterface, NavigationItemPosition, MSFluentWindow,
    SubtitleLabel, setTheme, Theme, FluentIcon, InfoBar, InfoBarPosition
)
from config.settings import get_setting, get_int_setting, get_bool_setting
from ui.sidebar import Sidebar
from ui.download_panel import DownloadPanel
from ui.draft_list_panel import DraftListPanel
from handlers.message_handler import MessageHandler

class MainWindow(MSFluentWindow):
    """Main application window using Fluent Design"""
    
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
        
        # Apply fluent theme
        setTheme(Theme.AUTO)
        
        # Create panels
        self.download_panel = DownloadPanel(self)
        self.draft_list_panel = DraftListPanel(self)
        
        # Add items to navigation interface
        self.navigation_interface.addItem(
            routeKey='download',
            icon=FluentIcon.DOWNLOAD,
            text='下载草稿箱',
            position=NavigationItemPosition.TOP
        )
        
        self.navigation_interface.addItem(
            routeKey='draft_list',
            icon=FluentIcon.DOCUMENT,
            text='草稿箱列表',
            position=NavigationItemPosition.TOP
        )
        
        self.navigation_interface.addItem(
            routeKey='settings',
            icon=FluentIcon.SETTING,
            text='设置',
            position=NavigationItemPosition.BOTTOM
        )
        
        # Add sub interfaces
        self.addSubInterface(
            interface=self.download_panel,
            routeKey='download',
            title='下载草稿箱'
        )
        
        self.addSubInterface(
            interface=self.draft_list_panel,
            routeKey='draft_list',
            title='草稿箱列表'
        )
        
        # Set default route
        self.navigation_interface.setCurrentItem('download')
        
        # Add app version label to status bar
        self.statusBar().showMessage(f"版本: {get_setting('APP_VERSION', '1.0.0')}")
        
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
        Show a message using Fluent InfoBar
        
        Args:
            message (str): Message to display
            message_type (str): Type of message (info, success, warning, error)
            duration (int): Duration in milliseconds
        """
        # Map message type to InfoBar type
        title = "信息"
        icon = None
        
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
        
        # Show InfoBar
        InfoBar.success(
            title=title,
            content=message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=duration,
            parent=self
        )
        
        # Also show in status bar
        self.statusBar().showMessage(message, duration) 