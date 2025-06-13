#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import traceback
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox
from config.settings import get_bool_setting

class ExceptionHandler(QObject):
    """Global exception handler for the application"""
    
    exception_raised = pyqtSignal(str, str)  # message, traceback
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.show_detailed_errors = get_bool_setting('SHOW_DETAILED_ERRORS', True)
        
        # Connect signal to show error dialog
        self.exception_raised.connect(self.show_error_dialog)
        
    def install(self):
        """Install this exception handler as the global exception handler"""
        sys.excepthook = self.handle_exception
        self.logger.info("Global exception handler installed")
        
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handle uncaught exceptions
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        # Log the exception
        self.logger.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Format traceback as string
        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        # Get error message
        error_msg = str(exc_value)
        
        # Emit signal to show error dialog
        self.exception_raised.emit(error_msg, tb_str)
        
    def show_error_dialog(self, message, traceback_str):
        """
        Show error dialog with exception details
        
        Args:
            message (str): Error message
            traceback_str (str): Formatted traceback
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("应用程序错误")
        msg_box.setText("发生了一个未处理的错误")
        msg_box.setInformativeText(message)
        
        if self.show_detailed_errors:
            msg_box.setDetailedText(traceback_str)
            
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        
    def handle_database_error(self, error):
        """
        Handle database-specific errors
        
        Args:
            error: Database error
        
        Returns:
            bool: True if user wants to retry, False otherwise
        """
        self.logger.error("Database error: %s", error)
        
        if "timeout" in str(error).lower():
            return self.show_retry_dialog(
                "数据库连接超时", 
                "数据库响应时间过长，是否重试？"
            )
        elif "access denied" in str(error).lower():
            self.show_error_dialog(
                "数据库访问被拒绝",
                "请检查用户名和密码配置"
            )
            return False
        else:
            self.show_error_dialog(
                "数据库错误",
                str(error)
            )
            return False
            
    def handle_network_error(self, error):
        """
        Handle network-specific errors
        
        Args:
            error: Network error
        
        Returns:
            bool: True if user wants to retry, False otherwise
        """
        self.logger.error("Network error: %s", error)
        
        error_str = str(error).lower()
        if "timeout" in error_str:
            return self.show_retry_dialog(
                "网络连接超时", 
                "服务器响应时间过长，是否重试？"
            )
        elif "connection refused" in error_str:
            return self.show_retry_dialog(
                "连接被拒绝", 
                "无法连接到服务器，是否重试？"
            )
        elif "name resolution" in error_str:
            self.show_error_dialog(
                "DNS解析失败",
                "无法解析服务器地址，请检查网络设置和域名配置"
            )
            return False
        else:
            self.show_error_dialog(
                "网络错误",
                str(error)
            )
            return False
    
    def show_retry_dialog(self, title, message):
        """
        Show a retry dialog
        
        Args:
            title (str): Dialog title
            message (str): Dialog message
        
        Returns:
            bool: True if user clicked Retry, False otherwise
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Retry | 
            QMessageBox.StandardButton.Cancel
        )
        return msg_box.exec() == QMessageBox.StandardButton.Retry

def setup_exception_handler(app):
    """
    Setup the global exception handler for the application
    
    Args:
        app (QApplication): The application instance
    
    Returns:
        ExceptionHandler: The exception handler instance
    """
    handler = ExceptionHandler(app)
    handler.install()
    return handler 