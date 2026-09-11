#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOUD WHO WRITES — UI tab
Displays hardware breakpoint write events in a scrollable log
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from core.lang import t


class WhoWritesTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.debugger = None
        self.setup_ui()

    def setup_ui(self):
        # Top bar: address input + buttons
        top = ttk.Frame(self.parent, style='Dark.TFrame')
        top.pack(fill=tk.X, padx=5, pady=8)

        ttk.Label(top, text=t('ww_address_label'),
                  style='Dark.TLabel').pack(side=tk.LEFT, padx=(0, 5))

        self.addr_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.addr_var, width=20)
        entry.pack(side=tk.LEFT, padx=(0, 10))

        self.start_btn = ttk.Button(top, text=t('ww_start'),
                                     command=self.start_debug,
                                     style='Dark.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=2)

        self.stop_btn = ttk.Button(top, text=t('ww_stop'),
                                    command=self.stop_debug,
                                    style='Dark.TButton')
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        self.stop_btn.config(state=tk.DISABLED)

        ttk.Button(top, text=t('ww_clear'),
                   command=self.clear_output,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)

        # Info line
        self.info_label = ttk.Label(self.parent, text=t('ww_how_to_use'),
                                     style='Dark.TLabel', font=('Consolas', 9))
        self.info_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

        # Status
        self.status_label = ttk.Label(self.parent, text=t('ww_status_idle'),
                                       style='Dark.TLabel',
                                       font=('Consolas', 10, 'bold'))
        self.status_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

        # Output area
        self.output = scrolledtext.ScrolledText(
            self.parent, bg='#000000', fg='#00ff00',
            font=('Consolas', 9), wrap=tk.WORD
        )
        self.output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def clear_output(self):
        self.output.delete(1.0, tk.END)

    def start_debug(self):
        pid = getattr(self.app, 'target_pid', None)
        if not pid:
            messagebox.showwarning(t('warning'), t('ww_select_process'))
            return

        addr_str = self.addr_var.get().strip().replace('0x', '').replace('0X', '')
        if not addr_str:
            messagebox.showwarning(t('warning'), t('ww_invalid_address'))
            return
        try:
            address = int(addr_str, 16)
        except ValueError:
            messagebox.showwarning(t('warning'), t('ww_invalid_address'))
            return

        try:
            from hook.who_writes import WhoWritesDebugger
            self.debugger = WhoWritesDebugger(pid, address,
                                              on_event=self.on_write_event)
            self.debugger.start()
        except Exception as e:
            messagebox.showerror(t('error'), str(e))
            self.debugger = None
            return

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text=t('ww_status_running'))
        self.output.insert(tk.END,
                            t('ww_started', pid=pid, addr=address) + "\n\n")
        self.output.see(tk.END)

    def stop_debug(self):
        if self.debugger:
            try:
                self.debugger.stop()
            except Exception:
                pass
            count = len(self.debugger.records)
            self.output.insert(tk.END,
                                "\n" + t('ww_stopped_info', count=count) + "\n")
            self.debugger = None

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text=t('ww_status_stopped'))

    def on_write_event(self, rec):
        """Called from debugger thread — marshal to UI thread"""
        try:
            self.parent.after(0, lambda: self._write_event_ui(rec))
        except Exception:
            pass

    def _write_event_ui(self, rec):
        lines = []
        lines.append("=" * 60)
        lines.append(f"  {t('ww_write_detected')}")
        lines.append("=" * 60)
        lines.append(f"{t('ww_thread')}: {rec['thread']}")
        lines.append(f"{t('ww_rip')}: 0x{rec['rip']:X}")
        lines.append(f"{t('ww_module')}: {rec['module']} + 0x{rec['offset']:X}")
        lines.append(f"{t('ww_instruction')}: {rec['instruction']}")
        lines.append("")
        lines.append(f"{t('ww_registers')}:")
        for k, v in rec['regs'].items():
            lines.append(f"  {k} = 0x{v:X}")
        lines.append("")

        self.output.insert(tk.END, "\n".join(lines) + "\n")
        self.output.see(tk.END)