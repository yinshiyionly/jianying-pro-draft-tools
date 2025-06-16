#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import FluentWindow, PushButton, setTheme, Theme

def main():
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置主题
    setTheme(Theme.AUTO)
    
    # 创建窗口
    window = FluentWindow()
    window.setWindowTitle("测试窗口")
    
    # 创建中心小部件
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    # 添加标签
    label = QLabel("这是一个测试窗口")
    layout.addWidget(label)
    
    # 添加按钮
    button = PushButton("测试按钮")
    button.clicked.connect(lambda: label.setText("按钮已点击"))
    layout.addWidget(button)
    
    # 设置中心小部件
    window.setCentralWidget(central_widget)
    
    # 显示窗口
    window.resize(400, 300)
    window.show()
    
    # 启动应用程序事件循环
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 