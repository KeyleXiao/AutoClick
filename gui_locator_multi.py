import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import tempfile
import os
import json
import base64
import pyautogui
import sys

try:
    import keyboard as _keyboard
except Exception:
    _keyboard = None

if sys.platform == 'darwin':
    from pynput import keyboard as _pynput_keyboard

    class _MacHotkey:
        def __init__(self):
            self._listener = None

        def add_hotkey(self, key, callback):
            if self._listener:
                self._listener.stop()
            hotkey = f'<{key.lower()}>'
            self._listener = _pynput_keyboard.GlobalHotKeys({hotkey: callback})
            self._listener.start()

        def clear_all_hotkeys(self):
            if self._listener:
                self._listener.stop()
                self._listener = None

    keyboard = _MacHotkey()
else:
    keyboard = _keyboard
import time

from KeyleFinderModule import KeyleFinderModule

if sys.platform == 'darwin':
    from pynput.mouse import Controller as _Mouse
    _mouse = _Mouse()

    def move_mouse(x, y):
        _mouse.position = (x, y)
else:
    def move_mouse(x, y):
        pyautogui.moveTo(x, y)

HOTKEY = 'F2'
HOTKEY_OPTIONS = [f'F{i}' for i in range(1, 13)]


class ScreenCropper(tk.Toplevel):
    def __init__(self, master, screenshot, callback):
        super().__init__(master)
        self.callback = callback
        self.screenshot = screenshot
        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.overrideredirect(True)
        self.canvas = tk.Canvas(self, cursor='cross')
        self.canvas.pack(fill='both', expand=True)
        self.tk_img = ImageTk.PhotoImage(screenshot)
        self.canvas.create_image(0, 0, image=self.tk_img, anchor='nw')
        self.rect = None
        self.start_x = 0
        self.start_y = 0
        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)

    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2
        )

    def on_drag(self, event):
        if not self.rect:
            return
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if not self.rect:
            self.destroy()
            self.callback(None)
            return
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        if x2 - x1 < 1 or y2 - y1 < 1:
            self.destroy()
            self.callback(None)
            return
        cropped = self.screenshot.crop((x1, y1, x2, y2))
        self.destroy()
        self.callback(cropped)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Multi Locator')
        self.geometry('600x600')
        self.resizable(False, False)

        ttk.Style(self).theme_use('clam')

        self.items = []  # each item is a dict with action, delay etc
        self.debug_var = tk.BooleanVar(value=False)
        self.auto_start_var = tk.BooleanVar(value=False)
        self.loop_var = tk.BooleanVar(value=False)
        self.hotkey_var = tk.StringVar(value=HOTKEY)

        top = ttk.Frame(self)
        top.pack(fill='x', pady=5)

        add_btn = ttk.Button(top, text='➕', width=3, command=self.add_item)
        add_btn.pack(side='left', padx=2)

        start_btn = ttk.Button(top, text='▶', width=3, command=self.trigger_search)
        start_btn.pack(side='left', padx=2)

        export_btn = ttk.Button(top, text='💾', width=3, command=self.export_items)
        export_btn.pack(side='left', padx=2)

        import_btn = ttk.Button(top, text='📥', width=3, command=self.import_items)
        import_btn.pack(side='left', padx=2)

        setting_btn = ttk.Button(top, text='⚙', width=3, command=self.open_settings)
        setting_btn.pack(side='left', padx=2)

        about_btn = ttk.Button(top, text='About', command=self.show_about)
        about_btn.pack(side='right', padx=5)

        self.tree = ttk.Treeview(
            self,
            columns=('action', 'delay', 'interrupt', 'enable'),
            show='tree headings',
            height=8,
        )
        self.tree.heading('#0', text='名称')
        self.tree.column('#0', width=200)
        self.tree.heading('action', text='动作')
        self.tree.column('action', width=60, anchor='center')
        self.tree.heading('delay', text='延迟(ms)')
        self.tree.column('delay', width=70, anchor='center')
        self.tree.heading('interrupt', text='中断')
        self.tree.column('interrupt', width=50, anchor='center')
        self.tree.heading('enable', text='启用')
        self.tree.column('enable', width=50, anchor='center')
        self.tree.pack(padx=10, pady=5, fill='x')
        self.tree.bind('<Double-1>', self.on_tree_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        self.current_index = None

        self.photo_label = ttk.Label(self, text='No Image', relief='groove')
        self.photo_label.pack(padx=10, pady=5, fill='both', expand=True)
        self.photo_label.bind('<Button-1>', self.on_photo_click)

        self.log_label = ttk.Label(self, text='', foreground='gray')
        self.log_label.pack(side='bottom', fill='x')
        self.log_label.bind('<Button-1>', self.copy_log)

        self.hotkey_var.trace_add('write', self.update_hotkey)
        keyboard.add_hotkey(self.hotkey_var.get(), self.trigger_search)
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    def log(self, msg):
        self.log_label.config(text=msg)

    def copy_log(self, _):
        self.clipboard_clear()
        self.clipboard_append(self.log_label.cget('text'))

    def update_photo(self, idx):
        path = self.items[idx]['path']
        offset = self.items[idx].get('offset', [0.5, 0.5])
        if os.path.exists(path):
            img = Image.open(path)
            w, h = img.size
            dot_x = int(offset[0] * w)
            dot_y = int(offset[1] * h)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            r = 2
            draw.ellipse((dot_x - r, dot_y - r, dot_x + r, dot_y + r), fill='red')
            img.thumbnail((200, 200))
            tk_img = ImageTk.PhotoImage(img)
            self.photo_label.config(image=tk_img, text='')
            self.photo_label.image = tk_img
            self.photo_label.img_width, self.photo_label.img_height = img.size

    def on_photo_click(self, event):
        if self.current_index is None:
            return
        img_w = getattr(self.photo_label, 'img_width', None)
        img_h = getattr(self.photo_label, 'img_height', None)
        if not img_w or not img_h:
            return
        lbl_w = self.photo_label.winfo_width()
        lbl_h = self.photo_label.winfo_height()
        offset_x = event.x - (lbl_w - img_w) // 2
        offset_y = event.y - (lbl_h - img_h) // 2
        if not (0 <= offset_x <= img_w and 0 <= offset_y <= img_h):
            return
        rel_x = offset_x / img_w
        rel_y = offset_y / img_h
        self.items[self.current_index]['offset'] = [rel_x, rel_y]
        self.update_photo(self.current_index)

    def on_tree_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        self.current_index = idx
        self.update_photo(idx)

    def refresh_tree_row(self, idx):
        item_id = self.tree.get_children()[idx]
        item = self.items[idx]
        action_map = {'single': '单击', 'double': '双击', 'long': '长按'}
        self.tree.item(item_id, text=os.path.basename(item['path']))
        self.tree.set(item_id, 'action', action_map.get(item.get('action', 'single'), '单击'))
        self.tree.set(item_id, 'delay', str(item.get('delay', 0)))
        self.tree.set(item_id, 'interrupt', '✔' if item.get('interrupt') else '')
        self.tree.set(item_id, 'enable', '✔' if item.get('enable', True) else '')

    def on_tree_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id:
            return
        idx = self.tree.index(item_id)
        item = self.items[idx]
        if column == '#1':  # action
            order = ['single', 'double', 'long']
            current = item.get('action', 'single')
            item['action'] = order[(order.index(current) + 1) % 3]
        elif column == '#2':  # delay
            val = simpledialog.askinteger('Delay', 'Delay in ms:', initialvalue=item.get('delay', 0), minvalue=0)
            if val is None:
                return
            item['delay'] = val
        elif column == '#3':  # interrupt
            item['interrupt'] = not item.get('interrupt', False)
        elif column == '#4':  # enable
            item['enable'] = not item.get('enable', True)
        self.refresh_tree_row(idx)

    def add_item(self):
        self.iconify()
        time.sleep(0.2)
        screenshot = pyautogui.screenshot()
        ScreenCropper(self, screenshot, self.on_crop_done)

    def on_crop_done(self, cropped):
        self.deiconify()
        if cropped is None:
            return
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            cropped.save(tmp.name)
            path = tmp.name
        img = cropped.copy()
        img.thumbnail((200, 200))
        tk_img = ImageTk.PhotoImage(img)
        self.photo_label.config(image=tk_img, text='')
        self.photo_label.image = tk_img
        item = {
            'path': path,
            'action': 'single',
            'delay': 0,
            'interrupt': False,
            'enable': True,
            'offset': [0.5, 0.5]
        }
        self.items.append(item)
        self.tree.insert('', 'end', text=os.path.basename(path), values=('', '', '', ''))
        idx = len(self.items) - 1
        self.refresh_tree_row(idx)
        self.current_index = idx
        self.update_photo(idx)
        if self.auto_start_var.get():
            self.trigger_search()

    def export_items(self):
        if not self.items:
            messagebox.showinfo('Info', 'No items to export')
            return
        file = filedialog.asksaveasfilename(defaultextension='.json')
        if not file:
            return
        data = []
        for item in self.items:
            with open(item['path'], 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            data.append({
                'image': encoded,
                'action': item.get('action', 'single'),
                'delay': item.get('delay', 0),
                'interrupt': item.get('interrupt', False),
                'enable': item.get('enable', True),
                'offset': item.get('offset', [0.5, 0.5])
            })
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        self.log(f'Exported {len(self.items)} items to {file}')

    def import_items(self):
        file = filedialog.askopenfilename(filetypes=[('JSON', '*.json')])
        if not file:
            return
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for entry in data:
            img_data = base64.b64decode(entry['image'])
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                tmp.write(img_data)
                path = tmp.name
            item = {
                'path': path,
                'action': entry.get('action', 'single' if not entry.get('double_click') else 'double'),
                'delay': entry.get('delay', 0),
                'interrupt': entry.get('interrupt', False),
                'enable': entry.get('enable', True),
                'offset': entry.get('offset', [0.5, 0.5])
            }
            self.items.append(item)
            self.tree.insert('', 'end', text=os.path.basename(path), values=('', '', '', ''))
            idx = len(self.items) - 1
            self.refresh_tree_row(idx)
            self.current_index = idx
            self.update_photo(idx)
        self.log(f'Imported {len(data)} items from {file}')

    def update_hotkey(self, *_):
        keyboard.clear_all_hotkeys()
        keyboard.add_hotkey(self.hotkey_var.get(), self.trigger_search)

    def show_about(self):
        messagebox.showinfo('About', 'KeyleFinder\nAuthor: keyle\nhttps://vrast.cn')

    def open_settings(self):
        win = tk.Toplevel(self)
        win.title('Settings')
        win.resizable(False, False)
        ttk.Checkbutton(win, text='Debug', variable=self.debug_var).pack(anchor='w', padx=10, pady=5)
        ttk.Checkbutton(win, text='Auto Start', variable=self.auto_start_var).pack(anchor='w', padx=10, pady=5)
        loop_chk = ttk.Checkbutton(win, text='循环执行 (危险)', variable=self.loop_var)
        loop_chk.pack(anchor='w', padx=10, pady=5)
        loop_chk.config(style='Danger.TCheckbutton')
        ttk.Label(win, text='Hotkey:').pack(anchor='w', padx=10, pady=(10, 0))
        ttk.Combobox(win, width=4, state='readonly',
                     values=HOTKEY_OPTIONS, textvariable=self.hotkey_var).pack(anchor='w', padx=10, pady=5)
        ttk.Button(win, text='Close', command=win.destroy).pack(pady=10)
        style = ttk.Style(win)
        style.configure('Danger.TCheckbutton', foreground='red')

    def trigger_search(self):
        if not self.items:
            messagebox.showwarning('Warning', 'Add item first')
            return
        def run_items(idx=0):
            if idx >= len(self.items):
                if self.loop_var.get():
                    self.after(500, lambda: run_items(0))
                return

            item = self.items[idx]
            if not item.get('enable', True):
                self.after(10, lambda: run_items(idx + 1))
                return

            item_id = self.tree.get_children()[idx]
            self.tree.item(item_id, tags=('running',))
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                screenshot = pyautogui.screenshot()
                screenshot.save(tmp.name)
                finder = KeyleFinderModule(tmp.name)
                result = finder.locate(item['path'], debug=self.debug_var.get())
            os.unlink(tmp.name)

            if result.get('status') == 0:
                tl = result['top_left']
                br = result['bottom_right']
                width = br[0] - tl[0]
                height = br[1] - tl[1]
                offset = item.get('offset', [0.5, 0.5])
                click_x = tl[0] + int(width * offset[0])
                click_y = tl[1] + int(height * offset[1])
                move_mouse(click_x, click_y)
                if item.get('action') == 'double':
                    pyautogui.click(clicks=2)
                elif item.get('action') == 'long':
                    pyautogui.mouseDown()
                    time.sleep(1)
                    pyautogui.mouseUp()
                else:
                    pyautogui.click()
                self.tree.item(item_id, tags=('success',))
                self.log(f'Item {idx} matched at {click_x},{click_y}')
                delay = item.get('delay', 0) / 1000.0
                self.after(int(delay * 1000), lambda: run_items(idx + 1))
            else:
                self.tree.item(item_id, tags=('fail',))
                self.log(f'Item {idx} match failed')
                if item.get('interrupt'):
                    self.after(10, lambda: run_items(0))
                else:
                    self.after(10, lambda: run_items(idx + 1))

        self.tree.tag_configure('running', background='lightgreen')
        self.tree.tag_configure('success', background='lightgreen')
        self.tree.tag_configure('fail', background='lightcoral')
        self.after(100, lambda: run_items(0))

    def on_close(self):
        keyboard.clear_all_hotkeys()
        self.destroy()


def main():
    App().mainloop()


if __name__ == '__main__':
    main()
