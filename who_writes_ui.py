#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — Who Writes UI (User-Mode)
Polling + thread snapshot
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time

from hook.who_writes import WhoWrites
from core.lang import t


class WhoWritesTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.ww = None
        self.setup_ui()

    def setup_ui(self):
        # ==================== TOP BAR ====================
        top = tk.Frame(self.parent, bg='#0f1115')
        top.pack(fill=tk.X, padx=12, pady=(12, 8))

        tk.Label(top, text="👁", bg='#0f1115', fg='#58a6ff',
                 font=('Segoe UI', 12)).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(top, text=t('ww_address_label'), bg='#0f1115', fg='#e6edf3',
                 font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 6))

        self.addr_var = tk.StringVar()
        addr_entry = tk.Entry(top, textvariable=self.addr_var, width=18,
                              bg='#21262e', fg='#e6edf3',
                              insertbackground='#e6edf3', borderwidth=0,
                              font=('Cascadia Code', 10),
                              highlightthickness=1, highlightbackground='#2a303a')
        addr_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=5)

        tk.Label(top, text="Type:", bg='#0f1115', fg='#7d8590',
                 font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 6))

        self.type_var = tk.StringVar(value='byte')
        type_combo = ttk.Combobox(
            top, textvariable=self.type_var,
            values=['byte', 'word', 'int', 'float', 'double',
                    'int8', 'uint8', 'int16', 'uint16',
                    'int32', 'uint32', 'int64', 'uint64'],
            width=10, state='readonly'
        )
        type_combo.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(top, text="ms:", bg='#0f1115', fg='#7d8590',
                 font=('Segoe UI', 10)).pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value='20')
        interval_entry = tk.Entry(top, textvariable=self.interval_var, width=5,
                                  bg='#21262e', fg='#e6edf3',
                                  insertbackground='#e6edf3', borderwidth=0,
                                  font=('Cascadia Code', 10),
                                  highlightthickness=1, highlightbackground='#2a303a')
        interval_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=5)

        self.debug_var = tk.BooleanVar(value=False)
        tk.Checkbutton(top, text="Debug", variable=self.debug_var,
                       bg='#0f1115', fg='#e6edf3',
                       activebackground='#0f1115',
                       selectcolor='#21262e',
                       font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 10))

        # Butonlar
        self.start_btn = self._make_button(top, "BAŞLAT", self.start_watch,
                                            icon='▶', color='#3fb950')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.stop_btn = self._make_button(top, "DURDUR", self.stop_watch,
                                           icon='⏹', color='#f85149')
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 6))
        self.stop_btn.configure(state=tk.DISABLED)

        self._make_button(top, "TEMİZLE", self.clear_output,
                          icon='🗑', color='#d29922').pack(side=tk.LEFT)

        # ==================== STATUS ====================
        self.status_label = tk.Label(
            self.parent, text=t('ww_status_idle'),
            bg='#0f1115', fg='#7d8590',
            font=('Segoe UI', 10, 'bold')
        )
        self.status_label.pack(anchor=tk.W, padx=12, pady=(0, 8))

        # ==================== INFO ====================
        tk.Label(self.parent, text=t('ww_how_to_use'),
                 bg='#0f1115', fg='#484f58',
                 font=('Segoe UI', 9)).pack(anchor=tk.W, padx=12, pady=(0, 8))

        # ==================== OUTPUT ====================
        output_frame = tk.Frame(self.parent, bg='#1c2129',
                                highlightthickness=1, highlightbackground='#2a303a')
        output_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.output = scrolledtext.ScrolledText(
            output_frame, bg='#0f1115', fg='#e6edf3',
            font=('Cascadia Code', 9), wrap=tk.WORD,
            borderwidth=0, insertbackground='#e6edf3',
            selectbackground='#1f6feb', selectforeground='#ffffff',
            padx=10, pady=10
        )
        self.output.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def _make_button(self, parent, text, command, icon='', color='#58a6ff'):
        btn = tk.Button(
            parent, text=f"{icon} {text}" if icon else text,
            command=command, bg='#1c2129', fg=color,
            activebackground='#2a303a', activeforeground=color,
            font=('Segoe UI', 10, 'bold'),
            borderwidth=0, padx=12, pady=6, cursor='hand2'
        )
        return btn

    # ==================== START ====================
    def start_watch(self):
        pid = getattr(self.app, 'target_pid', None)
        if not pid:
            messagebox.showwarning("Uyarı", t('ww_select_process'))
            return

        addr_str = self.addr_var.get().strip().replace('0x', '').replace('0X', '')
        if not addr_str:
            messagebox.showwarning("Uyarı", t('ww_invalid_address'))
            return

        try:
            address = int(addr_str, 16)
        except ValueError:
            messagebox.showwarning("Uyarı", t('ww_invalid_address'))
            return

        try:
            interval = int(self.interval_var.get())
        except ValueError:
            interval = 20

        value_type = self.type_var.get()
        debug = bool(self.debug_var.get())

        try:
            self.ww = WhoWrites(
                pid=pid,
                address=address,
                value_type=value_type,
                interval_ms=interval,
                on_event=self._on_event,
                debug=debug,
            )
            self.ww.start()
        except Exception as e:
            messagebox.showerror("Hata", str(e))
            self.ww = None
            return

        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.status_label.configure(text=t('ww_status_running'), fg='#d29922')

        self.output.insert(
            tk.END,
            f"[+] İzleniyor: 0x{address:X} ({value_type}), interval={interval}ms\n"
        )
        if debug:
            self.output.insert(tk.END, "[+] DEBUG modu açık — CMD'de [SNAP] satırlarını gör\n")
        self.output.insert(tk.END, "\n")
        self.output.see(tk.END)

    # ==================== STOP ====================
    def stop_watch(self):
        if self.ww:
            try:
                self.ww.stop()
            except Exception:
                pass
            cnt = len(self.ww.records)
            self.output.insert(tk.END, f"\n[*] Durduruldu — {cnt} olay yakalandı\n")
            self.ww = None

        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.status_label.configure(text=t('ww_status_stopped'), fg='#7d8590')

    # ==================== CLEAR ====================
    def clear_output(self):
        self.output.delete(1.0, tk.END)

    # ==================== EVENT ====================
    def _on_event(self, rec):
        try:
            self.parent.after(0, lambda: self._print_event(rec))
        except Exception:
            pass

    def _print_event(self, rec):
        lines = []
        lines.append(
            f"═══ DEĞİŞİM @ {time.strftime('%H:%M:%S', time.localtime(rec['time']))} ═══"
        )
        lines.append(f"  {rec['old']}  →  {rec['new']}    (0x{rec['address']:X})")

        if rec['threads']:
            lines.append(f"  Threads: {len(rec['threads'])}")
            for th in rec['threads'][:12]:
                lines.append(
                    f"    [{th['tid']:>6}]  {th['module']}+0x{th['offset']:X}"
                )
        else:
            lines.append("  (thread snapshot yok)")

        lines.append("")
        self.output.insert(tk.END, "\n".join(lines) + "\n")
        self.output.see(tk.END)