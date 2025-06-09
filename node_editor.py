import tkinter as tk
from tkinter import simpledialog
import os

class Edge:
    def __init__(self, editor, src, dst):
        self.editor = editor
        self.src = src
        self.dst = dst
        sx, sy = src.output_position()
        dx, dy = dst.input_position()
        self.line = editor.canvas.create_line(sx, sy, dx, dy, arrow=tk.LAST, fill='#555')

    def update(self):
        sx, sy = self.src.output_position()
        dx, dy = self.dst.input_position()
        self.editor.canvas.coords(self.line, sx, sy, dx, dy)

class Node:
    WIDTH = 140
    HEIGHT = 70

    def __init__(self, editor, item, x=50, y=50):
        self.editor = editor
        self.item = item
        self.x = x
        self.y = y
        self.rect = editor.canvas.create_rectangle(
            x,
            y,
            x + self.WIDTH,
            y + self.HEIGHT,
            fill='#f5f5f5',
            outline='#333',
            width=2,
        )
        name = os.path.basename(item.get('path', 'Node'))
        self.text = editor.canvas.create_text(x + self.WIDTH / 2, y + 20, text=name)
        self.act_text = editor.canvas.create_text(
            x + self.WIDTH / 2, y + 45, text=item.get('action', 'single')
        )
        self.in_port = editor.canvas.create_oval(
            x - 6, y + self.HEIGHT / 2 - 6, x + 6, y + self.HEIGHT / 2 + 6, fill='#333'
        )
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
        items = [self.rect, self.text, self.act_text, self.in_port, self.out_port]
        for item in items:
            self.editor.canvas.move(item, dx, dy)
        for e in self.in_edges + self.out_edges:
            e.update()

    def on_press(self, event):
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

    def start_link(self, event):
        self.editor.start_connection(self, event.x, event.y)

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
        x, y = self.output_position()
        self.editor.start_connection(self, x, y)

    def edit(self, event=None):
        action = simpledialog.askstring('Action', 'action', initialvalue=self.item.get('action', 'single'), parent=self.editor.master)
        if action:
            self.item['action'] = action
            self.editor.canvas.itemconfigure(self.act_text, text=action)

    def input_position(self):
        return self.x, self.y + self.HEIGHT/2

    def output_position(self):
        return self.x + self.WIDTH, self.y + self.HEIGHT/2

class NodeEditor(tk.Frame):
    def __init__(self, master, items, on_apply=None):
        super().__init__(master)
        self.master = master
        self.items = items
        self.on_apply = on_apply
        self.master.protocol('WM_DELETE_WINDOW', self.close)
        self.canvas = tk.Canvas(self, bg='white')
        self.canvas.pack(fill='both', expand=True)
        self.nodes = []
        self.edges = []
        self.temp_line = None
        self.start_node = None
        for i, item in enumerate(items):
            node = Node(self, item, x=60 + i*160, y=60)
            self.nodes.append(node)
        self.pack(fill='both', expand=True)

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

    def start_connection(self, node, x, y):
        self.start_node = node
        self.temp_line = self.canvas.create_line(x, y, x, y, dash=(4, 2))
        self.canvas.bind('<Motion>', self.track_temp)

    def track_temp(self, event):
        if self.temp_line:
            sx, sy, _, _ = self.canvas.coords(self.temp_line)
            self.canvas.coords(self.temp_line, sx, sy, event.x, event.y)

    def finish_connection(self, node=None):
        if self.start_node and node and self.start_node != node:
            edge = Edge(self, self.start_node, node)
            self.edges.append(edge)
            self.start_node.out_edges.append(edge)
            node.in_edges.append(edge)
        if self.temp_line:
            self.canvas.delete(self.temp_line)
        self.temp_line = None
        self.start_node = None
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
