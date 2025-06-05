# AutoClick

AutoClick provides a simple way to locate a template image inside a bigger screenshot and automate mouse actions. It includes a command line example and a small GUI for managing multiple templates.

## Features

- ORB based feature matching with a template fallback
- Screenshot cropping interface for quickly creating templates
- Global hotkey to trigger searches
- Works on Windows, Linux and macOS

## Requirements

- Python 3.8+
- `opencv-python-headless`
- `numpy`
- `Pillow`
- `pyautogui`
- `keyboard` (Windows/Linux)
- `pynput` (macOS)
- On macOS the packages `pyobjc-core` and `pyobjc` are required for screenshots

Install the dependencies with:

```bash
pip install opencv-python-headless numpy Pillow pyautogui keyboard pynput pyobjc-core pyobjc
```

## Usage

Run the test script to see the matcher in action:

```bash
python KeyleFinderModuleTest.py
```

Launch the GUI tool with:

```bash
python gui_locator_multi.py
```

Press the configured hotkey (default `F2`) to scan the screen for your templates.

## CLI Workflow Tool

You can execute a sequence of template clicks directly from the command line using `cli_workflow.py`:

```bash
python cli_workflow.py workflow.json
```

`workflow.json` is compatible with files exported from the GUI. Each entry contains base64 encoded image data and an optional `double_click` flag.

## 中文简介

AutoClick 是一个自动点击工具，通过配置模板图像来实现开发者自动化工作流程。

### 功能

- 基于 ORB 的特征匹配，失败时回退到模板匹配
- 方便的截图修剪界面用于创建模板
- 全局热键触发搜索
- 支持 Windows、Linux 和 macOS

### 使用

1. `python KeyleFinderModuleTest.py`运行测试
2. `python gui_locator_multi.py`启动图形界面
3. `python cli_workflow.py workflow.json`从命令行执行工作流程
