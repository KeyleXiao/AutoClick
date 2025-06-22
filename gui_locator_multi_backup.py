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
            self._hotkeys = {}

        def _restart(self):
            if self._listener:
                self._listener.stop()
            if self._hotkeys:
                self._listener = _pynput_keyboard.GlobalHotKeys(self._hotkeys)
                self._listener.start()
            else:
                self._listener = None

        def add_hotkey(self, key, callback):
            self._hotkeys[f'<{key.lower()}>'] = callback
            self._restart()

        def remove_hotkey(self, key):
            self._hotkeys.pop(f'<{key.lower()}>', None)
            self._restart()

        def clear_all_hotkeys(self):
            if self._listener:
                self._listener.stop()
                self._listener = None
            self._hotkeys = {}

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

# Dopamine inspired color scheme
BG_COLOR = '#f9f6ff'
ACCENT_COLOR = '#ff6bcb'
ACCENT_HOVER = '#ff87d2'
RUNNING_COLOR = '#c8ffd4'
FAIL_COLOR = '#ffb3b3'


class ScreenCropper(tk.Toplevel):
    def __init__(self, master, screenshot, callback):
        super().__init__(master)
        self.callback = callback
        self.screenshot = screenshot
        self.screen_w = self.winfo_screenwidth()
        self.screen_h = self.winfo_screenheight()
        self.scale_x = screenshot.width / self.screen_w
        self.scale_y = screenshot.height / self.screen_h
        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.overrideredirect(True)
        self.canvas = tk.Canvas(self, cursor='cross')
        self.canvas.pack(fill='both', expand=True)
        if self.scale_x != 1 or self.scale_y != 1:
            display_img = screenshot.resize((self.screen_w, self.screen_h))
        else:
            display_img = screenshot
        self.tk_img = ImageTk.PhotoImage(display_img)
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
        img_x1 = int(x1 * self.scale_x)
        img_y1 = int(y1 * self.scale_y)
        img_x2 = int(x2 * self.scale_x)
        img_y2 = int(y2 * self.scale_y)
        if img_x2 - img_x1 < 1 or img_y2 - img_y1 < 1:
            self.destroy()
            self.callback(None)
            return
        cropped = self.screenshot.crop((img_x1, img_y1, img_x2, img_y2))
        self.destroy()
        self.callback(cropped)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Multi Locator')
        self.geometry('800x600')
        self.resizable(False, False)

        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background=BG_COLOR)
        style.configure('TLabel', background=BG_COLOR)
        style.configure('TCheckbutton', background=BG_COLOR)
        style.configure('TButton', background=ACCENT_COLOR, foreground='white', relief='flat')
        style.map('TButton', background=[('active', ACCENT_HOVER)])
        style.configure('Treeview', background='white', fieldbackground='white', foreground='#333')
        style.map('Treeview', background=[('selected', ACCENT_COLOR)])

        self.configure(background=BG_COLOR)

        self.items = []  # each item is a dict with action, delay etc
        self.debug_var = tk.BooleanVar(value=False)
        self.auto_start_var = tk.BooleanVar(value=True)
        self.loop_var = tk.BooleanVar(value=False)
        self.failsafe_var = tk.BooleanVar(value=True)
        self.hide_window_var = tk.BooleanVar(value=True)
        self.hotkey_enabled_var = tk.BooleanVar(value=False)  # 默认关闭热键
        self.hotkey_var = tk.StringVar(value=HOTKEY)
        self.long_press_active = False
        self.long_press_pos = None
        self.after(100, self.check_long_press)
        self.running = False
        self.run_after_id = None
        self.finish_search_func = None

        top = ttk.Frame(self)
        top.pack(fill='x', pady=5)

        add_btn = ttk.Button(top, text='➕', width=3, command=self.add_item)
        add_btn.pack(side='left', padx=2)

        start_btn = ttk.Button(top, text='▶', width=3, command=self.toggle_search)
        start_btn.pack(side='left', padx=2)

        copy_btn = ttk.Button(top, text='⧉', width=3, command=self.copy_item)
        copy_btn.pack(side='left', padx=2)

        up_btn = ttk.Button(top, text='▲', width=3, command=self.move_item_up)
        up_btn.pack(side='left', padx=2)

        down_btn = ttk.Button(top, text='▼', width=3, command=self.move_item_down)
        down_btn.pack(side='left', padx=2)

        del_btn = ttk.Button(top, text='🗑', width=3, command=self.delete_item)
        del_btn.pack(side='left', padx=2)

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
            columns=('alias', 'action', 'delay', 'interrupt', 'enable'),
            show='tree headings',
            height=8,
        )
        self.tree.heading('#0', text='文件名')
        self.tree.column('#0', width=150)
        self.tree.heading('alias', text='别名')
        self.tree.column('alias', width=120)
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

        self.photo_frame = ttk.Frame(self)
        self.photo_frame.pack(padx=10, pady=5, fill='both', expand=True)
        self.photo_label = ttk.Label(self.photo_frame, text='No Image', relief='groove')
        self.photo_label.pack(expand=True)
        self.photo_label.bind('<Button-1>', self.on_photo_click)

        self.log_label = ttk.Label(self, text='', foreground='gray')
        self.log_label.pack(side='bottom', fill='x')
        self.log_label.bind('<Button-1>', self.copy_log)

        self.hotkey_var.trace_add('write', self.update_hotkey)
        self.failsafe_var.trace_add('write', self.update_failsafe)
        self.update_failsafe()
        self.hotkey_available = False
        # 暂时禁用热键功能以避免macOS权限问题
        # if keyboard:
        #     try:
        #         keyboard.add_hotkey(self.hotkey_var.get(), self.toggle_search)
        #         keyboard.add_hotkey('esc', self.stop_search)
        #         self.hotkey_available = True
        #         self.log('热键已启用 - 按F2开始搜索，ESC停止')
        #     except Exception as e:
        #         print(f'Warning: global hotkeys are unavailable: {e}')
        #         self.log('热键不可用 - 请在系统偏好设置中授予辅助功能权限')
        # else:
        #     print('Warning: global hotkeys are unavailable')
        #     self.log('热键不可用 - 请在系统偏好设置中授予辅助功能权限')
        
        self.log('使用界面按钮控制 - 点击▶开始搜索')
        
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    def log(self, msg):
        self.log_label.config(text=msg)

    def copy_log(self, _):
        self.clipboard_clear()
        self.clipboard_append(self.log_label.cget('text'))

    def check_long_press(self):
        if self.long_press_active and pyautogui.position() != self.long_press_pos:
            pyautogui.mouseUp()
            self.long_press_active = False
        self.after(100, self.check_long_press)

    def update_photo(self, idx):
        path = self.items[idx]['path']
        offset = self.items[idx].get('offset', [0.5, 0.5])
        if os.path.exists(path):
            img = Image.open(path)
            img.thumbnail((200, 200))
            w, h = img.size
            dot_x = int(offset[0] * w)
            dot_y = int(offset[1] * h)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            r = 2
            draw.ellipse((dot_x - r, dot_y - r, dot_x + r, dot_y + r), fill='red')
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
        self.tree.set(item_id, 'alias', item.get('alias', ''))
        self.tree.set(item_id, 'action', action_map.get(item.get('action', 'single'), '单击'))
        self.tree.set(item_id, 'delay', str(item.get('delay', 0)))
        self.tree.set(item_id, 'interrupt', '✔' if item.get('interrupt') else '')
        self.tree.set(item_id, 'enable', '✔' if item.get('enable', True) else '')

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.items:
            self.tree.insert('', 'end', text=os.path.basename(item['path']), values=('', '', '', '', ''))
        for i in range(len(self.items)):
            self.refresh_tree_row(i)


    def on_tree_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id:
            return
        idx = self.tree.index(item_id)
        item = self.items[idx]
        if column == '#0':
            self.trigger_search(idx)
            return
        if column == '#1':  # alias
            val = simpledialog.askstring('别名', '请输入别名:', initialvalue=item.get('alias', ''))
            if val is None:
                return
            item['alias'] = val
        elif column == '#2':  # action
            order = ['single', 'double', 'long']
            current = item.get('action', 'single')
            item['action'] = order[(order.index(current) + 1) % 3]
        elif column == '#3':  # delay
            val = simpledialog.askinteger('Delay', 'Delay in ms:', initialvalue=item.get('delay', 0), minvalue=0)
            if val is None:
                return
            item['delay'] = val
        elif column == '#4':  # interrupt
            item['interrupt'] = not item.get('interrupt', False)
        elif column == '#5':  # enable
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
            'alias': '',
            'action': 'single',
            'delay': 0,
            'interrupt': False,
            'enable': True,
            'offset': [0.5, 0.5]
        }
        self.items.append(item)
        self.tree.insert('', 'end', text=os.path.basename(path), values=('', '', '', '', ''))
        idx = len(self.items) - 1
        self.refresh_tree_row(idx)
        self.current_index = idx
        self.update_photo(idx)

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
                'alias': item.get('alias', ''),
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
                'alias': entry.get('alias', ''),
                'action': entry.get('action', 'single' if not entry.get('double_click') else 'double'),
                'delay': entry.get('delay', 0),
                'interrupt': entry.get('interrupt', False),
                'enable': entry.get('enable', True),
                'offset': entry.get('offset', [0.5, 0.5])
            }
            self.items.append(item)
            self.tree.insert('', 'end', text=os.path.basename(path), values=('', '', '', '', ''))
            idx = len(self.items) - 1
            self.refresh_tree_row(idx)
            self.current_index = idx
            self.update_photo(idx)
        self.log(f'Imported {len(data)} items from {file}')

    def delete_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Info', 'Select an item to delete')
            return
        item_id = sel[0]
        idx = self.tree.index(item_id)
        self.tree.delete(item_id)
        item = self.items.pop(idx)
        try:
            os.unlink(item['path'])
        except Exception:
            pass
        if self.items:
            self.current_index = 0
            self.tree.selection_set(self.tree.get_children()[0])
            self.update_photo(0)
        else:
            self.current_index = None
            self.photo_label.config(image='', text='No Image')

    def copy_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Info', 'Select an item to copy')
            return
        idx = self.tree.index(sel[0])
        src = self.items[idx]
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            with open(src['path'], 'rb') as f:
                tmp.write(f.read())
            new_path = tmp.name
        item = src.copy()
        item['path'] = new_path
        self.items.insert(idx + 1, item)
        self.tree.insert('', idx + 1, text=os.path.basename(new_path), values=('', '', '', '', ''))
        self.refresh_tree_row(idx + 1)
        self.tree.selection_set(self.tree.get_children()[idx + 1])
        self.current_index = idx + 1
        self.update_photo(idx + 1)

    def move_item_up(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Info', 'Select an item to move')
            return
        idx = self.tree.index(sel[0])
        if idx == 0:
            return
        self.items[idx - 1], self.items[idx] = self.items[idx], self.items[idx - 1]
        item_id = self.tree.get_children()[idx]
        self.tree.move(item_id, '', idx - 1)
        self.refresh_tree_row(idx - 1)
        self.refresh_tree_row(idx)
        self.tree.selection_set(self.tree.get_children()[idx - 1])
        self.current_index = idx - 1

    def move_item_down(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Info', 'Select an item to move')
            return
        idx = self.tree.index(sel[0])
        if idx >= len(self.items) - 1:
            return
        self.items[idx + 1], self.items[idx] = self.items[idx], self.items[idx + 1]
        item_id = self.tree.get_children()[idx]
        self.tree.move(item_id, '', idx + 1)
        self.refresh_tree_row(idx)
        self.refresh_tree_row(idx + 1)
        self.tree.selection_set(self.tree.get_children()[idx + 1])
        self.current_index = idx + 1

        if not hasattr(self, "hotkey_enabled_var") or not hasattr(self, "hotkey_var"):
            return
            
        if not self.hotkey_enabled_var.get():
            # 关闭热键 - 彻底释放监听对象
            if hasattr(self, "_hotkey_listener") and self._hotkey_listener:
                try:
                    self._hotkey_listener.stop()
                except Exception:
                    pass
                self._hotkey_listener = None
            self.hotkey_available = False
            self.log("热键已关闭")
            return
            
        # 启用热键 - 动态import pynput
        try:
            # 只有在需要时才import pynput
            from pynput import keyboard as _pynput_keyboard
            
            # 停止之前的监听器
            if hasattr(self, "_hotkey_listener") and self._hotkey_listener:
                try:
                    self._hotkey_listener.stop()
                except Exception:
                    pass
            
            # 创建新的热键映射
            hotkeys = {
                f"<{self.hotkey_var.get().lower()}>": self.toggle_search,
                "<esc>": self.stop_search
        ttk.Checkbutton(win, text="启用全局热键", variable=self.hotkey_enabled_var, command=self.update_hotkey).pack(anchor="w", padx=10, pady=(10, 0))
        ttk.Label(win, text="勾选后可用F2/ESC全局快捷键（需系统辅助权限）").pack(anchor="w", padx=30, pady=(0, 5))            }
            
            # 创建并启动监听器
            self._hotkey_listener = _pynput_keyboard.GlobalHotKeys(hotkeys)
            self._hotkey_listener.start()
            self.hotkey_available = True
            self.log("热键已启用 - 按F2开始/ESC停止（需辅助权限）")
            
        except Exception as e:
            print(f"Warning: global hotkeys are unavailable: {e}")
            self.hotkey_available = False
            self.log("热键不可用 - 请在系统偏好设置中授予辅助功能权限")
            # 确保监听器被清理
            if hasattr(self, "_hotkey_listener"):
                self._hotkey_listener = None
    def update_failsafe(self, *_):
        pyautogui.FAILSAFE = self.failsafe_var.get()

    def show_about(self):
        messagebox.showinfo('About', 'KeyleFinder\nAuthor: keyle\nhttps://vrast.cn')

    def open_settings(self):
        win = tk.Toplevel(self)
        win.title('Settings')
        win.resizable(False, False)
        win.configure(background=BG_COLOR)
        ttk.Checkbutton(win, text='Debug', variable=self.debug_var).pack(anchor='w', padx=10, pady=(5, 0))
        ttk.Label(win, text='调试模式，显示匹配结果').pack(anchor='w', padx=30, pady=(0, 5))

        ttk.Checkbutton(win, text='Auto Start', variable=self.auto_start_var).pack(anchor='w', padx=10, pady=(0, 0))
        ttk.Label(win, text='自动从上到下执行全部项目').pack(anchor='w', padx=30, pady=(0, 5))

        ttk.Checkbutton(win, text='Fail-safe', variable=self.failsafe_var).pack(anchor='w', padx=10, pady=(0, 0))
        ttk.Label(win, text='将鼠标移到屏幕角落终止').pack(anchor='w', padx=30, pady=(0, 5))

        ttk.Checkbutton(win, text='Hide window while searching',
                        variable=self.hide_window_var).pack(anchor='w', padx=10, pady=(0, 0))
        ttk.Label(win, text='搜索时隐藏主窗体').pack(anchor='w', padx=30, pady=(0, 5))

        loop_chk = ttk.Checkbutton(win, text='循环执行 (危险)', variable=self.loop_var)
        loop_chk.pack(anchor='w', padx=10, pady=(0, 0))
        ttk.Label(win, text='完成后从头开始重复').pack(anchor='w', padx=30, pady=(0, 5))
        loop_chk.config(style='Danger.TCheckbutton')
        ttk.Label(win, text='Hotkey:').pack(anchor='w', padx=10, pady=(10, 0))
        ttk.Combobox(win, width=4, state='readonly',
                     values=HOTKEY_OPTIONS, textvariable=self.hotkey_var).pack(anchor='w', padx=10, pady=(0, 0))
        ttk.Label(win, text='触发搜索的快捷键').pack(anchor='w', padx=30, pady=(0, 5))
        ttk.Button(win, text='Close', command=win.destroy).pack(pady=10)
        style = ttk.Style(win)
        style.configure('Danger.TCheckbutton', foreground='red', background=BG_COLOR)

    def toggle_search(self, *_):
        if self.running:
            self.stop_search()
        else:
            self.trigger_search()

    def stop_search(self, *_):
        if not self.running:
            return
        if self.run_after_id:
            self.after_cancel(self.run_after_id)
            self.run_after_id = None
        if self.long_press_active:
            pyautogui.mouseUp()
            self.long_press_active = False
        if self.finish_search_func:
            self.finish_search_func()

    def trigger_search(self, start_idx=None):
        if self.running:
            return
        if not self.items:
            messagebox.showwarning('Warning', 'Add item first')
            return
        for iid in self.tree.get_children():
            tags = list(self.tree.item(iid, 'tags'))
            if 'running' in tags:
                tags.remove('running')
            self.tree.item(iid, tags=tuple(tags))

        if start_idx is None:
            if self.auto_start_var.get():
                start_idx = 0
            else:
                sel = self.tree.selection()
                if not sel:
                    messagebox.showinfo('Info', 'Select an item to run or enable Auto Start')
                    return
                start_idx = self.tree.index(sel[0])

        hide_window = self.hide_window_var.get()
        if hide_window:
            self.withdraw()

        orig_image = getattr(self.photo_label, 'image', None)
        orig_text = self.photo_label.cget('text')
        self.photo_label.config(image='', text='')
        self.running = True

        def finish_search():
            if hide_window:
                self.deiconify()
            if orig_image:
                self.photo_label.config(image=orig_image, text='')
                self.photo_label.image = orig_image
            else:
                self.photo_label.config(image='', text=orig_text)
            self.running = False
            self.run_after_id = None
            self.finish_search_func = None

        def run_items(idx=0):
            if idx >= len(self.items):
                if self.long_press_active:
                    pyautogui.mouseUp()
                    self.long_press_active = False
                if self.loop_var.get():
                    self.run_after_id = self.after(500, lambda: run_items(0))
                else:
                    finish_search()
                return

            item = self.items[idx]
            if not item.get('enable', True):
                self.after(10, lambda: run_items(idx + 1))
                return

            def execute():
                if self.long_press_active and item.get('action') != 'long':
                    pyautogui.mouseUp()
                    self.long_press_active = False

                item_id = self.tree.get_children()[idx]
                self.tree.item(item_id, tags=('running',))
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                    screenshot = pyautogui.screenshot()
                    screenshot.save(tmp.name)
                    finder = KeyleFinderModule(tmp.name)
                    result = finder.locate(item['path'], debug=self.debug_var.get())
                os.unlink(tmp.name)

                next_idx = idx + 1
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
                        self.long_press_active = True
                        self.long_press_pos = (click_x, click_y)
                    else:
                        pyautogui.click()
                    tags = list(self.tree.item(item_id, 'tags'))
                    if 'running' in tags:
                        tags.remove('running')
                    if 'fail' in tags:
                        tags.remove('fail')
                    self.tree.item(item_id, tags=tuple(tags))
                    self.log(f'Item {idx} matched at {click_x},{click_y}')
                else:
                    self.tree.item(item_id, tags=('fail',))
                    
                    self.log(f'Item {idx} match failed')
                    if item.get('interrupt'):
                        next_idx = 0

                delay = item.get('delay', 0)
                self.run_after_id = self.after(delay, lambda: run_items(next_idx))

            execute()

        self.tree.tag_configure('running', background=RUNNING_COLOR)
        self.tree.tag_configure('fail', background=FAIL_COLOR)

        self.finish_search_func = finish_search
        self.run_after_id = self.after(100, lambda: run_items(start_idx))

        # 清理热键监听器
        if hasattr(self, "_hotkey_listener") and self._hotkey_listener:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
        self.destroy()        self.destroy()


def main():
    App().mainloop()


if __name__ == '__main__':
    main()
