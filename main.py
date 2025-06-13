#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTranslator, QLocale
from config.settings import load_settings
from ui.main_window import MainWindow
from utils.logger import setup_logger
from handlers.exception_handler import setup_exception_handler

def main():
    """Application entry point"""
    # Load environment settings
    load_settings()
    
    # Setup logging
    logger = setup_logger()
    logger.info("Application starting...")
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName(os.getenv('APP_NAME', '草稿箱管理系统'))
    app.setApplicationVersion(os.getenv('APP_VERSION', '1.0.0'))
    
    # Setup exception handler
    setup_exception_handler(app)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 