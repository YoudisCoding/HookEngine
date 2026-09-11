#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — HT Editor
Görsel .ht düzenleyici
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ht.ht_v3 import (
    HTTable, HTEntry, HTGroup, default_template,
    MODE_TOGGLE, MODE_ACTION, MODE_FREEZE, MODE_SCRIPT,
    MODE_INJECT, MODE_FORMULA, MODE_CONDITION,
    TYPE_INT, TYPE_INT64, TYPE_FLOAT, TYPE_DOUBLE, TYPE_BYTE, TYPE_STRING
)
from core.lang import t


class HTEditor:
    def __init__(self, parent, ht_tab):
        self.ht_tab = ht_tab
        self.table = ht_tab.table if ht_tab.table else HTTable()
        self.entry_widgets = []

        self.win = tk.Toplevel(parent)
        self.win.title(t('editor_title'))
        self.win.geometry("1100x700")
        self.win.configure(bg='#0a0a0a')

        self.setup_ui()
        self.render()

    def setup_ui(self):
        # Top bar
        top = tk.Frame(self.win, bg='#0a0a0a')
        top.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(top, text=t('editor_title'), bg='#0a0a0a', fg='#ff3030',
                 font=('Consolas', 16, 'bold')).pack(side=tk.LEFT)

        tk.Button(top, text=t('editor_new'), bg='#1a3a1a', fg='#00ff00',
                  font=('Consolas', 10), bd=0, padx=10, pady=6,
                  command=self.new_table).pack(side=tk.RIGHT, padx=3)
        tk.Button(top, text=t('editor_open'), bg='#1a3a1a', fg='#00ff00',
                  font=('Consolas', 10), bd=0, padx=10, pady=6,
                  command=self.load_table).pack(side=tk.RIGHT, padx=3)

        # Scrollable
        container = tk.Frame(self.win, bg='#0a0a0a')
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(container, bg='#0a0a0a', highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=sb.set)

        self.groups_frame = tk.Frame(self.canvas, bg='#0a0a0a')
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.groups_frame, anchor='nw'
        )
        self.groups_frame.bind(
            '<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        )
        self.canvas.bind(
            '<Configure>',
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        # Bottom
        bottom = tk.Frame(self.win, bg='#0a0a0a')
        bottom.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(bottom, text=t('editor_add_group'), bg='#1a2a3a', fg='#55aaff',
                  font=('Consolas', 11, 'bold'), bd=0, padx=15, pady=8,
                  command=self.add_group).pack(side=tk.LEFT, padx=3)

        tk.Button(bottom, text=t('editor_save'), bg='#1a3a1a', fg='#00ff00',
                  font=('Consolas', 11, 'bold'), bd=0, padx=20, pady=8,
                  command=self.save_table).pack(side=tk.RIGHT, padx=3)
        tk.Button(bottom, text=t('editor_save_as'), bg='#1a3a1a', fg='#00ff00',
                  font=('Consolas', 11, 'bold'), bd=0, padx=20, pady=8,
                  command=self.save_as_table).pack(side=tk.RIGHT, padx=3)
        tk.Button(bottom, text=t('editor_close'), bg='#3a1a1a', fg='#ff5555',
                  font=('Consolas', 11, 'bold'), bd=0, padx=20, pady=8,
                  command=self.win.destroy).pack(side=tk.RIGHT, padx=3)

    def new_table(self):
        self.table = HTTable()
        self.render()

    def load_table(self):
        path = filedialog.askopenfilename(filetypes=[("HT", "*.ht")])
        if not path:
            return
        t_obj = HTTable.load(path)
        if t_obj:
            self.table = t_obj
            self.render()

    def save_table(self):
        if not self.ht_tab.ht_path:
            self.save_as_table()
            return
        try:
            self.table.save(self.ht_tab.ht_path)
            messagebox.showinfo(t('success'), f"Saved: {self.ht_tab.ht_path}")
        except Exception as e:
            messagebox.showerror(t('error'), str(e))

    def save_as_table(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".ht",
            filetypes=[("HT", "*.ht")],
            initialfile="hookengine_table.ht"
        )
        if not path:
            return
        try:
            self.table.save(path)
            self.ht_tab.ht_path = path
            self.ht_tab.table = self.table
            messagebox.showinfo(t('success'), f"Saved: {path}")
        except Exception as e:
            messagebox.showerror(t('error'), str(e))

    def add_group(self):
        self.table.add_group(f"Group {len(self.table.groups) + 1}", "#00ff00")
        self.render()

    def render(self):
        for w in self.groups_frame.winfo_children():
            w.destroy()
        self.entry_widgets = []

        for gi, group in enumerate(self.table.groups):
            self.render_group(gi, group)

    def render_group(self, gi, group):
        gf = tk.LabelFrame(
            self.groups_frame, text=f"  {group.name}  ",
            bg='#0f0f0f', fg=group.color,
            font=('Consolas', 11, 'bold'), bd=1
        )
        gf.pack(fill=tk.X, padx=4, pady=6)

        # Group name + color
        name_row = tk.Frame(gf, bg='#0f0f0f')
        name_row.pack(fill=tk.X, padx=6, pady=3)

        tk.Label(name_row, text=t('editor_group_name'), bg='#0f0f0f', fg='#888888',
                 font=('Consolas', 9)).pack(side=tk.LEFT)
        name_var = tk.StringVar(value=group.name)
        tk.Entry(name_row, textvariable=name_var, bg='#000000', fg='#00ff00',
                 font=('Consolas', 10), width=25,
                 insertbackground='#00ff00').pack(side=tk.LEFT, padx=5)

        tk.Label(name_row, text=t('editor_group_color'), bg='#0f0f0f', fg='#888888',
                 font=('Consolas', 9)).pack(side=tk.LEFT, padx=(20, 0))
        color_var = tk.StringVar(value=group.color)
        tk.Entry(name_row, textvariable=color_var, bg='#000000', fg='#00ff00',
                 font=('Consolas', 10), width=10,
                 insertbackground='#00ff00').pack(side=tk.LEFT, padx=5)

        name_var.trace_add('write', lambda *_: setattr(group, 'name', name_var.get()))
        color_var.trace_add('write', lambda *_: setattr(group, 'color', color_var.get()))

        tk.Button(name_row, text=t('editor_delete'), bg='#3a1a1a', fg='#ff5555',
                  font=('Consolas', 9), bd=0, padx=8,
                  command=lambda: self.delete_group(gi)).pack(side=tk.RIGHT)

        # Column headers
        hdr = tk.Frame(gf, bg='#0f0f0f')
        hdr.pack(fill=tk.X, padx=6, pady=(5, 2))
        for text, w in [(t('editor_label'), 20), (t('editor_read'), 30),
                        (t('editor_type'), 8), (t('editor_value'), 10),
                        (t('editor_mode'), 10), (t('editor_hotkey'), 6)]:
            tk.Label(hdr, text=text, bg='#0f0f0f', fg='#666666',
                     font=('Consolas', 8, 'bold'), width=w, anchor='w'
                     ).pack(side=tk.LEFT)

        # Entries
        for ei, entry in enumerate(group.entries):
            self.render_entry(gf, gi, ei, entry)

        # Add entry
        tk.Button(gf, text=t('editor_add_entry'), bg='#1a2a3a', fg='#55aaff',
                  font=('Consolas', 9), bd=0, padx=10, pady=4,
                  command=lambda g=group: self.add_entry(g)).pack(pady=5)

    def render_entry(self, parent, gi, ei, entry):
        row = tk.Frame(parent, bg='#0f0f0f')
        row.pack(fill=tk.X, padx=6, pady=2)

        # Vars
        read_str = " | ".join(entry.read) if isinstance(entry.read, list) else str(entry.read)
        label_var = tk.StringVar(value=entry.label)
        read_var = tk.StringVar(value=read_str)
        type_var = tk.StringVar(value=entry.type)
        mode_var = tk.StringVar(value=entry.mode)
        value_var = tk.StringVar(value=str(entry.value))
        hotkey_var = tk.StringVar(value=entry.hotkey)

        def make_entry(var, width):
            return tk.Entry(row, textvariable=var, bg='#000000', fg='#00ff00',
                            font=('Consolas', 9), width=width,
                            insertbackground='#00ff00')

        make_entry(label_var, 20).pack(side=tk.LEFT, padx=1)
        make_entry(read_var, 30).pack(side=tk.LEFT, padx=1)

        ttk.Combobox(row, textvariable=type_var,
                     values=[TYPE_INT, TYPE_FLOAT, TYPE_DOUBLE, TYPE_BYTE, TYPE_INT64, TYPE_STRING],
                     width=7, font=('Consolas', 9)).pack(side=tk.LEFT, padx=1)

        make_entry(value_var, 10).pack(side=tk.LEFT, padx=1)

        ttk.Combobox(row, textvariable=mode_var,
                     values=[MODE_TOGGLE, MODE_ACTION, MODE_FREEZE, MODE_SCRIPT,
                             MODE_INJECT, MODE_FORMULA, MODE_CONDITION],
                     width=9, font=('Consolas', 9)).pack(side=tk.LEFT, padx=1)

        make_entry(hotkey_var, 6).pack(side=tk.LEFT, padx=1)

        def update(*_):
            entry.label = label_var.get()
            entry.read = [p.strip() for p in read_var.get().split('|')]
            entry.type = type_var.get()
            entry.mode = mode_var.get()
            try:
                v = value_var.get()
                if type_var.get() == TYPE_FLOAT or type_var.get() == TYPE_DOUBLE:
                    entry.value = float(v)
                elif type_var.get() == TYPE_STRING:
                    entry.value = v
                else:
                    entry.value = int(v) if v.lstrip('-').isdigit() else v
            except Exception:
                entry.value = value_var.get()
            entry.hotkey = hotkey_var.get()

        for v in (label_var, read_var, type_var, mode_var, value_var, hotkey_var):
            v.trace_add('write', update)

        tk.Button(row, text="✗", bg='#3a1a1a', fg='#ff5555',
                  font=('Consolas', 9), bd=0, padx=6,
                  command=lambda: self.delete_entry(entry)).pack(side=tk.RIGHT, padx=2)

    def add_entry(self, group):
        e = HTEntry()
        e.id = f"entry_{len(group.entries) + 1}"
        e.label = f"Entry {len(group.entries) + 1}"
        e.read = ["0x0"]
        e.type = TYPE_INT
        e.value = 0
        e.mode = MODE_TOGGLE
        group.add(e)
        self.render()

    def delete_entry(self, entry):
        for g in self.table.groups:
            if entry in g.entries:
                g.entries.remove(entry)
                break
        self.render()

    def delete_group(self, gi):
        if 0 <= gi < len(self.table.groups):
            del self.table.groups[gi]
        self.render()