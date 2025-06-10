import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
import os
from copy import deepcopy
from PIL import Image, ImageTk

RUNNING_COLOR = '#c8ffd4'
FAIL_COLOR = '#ffb3b3'

class Edge:
    def __init__(self, editor, src, dst, port_type='default'):
        self.editor = editor
        self.src = src
        self.dst = dst
        self.port_type = port_type
        color = '#555'
        if port_type == 'success':
            color = '#0a0'
        elif port_type == 'failure':
            color = '#a00'
        sx, sy = src.output_position(port_type)
        dx, dy = dst.input_position()
        self.line = editor.canvas.create_line(sx, sy, dx, dy, arrow=tk.LAST, fill=color)

    def update(self):
        sx, sy = self.src.output_position(self.port_type)
        dx, dy = self.dst.input_position()
        self.editor.canvas.coords(self.line, sx, sy, dx, dy)

class Node:
    WIDTH = 200
    HEIGHT = 120

    def __init__(self, editor, item, x=50, y=50):
        self.editor = editor
        self.item = item
        self.type = item.get('type', 'normal')
        self.x = x
        self.y = y
        self.normal_color = '#f5f5f5'
        self.rect = editor.canvas.create_rectangle(
            x,
            y,
            x + self.WIDTH,
            y + self.HEIGHT,
            fill=self.normal_color,
            outline='#333',
            width=2,
        )
        name = os.path.basename(item.get('path', 'Node'))
        self.text = editor.canvas.create_text(x + self.WIDTH / 2, y + 10, text=name, anchor='n')
        img_path = item.get('path')
        self.image = None
        self.image_id = None
        if img_path and os.path.exists(img_path):
            img = Image.open(img_path)
            img.thumbnail((self.WIDTH - 20, self.HEIGHT - 50))
            self.image = ImageTk.PhotoImage(img)
            self.image_id = editor.canvas.create_image(x + self.WIDTH / 2, y + self.HEIGHT / 2, image=self.image)
        self.act_text = editor.canvas.create_text(
            x + self.WIDTH / 2, y + self.HEIGHT - 10,
            text=item.get('action', 'single'), anchor='s'
        )
        self.in_port = editor.canvas.create_oval(
            x - 6, y + self.HEIGHT / 2 - 6, x + 6, y + self.HEIGHT / 2 + 6, fill='#333'
        )
        if self.type == 'condition':
            self.out_port_success = editor.canvas.create_oval(
                x + self.WIDTH - 6,
                y + self.HEIGHT / 3 - 6,
                x + self.WIDTH + 6,
                y + self.HEIGHT / 3 + 6,
                fill='#0a0',
            )
            self.out_port_failure = editor.canvas.create_oval(
                x + self.WIDTH - 6,
                y + 2 * self.HEIGHT / 3 - 6,
                x + self.WIDTH + 6,
                y + 2 * self.HEIGHT / 3 + 6,
                fill='#a00',
            )
        else:
            self.out_port = editor.canvas.create_oval(
                x + self.WIDTH - 6,
                y + self.HEIGHT / 2 - 6,
                x + self.WIDTH + 6,
                y + self.HEIGHT / 2 + 6,
                fill='#333',
            )

        for item_id in [self.rect, self.text, self.act_text]:
            editor.canvas.tag_bind(item_id, '<ButtonPress-1>', self.on_press)
            editor.canvas.tag_bind(item_id, '<B1-Motion>', self.on_drag)
            editor.canvas.tag_bind(item_id, '<ButtonRelease-1>', self.on_release)
            editor.canvas.tag_bind(item_id, '<Double-1>', self.edit)
        if self.type == 'condition':
            editor.canvas.tag_bind(
                self.out_port_success,
                '<ButtonPress-1>',
                lambda e: self.start_link(e, 'success')
            )
            editor.canvas.tag_bind(
                self.out_port_failure,
                '<ButtonPress-1>',
                lambda e: self.start_link(e, 'failure')
            )
        else:
            editor.canvas.tag_bind(self.out_port, '<ButtonPress-1>', self.start_link)
        editor.canvas.tag_bind(self.in_port, '<ButtonRelease-1>', self.finish_link)
        self.drag_data = None
        self.in_edges = []
        self.out_edges = []
        self._press_job = None
        self._moved = False

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        items = [self.rect, self.text, self.act_text, self.in_port]
        if self.image_id:
            items.append(self.image_id)
        if self.type == 'condition':
            items.extend([self.out_port_success, self.out_port_failure])
        else:
            items.append(self.out_port)
        for item in items:
            self.editor.canvas.move(item, dx, dy)
        for e in self.in_edges + self.out_edges:
            e.update()

    def on_press(self, event):
        self.editor.select_node(self)
        self.drag_data = (event.x, event.y)
        self._moved = False
        if self._press_job:
            self.editor.canvas.after_cancel(self._press_job)
        self._press_job = self.editor.canvas.after(500, self.start_long_link)

    def on_drag(self, event):
        if self.drag_data is None:
            return
        dx = event.x - self.drag_data[0]
        dy = event.y - self.drag_data[1]
        if self._press_job and (abs(dx) > 3 or abs(dy) > 3):
            self.editor.canvas.after_cancel(self._press_job)
            self._press_job = None
            self._moved = True
        if self.editor.start_node is self and self.editor.temp_line:
            return
        if not self._press_job:
            self.drag_data = (event.x, event.y)
            self.move(dx, dy)

    def start_link(self, event, port_type='default'):
        self.editor.start_connection(self, port_type, event.x, event.y)

    def finish_link(self, event):
        self.editor.finish_connection(self)

    def on_release(self, _):
        if self._press_job:
            self.editor.canvas.after_cancel(self._press_job)
            self._press_job = None
        self.drag_data = None
        if self.editor.start_node is self:
            self.editor.finish_connection()

    def start_long_link(self):
        self._press_job = None
        x, y = self.output_position('default')
        self.editor.start_connection(self, 'default', x, y)

    def edit(self, event=None):
        action = simpledialog.askstring(
            'Action',
            'click type: single/double/long/right_single/right_double/right_long',
            initialvalue=self.item.get('action', 'single'),
            parent=self.editor.master,
        )
        if action:
            self.item['action'] = action
            self.editor.canvas.itemconfigure(self.act_text, text=action)
        delay = simpledialog.askinteger(
            'Delay', 'delay(ms)', initialvalue=self.item.get('delay', 0), parent=self.editor.master
        )
        if delay is not None:
            self.item['delay'] = delay
        interrupt = messagebox.askyesno('Interrupt', 'interrupt on fail?', parent=self.editor.master)
        self.item['interrupt'] = interrupt

    def input_position(self):
        return self.x, self.y + self.HEIGHT/2

    def output_position(self, port_type='default'):
        if self.type == 'condition':
            if port_type == 'success':
                return self.x + self.WIDTH, self.y + self.HEIGHT/3
            elif port_type == 'failure':
                return self.x + self.WIDTH, self.y + 2 * self.HEIGHT/3
        return self.x + self.WIDTH, self.y + self.HEIGHT/2

    def highlight_running(self):
        self.editor.canvas.itemconfigure(self.rect, fill=RUNNING_COLOR)

    def highlight_fail(self):
        self.editor.canvas.itemconfigure(self.rect, fill=FAIL_COLOR)

    def clear_highlight(self):
        self.editor.canvas.itemconfigure(self.rect, fill=self.normal_color)

class NodeEditor(tk.Frame):
    def __init__(self, master, items, on_apply=None):
        super().__init__(master)
        self.master = master
        self.items = items
        self.on_apply = on_apply
        self.master.protocol('WM_DELETE_WINDOW', self.close)
        toolbar = tk.Frame(self)
        toolbar.pack(fill='x')
        tk.Button(toolbar, text='Add Node', command=self.add_node).pack(side='left')
        tk.Button(toolbar, text='Copy', command=self.copy_node).pack(side='left')
        tk.Button(toolbar, text='Paste', command=self.paste_node).pack(side='left')
        tk.Button(toolbar, text='Delete', command=self.delete_node).pack(side='left')
        self.canvas = tk.Canvas(self, bg='white')
        self.canvas.pack(fill='both', expand=True)
        zoom_frame = tk.Frame(self)
        zoom_frame.pack(fill='x', side='bottom')
        tk.Label(zoom_frame, text='Zoom').pack(side='left')
        self.zoom_var = tk.DoubleVar(value=1.0)
        self._last_zoom = 1.0
        ttk.Scale(zoom_frame, from_=0.5, to=2.0, variable=self.zoom_var, command=self.on_zoom).pack(side='right', fill='x', expand=True)
        self.nodes = []
        self.item_to_node = {}
        self.edges = []
        self.temp_line = None
        self.start_node = None
        self.selected_node = None
        self.clipboard = None
        for i, item in enumerate(items):
            node = Node(self, item, x=60 + i*160, y=60)
            self.nodes.append(node)
            self.item_to_node[item] = node
        self.pack(fill='both', expand=True)

    def add_node(self):
        node_type = simpledialog.askstring(
            'Node Type', 'Type (normal/condition):', parent=self.master
        )
        if not node_type:
            return
        node_type = node_type.lower()
        if node_type not in ('normal', 'condition'):
            messagebox.showerror('Error', 'Invalid node type')
            return
        item = {'type': node_type}
        node = Node(self, item, x=60, y=60)
        self.nodes.append(node)
        self.item_to_node[item] = node

    def select_node(self, node):
        if self.selected_node and self.selected_node is not node:
            self.canvas.itemconfigure(self.selected_node.rect, outline='#333')
        self.selected_node = node
        self.canvas.itemconfigure(node.rect, outline='#ff6bcb')

    def copy_node(self):
        if self.selected_node:
            self.clipboard = deepcopy(self.selected_node.item)

    def paste_node(self):
        if not self.clipboard:
            return
        item = deepcopy(self.clipboard)
        node = Node(self, item, x=60, y=60)
        self.nodes.append(node)
        self.item_to_node[item] = node

    def delete_node(self):
        node = self.selected_node
        if not node:
            return
        for e in node.in_edges + node.out_edges:
            self.canvas.delete(e.line)
            if e in self.edges:
                self.edges.remove(e)
            if e.src is not node and e in e.src.out_edges:
                e.src.out_edges.remove(e)
            if e.dst is not node and e in e.dst.in_edges:
                e.dst.in_edges.remove(e)
        items = [node.rect, node.text, node.act_text, node.in_port]
        if node.image_id:
            items.append(node.image_id)
        if node.type == 'condition':
            items.extend([node.out_port_success, node.out_port_failure])
        else:
            items.append(node.out_port)
        for itm in items:
            self.canvas.delete(itm)
        self.nodes.remove(node)
        self.item_to_node.pop(node.item, None)
        self.selected_node = None

    def on_zoom(self, value=None):
        scale = float(value) if value else self.zoom_var.get()
        self.canvas.scale('all', 0, 0, scale / getattr(self, '_last_zoom', 1.0), scale / getattr(self, '_last_zoom', 1.0))
        self._last_zoom = scale

    def close(self):
        if self.on_apply:
            try:
                ordered = self.compute_order()
                self.on_apply(ordered)
            except Exception as e:
                print(f'Error computing order: {e}')
        self.master.destroy()

    def compute_order(self):
        visited = set()
        order = []

        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for e in node.out_edges:
                visit(e.dst)
            order.append(node)

        roots = [n for n in self.nodes if not n.in_edges]
        for n in roots:
            visit(n)
        for n in self.nodes:
            if n not in visited:
                visit(n)
        order.reverse()
        return [n.item for n in order]

    def highlight_running(self, item):
        node = self.item_to_node.get(item)
        if node:
            node.highlight_running()

    def highlight_fail(self, item):
        node = self.item_to_node.get(item)
        if node:
            node.highlight_fail()

    def clear_highlight(self, item):
        node = self.item_to_node.get(item)
        if node:
            node.clear_highlight()

    def start_connection(self, node, port_type, x, y):
        self.start_node = node
        self.start_port_type = port_type
        self.temp_line = self.canvas.create_line(x, y, x, y, dash=(4, 2))
        self.canvas.bind('<Motion>', self.track_temp)

    def track_temp(self, event):
        if self.temp_line:
            sx, sy, _, _ = self.canvas.coords(self.temp_line)
            self.canvas.coords(self.temp_line, sx, sy, event.x, event.y)

    def finish_connection(self, node=None):
        if self.start_node and node and self.start_node != node:
            edge = Edge(self, self.start_node, node, self.start_port_type)
            self.edges.append(edge)
            self.start_node.out_edges.append(edge)
            node.in_edges.append(edge)
        if self.temp_line:
            self.canvas.delete(self.temp_line)
        self.temp_line = None
        self.start_node = None
        self.start_port_type = None
        self.canvas.unbind('<Motion>')

def main():
    root = tk.Tk()
    root.title('Node Editor')
    items = [{}, {}]  # empty demo items
    NodeEditor(root, items)
    root.geometry('800x600')
    root.mainloop()

if __name__ == '__main__':
    main()
