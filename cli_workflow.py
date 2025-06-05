import json
import base64
import tempfile
import os
import time
import argparse
import sys
import pyautogui
from KeyleFinderModule import KeyleFinderModule

if sys.platform == 'darwin':
    from pynput.mouse import Controller as _Mouse
    _mouse = _Mouse()

    def move_mouse(x, y):
        _mouse.position = (x, y)
else:
    def move_mouse(x, y):
        pyautogui.moveTo(x, y)


def load_items(config_path):
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
    for item in items:
        path = item['path']
        if path.startswith(tempfile.gettempdir()) and os.path.exists(path):
            os.unlink(path)


def run_workflow(items, debug=False, loop=False, interval=0.5):
    try:
        while True:
            screenshot = pyautogui.screenshot()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                screenshot.save(tmp.name)
                screen_path = tmp.name
            finder = KeyleFinderModule(screen_path)
            idx = 0
            while idx < len(items):
                item = items[idx]
                if not item.get('enable', True):
                    idx += 1
                    continue
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
                        time.sleep(1)
                        pyautogui.mouseUp()
                    else:
                        pyautogui.click()
                    print(f'Item {idx} matched at {center_x},{center_y}')
                    time.sleep(item.get('delay', 0) / 1000.0)
                    idx += 1
                else:
                    print(f'Item {idx} match failed')
                    if item.get('interrupt'):
                        idx = 0
                    else:
                        idx += 1
            os.unlink(screen_path)
            if not loop:
                break
            time.sleep(interval)
    finally:
        cleanup_items(items)


def main():
    parser = argparse.ArgumentParser(description='Run AutoClick workflow from a JSON file')
    parser.add_argument('config', help='JSON workflow file exported from the GUI')
    parser.add_argument('--debug', action='store_true', help='show debug preview windows')
    parser.add_argument('--loop', action='store_true', help='repeat workflow until interrupted')
    parser.add_argument('--interval', type=float, default=0.5, help='delay between loops in seconds')
    parser.add_argument('--disable-failsafe', action='store_true',
                        help='disable PyAutoGUI fail-safe (use with caution)')
    args = parser.parse_args()

    if args.disable_failsafe:
        pyautogui.FAILSAFE = False

    items = load_items(args.config)
    run_workflow(items, debug=args.debug, loop=args.loop, interval=args.interval)


if __name__ == '__main__':
    main()
