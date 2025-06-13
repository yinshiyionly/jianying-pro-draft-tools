# 剪映专业版草稿箱管理工具

这是一个用于管理剪映专业版草稿箱的桌面应用程序。它允许用户下载、管理和打开剪映专业版的草稿箱项目。

## 功能特点

- 通过UUID下载草稿箱
- 管理本地草稿箱列表
- 查看草稿箱详情
- 打开本地草稿箱文件夹
- 实时显示下载进度
- 支持暂停、取消和继续下载
- 支持多草稿箱并行下载

## 系统要求

- Python 3.8+
- PyQt6
- MySQL数据库（用于本地存储）
- 支持的操作系统：Windows、macOS、Linux
- 支持的CPU架构：x86_64、ARM64

## 安装

### 预编译版本

你可以直接下载适合你系统的预编译版本：

- Windows: 
  - [Windows x64版本](https://github.com/yourusername/jianying-pro-draft-tools/releases)
  - [Windows ARM64版本](https://github.com/yourusername/jianying-pro-draft-tools/releases)
- macOS:
  - [macOS x64版本](https://github.com/yourusername/jianying-pro-draft-tools/releases)
  - [macOS Apple Silicon (ARM64)版本](https://github.com/yourusername/jianying-pro-draft-tools/releases) 
- Linux:
  - [Linux x64 (AppImage)](https://github.com/yourusername/jianying-pro-draft-tools/releases)
  - [Linux x64 (DEB)](https://github.com/yourusername/jianying-pro-draft-tools/releases)
  - [Linux ARM64 (AppImage)](https://github.com/yourusername/jianying-pro-draft-tools/releases)

### 从源码安装

1. 克隆仓库

```bash
git clone https://github.com/yourusername/jianying-pro-draft-tools.git
cd jianying-pro-draft-tools
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 配置数据库

在`.env`文件中配置数据库连接信息：

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=draft_box
```

4. 运行应用程序

```bash
python main.py
```

## 项目结构

```
jianying-pro-draft-tools/
├── config/                # 配置模块
│   ├── __init__.py
│   ├── database.py        # 数据库配置
│   └── settings.py        # 应用程序设置
├── handlers/              # 事件处理器
│   ├── __init__.py
│   ├── exception_handler.py  # 异常处理器
│   └── message_handler.py    # 消息处理器
├── models/                # 数据模型
│   ├── __init__.py
│   ├── draft_model.py     # 草稿箱模型
│   └── download_task.py   # 下载任务模型
├── services/              # 服务层
│   ├── __init__.py
│   ├── api_service.py     # API服务
│   ├── database_service.py  # 数据库服务
│   ├── download_service.py  # 下载服务
│   └── draft_service.py   # 草稿箱服务
├── ui/                    # 用户界面
│   ├── __init__.py
│   ├── components/        # UI组件
│   ├── draft_list_panel.py  # 草稿箱列表面板
│   ├── download_panel.py  # 下载面板
│   ├── main_window.py     # 主窗口
│   └── sidebar.py         # 侧边栏
├── utils/                 # 工具函数
│   ├── __init__.py
│   ├── file_utils.py      # 文件工具
│   └── logger.py          # 日志工具
├── workers/               # 后台工作线程
│   ├── __init__.py
│   └── download_worker.py # 下载工作线程
├── resources/             # 资源文件
│   ├── icons/             # 图标
│   ├── styles/            # 样式表
│   └── sounds/            # 音效
├── .env                   # 环境变量配置
├── main.py                # 应用程序入口
├── requirements.txt       # 依赖列表
└── README.md              # 项目说明
```

## 使用方法

1. 下载草稿箱

   - 在"下载草稿箱"标签页中，输入草稿箱UUID
   - 选择保存路径
   - 点击"下载草稿箱"按钮

2. 管理草稿箱

   - 在"草稿箱列表"标签页中，可以查看所有已下载的草稿箱
   - 可以按状态筛选草稿箱
   - 可以搜索草稿箱
   - 可以查看草稿箱详情、打开草稿箱文件夹或删除草稿箱

## 开发

### 环境设置

1. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. 安装开发依赖

```bash
pip install -r requirements-dev.txt
```

### 运行测试

```bash
pytest
```

## 许可证

[MIT](LICENSE)

## 贡献

欢迎贡献代码、报告问题或提出改进建议。请遵循以下步骤：

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 打包

本项目提供了针对多种操作系统和CPU架构的打包脚本。

### 打包前准备

确保已安装PyInstaller:

```bash
pip install pyinstaller
```

对于macOS平台，如果需要创建DMG安装包，请安装create-dmg:

```bash
brew install create-dmg
```

对于Linux平台，如果需要创建AppImage，请下载appimagetool:

```bash
# 下载appimagetool
wget "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" -O appimagetool
chmod +x appimagetool
sudo mv appimagetool /usr/local/bin/
```

### Windows打包

打包Windows x64版本:

```bash
cd build_scripts
python build_windows.py
```

打包Windows ARM64版本:

```bash
cd build_scripts
python build_arm.py  # 在Windows ARM设备上运行
```

### macOS打包

打包macOS x64版本:

```bash
cd build_scripts
python build_macos.py
```

打包macOS ARM64版本 (Apple Silicon):

```bash
cd build_scripts
python build_arm.py  # 在M1/M2 Mac上运行
```

### Linux打包

打包Linux x64版本:

```bash
cd build_scripts
python build_linux.py
```

打包Linux ARM64版本:

```bash
cd build_scripts
python build_arm.py  # 在Linux ARM设备上运行
```

### 打包输出

打包后的文件将位于项目根目录的`dist`文件夹中，按平台和架构分类:

- Windows: `dist/windows/`
- macOS: `dist/macos/`
- Linux: `dist/linux/`
- ARM架构: `dist/arm-windows/`, `dist/arm-darwin/`, `dist/arm-linux/`

## 多架构适配说明

本项目支持x86_64和ARM64架构。注意事项:

1. ARM64版本需要在对应的ARM设备上构建
2. PyQt6在不同架构上可能有细微差异，已在代码中处理
3. 数据库连接在ARM设备上可能需要特殊配置，请参考MySQL文档

## 常见问题

### Q: 在ARM设备上打包失败怎么办?
A: 确保已安装ARM版本的Python和依赖库。某些库可能需要从源码编译。

### Q: 支持哪些ARM设备?
A: 支持Windows ARM (如Surface Pro X)、Apple Silicon Mac (M1/M2)、树莓派4及其他ARM Linux设备。

### Q: 如何确认我的系统架构?
A: 
- Windows: 在命令提示符中运行 `echo %PROCESSOR_ARCHITECTURE%`
- macOS/Linux: 在终端中运行 `uname -m`

## 国际化支持

本应用程序默认使用中文界面，但已准备好支持多语言。翻译文件位于`resources/translations/`目录。
