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
