#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, Qt
from PyQt6.QtWidgets import QMessageBox, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QColor, QPalette, QFont
from config.settings import get_bool_setting

class ToastNotification(QWidget):
    """Toast notification widget that appears at the bottom right of the screen"""
    
    def __init__(self, parent=None, message="", message_type="info", duration=3000):
        super().__init__(parent)
        
        # Set window flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Set up layout
        layout = QVBoxLayout(self)
        
        # Create message label
        self.label = QLabel(message)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set font
        font = QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        
        # Add label to layout
        layout.addWidget(self.label)
        
        # Set style based on message type
        self.set_style(message_type)
        
        # Set size
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)
        
        # Set up timer to close the notification
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.timer.start(duration)
        
        # Position the notification
        self.position_notification()
        
    def set_style(self, message_type):
        """Set the style of the notification based on the message type"""
        base_style = """
            QWidget {
                border-radius: 6px;
                padding: 10px;
            }
        """
        
        if message_type == "info":
            style = base_style + """
                background-color: #2196F3;
                color: white;
            """
        elif message_type == "success":
            style = base_style + """
                background-color: #4CAF50;
                color: white;
            """
        elif message_type == "warning":
            style = base_style + """
                background-color: #FF9800;
                color: white;
            """
        elif message_type == "error":
            style = base_style + """
                background-color: #F44336;
                color: white;
            """
        else:
            style = base_style + """
                background-color: #2196F3;
                color: white;
            """
            
        self.setStyleSheet(style)
        
    def position_notification(self):
        """Position the notification at the bottom right of the screen"""
        if self.parentWidget():
            parent_rect = self.parentWidget().geometry()
            x = parent_rect.width() - self.width() - 20
            y = parent_rect.height() - self.height() - 20
            self.move(x, y)

class MessageHandler(QObject):
    """Message handler for displaying various types of notifications"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.parent = parent
        self.toast_queue = []
        self.current_toast = None
        self.enable_sound = get_bool_setting('ENABLE_SOUND_NOTIFICATIONS', True)
        
    def show_toast(self, message, message_type="info", duration=3000):
        """
        Show a toast notification
        
        Args:
            message (str): Message to display
            message_type (str): Type of message (info, success, warning, error)
            duration (int): Duration in milliseconds
        """
        self.logger.debug("Showing toast: %s (%s)", message, message_type)
        
        # Add to queue
        self.toast_queue.append((message, message_type, duration))
        
        # If no toast is currently showing, show this one
        if not self.current_toast:
            self._show_next_toast()
            
    def _show_next_toast(self):
        """Show the next toast in the queue"""
        if not self.toast_queue:
            self.current_toast = None
            return
            
        # Get the next toast from the queue
        message, message_type, duration = self.toast_queue.pop(0)
        
        # Create and show the toast
        toast = ToastNotification(
            self.parent,
            message,
            message_type,
            duration
        )
        toast.show()
        
        # Set as current toast
        self.current_toast = toast
        
        # Connect to the destroyed signal to show the next toast
        toast.destroyed.connect(self._show_next_toast)
        
    def show_info(self, message, duration=3000):
        """
        Show an info message
        
        Args:
            message (str): Message to display
            duration (int): Duration in milliseconds
        """
        self.show_toast(message, "info", duration)
        
    def show_success(self, message, duration=3000):
        """
        Show a success message
        
        Args:
            message (str): Message to display
            duration (int): Duration in milliseconds
        """
        self.show_toast(message, "success", duration)
        if self.enable_sound:
            self.play_sound('success')
            
    def show_warning(self, message, duration=4000):
        """
        Show a warning message
        
        Args:
            message (str): Message to display
            duration (int): Duration in milliseconds
        """
        self.show_toast(message, "warning", duration)
        if self.enable_sound:
            self.play_sound('warning')
            
    def show_error(self, message, details=None, duration=5000):
        """
        Show an error message
        
        Args:
            message (str): Message to display
            details (str, optional): Detailed error message
            duration (int): Duration in milliseconds
        """
        self.show_toast(message, "error", duration)
        
        if details and get_bool_setting('SHOW_DETAILED_ERRORS', True):
            self.show_error_dialog(message, details)
            
        if self.enable_sound:
            self.play_sound('error')
            
    def show_error_dialog(self, message, details=None):
        """
        Show an error dialog
        
        Args:
            message (str): Error message
            details (str, optional): Detailed error message
        """
        msg_box = QMessageBox(self.parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("错误")
        msg_box.setText(message)
        
        if details:
            msg_box.setDetailedText(details)
            
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        
    def show_retry_dialog(self, title, message):
        """
        Show a retry dialog
        
        Args:
            title (str): Dialog title
            message (str): Dialog message
            
        Returns:
            bool: True if user clicked Retry, False otherwise
        """
        msg_box = QMessageBox(self.parent)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Retry | 
            QMessageBox.StandardButton.Cancel
        )
        return msg_box.exec() == QMessageBox.StandardButton.Retry
        
    def show_confirm_dialog(self, title, message, default_button=QMessageBox.StandardButton.No):
        """
        Show a confirmation dialog
        
        Args:
            title (str): Dialog title
            message (str): Dialog message
            default_button: Default button (Yes or No)
            
        Returns:
            bool: True if user clicked Yes, False otherwise
        """
        msg_box = QMessageBox(self.parent)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(default_button)
        return msg_box.exec() == QMessageBox.StandardButton.Yes
        
    def play_sound(self, sound_type):
        """
        Play a sound notification
        
        Args:
            sound_type (str): Type of sound to play (success, warning, error)
        """
        # This is a placeholder for sound playback functionality
        # Implement actual sound playback using QSound or another library
        self.logger.debug("Playing sound: %s", sound_type) 