#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine v3.0
Hook + Memory + DLL + HT Table + Who Writes + Multilingual
"""

# ==================== ADMIN ELEVATION (MUST BE FIRST) ====================
import ctypes
import sys
import os


def _is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _elevate_to_admin():
    try:
        if getattr(sys, 'frozen', False):
            exe = sys.executable
            params = " ".join(f'"{a}"' for a in sys.argv[1:])
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", exe, params, None, 1
            )
        else:
            script = os.path.abspath(sys.argv[0])
            params = " ".join(f'"{a}"' for a in sys.argv[1:])
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}" {params}', None, 1
            )
        return result > 32
    except Exception:
        return False


if not _is_admin():
    if _elevate_to_admin():
        sys.exit(0)
    else:
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                "Administrator privileges required.\n"
                "The application will now close.",
                "HookEngine",
                0x10
            )
        except Exception:
            pass
        sys.exit(1)
# ==================== END ADMIN ELEVATION ====================


import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import json
import time
import winreg
import psutil
from datetime import datetime

# ==================== CORE IMPORTS ====================
try:
    from core.process_manager import ProcessManager
except ImportError:
    class ProcessManager:
        def get_all_processes(self):
            return []
        def get_process_info(self, pid):
            return None

try:
    from core.memory_engine import MemoryEngine
except ImportError:
    class MemoryEngine:
        def __init__(self, pid):
            self.pid = pid
        def open(self): return False
        def close(self): pass
        def read_int(self, addr): return None
        def write_int(self, addr, val): return False

try:
    from core.value_scanner import UltraValueScanner
except ImportError:
    class UltraValueScanner:
        def __init__(self, pid):
            self.pid = pid
        def scan(self, t, v): return []
        def scan_all_ints(self): return []
        def scan_pointer(self, a): return []
        def scan_increased(self, r): return []
        def scan_decreased(self, r): return []
        def scan_unchanged(self, r): return []
        def scan_changed(self, r): return []

try:
    from core.lang import (
        t, current as cur_lang, save_language,
        get_saved_language, set_current as set_lang
    )
except ImportError:
    def t(key, **kwargs):
        return key
    def cur_lang(): return 'en'
    def save_language(lang): return False
    def get_saved_language(): return 'en'
    def set_lang(lang): pass

# ==================== HOOK IMPORTS ====================
try:
    from hook.hook_scanner import ProfessionalHookScannerV5
except ImportError:
    class ProfessionalHookScannerV5:
        def __init__(self, pid):
            self.pid = pid
        def set_mode(self, m): pass
        def set_target_dll(self, d): pass
        def scan_quick(self):
            return [], None
        def scan_all(self):
            return [], None

try:
    from hook.who_writes_ui import WhoWritesTab
except ImportError:
    WhoWritesTab = None

# ==================== HT IMPORTS ====================
try:
    from ht.ht_ui_v3 import HTTableV3
except ImportError:
    HTTableV3 = None

try:
    from ht.ht_editor import HTEditor
except ImportError:
    HTEditor = None

# ==================== INJECTOR ====================
try:
    from injector.dll_injector import ProfessionalDLLInjector
except ImportError:
    class ProfessionalDLLInjector:
        def __init__(self, pid):
            self.pid = pid
        def inject_loadlibrary(self, p): return False
        def inject_manual_map(self, p): return False
        def inject_thread_hijack(self, p): return False

# ==================== REPORT ====================
try:
    from report.report_generator import ReportGenerator
except ImportError:
    class ReportGenerator:
        def __init__(self, pid):
            self.pid = pid
        def generate_full_report(self):
            return f"Report — PID: {self.pid}"


# ==================== HELPERS ====================

def get_icon_path():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(script_dir, "ico", "YoudHook.ico"),
            os.path.join(script_dir, "icons", "YoudHook.ico"),
            os.path.join(script_dir, "YoudHook.ico"),
            os.path.join(os.getcwd(), "ico", "YoudHook.ico"),
            os.path.join(os.getcwd(), "YoudHook.ico"),
        ]
        if hasattr(sys, 'frozen'):
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            candidates.insert(0, os.path.join(exe_dir, "ico", "YoudHook.ico"))
            candidates.insert(0, os.path.join(exe_dir, "YoudHook.ico"))
        for path in candidates:
            if os.path.exists(path):
                return path
    except Exception:
        pass
    return None


def register_ht_extension():
    try:
        if hasattr(sys, 'frozen'):
            exe_path = os.path.abspath(sys.executable)
            base_dir = os.path.dirname(exe_path)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        icon_path = None
        for c in [
            os.path.join(base_dir, "ico", "YoudHook.ico"),
            os.path.join(base_dir, "YoudHook.ico"),
        ]:
            if os.path.exists(c):
                icon_path = c
                break

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.ht")
        winreg.SetValue(key, "", winreg.REG_SZ, "HookEngine.Table")
        winreg.CloseKey(key)

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\HookEngine.Table")
        winreg.SetValue(key, "", winreg.REG_SZ, "HookEngine Table")
        winreg.CloseKey(key)

        if icon_path:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\Classes\HookEngine.Table\DefaultIcon")
            winreg.SetValue(key, "", winreg.REG_SZ, icon_path)
            winreg.CloseKey(key)

        if hasattr(sys, 'frozen'):
            command = f'"{exe_path}" "%1"'
        else:
            command = f'"{sys.executable}" "{os.path.abspath(__file__)}" "%1"'

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Classes\HookEngine.Table\shell\open\command")
        winreg.SetValue(key, "", winreg.REG_SZ, command)
        winreg.CloseKey(key)

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Classes\.ht\ShellNew")
        winreg.SetValue(key, "NullFile", winreg.REG_SZ, "")
        winreg.CloseKey(key)

        return True
    except Exception:
        return False


# ==================== MAIN APP ====================

class HookEngine:
    def __init__(self):
        register_ht_extension()
        set_lang(get_saved_language())

        self.root = tk.Tk()
        self.root.title(t('app_title'))
        self.root.geometry("1600x1000")
        self.root.configure(bg='#0a0a0a')

        icon_path = get_icon_path()
        if icon_path:
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # State
        self.target_pid = None
        self.target_dll = None
        self.process_manager = ProcessManager()
        self.memory_engine = None
        self.hook_scanner = None
        self.value_scanner = None
        self.dll_injector = None
        self.is_analyzing = False
        self.hook_mode = "full"
        self.scan_results = []
        self.filtered_results = []
        self.frozen_addresses = []
        self.is_freezing = False
        self.ht_tab = None
        self.ww_tab = None
        self.ht_editor = None

        self.setup_styles()
        self.setup_ui()
        self.refresh_processes()

        if len(sys.argv) > 1 and sys.argv[1].endswith('.ht'):
            self.load_ht_file(sys.argv[1])

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.TFrame', background='#0a0a0a')
        style.configure('Dark.TLabel', background='#0a0a0a',
                        foreground='#00ff00', font=('Consolas', 10))
        style.configure('Header.TLabel', background='#0a0a0a',
                        foreground='#ff0000', font=('Consolas', 14, 'bold'))
        style.configure('Dark.TButton', background='#1a1a1a',
                        foreground='#00ff00', font=('Consolas', 10))
        style.configure('Nav.TButton', background='#0a2a0a',
                        foreground='#00ff00', font=('Consolas', 9))
        style.configure('TopNav.TButton', background='#2a0a0a',
                        foreground='#ff5555', font=('Consolas', 10, 'bold'))
        style.configure('Dark.TNotebook', background='#0a0a0a', borderwidth=0)
        style.configure('Dark.TNotebook.Tab', background='#1a1a1a',
                        foreground='#00ff00', font=('Consolas', 10))
        style.map('Dark.TNotebook.Tab', background=[('selected', '#333333')])
        style.configure('Dark.TRadiobutton', background='#0a0a0a',
                        foreground='#00ff00', font=('Consolas', 11))

    def setup_ui(self):
        # Header
        header_frame = ttk.Frame(self.root, style='Dark.TFrame')
        header_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(header_frame, text=t('app_title'),
                  style='Header.TLabel').pack()

        # Top nav
        topnav = ttk.Frame(self.root, style='Dark.TFrame')
        topnav.pack(fill=tk.X, padx=10, pady=(5, 0))

        ttk.Button(topnav, text=t('btn_ht_creator'),
                   command=self.open_ht_editor,
                   style='TopNav.TButton').pack(side=tk.LEFT, padx=3)
        ttk.Button(topnav, text=t('btn_dll_injector'),
                   command=self.open_dll_injector_window,
                   style='TopNav.TButton').pack(side=tk.LEFT, padx=3)
        ttk.Button(topnav, text=t('btn_settings'),
                   command=self.goto_settings,
                   style='TopNav.TButton').pack(side=tk.LEFT, padx=3)

        # Main layout
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # LEFT
        left_panel = ttk.Frame(main_frame, style='Dark.TFrame', width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        ttk.Label(left_panel, text=t('process_list'),
                  style='Header.TLabel').pack(anchor=tk.W, pady=(0, 5))

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(left_panel, textvariable=self.search_var, width=40)
        search_entry.pack(fill=tk.X, pady=(0, 5))
        search_entry.bind('<KeyRelease>', self.filter_processes)

        listbox_frame = ttk.Frame(left_panel, style='Dark.TFrame')
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.process_listbox = tk.Listbox(
            listbox_frame, bg='#000000', fg='#00ff00',
            selectbackground='#006600', font=('Consolas', 10),
            selectforeground='#ffffff', yscrollcommand=scrollbar.set
        )
        self.process_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.process_listbox.yview)

        self.process_info_label = ttk.Label(
            left_panel, text=t('process_none'),
            style='Dark.TLabel', wraplength=330
        )
        self.process_info_label.pack(anchor=tk.W, pady=(5, 0))

        btn_frame = ttk.Frame(left_panel, style='Dark.TFrame')
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(btn_frame, text=t('refresh'),
                   command=self.refresh_processes,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=t('select'),
                   command=self.select_process,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)

        ttk.Label(left_panel, text=t('target_dll'),
                  style='Dark.TLabel').pack(anchor=tk.W, pady=(10, 0))
        self.dll_search_var = tk.StringVar()
        ttk.Entry(left_panel, textvariable=self.dll_search_var,
                  width=40).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(left_panel, text=t('scan_by_dll'),
                   command=self.set_target_dll,
                   style='Dark.TButton').pack(fill=tk.X)
        ttk.Button(left_panel, text=t('save_ht'),
                   command=self.save_ht_file,
                   style='Dark.TButton').pack(fill=tk.X, pady=(5, 0))

        # RIGHT — Notebook
        right_panel = ttk.Frame(main_frame, style='Dark.TFrame')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(right_panel, style='Dark.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # HOOK
        self.hook_tab = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(self.hook_tab, text=t('tab_hook'))
        self.setup_hook_tab()

        # MEMORY
        self.memory_tab = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(self.memory_tab, text=t('tab_memory'))
        self.setup_memory_tab()

        # HT TABLE (v3)
        if HTTableV3 is not None:
            self.ht_tab_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
            self.notebook.add(self.ht_tab_frame, text=t('tab_ht_table'))
            self.ht_tab = HTTableV3(self.ht_tab_frame, self)

        # WHO WRITES
        if WhoWritesTab is not None:
            self.ww_tab_frame = ttk.Frame(self.notebook, style='Dark.TFrame')
            self.notebook.add(self.ww_tab_frame, text=t('tab_who_writes'))
            self.ww_tab = WhoWritesTab(self.ww_tab_frame, self)

        # REPORT
        self.report_tab = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(self.report_tab, text=t('tab_report'))
        self.setup_report_tab()

        # SETTINGS
        self.settings_tab = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(self.settings_tab, text=t('tab_settings'))
        self.setup_settings_tab()

    # ==================== HOOK TAB ====================

    def setup_hook_tab(self):
        nav_frame = ttk.Frame(self.hook_tab, style='Dark.TFrame')
        nav_frame.pack(fill=tk.X, padx=5, pady=5)

        for text, cmd in [("IAT", self.goto_iat), ("EAT", self.goto_eat),
                          ("JMP", self.goto_jmp), ("CALL", self.goto_call),
                          ("VTABLE", self.goto_vtable), ("DETOUR", self.goto_detour),
                          ("SYSCALL", self.goto_syscall), ("ANTI-DBG", self.goto_antidebug),
                          ("PUSH RET", self.goto_pushret), ("HOTPATCH", self.goto_hotpatch),
                          ("INT3", self.goto_int3)]:
            ttk.Button(nav_frame, text=text, command=cmd,
                       style='Nav.TButton').pack(side=tk.LEFT, padx=1)

        copy_frame = ttk.Frame(self.hook_tab, style='Dark.TFrame')
        copy_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(copy_frame, text=t('chars'),
                  style='Dark.TLabel').pack(side=tk.LEFT)
        self.copy_chars_var = tk.StringVar(value="1000")
        ttk.Entry(copy_frame, textvariable=self.copy_chars_var,
                  width=10).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(copy_frame, text=t('copy'),
                   command=self.copy_hook_results,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)

        self.hook_output = scrolledtext.ScrolledText(
            self.hook_tab, bg='#000000', fg='#00ff00', font=('Consolas', 10)
        )
        self.hook_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scan_frame = ttk.Frame(self.hook_tab, style='Dark.TFrame')
        scan_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(scan_frame, text=t('quick_scan'),
                   command=self.start_quick_scan,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(scan_frame, text=t('full_hook'),
                   command=self.start_full_hook,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(scan_frame, text=t('important'),
                   command=self.start_important_hook,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(scan_frame, text=t('filtered'),
                   command=self.start_filtered_hook,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(scan_frame, text=t('clear'),
                   command=self.clear_hook_output,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)

    # ==================== MEMORY TAB ====================

    def setup_memory_tab(self):
        top_frame = ttk.Frame(self.memory_tab, style='Dark.TFrame')
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top_frame, text=t('type'), style='Dark.TLabel').pack(side=tk.LEFT)
        self.scan_type_var = tk.StringVar(value="INT")
        ttk.Combobox(top_frame, textvariable=self.scan_type_var,
                     values=["INT", "FLOAT", "DOUBLE", "STRING", "BYTE", "AOB", "POINTER"],
                     width=10).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Label(top_frame, text=t('value'), style='Dark.TLabel').pack(side=tk.LEFT)
        self.scan_value_entry = ttk.Entry(top_frame, width=30)
        self.scan_value_entry.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(top_frame, text=t('scan'), command=self.scan_values,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text=t('all_values'), command=self.list_all_values,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text=t('pointer_scan'), command=self.scan_pointer,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)

        filter_frame = ttk.Frame(self.memory_tab, style='Dark.TFrame')
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        for text, cmd in [(t('increased'), self.scan_increased),
                          (t('decreased'), self.scan_decreased),
                          (t('unchanged'), self.scan_unchanged),
                          (t('changed'), self.scan_changed)]:
            ttk.Button(filter_frame, text=text, command=cmd,
                       style='Dark.TButton').pack(side=tk.LEFT, padx=2)

        listbox_frame = ttk.Frame(self.memory_tab, style='Dark.TFrame')
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.memory_listbox = tk.Listbox(
            listbox_frame, bg='#000000', fg='#00ff00',
            font=('Consolas', 10), selectbackground='#006600',
            selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set
        )
        self.memory_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.memory_listbox.yview)

        self.memory_listbox.bind('<Control-c>', self.copy_selected_memory)
        self.memory_listbox.bind('<Control-C>', self.copy_selected_memory)
        self.memory_listbox.bind('<c>', self.copy_selected_memory)
        self.memory_listbox.bind('<C>', self.copy_selected_memory)
        self.memory_listbox.bind('<Control-a>',
                                 lambda e: self.memory_listbox.select_set(0, tk.END))

        change_frame = ttk.Frame(self.memory_tab, style='Dark.TFrame')
        change_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(change_frame, text=t('new_value'),
                  style='Dark.TLabel').pack(side=tk.LEFT)
        self.new_value_entry = ttk.Entry(change_frame, width=20)
        self.new_value_entry.pack(side=tk.LEFT, padx=(5, 5))

        ttk.Button(change_frame, text=t('apply_selected'),
                   command=self.apply_memory_change,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(change_frame, text=t('apply_visible'),
                   command=self.apply_to_visible,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(change_frame, text=t('copy'),
                   command=self.copy_all_memory,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(change_frame, text=t('freeze'),
                   command=self.freeze_selected,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(change_frame, text=t('unfreeze'),
                   command=self.stop_freeze,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)

    # ==================== REPORT TAB ====================

    def setup_report_tab(self):
        self.report_output = scrolledtext.ScrolledText(
            self.report_tab, bg='#000000', fg='#00ff00', font=('Consolas', 10)
        )
        self.report_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(self.report_tab, style='Dark.TFrame')
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text=t('report'),
                   command=self.generate_report,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=t('report_save'),
                   command=self.save_report,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)

    # ==================== SETTINGS TAB ====================

    def setup_settings_tab(self):
        frame = ttk.Frame(self.settings_tab, style='Dark.TFrame')
        frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)

        ttk.Label(frame, text=t('settings_language'),
                  style='Header.TLabel').pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(frame, text=t('settings_language_hint'),
                  style='Dark.TLabel').pack(anchor=tk.W, pady=(0, 15))

        self.settings_lang_var = tk.StringVar(value=cur_lang())

        lang_frame = ttk.Frame(frame, style='Dark.TFrame')
        lang_frame.pack(anchor=tk.W, pady=(0, 20))

        ttk.Radiobutton(lang_frame, text=t('language_en'),
                        variable=self.settings_lang_var, value='en',
                        style='Dark.TRadiobutton').pack(anchor=tk.W, pady=4)
        ttk.Radiobutton(lang_frame, text=t('language_tr'),
                        variable=self.settings_lang_var, value='tr',
                        style='Dark.TRadiobutton').pack(anchor=tk.W, pady=4)

        ttk.Button(frame, text=t('save_settings'),
                   command=self.save_settings,
                   style='Dark.TButton').pack(anchor=tk.W, pady=(20, 0))

    def save_settings(self):
        new_lang = self.settings_lang_var.get()
        if new_lang == cur_lang():
            return
        save_language(new_lang)
        messagebox.showinfo(t('success'), t('restart_required'))

    def goto_settings(self):
        try:
            self.notebook.select(self.settings_tab)
        except Exception:
            pass

    # ==================== HT EDITOR ====================

    def open_ht_editor(self):
        if not HTEditor:
            messagebox.showerror(t('error'), "HT Editor not available")
            return
        if self.ht_tab is None:
            messagebox.showerror(t('error'), "HT Table not initialized")
            return
        try:
            HTEditor(self.root, self.ht_tab)
        except Exception as e:
            messagebox.showerror(t('error'), str(e))

    # ==================== DLL INJECTOR ====================

    def open_dll_injector_window(self):
        if not self.target_pid:
            messagebox.showwarning(t('warning'), t('warn_select_process'))
            return

        win = tk.Toplevel(self.root)
        win.title(t('btn_dll_injector'))
        win.geometry("600x500")
        win.configure(bg='#0a0a0a')

        tk.Label(win, text=t('btn_dll_injector'), bg='#0a0a0a', fg='#ff3030',
                 font=('Consolas', 16, 'bold')).pack(pady=10)

        tk.Label(win, text=f"Target: PID {self.target_pid}",
                 bg='#0a0a0a', fg='#00ff00',
                 font=('Consolas', 11)).pack()

        frame = tk.Frame(win, bg='#0a0a0a')
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tk.Label(frame, text="DLL File:", bg='#0a0a0a', fg='#00ff00',
                 font=('Consolas', 10)).pack(anchor=tk.W)

        path_var = tk.StringVar()
        tk.Entry(frame, textvariable=path_var, bg='#000000', fg='#00ff00',
                 font=('Consolas', 10), insertbackground='#00ff00'
                 ).pack(fill=tk.X, pady=5)

        tk.Button(frame, text="Browse...",
                  bg='#1a3a1a', fg='#00ff00', font=('Consolas', 10),
                  command=lambda: path_var.set(
                      filedialog.askopenfilename(filetypes=[("DLL", "*.dll")]))
                  ).pack(anchor=tk.W, pady=3)

        tk.Label(frame, text="Method:", bg='#0a0a0a', fg='#00ff00',
                 font=('Consolas', 10)).pack(anchor=tk.W, pady=(10, 0))

        method_var = tk.StringVar(value="LoadLibrary")
        ttk.Combobox(frame, textvariable=method_var,
                     values=["LoadLibrary", "Manual Map", "Thread Hijacking"],
                     width=25).pack(anchor=tk.W, pady=5)

        log = scrolledtext.ScrolledText(frame, bg='#000000', fg='#00ff00',
                                         font=('Consolas', 9), height=8)
        log.pack(fill=tk.BOTH, expand=True, pady=10)

        def do_inject():
            path = path_var.get()
            if not path or not os.path.exists(path):
                log.insert(tk.END, "[ERROR] Invalid DLL path\n")
                return
            try:
                inj = ProfessionalDLLInjector(self.target_pid)
                method = method_var.get()
                if method == "LoadLibrary":
                    ok = inj.inject_loadlibrary(path)
                elif method == "Manual Map":
                    ok = inj.inject_manual_map(path)
                else:
                    ok = inj.inject_thread_hijack(path)
                status = t('injection_success') if ok else t('injection_fail')
                log.insert(tk.END, f"[{'+' if ok else '-'}] {status}\n")
            except Exception as e:
                log.insert(tk.END, f"[ERROR] {e}\n")

        tk.Button(frame, text="INJECT",
                  bg='#2a0a0a', fg='#ff5555', font=('Consolas', 11, 'bold'),
                  command=do_inject).pack(pady=5)

    # ==================== PROCESS MGMT ====================

    def refresh_processes(self):
        try:
            self.process_listbox.delete(0, tk.END)
            for pid, name in self.process_manager.get_all_processes():
                self.process_listbox.insert(tk.END, f"{name} (PID: {pid})")
        except Exception:
            pass

    def filter_processes(self, event):
        try:
            search_text = self.search_var.get().lower()
            self.process_listbox.delete(0, tk.END)
            for pid, name in self.process_manager.get_all_processes():
                if search_text in name.lower():
                    self.process_listbox.insert(tk.END, f"{name} (PID: {pid})")
        except Exception:
            pass

    def select_process(self):
        self.target_pid = self.get_selected_pid()
        if self.target_pid:
            try:
                info = self.process_manager.get_process_info(self.target_pid)
                if info:
                    self.process_info_label.config(
                        text=t('process_info',
                               name=info['name'], pid=info['pid'],
                               mem=info['memory'])
                    )
            except Exception:
                pass
            if self.ht_tab:
                try:
                    self.ht_tab.update_exe_label()
                except Exception:
                    pass

    def get_selected_pid(self):
        selection = self.process_listbox.curselection()
        if not selection:
            messagebox.showwarning(t('warning'), t('warn_select_process'))
            return None
        try:
            text = self.process_listbox.get(selection[0])
            return int(text.split("PID: ")[1].rstrip(")"))
        except Exception:
            return None

    def set_target_dll(self):
        dll_name = self.dll_search_var.get().strip()
        if dll_name:
            self.target_dll = dll_name.lower()
        else:
            self.target_dll = None

    # ==================== HT SAVE/LOAD ====================

    def save_ht_file(self):
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".ht",
                filetypes=[("HookEngine Table", "*.ht")],
                initialfile="hookengine_table.ht"
            )
            if not path:
                return
            addresses = [self.memory_listbox.get(i)
                         for i in range(self.memory_listbox.size())]
            data = {
                'version': '3.0',
                'name': 'Quick Save',
                'addresses': addresses,
                'hook_results': self.hook_output.get(1.0, tk.END),
                'target_pid': self.target_pid,
                'game': self.target_dll or "",
                'saved_at': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                'language': cur_lang(),
                'groups': []
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo(t('success'), t('ht_saved', path=path))
            self.refresh_explorer()
        except Exception as e:
            messagebox.showerror(t('error'), str(e))

    def load_ht_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.loads(f.read())

            if 'addresses' in data:
                self.memory_listbox.delete(0, tk.END)
                for addr in data['addresses']:
                    self.memory_listbox.insert(tk.END, addr)

            if 'hook_results' in data:
                self.hook_output.insert(tk.END, data['hook_results'])

            if 'groups' in data and self.ht_tab:
                try:
                    from ht.ht_v3 import HTTable
                    self.ht_tab.table = HTTable.load(path)
                    self.ht_tab.ht_path = path
                    fname = os.path.basename(path)
                    self.ht_tab.ht_label.config(
                        text=f"{t('ht_current_table')} {fname}"
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def refresh_explorer(self):
        try:
            SHCNE_ASSOCCHANGED = 0x08000000
            SHCNF_IDLIST = 0x0000
            ctypes.windll.shell32.SHChangeNotify(
                SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None
            )
        except Exception:
            pass

    # ==================== HOOK NAV ====================

    def _jump(self, keyword):
        content = self.hook_output.get(1.0, tk.END)
        pos = content.find(keyword)
        if pos != -1:
            line = content[:pos].count('\n') + 1
            self.hook_output.see(f"{line}.0")

    def goto_iat(self): self._jump("IAT HOOK")
    def goto_eat(self): self._jump("EAT HOOK")
    def goto_jmp(self): self._jump("[JMP]")
    def goto_call(self): self._jump("[CALL]")
    def goto_vtable(self): self._jump("VTABLE")
    def goto_detour(self): self._jump("DETOUR")
    def goto_syscall(self): self._jump("SYSCALL")
    def goto_antidebug(self): self._jump("ANTI-DEBUG")
    def goto_pushret(self): self._jump("PUSH RET")
    def goto_hotpatch(self): self._jump("HOTPATCH")
    def goto_int3(self): self._jump("INT3")

    def copy_hook_results(self):
        try:
            count = int(self.copy_chars_var.get())
            content = self.hook_output.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(content[:count])
        except Exception:
            pass

    # ==================== HOOK SCAN ====================

    def start_quick_scan(self): self.start_hook_analysis("quick")
    def start_full_hook(self): self.start_hook_analysis("full")
    def start_important_hook(self): self.start_hook_analysis("important")
    def start_filtered_hook(self): self.start_hook_analysis("filtered")

    def start_hook_analysis(self, mode):
        if not self.target_pid:
            self.target_pid = self.get_selected_pid()
        if not self.target_pid or self.is_analyzing:
            return
        self.is_analyzing = True
        threading.Thread(target=self.run_hook_thread, args=(mode,), daemon=True).start()

    def run_hook_thread(self, mode):
        try:
            self.hook_output.insert(tk.END, f"[+] {mode.upper()} SCAN\n")
            self.hook_scanner = ProfessionalHookScannerV5(self.target_pid)
            self.hook_scanner.set_mode(mode)
            if self.target_dll:
                self.hook_scanner.set_target_dll(self.target_dll)

            if mode == "quick":
                results, _ = self.hook_scanner.scan_quick()
            else:
                results, output_path = self.hook_scanner.scan_all()
                if output_path:
                    self.hook_output.insert(tk.END, f"[+] TXT: {output_path}\n")

            for line in results:
                self.hook_output.insert(tk.END, line + "\n")
            self.hook_output.see(tk.END)
        except Exception as e:
            self.hook_output.insert(tk.END, f"[ERROR]: {e}\n")
        finally:
            self.is_analyzing = False

    def clear_hook_output(self):
        self.hook_output.delete(1.0, tk.END)

    # ==================== MEMORY SCAN ====================

    def scan_values(self):
        if not self.target_pid:
            return
        try:
            scan_type = self.scan_type_var.get()
            value_str = self.scan_value_entry.get()
            self.value_scanner = UltraValueScanner(self.target_pid)
            self.scan_results = self.value_scanner.scan(scan_type, value_str)
            self.filtered_results = self.scan_results.copy()
            self.update_memory_listbox()
        except Exception:
            pass

    def list_all_values(self):
        if not self.target_pid:
            return
        try:
            self.value_scanner = UltraValueScanner(self.target_pid)
            self.scan_results = self.value_scanner.scan_all_ints()
            self.filtered_results = self.scan_results.copy()
            self.update_memory_listbox()
        except Exception:
            pass

    def scan_pointer(self):
        if not self.target_pid:
            return
        try:
            value_str = self.scan_value_entry.get()
            target = int(value_str, 16)
            self.value_scanner = UltraValueScanner(self.target_pid)
            self.scan_results = self.value_scanner.scan_pointer(target)
            self.filtered_results = self.scan_results.copy()
            self.update_memory_listbox()
        except Exception:
            pass

    def scan_increased(self):
        if not self.filtered_results:
            return
        try:
            self.value_scanner = UltraValueScanner(self.target_pid)
            self.filtered_results = self.value_scanner.scan_increased(self.filtered_results)
            self.update_memory_listbox()
        except Exception:
            pass

    def scan_decreased(self):
        if not self.filtered_results:
            return
        try:
            self.value_scanner = UltraValueScanner(self.target_pid)
            self.filtered_results = self.value_scanner.scan_decreased(self.filtered_results)
            self.update_memory_listbox()
        except Exception:
            pass

    def scan_unchanged(self):
        if not self.filtered_results:
            return
        try:
            self.value_scanner = UltraValueScanner(self.target_pid)
            self.filtered_results = self.value_scanner.scan_unchanged(self.filtered_results)
            self.update_memory_listbox()
        except Exception:
            pass

    def scan_changed(self):
        if not self.filtered_results:
            return
        try:
            self.value_scanner = UltraValueScanner(self.target_pid)
            self.filtered_results = self.value_scanner.scan_changed(self.filtered_results)
            self.update_memory_listbox()
        except Exception:
            pass

    def update_memory_listbox(self):
        self.memory_listbox.delete(0, tk.END)
        for addr, value in self.filtered_results[:5000]:
            self.memory_listbox.insert(tk.END, f"0x{addr:X} = {value}")

    # ==================== COPY / APPLY ====================

    def copy_selected_memory(self, event=None):
        try:
            selections = self.memory_listbox.curselection()
            if not selections:
                return
            lines = [self.memory_listbox.get(i) for i in selections]
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(lines))
        except Exception:
            pass

    def copy_all_memory(self):
        try:
            lines = [self.memory_listbox.get(i)
                     for i in range(self.memory_listbox.size())]
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(lines))
            messagebox.showinfo(t('copy'), t('copied_info', count=len(lines)))
        except Exception:
            pass

    def apply_memory_change(self):
        selections = self.memory_listbox.curselection()
        if not selections:
            messagebox.showwarning(t('warning'), t('warn_select_address'))
            return
        try:
            new_value = self.new_value_entry.get()
            scan_type = self.scan_type_var.get()
            self.memory_engine = MemoryEngine(self.target_pid)
            self.memory_engine.open()
            success = 0
            for idx in selections:
                try:
                    addr = int(self.memory_listbox.get(idx).split(" = ")[0], 16)
                    if scan_type == "INT":
                        if self.memory_engine.write_int(addr, int(new_value)):
                            success += 1
                    elif scan_type == "FLOAT":
                        if self.memory_engine.write_float(addr, float(new_value)):
                            success += 1
                    elif scan_type == "DOUBLE":
                        if self.memory_engine.write_double(addr, float(new_value)):
                            success += 1
                    elif scan_type == "BYTE":
                        if self.memory_engine.write_byte(addr, int(new_value, 16)):
                            success += 1
                    elif scan_type == "STRING":
                        if self.memory_engine.write_string(addr, str(new_value)):
                            success += 1
                except Exception:
                    pass
            self.memory_engine.close()
            messagebox.showinfo(t('success'), t('applied_info', success=success))
        except Exception:
            pass

    def apply_to_visible(self):
        try:
            new_value = self.new_value_entry.get()
            scan_type = self.scan_type_var.get()
            self.memory_engine = MemoryEngine(self.target_pid)
            self.memory_engine.open()
            success = 0
            total = self.memory_listbox.size()
            for i in range(total):
                try:
                    addr = int(self.memory_listbox.get(i).split(" = ")[0], 16)
                    if scan_type == "INT":
                        if self.memory_engine.write_int(addr, int(new_value)):
                            success += 1
                    elif scan_type == "FLOAT":
                        if self.memory_engine.write_float(addr, float(new_value)):
                            success += 1
                    elif scan_type == "DOUBLE":
                        if self.memory_engine.write_double(addr, float(new_value)):
                            success += 1
                except Exception:
                    pass
            self.memory_engine.close()
            messagebox.showinfo(t('success'),
                                t('applied_bulk', success=success, total=total))
        except Exception:
            pass

    # ==================== FREEZE ====================

    def freeze_selected(self):
        selections = self.memory_listbox.curselection()
        if not selections:
            messagebox.showwarning(t('warning'), t('warn_select_address'))
            return

        self.frozen_addresses = []
        for idx in selections:
            try:
                text = self.memory_listbox.get(idx)
                addr = int(text.split(" = ")[0], 16)
                value = int(text.split(" = ")[1])
                self.frozen_addresses.append((addr, value))
            except Exception:
                pass

        if not self.frozen_addresses:
            return

        self.is_freezing = True
        threading.Thread(target=self._freeze_loop, daemon=True).start()
        messagebox.showinfo(t('freeze'),
                            t('frozen_info', count=len(self.frozen_addresses)))

    def _freeze_loop(self):
        engine = MemoryEngine(self.target_pid)
        engine.open()
        while self.is_freezing and self.frozen_addresses:
            for addr, value in self.frozen_addresses:
                try:
                    engine.write_int(addr, value)
                except Exception:
                    pass
            time.sleep(0.05)
        engine.close()

    def stop_freeze(self):
        self.is_freezing = False
        self.frozen_addresses = []
        messagebox.showinfo(t('unfreeze'), t('freeze_stopped'))

    # ==================== REPORT ====================

    def generate_report(self):
        if not self.target_pid:
            return
        try:
            self.report_output.delete(1.0, tk.END)
            self.report_output.insert(
                tk.END, ReportGenerator(self.target_pid).generate_full_report()
            )
        except Exception:
            pass

    def save_report(self):
        content = self.report_output.get(1.0, tk.END)
        if not content.strip():
            return
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".txt", filetypes=[("Text", "*.txt")]
            )
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
        except Exception:
            pass

    # ==================== RUN ====================

    def run(self):
        self.root.mainloop()


# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    try:
        app = HookEngine()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        input("Enter...")