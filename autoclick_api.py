import os
import sys
import json
import base64
import tempfile
import time
import pyautogui
from KeyleFinderModule import KeyleFinderModule

if sys.platform == 'darwin':
    from pynput.mouse import Controller as _Mouse
    _mouse = _Mouse()

    def move_mouse(x: int, y: int) -> None:
        _mouse.position = (x, y)
else:
    def move_mouse(x: int, y: int) -> None:
        pyautogui.moveTo(x, y)

def load_items(config_path: str):
    """Load workflow items from a JSON configuration."""
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = []
    for entry in data:
        if 'image' in entry:
            img_data = base64.b64decode(entry['image'])
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            tmp.write(img_data)
            tmp.close()
            path = tmp.name
        else:
            path = entry['path']
        item = {
            'path': path,
            'action': entry.get('action', 'single' if not entry.get('double_click') else 'double'),
            'delay': entry.get('delay', 0),
            'interrupt': entry.get('interrupt', False),
            'enable': entry.get('enable', True)
        }
        items.append(item)
    return items

def cleanup_items(items):
    """Remove temporary files created for items."""
    for item in items:
        path = item['path']
        if path.startswith(tempfile.gettempdir()) and os.path.exists(path):
            os.unlink(path)

def run_workflow(items, debug=False, loop=False, interval=0.5):
    """Execute the workflow items until completion or interruption."""
    long_press_active = False
    long_press_pos = None
    try:
        while True:
            idx = 0
            while idx < len(items):
                item = items[idx]
                if not item.get('enable', True):
                    idx += 1
                    continue

                if long_press_active:
                    if pyautogui.position() != long_press_pos:
                        pyautogui.mouseUp()
                        long_press_active = False

                if long_press_active and item.get('action') != 'long':
                    pyautogui.mouseUp()
                    long_press_active = False

                screenshot = pyautogui.screenshot()
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                    screenshot.save(tmp.name)
                    screen_path = tmp.name
                finder = KeyleFinderModule(screen_path)
                result = finder.locate(item['path'], debug=debug)
                if result.get('status') == 0:
                    tl = result['top_left']
                    br = result['bottom_right']
                    center_x = (tl[0] + br[0]) // 2
                    center_y = (tl[1] + br[1]) // 2
                    move_mouse(center_x, center_y)
                    if item.get('action') == 'double':
                        pyautogui.click(clicks=2)
                    elif item.get('action') == 'long':
                        pyautogui.mouseDown()
                        long_press_active = True
                        long_press_pos = pyautogui.position()
                    else:
                        pyautogui.click()
                    idx += 1
                else:
                    if item.get('interrupt'):
                        idx = 0
                    else:
                        idx += 1
                os.unlink(screen_path)
                delay = item.get('delay', 0) / 1000.0
                time.sleep(delay)
            if long_press_active:
                pyautogui.mouseUp()
                long_press_active = False
            if not loop:
                break
            time.sleep(interval)
    finally:
        cleanup_items(items)
