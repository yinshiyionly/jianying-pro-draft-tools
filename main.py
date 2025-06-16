#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from PyQt6.QtWidgets import QApplication

# 在所有导入之前创建QApplication实例
app = QApplication(sys.argv)

# 在这之后导入其他模块
from PyQt6.QtCore import QTranslator, QLocale
from PyQt6.QtGui import QFont, QFontDatabase
from qfluentwidgets import setTheme, Theme

# 现在可以安全地导入配置和日志模块
from config.settings import load_settings, get_setting
from utils.logger import setup_logger
from handlers.exception_handler import setup_exception_handler

def main():
    """Application entry point"""
    # 加载环境设置
    load_settings()
    
    # 设置日志
    logger = setup_logger()
    logger.info("Application starting...")
    
    # 设置应用程序名称和版本
    app.setApplicationName(get_setting('APP_NAME', '草稿箱管理系统'))
    app.setApplicationVersion(get_setting('APP_VERSION', '1.0.0'))
    
    # 设置应用程序字体
    # 尝试加载系统中的中文字体
    font_families = ["Microsoft YaHei", "WenQuanYi Micro Hei", "SimSun", "Noto Sans CJK SC", "Noto Sans SC"]
    
    default_font = None
    available_families = QFontDatabase.families()
    for family in font_families:
        font = QFont(family)
        if font.exactMatch() or family in available_families:
            default_font = font
            logger.info(f"使用字体: {family}")
            break
    
    if default_font:
        app.setFont(default_font)
    else:
        logger.warning("找不到合适的中文字体，请安装中文字体包")
    
    # 设置Fluent Design主题
    setTheme(Theme.AUTO)
    
    # 设置异常处理器
    setup_exception_handler(app)
    
    # 最后再导入MainWindow
    from ui.main_window import MainWindow
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 启动应用程序事件循环
    sys.exit(app.exec())

if __name__ == "__main__":
    main()