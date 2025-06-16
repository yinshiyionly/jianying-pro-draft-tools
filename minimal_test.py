#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

# 确保最早创建QApplication
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)

# 然后导入其他组件
from PyQt6.QtWidgets import QLabel, QWidget

# 创建一个最简单的窗口
widget = QWidget()
widget.setWindowTitle("最小化测试")
label = QLabel("Hello World!", widget)
label.move(50, 50)
widget.resize(200, 100)
widget.show()

# 启动事件循环
sys.exit(app.exec()) 