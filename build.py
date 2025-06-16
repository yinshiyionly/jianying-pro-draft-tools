#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
打包脚本 - 用于将应用程序打包为Windows可执行文件
使用方法：在Windows环境中运行 python build.py
"""

import os
import sys
import subprocess
import shutil

APP_NAME = "草稿箱管理系统"
APP_VERSION = "1.0.0"

def clean_build_dirs():
    """清理构建目录"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)

def build_app():
    """构建应用程序"""
    print("开始构建应用程序...")
    
    # PyInstaller命令和参数
    pyinstaller_cmd = [
        "pyinstaller",
        "--name", APP_NAME,
        "--windowed",  # 无控制台窗口
        "--icon=assets/icon.ico",  # 应用图标，请确保此路径存在
        "--add-data", "assets;assets",  # 添加资源文件
        "--hidden-import", "PyQt6.QtSvg",  # 添加隐式导入
        "--hidden-import", "PyQt6.QtXml",
        "--log-level", "INFO",
        "--clean",  # 每次构建前清理
        "--noconfirm",  # 不提示确认
        "main.py"  # 主程序入口
    ]
    
    # 执行PyInstaller命令
    result = subprocess.run(pyinstaller_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("构建失败!")
        print("错误信息:")
        print(result.stderr)
        return False
    
    print("构建成功!")
    print(f"可执行文件位置: dist/{APP_NAME}/{APP_NAME}.exe")
    return True

def create_installer():
    """创建安装程序 (需要Inno Setup)"""
    print("暂未实现安装程序创建功能")
    print("提示: 您可以使用Inno Setup创建安装程序")

def main():
    """主函数"""
    # 检查是否在Windows环境中运行
    if sys.platform != "win32":
        print("警告: 此脚本设计用于Windows环境中运行")
        response = input("是否继续? (y/n): ")
        if response.lower() != 'y':
            return
    
    # 清理构建目录
    clean_build_dirs()
    
    # 构建应用程序
    if build_app():
        # 可选: 创建安装程序
        create_installer_choice = input("是否创建安装程序? (y/n): ")
        if create_installer_choice.lower() == 'y':
            create_installer()

if __name__ == "__main__":
    main() 