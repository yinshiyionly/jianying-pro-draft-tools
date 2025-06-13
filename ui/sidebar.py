#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont

from config.settings import get_setting

class SidebarButton(QPushButton):
    """Custom sidebar button with icon and text"""
    
    def __init__(self, text, parent=None):
        """Initialize the sidebar button"""
        super().__init__(text, parent)
        
        # Set button style
        self.setFixedHeight(50)
        self.setIconSize(QSize(24, 24))
        self.setFont(QFont("Arial", 10))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Set style sheet
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 20px;
                border: none;
                background-color: transparent;
                color: #333333;
            }
            
            QPushButton:hover {
                background-color: #E0E0E0;
            }
            
            QPushButton:pressed {
                background-color: #CCCCCC;
            }
            
            QPushButton:checked {
                background-color: #D0D0D0;
                font-weight: bold;
            }
        """)
        
        # Make checkable
        self.setCheckable(True)

class Sidebar(QFrame):
    """Sidebar widget with navigation buttons"""
    
    def __init__(self, parent=None):
        """Initialize the sidebar"""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        self.parent = parent
        
        # Set up UI
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface"""
        # Set frame style
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setFixedWidth(200)
        
        # Set style sheet
        self.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-right: 1px solid #E0E0E0;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Add app title
        title_label = QLabel(get_setting('APP_NAME', '草稿箱管理系统'))
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("padding: 20px 0;")
        layout.addWidget(title_label)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #E0E0E0;")
        layout.addWidget(separator)
        
        # Add navigation buttons
        self.download_button = SidebarButton("下载草稿箱")
        self.download_button.setChecked(True)
        self.download_button.clicked.connect(lambda: self.switch_tab(0))
        layout.addWidget(self.download_button)
        
        self.draft_list_button = SidebarButton("草稿箱列表")
        self.draft_list_button.clicked.connect(lambda: self.switch_tab(1))
        layout.addWidget(self.draft_list_button)
        
        self.settings_button = SidebarButton("设置")
        self.settings_button.clicked.connect(self.show_settings)
        layout.addWidget(self.settings_button)
        
        # Add spacer
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Add version label
        version_label = QLabel(f"版本: {get_setting('APP_VERSION', '1.0.0')}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("padding: 10px 0; color: #999999;")
        layout.addWidget(version_label)
        
    def switch_tab(self, index):
        """
        Switch to the specified tab
        
        Args:
            index (int): Tab index
        """
        # Update button states
        self.download_button.setChecked(index == 0)
        self.draft_list_button.setChecked(index == 1)
        self.settings_button.setChecked(False)
        
        # Switch tab
        if hasattr(self.parent, 'tab_widget'):
            self.parent.tab_widget.setCurrentIndex(index)
            
    def show_settings(self):
        """Show settings dialog"""
        # Update button states
        self.download_button.setChecked(False)
        self.draft_list_button.setChecked(False)
        self.settings_button.setChecked(True)
        
        # TODO: Show settings dialog
        self.logger.info("Settings button clicked") 