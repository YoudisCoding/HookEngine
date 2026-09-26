#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — HT v3.0 UI

FIX v3.1:
- _update_values artık batch okuma kullanıyor (read_batch)
- 500ms polling → 800ms'e çıkarıldı (CPU rahatlatma)
- Refresh skip: engine yoksa hiç çağrı yapılmıyor
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import time

from ht.ht_v3 import (
    HTTable, HTEntry, HTGroup, default_template,
    MODE_TOGGLE, MODE_ACTION, MODE_FREEZE, MODE_SCRIPT,
    MODE_INJECT, MODE_FORMULA, MODE_CONDITION
)
from ht.ht_engine import HTEngine
from core.lang import t


class HTTableV3:
    """HT v3.0 Table UI"""

    REFRESH_MS = 800

    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.engine = None
        self.table = None
        self.ht_path = None
        self.entry_widgets = {}
        self.setup_ui()
        self._periodic_refresh()

    # ==================== UI ====================
    def setup_ui(self):
        header = ttk.Frame(self.parent, style='Dark.TFrame')
        header.pack(fill=tk.X, padx=5, pady=5)

        self.exe_label = ttk.Label(
            header, text=f"{t('ht_current_exe')} {t('ht_not_selected')}",
            style='Dark.TLabel', font=('Consolas', 10, 'bold')
        )
        self.exe_label.pack(side=tk.LEFT, padx=(0, 20))

        self.ht_label = ttk.Label(
            header, text=f"{t('ht_current_table')} {t('ht_none')}",
            style='Dark.TLabel', font=('Consolas', 10)
        )
        self.ht_label.pack(side=tk.LEFT)

        ctrl = ttk.Frame(self.parent, style='Dark.TFrame')
        ctrl.pack(fill=tk.X, padx=5, pady=(0, 5))

        ttk.Button(ctrl, text=t('ht_btn_add'),
                   command=self.add_ht, style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text=t('ht_btn_ok'),
                   command=self.apply_ht, style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text=t('ht_btn_clear'),
                   command=self.clear_all, style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text=t('ht_btn_reload'),
                   command=self.reload_widgets, style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text=t('ht_btn_edit'),
                   command=self.open_editor, style='Dark.TButton').pack(side=tk.LEFT, padx=2)

        self.info_label = ttk.Label(
            self.parent, text=t('ht_how_to_use'),
            style='Dark.TLabel', font=('Consolas', 9)
        )
        self.info_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

        self.status_label = ttk.Label(
            self.parent, text="", style='Dark.TLabel',
            font=('Consolas', 9, 'bold'), foreground='#ffff55'
        )
        self.status_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

        container = ttk.Frame(self.parent, style='Dark.TFrame')
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(container, bg='#0a0a0a', highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=sb.set)

        self.groups_frame = ttk.Frame(self.canvas, style='Dark.TFrame')
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

        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _periodic_refresh(self):
        if self.table and self.engine and self.entry_widgets:
            try:
                self._update_values()
            except Exception:
                pass
        self.parent.after(self.REFRESH_MS, self._periodic_refresh)

    def _update_values(self):
        """Batch okuma — resolver cache'inden faydalanır."""
        if not self.engine or not self.engine.resolver:
            return
        entries = self._all_entries()
        if not entries:
            return

        try:
            values = self.engine.resolver.read_batch(entries)
        except Exception:
            return

        for entry in entries:
            w = self.entry_widgets.get(entry.id)
            if not w:
                continue
            current = values.get(entry.id)
            if current is None:
                try:
                    w['value_label'].config(text="?")
                except Exception:
                    pass
                continue
            try:
                if isinstance(current, float):
                    w['value_label'].config(text=f"{current:.2f}")
                else:
                    w['value_label'].config(text=str(current))
            except Exception:
                pass

    def _all_entries(self):
        if not self.table:
            return []
        result = []
        for g in self.table.groups:
            result.extend(g.entries)
        return result

    def update_exe_label(self):
        pid = getattr(self.app, 'target_pid', None)
        if pid:
            try:
                import psutil
                proc = psutil.Process(pid)
                self.exe_label.config(
                    text=f"{t('ht_current_exe')} {proc.name()}  (PID: {pid})"
                )
            except Exception:
                self.exe_label.config(
                    text=f"{t('ht_current_exe')} {t('ht_not_selected')}"
                )
        else:
            self.exe_label.config(
                text=f"{t('ht_current_exe')} {t('ht_not_selected')}"
            )

    # ==================== FILE ====================
    def add_ht(self):
        path = filedialog.askopenfilename(
            title=t('ht_btn_add'),
            filetypes=[("HT Files", "*.ht"), ("All Files", "*.*")]
        )
        if not path:
            return
        table = HTTable.load(path)
        if not table:
            messagebox.showerror(t('error'), t('ht_load_failed', error=path))
            return
        self.table = table
        self.ht_path = path
        fname = os.path.basename(path)
        self.ht_label.config(text=f"{t('ht_current_table')} {fname}")
        self.status_label.config(
            text=t('ht_loaded_info', name=fname, count=len(table.groups)),
            foreground='#55ff55'
        )

    def apply_ht(self):
        if not self.table:
            messagebox.showwarning(t('warning'), t('warn_select_entry'))
            return
        pid = getattr(self.app, 'target_pid', None)
        if not pid:
            messagebox.showwarning(t('warning'), t('warn_select_process'))
            return

        if self.engine is None:
            self.engine = HTEngine(pid, on_log=self._log_engine)
        else:
            self.engine.unload()
            self.engine = HTEngine(pid, on_log=self._log_engine)

        if not self.engine.load(self.table):
            messagebox.showerror(t('error'), "HT validation failed — see log")
            return

        self.clear_widgets()
        self.render_groups()
        self.status_label.config(
            text=f"OK — {self.table.name} active", foreground='#55ff55'
        )

    def clear_all(self):
        if self.engine:
            self.engine.unload()
            self.engine = None
        self.table = None
        self.ht_path = None
        self.ht_label.config(text=f"{t('ht_current_table')} {t('ht_none')}")
        self.clear_widgets()
        self.status_label.config(text="", foreground='#ffff55')
        self.info_label.config(text=t('ht_how_to_use'))

    def clear_widgets(self):
        for w in self.groups_frame.winfo_children():
            w.destroy()
        self.entry_widgets = {}

    def reload_widgets(self):
        if self.table:
            self.clear_widgets()
            self.render_groups()

    def _log_engine(self, msg):
        try:
            self.status_label.config(text=msg, foreground='#00aaff')
        except Exception:
            pass

    # ==================== RENDER ====================
    def render_groups(self):
        if not self.table:
            return
        for group in self.table.groups:
            self.render_group(group)

    def render_group(self, group):
        gf = tk.Frame(self.groups_frame, bg='#0f0f0f',
                      highlightbackground=group.color, highlightthickness=1)
        gf.pack(fill=tk.X, padx=4, pady=6)

        header = tk.Frame(gf, bg='#0f0f0f')
        header.pack(fill=tk.X, padx=6, pady=(6, 3))

        tk.Label(header, text=f"> {group.name}", bg='#0f0f0f',
                 fg=group.color, font=('Consolas', 11, 'bold')).pack(side=tk.LEFT)

        btn_frame = tk.Frame(header, bg='#0f0f0f')
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(btn_frame, text=t('ht_enable_all'), bg='#1a3a1a', fg='#00ff00',
                  font=('Consolas', 8), bd=0, padx=6,
                  command=lambda g=group: self.enable_all(g)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text=t('ht_disable_all'), bg='#3a1a1a', fg='#ff5555',
                  font=('Consolas', 8), bd=0, padx=6,
                  command=lambda g=group: self.disable_all(g)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text=t('ht_freeze_all'), bg='#1a2a3a', fg='#55aaff',
                  font=('Consolas', 8), bd=0, padx=6,
                  command=lambda g=group: self.freeze_all(g)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text=t('ht_unfreeze_all'), bg='#2a2a2a', fg='#aaaaaa',
                  font=('Consolas', 8), bd=0, padx=6,
                  command=lambda g=group: self.unfreeze_all(g)).pack(side=tk.LEFT, padx=2)

        for entry in group.entries:
            self.render_entry(gf, entry)

    def render_entry(self, parent, entry):
        row = tk.Frame(parent, bg='#0f0f0f')
        row.pack(fill=tk.X, padx=6, pady=3)

        var = tk.BooleanVar(value=entry.enabled_by_default)
        chk = tk.Checkbutton(
            row, variable=var, bg='#0f0f0f', fg='#00ff00',
            activebackground='#0f0f0f', activeforeground='#00ff00',
            selectcolor='#000000', bd=0
        )
        chk.pack(side=tk.LEFT)

        label_text = entry.label
        if entry.hotkey:
            label_text += f"  [{entry.hotkey}]"
        tk.Label(row, text=label_text, bg='#0f0f0f', fg='#cccccc',
                 font=('Consolas', 10), width=24, anchor='w').pack(side=tk.LEFT, padx=4)

        value_label = tk.Label(row, text="?", bg='#0f0f0f', fg='#55aaff',
                                font=('Consolas', 10, 'bold'), width=10, anchor='w')
        value_label.pack(side=tk.LEFT, padx=4)

        tk.Label(row, text=f"-> {entry.value}", bg='#0f0f0f', fg='#888888',
                 font=('Consolas', 9), width=10, anchor='w').pack(side=tk.LEFT)

        tk.Label(row, text=entry.description or "", bg='#0f0f0f', fg='#666666',
                 font=('Consolas', 9), anchor='w').pack(side=tk.LEFT, padx=4)

        def on_toggle(e=entry, v=var):
            e.enabled_by_default = v.get()
            if self.engine:
                if v.get():
                    self.engine.enable(e)
                else:
                    self.engine.disable(e)
        chk.config(command=on_toggle)

        if entry.mode in (MODE_ACTION, MODE_FREEZE, MODE_INJECT):
            btn_text = t('ht_run') if entry.mode == MODE_ACTION else t('ht_freeze')
            tk.Button(
                row, text=btn_text,
                bg='#1a3a1a', fg='#00ff00', font=('Consolas', 8),
                bd=0, padx=8,
                command=lambda e=entry: self.execute_entry(e)
            ).pack(side=tk.RIGHT, padx=2)

        self.entry_widgets[entry.id] = {
            'var': var,
            'value_label': value_label,
            'chk': chk,
        }

    # ==================== ACTIONS ====================
    def execute_entry(self, entry):
        if not self.engine:
            return
        if entry.id in self.engine.active_entries:
            self.engine.disable(entry)
        else:
            self.engine.enable(entry)

    def enable_all(self, group):
        for e in group.entries:
            e.enabled_by_default = True
            if self.engine and e.id not in self.engine.active_entries:
                self.engine.enable(e)
        self.reload_widgets()

    def disable_all(self, group):
        for e in group.entries:
            e.enabled_by_default = False
            if self.engine and e.id in self.engine.active_entries:
                self.engine.disable(e)
        self.reload_widgets()

    def freeze_all(self, group):
        for e in group.entries:
            if e.mode != MODE_FREEZE:
                e.mode = MODE_FREEZE
            if self.engine and e.id not in self.engine.active_entries:
                self.engine.enable(e)
        self.reload_widgets()

    def unfreeze_all(self, group):
        for e in group.entries:
            if self.engine and e.id in self.engine.active_entries:
                self.engine.disable(e)
        self.reload_widgets()

    # ==================== EDITOR ====================
    def open_editor(self):
        try:
            from ht.ht_editor import HTEditor
            HTEditor(self.parent, self)
        except ImportError:
            messagebox.showerror(t('error'), "HT Editor module not found")