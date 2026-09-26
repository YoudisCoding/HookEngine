#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine v3.1 — main.py
Fast multi-threaded scanner + pipe separator fix

FIX v3.1:
- _write_by_type WORD/BYTE overflow guard
- save_ht_file v3 format (HTTable.save ile aynı şema)
- import time temizlendi
- Refresh ve scan işlemleri Tk-safe
- PATH FIX: src/ + others/ sys.path'e ekleniyor (frozen modda sys._MEIPASS)
- ICON FIX: ico/ ve others/ico/ her ikisi de deneniyor
"""

# ==================== ADMIN ELEVATION ====================
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


# ==================== PATH FIX ====================
# Proje yapısı (development):
#   HookTool/
#   ├── main.py
#   ├── src/       (core, hook, ht, injector, installer)
#   ├── others/    (report, bat, scripts, ico, garbage, hook_results)
#   └── ico/
#
# PyInstaller --onefile ile paketlendiğinde kaynaklar `sys._MEIPASS`
# altında açılır. Aşağıdaki blok her iki durumu da kapsar.
if getattr(sys, 'frozen', False):
    _HERE = getattr(sys, '_MEIPASS',
                    os.path.dirname(os.path.abspath(sys.executable)))
else:
    _HERE = os.path.dirname(os.path.abspath(__file__))

# sys.path'e eklenecek klasörler — sırayla denenir
_IMPORT_PATHS = [
    os.path.join(_HERE, "src"),                       # core, hook, ht, injector, installer
    os.path.join(_HERE, "others"),                    # report paketi
    os.path.join(_HERE, "others", "report"),          # report alt paketi
]
for _p in _IMPORT_PATHS:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# İkon arama klasörleri
_ICON_DIRS = [
    os.path.join(_HERE, "ico"),
    os.path.join(_HERE, "others", "ico"),
    os.path.join(_HERE, "icons"),
    os.path.join(_HERE, ""),
]
# ==================== END PATH FIX ====================


import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import json
import time
import winreg
from datetime import datetime


# ==================== CORE IMPORTS ====================
try:
    from core.process_manager import ProcessManager
except ImportError:
    class ProcessManager:
        def get_all_processes(self): return []
        def get_process_info(self, pid): return None
        def get_process_modules(self, pid): return []
        def get_process_threads(self, pid): return []
        def get_process_connections(self, pid): return []

try:
    from core.memory_engine import MemoryEngine
except ImportError:
    class MemoryEngine:
        def __init__(self, pid): self.pid = pid
        def open(self): return False
        def close(self): pass
        def read_int(self, a): return None
        def write_int(self, a, v): return False
        def write_int64(self, a, v): return False
        def read_float(self, a): return None
        def write_float(self, a, v): return False
        def read_double(self, a): return None
        def write_double(self, a, v): return False
        def read_byte(self, a): return None
        def write_byte(self, a, v): return False
        def read_string(self, a, n=256): return None
        def write_string(self, a, v): return False
        def write_bytes(self, a, d): return False

try:
    from core.fast_scanner import FastScanner
    FAST_SCANNER_AVAILABLE = True
except ImportError:
    FastScanner = None
    FAST_SCANNER_AVAILABLE = False
    print("[!] core.fast_scanner bulunamadi")

try:
    from core.value_scanner import UltraValueScanner
except ImportError:
    class UltraValueScanner:
        def __init__(self, pid): self.pid = pid
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
    def t(key, **kwargs): return key
    def cur_lang(): return 'en'
    def save_language(lang): return False
    def get_saved_language(): return 'en'
    def set_lang(lang): pass

# ==================== VIP ====================
try:
    from core.vip import is_vip, activate_key, deactivate_key, get_vip_info, get_hwid
    VIP_AVAILABLE = True
except ImportError:
    VIP_AVAILABLE = False
    def is_vip(): return False
    def activate_key(k): return False, "VIP modulu yok"
    def deactivate_key(): return False
    def get_vip_info(): return None
    def get_hwid(): return "unknown"

# ==================== HOOK IMPORTS ====================
try:
    from hook.hook_scanner import ProfessionalHookScannerV5
except ImportError:
    class ProfessionalHookScannerV5:
        def __init__(self, pid): self.pid = pid
        def set_mode(self, m): pass
        def set_target_dll(self, d): pass
        def scan_quick(self): return [], None
        def scan_all(self): return [], None

try:
    from hook.who_writes_ui import WhoWritesTab
except ImportError:
    WhoWritesTab = None

try:
    from ht.ht_ui_v3 import HTTableV3
except ImportError:
    HTTableV3 = None

try:
    from ht.ht_editor import HTEditor
except ImportError:
    HTEditor = None

try:
    from ht.ht_v3 import HTTable as HTTableV3Model, HTGroup, HTEntry
except ImportError:
    HTTableV3Model = None
    HTGroup = None
    HTEntry = None

try:
    from injector.dll_injector import ProfessionalDLLInjector
except ImportError:
    class ProfessionalDLLInjector:
        def __init__(self, pid): self.pid = pid
        def inject_loadlibrary(self, p): return False
        def inject_manual_map(self, p): return False
        def inject_thread_hijack(self, p): return False

try:
    from report.report_generator import ReportGenerator
except ImportError:
    class ReportGenerator:
        def __init__(self, pid): self.pid = pid
        def generate_full_report(self):
            return f"Report — PID: {self.pid}"


# ==================== TEMA ====================
class Theme:
    BG          = '#0f1115'
    BG_PANEL    = '#161a22'
    BG_CARD     = '#1c2129'
    BG_INPUT    = '#21262e'
    BG_HOVER    = '#2a303a'
    BG_ACTIVE   = '#323945'

    BORDER      = '#2a303a'
    BORDER_LIT  = '#3a4250'

    TEXT        = '#e6edf3'
    TEXT_DIM    = '#7d8590'
    TEXT_MUTE   = '#484f58'
    TITLE       = '#ffffff'

    ACCENT      = '#58a6ff'
    ACCENT_DIM  = '#1f6feb'
    SUCCESS     = '#3fb950'
    WARNING     = '#d29922'
    ERROR       = '#f85149'
    PURPLE      = '#bc8cff'
    CYAN        = '#39c5cf'
    GOLD        = '#e3b341'

    FONT_UI     = ('Segoe UI', 10)
    FONT_UI_B   = ('Segoe UI', 10, 'bold')
    FONT_UI_L   = ('Segoe UI', 11)
    FONT_UI_XL  = ('Segoe UI', 13, 'bold')
    FONT_TITLE  = ('Segoe UI', 18, 'bold')
    FONT_SUB    = ('Segoe UI', 9)
    FONT_MONO   = ('Cascadia Code', 10)
    FONT_MONO_S = ('Cascadia Code', 9)
    FONT_MONO_XS = ('Cascadia Code', 8)

    @classmethod
    def apply_vip(cls):
        cls.BG          = '#12100a'
        cls.BG_PANEL    = '#1a1710'
        cls.BG_CARD     = '#211d14'
        cls.BG_INPUT    = '#2a2418'
        cls.BG_HOVER    = '#332c1c'
        cls.BG_ACTIVE   = '#3d3422'
        cls.BORDER      = '#3a3020'
        cls.BORDER_LIT  = '#5a4a30'
        cls.TEXT        = '#f0e6d0'
        cls.TEXT_DIM    = '#a89878'
        cls.TEXT_MUTE   = '#6a5f48'
        cls.TITLE       = '#ffffff'
        cls.ACCENT      = '#e3b341'
        cls.ACCENT_DIM  = '#b8932f'
        cls.SUCCESS     = '#7fc460'
        cls.WARNING     = '#e3b341'
        cls.ERROR       = '#e07060'
        cls.PURPLE      = '#bc8cff'
        cls.CYAN        = '#39c5cf'
        cls.GOLD        = '#f5d76e'


# ==================== HELPERS ====================
def get_icon_path(vip=False):
    """İkon dosyasını bul — frozen ve dev modda çalışır."""
    name = "YoudHookVIP.ico" if vip else "YoudHook.ico"
    try:
        if hasattr(sys, 'frozen'):
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            for d in (exe_dir,
                      os.path.join(exe_dir, "ico"),
                      os.path.join(exe_dir, "others", "ico"),
                      getattr(sys, '_MEIPASS', '')):
                if not d:
                    continue
                p = os.path.join(d, name)
                if os.path.exists(p):
                    return p

        for d in _ICON_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    except Exception:
        pass
    return None


def register_ht_extension():
    try:
        if hasattr(sys, 'frozen'):
            exe_path = os.path.abspath(sys.executable)
            base_dir = os.path.dirname(exe_path)
        else:
            exe_path = None
            base_dir = _HERE

        icon_path = get_icon_path(vip=False)

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

        self.vip_active = is_vip()
        if self.vip_active:
            Theme.apply_vip()

        set_lang(get_saved_language())

        self.root = tk.Tk()
        self.root.title("HookEngine v3.1 — " + ("VIP" if self.vip_active else "HOOK + MEMORY + DLL + HT"))
        self.root.geometry("1600x1000")
        self.root.minsize(1200, 700)
        self.root.configure(bg=Theme.BG)

        icon_path = get_icon_path(vip=self.vip_active)
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

        self._fast_scanner = None
        self._fast_scanner_pid = None

        self.setup_styles()
        self.setup_ui()
        self.refresh_processes()

        if len(sys.argv) > 1 and sys.argv[1].endswith('.ht'):
            self.load_ht_file(sys.argv[1])

    # ==================== STYLES ====================
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Dark.TFrame', background=Theme.BG)
        style.configure('Panel.TFrame', background=Theme.BG_PANEL)
        style.configure('Card.TFrame', background=Theme.BG_CARD)

        style.configure('Dark.TLabel', background=Theme.BG, foreground=Theme.TEXT,
                        font=Theme.FONT_UI)
        style.configure('Panel.TLabel', background=Theme.BG_PANEL, foreground=Theme.TEXT,
                        font=Theme.FONT_UI)
        style.configure('Dim.TLabel', background=Theme.BG, foreground=Theme.TEXT_DIM,
                        font=Theme.FONT_UI)
        style.configure('Header.TLabel', background=Theme.BG, foreground=Theme.TITLE,
                        font=Theme.FONT_TITLE)
        style.configure('Sub.TLabel', background=Theme.BG, foreground=Theme.TEXT_DIM,
                        font=Theme.FONT_SUB)
        style.configure('Accent.TLabel', background=Theme.BG, foreground=Theme.ACCENT,
                        font=Theme.FONT_UI_B)
        style.configure('Section.TLabel', background=Theme.BG_CARD,
                        foreground=Theme.TEXT, font=Theme.FONT_UI_B)

        style.configure('Dark.TButton', background=Theme.BG_INPUT, foreground=Theme.TEXT,
                        font=Theme.FONT_UI, borderwidth=0, padding=(12, 7))
        style.map('Dark.TButton',
                  background=[('active', Theme.BG_HOVER), ('pressed', Theme.ACCENT_DIM)],
                  foreground=[('pressed', Theme.TITLE)])

        style.configure('Accent.TButton', background=Theme.ACCENT, foreground=Theme.TITLE,
                        font=Theme.FONT_UI_B, borderwidth=0, padding=(12, 7))
        style.map('Accent.TButton',
                  background=[('active', '#4a8dd9'), ('pressed', Theme.ACCENT_DIM)])

        style.configure('Success.TButton', background=Theme.SUCCESS, foreground=Theme.BG,
                        font=Theme.FONT_UI_B, borderwidth=0, padding=(12, 7))
        style.map('Success.TButton', background=[('active', '#4cc95f')])

        style.configure('Danger.TButton', background=Theme.ERROR, foreground=Theme.TITLE,
                        font=Theme.FONT_UI_B, borderwidth=0, padding=(12, 7))
        style.map('Danger.TButton', background=[('active', '#ff6a62')])

        style.configure('Gold.TButton', background=Theme.GOLD, foreground='#1a1710',
                        font=Theme.FONT_UI_B, borderwidth=0, padding=(12, 7))
        style.map('Gold.TButton', background=[('active', '#f5d76e')])

        style.configure('Nav.TButton', background=Theme.BG_PANEL,
                        foreground=Theme.TEXT_DIM, font=Theme.FONT_MONO_S,
                        borderwidth=0, padding=(10, 5))
        style.map('Nav.TButton',
                  background=[('active', Theme.BG_HOVER)],
                  foreground=[('active', Theme.ACCENT)])

        style.configure('Dark.TNotebook', background=Theme.BG, borderwidth=0,
                        tabmargins=[0, 0, 0, 0])
        style.configure('Dark.TNotebook.Tab', background=Theme.BG_PANEL,
                        foreground=Theme.TEXT_DIM, font=Theme.FONT_UI,
                        padding=(20, 10), borderwidth=0)
        style.map('Dark.TNotebook.Tab',
                  background=[('selected', Theme.BG), ('active', Theme.BG_HOVER)],
                  foreground=[('selected', Theme.ACCENT), ('active', Theme.TEXT)])

        style.configure('Dark.TRadiobutton', background=Theme.BG,
                        foreground=Theme.TEXT, font=Theme.FONT_UI)
        style.map('Dark.TRadiobutton',
                  background=[('active', Theme.BG)],
                  foreground=[('active', Theme.ACCENT)])

        style.configure('Dark.TCheckbutton', background=Theme.BG,
                        foreground=Theme.TEXT, font=Theme.FONT_UI)
        style.map('Dark.TCheckbutton',
                  background=[('active', Theme.BG)],
                  foreground=[('active', Theme.ACCENT)])

        style.configure('Dark.TEntry', fieldbackground=Theme.BG_INPUT,
                        foreground=Theme.TEXT, borderwidth=0,
                        insertcolor=Theme.TEXT)
        style.configure('Dark.TCombobox', fieldbackground=Theme.BG_INPUT,
                        background=Theme.BG_INPUT, foreground=Theme.TEXT,
                        arrowcolor=Theme.TEXT, borderwidth=0)

        style.configure('Dark.Vertical.TScrollbar',
                        background=Theme.BG_PANEL, troughcolor=Theme.BG,
                        borderwidth=0, arrowcolor=Theme.TEXT_DIM)
        style.map('Dark.Vertical.TScrollbar',
                  background=[('active', Theme.BG_HOVER)])

        style.configure('Scan.Horizontal.TProgressbar',
                        background=Theme.ACCENT, troughcolor=Theme.BG_INPUT,
                        borderwidth=0, lightcolor=Theme.ACCENT, darkcolor=Theme.ACCENT)

    # ==================== UI SETUP ====================
    def setup_ui(self):
        topbar = tk.Frame(self.root, bg=Theme.BG_PANEL, height=60)
        topbar.pack(fill=tk.X)
        topbar.pack_propagate(False)

        logo_frame = tk.Frame(topbar, bg=Theme.BG_PANEL)
        logo_frame.pack(side=tk.LEFT, padx=(20, 0), pady=10)

        self.logo_path = get_icon_path(vip=self.vip_active)
        self.logo_image = None
        if self.logo_path:
            try:
                from PIL import Image, ImageTk
                img = Image.open(self.logo_path)
                img = img.resize((32, 32), Image.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(img)
                tk.Label(logo_frame, image=self.logo_image, bg=Theme.BG_PANEL).pack(side=tk.LEFT)
            except Exception:
                tk.Label(logo_frame, text="H", bg=Theme.BG_PANEL, fg=Theme.ACCENT,
                         font=('Segoe UI', 22, 'bold')).pack(side=tk.LEFT)
        else:
            tk.Label(logo_frame, text="H", bg=Theme.BG_PANEL, fg=Theme.ACCENT,
                     font=('Segoe UI', 22, 'bold')).pack(side=tk.LEFT)

        tk.Label(logo_frame, text="HookEngine", bg=Theme.BG_PANEL, fg=Theme.TITLE,
                 font=('Segoe UI', 16, 'bold')).pack(side=tk.LEFT, padx=(8, 6))
        tk.Label(logo_frame, text="v3.1", bg=Theme.BG_PANEL, fg=Theme.ACCENT,
                 font=('Segoe UI', 10)).pack(side=tk.LEFT)

        if FAST_SCANNER_AVAILABLE:
            fast_badge = tk.Frame(logo_frame, bg=Theme.CYAN)
            fast_badge.pack(side=tk.LEFT, padx=(8, 0))
            tk.Label(fast_badge, text="FAST", bg=Theme.CYAN, fg='#0f1115',
                     font=('Segoe UI', 9, 'bold')).pack(padx=6, pady=2)

        if self.vip_active:
            vip_frame = tk.Frame(logo_frame, bg=Theme.GOLD)
            vip_frame.pack(side=tk.LEFT, padx=(10, 0))
            tk.Label(vip_frame, text="VIP", bg=Theme.GOLD, fg='#1a1710',
                     font=('Segoe UI', 9, 'bold')).pack(padx=8, pady=2)

        status_frame = tk.Frame(topbar, bg=Theme.BG_PANEL)
        status_frame.pack(side=tk.RIGHT, padx=20, pady=10)

        self.status_dot = tk.Label(status_frame, text="o", bg=Theme.BG_PANEL,
                                    fg=Theme.TEXT_MUTE, font=('Segoe UI', 14))
        self.status_dot.pack(side=tk.LEFT)

        self.status_text = tk.Label(status_frame, text="Ready",
                                     bg=Theme.BG_PANEL, fg=Theme.TEXT_DIM,
                                     font=Theme.FONT_UI)
        self.status_text.pack(side=tk.LEFT, padx=(6, 20))

        if self.vip_active:
            self.vip_status = tk.Label(status_frame, text="* VIP Active",
                                        bg=Theme.BG_PANEL, fg=Theme.GOLD,
                                        font=Theme.FONT_UI_B)
        else:
            self.vip_status = tk.Label(status_frame, text="o Free",
                                        bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTE,
                                        font=Theme.FONT_UI)
        self.vip_status.pack(side=tk.LEFT, padx=(0, 20))

        admin_text = "Administrator" if _is_admin() else "Restricted"
        admin_color = Theme.SUCCESS if _is_admin() else Theme.ERROR
        tk.Label(status_frame, text=admin_text, bg=Theme.BG_PANEL,
                 fg=admin_color, font=Theme.FONT_SUB).pack(side=tk.LEFT)

        # ANA LAYOUT
        main = tk.Frame(self.root, bg=Theme.BG)
        main.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(main, bg=Theme.BG_PANEL, width=320)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        proc_header = tk.Frame(left, bg=Theme.BG_PANEL)
        proc_header.pack(fill=tk.X, padx=16, pady=(18, 8))

        tk.Label(proc_header, text="RUNNING PROCESSES", bg=Theme.BG_PANEL,
                 fg=Theme.TITLE, font=Theme.FONT_UI_B).pack(side=tk.LEFT)

        self.process_count_label = tk.Label(proc_header, text="0",
                                              bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTE,
                                              font=Theme.FONT_SUB)
        self.process_count_label.pack(side=tk.RIGHT)

        search_frame = tk.Frame(left, bg=Theme.BG_INPUT,
                                 highlightthickness=1, highlightbackground=Theme.BORDER)
        search_frame.pack(fill=tk.X, padx=16, pady=(0, 10))

        tk.Label(search_frame, text="?", bg=Theme.BG_INPUT, fg=Theme.TEXT_DIM,
                 font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(8, 0))

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                 bg=Theme.BG_INPUT, fg=Theme.TEXT,
                                 insertbackground=Theme.TEXT, borderwidth=0,
                                 font=Theme.FONT_UI)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=6)
        search_entry.bind('<KeyRelease>', self.filter_processes)

        list_container = tk.Frame(left, bg=Theme.BG_PANEL)
        list_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))

        self.process_listbox = tk.Listbox(
            list_container, bg=Theme.BG, fg=Theme.TEXT,
            selectbackground=Theme.ACCENT_DIM, selectforeground=Theme.TITLE,
            font=Theme.FONT_MONO_S, borderwidth=0, highlightthickness=0,
            activestyle='none'
        )
        self.process_listbox.pack(fill=tk.BOTH, expand=True)
        self.process_listbox.bind('<Double-Button-1>', lambda e: self.select_process())

        proc_btns = tk.Frame(left, bg=Theme.BG_PANEL)
        proc_btns.pack(fill=tk.X, padx=16, pady=(0, 10))

        self._make_modern_button(proc_btns, "REFRESH", self.refresh_processes,
                                  icon='R').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self._make_modern_button(proc_btns, "SELECT", self.select_process,
                                  icon='OK', color=Theme.SUCCESS).pack(side=tk.LEFT, fill=tk.X,
                                                                       expand=True, padx=(3, 0))

        dll_header = tk.Frame(left, bg=Theme.BG_PANEL)
        dll_header.pack(fill=tk.X, padx=16, pady=(10, 6))

        tk.Label(dll_header, text="TARGET DLL", bg=Theme.BG_PANEL,
                 fg=Theme.TITLE, font=Theme.FONT_UI_B).pack(side=tk.LEFT)

        dll_input_frame = tk.Frame(left, bg=Theme.BG_INPUT,
                                     highlightthickness=1, highlightbackground=Theme.BORDER)
        dll_input_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        self.dll_search_var = tk.StringVar()
        dll_entry = tk.Entry(dll_input_frame, textvariable=self.dll_search_var,
                              bg=Theme.BG_INPUT, fg=Theme.TEXT,
                              insertbackground=Theme.TEXT, borderwidth=0,
                              font=Theme.FONT_MONO_S)
        dll_entry.pack(fill=tk.X, padx=8, pady=6)

        self._make_modern_button(left, "SCAN BY DLL", self.set_target_dll,
                                  icon='S', color=Theme.PURPLE).pack(fill=tk.X, padx=16, pady=(0, 6))
        self._make_modern_button(left, "SAVE HT", self.save_ht_file,
                                  icon='W', color=Theme.WARNING).pack(fill=tk.X, padx=16, pady=(0, 16))

        right = tk.Frame(main, bg=Theme.BG)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        info_bar = tk.Frame(right, bg=Theme.BG_PANEL, height=44)
        info_bar.pack(fill=tk.X)
        info_bar.pack_propagate(False)

        self.target_info = tk.Label(info_bar,
                                     text="  No target selected",
                                     bg=Theme.BG_PANEL, fg=Theme.TEXT_DIM,
                                     font=Theme.FONT_UI)
        self.target_info.pack(side=tk.LEFT, padx=16)

        self.notebook = ttk.Notebook(right, style='Dark.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.hook_tab = tk.Frame(self.notebook, bg=Theme.BG)
        self.notebook.add(self.hook_tab, text='  HOOK ANALYSIS  ')
        self.setup_hook_tab()

        self.memory_tab = tk.Frame(self.notebook, bg=Theme.BG)
        self.notebook.add(self.memory_tab, text='  MEMORY  ')
        self.setup_memory_tab()

        if HTTableV3 is not None:
            self.ht_tab_frame = tk.Frame(self.notebook, bg=Theme.BG)
            self.notebook.add(self.ht_tab_frame, text='  HT TABLE  ')
            try:
                self.ht_tab = HTTableV3(self.ht_tab_frame, self)
            except Exception as e:
                print(f"[!] HTTableV3 init error: {e}")

        if WhoWritesTab is not None:
            self.ww_tab_frame = tk.Frame(self.notebook, bg=Theme.BG)
            self.notebook.add(self.ww_tab_frame, text='  WHO WRITES  ')
            try:
                self.ww_tab = WhoWritesTab(self.ww_tab_frame, self)
            except Exception as e:
                print(f"[!] WhoWritesTab init error: {e}")

        self.report_tab = tk.Frame(self.notebook, bg=Theme.BG)
        self.notebook.add(self.report_tab, text='  REPORT  ')
        self.setup_report_tab()

        self.settings_tab = tk.Frame(self.notebook, bg=Theme.BG)
        self.notebook.add(self.settings_tab, text='  SETTINGS  ')
        self.setup_settings_tab()

    def _make_modern_button(self, parent, text, command, icon='', color=None):
        btn_color = color or Theme.ACCENT
        frame = tk.Frame(parent, bg=Theme.BG_CARD, cursor='hand2',
                         highlightthickness=1, highlightbackground=Theme.BORDER)

        inner = tk.Frame(frame, bg=Theme.BG_CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        if icon:
            icon_lbl = tk.Label(inner, text=icon, bg=Theme.BG_CARD,
                                 fg=btn_color, font=('Segoe UI', 9, 'bold'))
            icon_lbl.pack(side=tk.LEFT, padx=(0, 6))
        else:
            icon_lbl = None

        text_lbl = tk.Label(inner, text=text, bg=Theme.BG_CARD,
                             fg=Theme.TEXT, font=Theme.FONT_UI)
        text_lbl.pack(side=tk.LEFT)

        def on_enter(e):
            for w in [frame, inner, text_lbl]:
                w.configure(bg=Theme.BG_HOVER)
            if icon_lbl:
                icon_lbl.configure(bg=Theme.BG_HOVER)

        def on_leave(e):
            for w in [frame, inner, text_lbl]:
                w.configure(bg=Theme.BG_CARD)
            if icon_lbl:
                icon_lbl.configure(bg=Theme.BG_CARD)

        def on_click(e):
            if command:
                command()

        widgets = [frame, inner, text_lbl]
        if icon_lbl:
            widgets.append(icon_lbl)
        for w in widgets:
            w.bind('<Enter>', on_enter)
            w.bind('<Leave>', on_leave)
            w.bind('<Button-1>', on_click)

        return frame

    # ==================== HOOK TAB ====================
    def setup_hook_tab(self):
        nav_container = tk.Frame(self.hook_tab, bg=Theme.BG_CARD,
                                  highlightthickness=1, highlightbackground=Theme.BORDER)
        nav_container.pack(fill=tk.X, padx=12, pady=(12, 8))

        nav_inner = tk.Frame(nav_container, bg=Theme.BG_CARD)
        nav_inner.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(nav_inner, text="NAV", bg=Theme.BG_CARD, fg=Theme.WARNING,
                 font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))

        nav_items = [("IAT", self.goto_iat), ("EAT", self.goto_eat),
                     ("JMP", self.goto_jmp), ("CALL", self.goto_call),
                     ("VTABLE", self.goto_vtable), ("DETOUR", self.goto_detour),
                     ("SYSCALL", self.goto_syscall), ("ANTI-DBG", self.goto_antidebug),
                     ("PUSH RET", self.goto_pushret), ("HOTPATCH", self.goto_hotpatch),
                     ("INT3", self.goto_int3)]

        for text, cmd in nav_items:
            ttk.Button(nav_inner, text=text, command=cmd,
                       style='Nav.TButton').pack(side=tk.LEFT, padx=2)

        ctrl = tk.Frame(self.hook_tab, bg=Theme.BG)
        ctrl.pack(fill=tk.X, padx=12, pady=(0, 8))

        tk.Label(ctrl, text="Chars:", bg=Theme.BG, fg=Theme.TEXT_DIM,
                 font=Theme.FONT_UI).pack(side=tk.LEFT, padx=(0, 6))

        self.copy_chars_var = tk.StringVar(value="1000")
        chars_entry = tk.Entry(ctrl, textvariable=self.copy_chars_var, width=8,
                                bg=Theme.BG_INPUT, fg=Theme.TEXT,
                                insertbackground=Theme.TEXT, borderwidth=0,
                                font=Theme.FONT_MONO_S,
                                highlightthickness=1, highlightbackground=Theme.BORDER)
        chars_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=4)

        self._make_modern_button(ctrl, "COPY", self.copy_hook_results,
                                  icon='C', color=Theme.CYAN).pack(side=tk.LEFT)

        output_frame = tk.Frame(self.hook_tab, bg=Theme.BG_CARD,
                                 highlightthickness=1, highlightbackground=Theme.BORDER)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        self.hook_output = scrolledtext.ScrolledText(
            output_frame, bg=Theme.BG, fg=Theme.TEXT,
            font=Theme.FONT_MONO, borderwidth=0, insertbackground=Theme.TEXT,
            selectbackground=Theme.ACCENT_DIM, selectforeground=Theme.TITLE,
            padx=10, pady=10, wrap=tk.WORD
        )
        self.hook_output.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        scan_frame = tk.Frame(self.hook_tab, bg=Theme.BG)
        scan_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        self._make_modern_button(scan_frame, "QUICK SCAN", self.start_quick_scan,
                                  icon='Q', color=Theme.WARNING).pack(side=tk.LEFT, padx=(0, 6))
        self._make_modern_button(scan_frame, "FULL HOOK", self.start_full_hook,
                                  icon='F', color=Theme.ACCENT).pack(side=tk.LEFT, padx=(0, 6))
        self._make_modern_button(scan_frame, "IMPORTANT", self.start_important_hook,
                                  icon='!', color=Theme.GOLD).pack(side=tk.LEFT, padx=(0, 6))
        self._make_modern_button(scan_frame, "FILTERED", self.start_filtered_hook,
                                  icon='#', color=Theme.PURPLE).pack(side=tk.LEFT, padx=(0, 6))
        self._make_modern_button(scan_frame, "CLEAR", self.clear_hook_output,
                                  icon='X', color=Theme.ERROR).pack(side=tk.LEFT)

    # ==================== MEMORY TAB ====================
    def setup_memory_tab(self):
        top = tk.Frame(self.memory_tab, bg=Theme.BG_CARD,
                       highlightthickness=1, highlightbackground=Theme.BORDER)
        top.pack(fill=tk.X, padx=12, pady=(12, 8))

        top_inner = tk.Frame(top, bg=Theme.BG_CARD)
        top_inner.pack(fill=tk.X, padx=14, pady=12)

        tk.Label(top_inner, text="Type:", bg=Theme.BG_CARD, fg=Theme.TEXT,
                 font=Theme.FONT_UI).pack(side=tk.LEFT, padx=(0, 6))

        self.scan_type_var = tk.StringVar(value="INT")
        type_combo = ttk.Combobox(
            top_inner, textvariable=self.scan_type_var,
            values=["INT", "INT64", "WORD", "BYTE", "FLOAT", "DOUBLE",
                    "STRING", "UTF16", "AOB", "POINTER"],
            width=10, style='Dark.TCombobox'
        )
        type_combo.pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(top_inner, text="Value:", bg=Theme.BG_CARD, fg=Theme.TEXT,
                 font=Theme.FONT_UI).pack(side=tk.LEFT, padx=(0, 6))

        self.scan_value_entry = tk.Entry(top_inner, width=25,
                                          bg=Theme.BG_INPUT, fg=Theme.TEXT,
                                          insertbackground=Theme.TEXT, borderwidth=0,
                                          font=Theme.FONT_MONO,
                                          highlightthickness=1, highlightbackground=Theme.BORDER)
        self.scan_value_entry.pack(side=tk.LEFT, padx=(0, 16), ipady=5)
        self.scan_value_entry.bind('<Return>', lambda e: self.scan_values())

        self.use_fast_scan_var = tk.BooleanVar(value=FAST_SCANNER_AVAILABLE)
        fast_chk = tk.Checkbutton(
            top_inner, text="FAST",
            variable=self.use_fast_scan_var,
            bg=Theme.BG_CARD, fg=Theme.CYAN,
            activebackground=Theme.BG_CARD,
            selectcolor=Theme.BG_INPUT,
            font=Theme.FONT_UI_B,
            disabledforeground=Theme.TEXT_MUTE
        )
        fast_chk.pack(side=tk.LEFT, padx=(0, 16))
        if not FAST_SCANNER_AVAILABLE:
            fast_chk.configure(state=tk.DISABLED)

        ttk.Button(top_inner, text="SCAN", command=self.scan_values,
                   style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(top_inner, text="ALL VALUES", command=self.list_all_values,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(top_inner, text="POINTER SCAN", command=self.scan_pointer,
                   style='Dark.TButton').pack(side=tk.LEFT)

        self.scan_progress = ttk.Progressbar(
            self.memory_tab, mode='determinate',
            style='Scan.Horizontal.TProgressbar'
        )
        self.scan_progress.pack(fill=tk.X, padx=12, pady=(0, 8))
        self.scan_progress.pack_forget()

        filter_bar = tk.Frame(self.memory_tab, bg=Theme.BG)
        filter_bar.pack(fill=tk.X, padx=12, pady=(0, 8))

        for text, cmd, icon in [("INCREASED", self.scan_increased, '^'),
                                 ("DECREASED", self.scan_decreased, 'v'),
                                 ("UNCHANGED", self.scan_unchanged, '='),
                                 ("CHANGED", self.scan_changed, '!')]:
            self._make_modern_button(filter_bar, text, cmd, icon=icon,
                                      color=Theme.PURPLE).pack(side=tk.LEFT, padx=(0, 6))

        list_frame = tk.Frame(self.memory_tab, bg=Theme.BG_CARD,
                              highlightthickness=1, highlightbackground=Theme.BORDER)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        self.memory_listbox = tk.Listbox(
            list_frame, bg=Theme.BG, fg=Theme.TEXT,
            font=Theme.FONT_MONO, selectbackground=Theme.ACCENT_DIM,
            selectforeground=Theme.TITLE, selectmode=tk.EXTENDED,
            borderwidth=0, highlightthickness=0, activestyle='none'
        )
        self.memory_listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.memory_listbox.bind('<Control-c>', self.copy_selected_memory)
        self.memory_listbox.bind('<Control-C>', self.copy_selected_memory)
        self.memory_listbox.bind('<Control-a>',
                                  lambda e: self.memory_listbox.select_set(0, tk.END))

        bottom = tk.Frame(self.memory_tab, bg=Theme.BG)
        bottom.pack(fill=tk.X, padx=12, pady=(0, 12))

        tk.Label(bottom, text="New:", bg=Theme.BG, fg=Theme.TEXT,
                 font=Theme.FONT_UI).pack(side=tk.LEFT, padx=(0, 6))

        self.new_value_entry = tk.Entry(bottom, width=18,
                                         bg=Theme.BG_INPUT, fg=Theme.TEXT,
                                         insertbackground=Theme.TEXT, borderwidth=0,
                                         font=Theme.FONT_MONO,
                                         highlightthickness=1, highlightbackground=Theme.BORDER)
        self.new_value_entry.pack(side=tk.LEFT, padx=(0, 12), ipady=5)

        self._make_modern_button(bottom, "APPLY", self.apply_memory_change,
                                  icon='OK', color=Theme.SUCCESS).pack(side=tk.LEFT, padx=(0, 6))
        self._make_modern_button(bottom, "APPLY ALL", self.apply_to_visible,
                                  icon='AA', color=Theme.SUCCESS).pack(side=tk.LEFT, padx=(0, 6))
        self._make_modern_button(bottom, "COPY", self.copy_all_memory,
                                  icon='C', color=Theme.CYAN).pack(side=tk.LEFT, padx=(0, 6))
        self._make_modern_button(bottom, "FREEZE", self.freeze_selected,
                                  icon='F', color=Theme.ACCENT).pack(side=tk.LEFT, padx=(0, 6))
        self._make_modern_button(bottom, "UNFREEZE", self.stop_freeze,
                                  icon='U', color=Theme.WARNING).pack(side=tk.LEFT)

    # ==================== REPORT TAB ====================
    def setup_report_tab(self):
        output_frame = tk.Frame(self.report_tab, bg=Theme.BG_CARD,
                                 highlightthickness=1, highlightbackground=Theme.BORDER)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 8))

        self.report_output = scrolledtext.ScrolledText(
            output_frame, bg=Theme.BG, fg=Theme.TEXT,
            font=Theme.FONT_MONO, borderwidth=0, insertbackground=Theme.TEXT,
            selectbackground=Theme.ACCENT_DIM, selectforeground=Theme.TITLE,
            padx=10, pady=10
        )
        self.report_output.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        btn_frame = tk.Frame(self.report_tab, bg=Theme.BG)
        btn_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        self._make_modern_button(btn_frame, "GENERATE", self.generate_report,
                                  icon='G', color=Theme.ACCENT).pack(side=tk.LEFT, padx=(0, 6))
        self._make_modern_button(btn_frame, "SAVE", self.save_report,
                                  icon='S', color=Theme.SUCCESS).pack(side=tk.LEFT)

    # ==================== SETTINGS TAB ====================
    def setup_settings_tab(self):
        container = tk.Frame(self.settings_tab, bg=Theme.BG)
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)

        vip_card = tk.Frame(container, bg=Theme.BG_CARD,
                            highlightthickness=1,
                            highlightbackground=Theme.GOLD if self.vip_active else Theme.BORDER)
        vip_card.pack(fill=tk.X, pady=(0, 16))

        vip_header = tk.Frame(vip_card, bg=Theme.BG_CARD)
        vip_header.pack(fill=tk.X, padx=14, pady=(12, 6))

        tk.Label(vip_header, text="*" if self.vip_active else "o",
                 bg=Theme.BG_CARD, fg=Theme.GOLD,
                 font=('Segoe UI', 14, 'bold')).pack(side=tk.LEFT)
        tk.Label(vip_header, text="VIP Membership", bg=Theme.BG_CARD,
                 fg=Theme.TITLE, font=Theme.FONT_UI_B).pack(side=tk.LEFT, padx=(8, 0))

        if self.vip_active:
            status_lbl = tk.Label(vip_header, text="ACTIVE",
                                   bg=Theme.GOLD, fg='#1a1710',
                                   font=('Segoe UI', 9, 'bold'))
        else:
            status_lbl = tk.Label(vip_header, text="INACTIVE",
                                   bg=Theme.BG_INPUT, fg=Theme.TEXT_MUTE,
                                   font=('Segoe UI', 9, 'bold'))
        status_lbl.pack(side=tk.RIGHT, padx=4, ipadx=8, ipady=2)

        vip_body = tk.Frame(vip_card, bg=Theme.BG_CARD)
        vip_body.pack(fill=tk.X, padx=14, pady=(6, 14))

        if self.vip_active:
            info = get_vip_info() or {}
            hwid = info.get('hwid', 'unknown')
            tk.Label(vip_body, text=f"HWID: {hwid[:16]}...",
                     bg=Theme.BG_CARD, fg=Theme.TEXT_DIM,
                     font=Theme.FONT_MONO_S).pack(anchor=tk.W, pady=(0, 4))
            tk.Label(vip_body, text="All VIP features unlocked",
                     bg=Theme.BG_CARD, fg=Theme.GOLD,
                     font=Theme.FONT_UI).pack(anchor=tk.W, pady=(8, 0))
            ttk.Button(vip_body, text="Deactivate (Test)",
                       command=self.deactivate_vip,
                       style='Dark.TButton').pack(anchor=tk.W, pady=(12, 0))
        else:
            tk.Label(vip_body, text="Enter your VIP key to unlock premium features:",
                     bg=Theme.BG_CARD, fg=Theme.TEXT,
                     font=Theme.FONT_UI).pack(anchor=tk.W, pady=(0, 10))

            key_frame = tk.Frame(vip_body, bg=Theme.BG_INPUT,
                                  highlightthickness=1,
                                  highlightbackground=Theme.BORDER)
            key_frame.pack(fill=tk.X, pady=(0, 10))

            self.vip_key_var = tk.StringVar()
            key_entry = tk.Entry(key_frame, textvariable=self.vip_key_var,
                                  bg=Theme.BG_INPUT, fg=Theme.GOLD,
                                  insertbackground=Theme.GOLD, borderwidth=0,
                                  font=Theme.FONT_MONO)
            key_entry.pack(fill=tk.X, padx=10, pady=8)
            key_entry.bind('<Return>', lambda e: self.activate_vip())

            ttk.Button(vip_body, text="ACTIVATE VIP",
                       command=self.activate_vip,
                       style='Gold.TButton').pack(anchor=tk.W)

        lang_card = tk.Frame(container, bg=Theme.BG_CARD,
                             highlightthickness=1, highlightbackground=Theme.BORDER)
        lang_card.pack(fill=tk.X, pady=(0, 16))

        lang_header = tk.Frame(lang_card, bg=Theme.BG_CARD)
        lang_header.pack(fill=tk.X, padx=14, pady=(12, 6))

        tk.Label(lang_header, text="LANG", bg=Theme.BG_CARD, fg=Theme.CYAN,
                 font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        tk.Label(lang_header, text="Language", bg=Theme.BG_CARD,
                 fg=Theme.TITLE, font=Theme.FONT_UI_B).pack(side=tk.LEFT, padx=(8, 0))

        lang_body = tk.Frame(lang_card, bg=Theme.BG_CARD)
        lang_body.pack(fill=tk.X, padx=14, pady=(6, 14))

        self.settings_lang_var = tk.StringVar(value=cur_lang())

        ttk.Radiobutton(lang_body, text="  English",
                        variable=self.settings_lang_var, value='en',
                        style='Dark.TRadiobutton').pack(anchor=tk.W, pady=4)
        ttk.Radiobutton(lang_body, text="  Turkce",
                        variable=self.settings_lang_var, value='tr',
                        style='Dark.TRadiobutton').pack(anchor=tk.W, pady=4)

        ttk.Button(lang_body, text="Save",
                   command=self.save_settings,
                   style='Success.TButton').pack(anchor=tk.W, pady=(12, 0))

        about_card = tk.Frame(container, bg=Theme.BG_CARD,
                               highlightthickness=1, highlightbackground=Theme.BORDER)
        about_card.pack(fill=tk.X)

        about_header = tk.Frame(about_card, bg=Theme.BG_CARD)
        about_header.pack(fill=tk.X, padx=14, pady=(12, 6))

        tk.Label(about_header, text="i", bg=Theme.BG_CARD, fg=Theme.PURPLE,
                 font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT)
        tk.Label(about_header, text="About", bg=Theme.BG_CARD,
                 fg=Theme.TITLE, font=Theme.FONT_UI_B).pack(side=tk.LEFT, padx=(8, 0))

        about_body = tk.Frame(about_card, bg=Theme.BG_CARD)
        about_body.pack(fill=tk.X, padx=14, pady=(6, 14))

        info_text = (
            "HookEngine v3.1\n"
            "Modern game hacking tool\n"
            "Fast multi-threaded scanner\n\n"
            "(c) 2026 Youd"
        )
        tk.Label(about_body, text=info_text, bg=Theme.BG_CARD,
                 fg=Theme.TEXT_DIM, font=Theme.FONT_UI,
                 justify=tk.LEFT).pack(anchor=tk.W)

    def activate_vip(self):
        key = self.vip_key_var.get().strip()
        if not key:
            messagebox.showwarning("VIP", "Please enter a key")
            return
        success, msg = activate_key(key)
        if success:
            messagebox.showinfo("VIP Activated",
                                 f"{msg}\n\nPlease restart HookEngine to apply the VIP theme.")
        else:
            messagebox.showerror("VIP Error", msg)

    def deactivate_vip(self):
        if messagebox.askyesno("Deactivate VIP",
                                "Deactivate VIP? This is for testing only."):
            deactivate_key()
            messagebox.showinfo("VIP", "VIP deactivated. Restart to apply.")

    def save_settings(self):
        new_lang = self.settings_lang_var.get()
        if new_lang == cur_lang():
            return
        save_language(new_lang)
        messagebox.showinfo("Success", "Restart required for changes.")

    # ==================== HT EDITOR ====================
    def open_ht_editor(self):
        if not HTEditor:
            messagebox.showerror("Error", "HT Editor not available")
            return
        if self.ht_tab is None:
            messagebox.showerror("Error", "HT Table not initialized")
            return
        try:
            HTEditor(self.root, self.ht_tab)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ==================== PROCESS MGMT ====================
    def refresh_processes(self):
        try:
            self.process_listbox.delete(0, tk.END)
            procs = self.process_manager.get_all_processes()
            for pid, name in procs:
                self.process_listbox.insert(tk.END, f"  {name}  |  {pid}")
            self.process_count_label.configure(text=str(len(procs)))
        except Exception as e:
            print(f"[refresh_processes error] {e}")

    def filter_processes(self, event=None):
        try:
            search_text = self.search_var.get().lower()
            self.process_listbox.delete(0, tk.END)
            procs = self.process_manager.get_all_processes()
            count = 0
            for pid, name in procs:
                if search_text in name.lower():
                    self.process_listbox.insert(tk.END, f"  {name}  |  {pid}")
                    count += 1
            self.process_count_label.configure(text=str(count))
        except Exception as e:
            print(f"[filter_processes error] {e}")

    def select_process(self):
        self.target_pid = self.get_selected_pid()
        if self.target_pid:
            self._fast_scanner = None
            self._fast_scanner_pid = None

            try:
                info = self.process_manager.get_process_info(self.target_pid)
                if info:
                    self.target_info.configure(
                        text=f"  Target: {info['name']}  |  PID {info['pid']}  |  {info['memory']:.1f} MB",
                        fg=Theme.SUCCESS
                    )
                    self.status_dot.configure(fg=Theme.SUCCESS)
                    self.status_text.configure(text="Attached", fg=Theme.SUCCESS)
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
            messagebox.showwarning("Warning", "Select a process first")
            return None
        try:
            text = self.process_listbox.get(selection[0])
            return int(text.rsplit("|", 1)[1].strip())
        except Exception as e:
            print(f"[get_selected_pid error] {e}")
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

            if HTTableV3Model is None:
                messagebox.showerror("Error", "HT model bulunamadı")
                return

            table = HTTableV3Model()
            table.name = "Quick Save"
            table.author = ""
            table.game = self.target_dll or ""

            if self.ht_tab is not None and getattr(self.ht_tab, 'table', None):
                table = self.ht_tab.table
            else:
                addresses = [
                    self.memory_listbox.get(i)
                    for i in range(self.memory_listbox.size())
                ]
                if addresses:
                    g = table.add_group("Quick Save", "#00aaff")
                    for line in addresses:
                        try:
                            addr_part = line.strip().split("  =  ")[0]
                            e = HTEntry()
                            e.id = f"addr_{addr_part.replace('0x', '').replace(' ', '_')}"
                            e.label = f"Addr {addr_part}"
                            e.read = [addr_part]
                            e.type = "int"
                            e.value = 0
                            e.mode = "action"
                            g.add(e)
                        except Exception:
                            pass

            if not table.save(path):
                messagebox.showerror("Error", f"Save failed: {path}")
                return

            messagebox.showinfo("Success", f"HT saved:\n{path}")
            self.refresh_explorer()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_ht_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.loads(f.read())

            if 'addresses' in data and 'groups' not in data:
                self.memory_listbox.delete(0, tk.END)
                for addr in data['addresses']:
                    self.memory_listbox.insert(tk.END, addr)

            if 'hook_results' in data:
                self.hook_output.insert(tk.END, data['hook_results'])

            if HTTableV3Model is not None and self.ht_tab is not None:
                try:
                    loaded = HTTableV3Model.load(path)
                    if loaded:
                        self.ht_tab.table = loaded
                        self.ht_tab.ht_path = path
                        fname = os.path.basename(path)
                        self.ht_tab.ht_label.config(text=f"HT Table: {fname}")
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
        self.status_text.configure(text="Scanning...", fg=Theme.WARNING)
        self.status_dot.configure(fg=Theme.WARNING)
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
            self.status_text.configure(text="Ready", fg=Theme.SUCCESS)
            self.status_dot.configure(fg=Theme.SUCCESS)

    def clear_hook_output(self):
        self.hook_output.delete(1.0, tk.END)

    # ==================== FAST SCANNER ====================
    def _get_fast_scanner(self):
        if not FAST_SCANNER_AVAILABLE:
            return None
        if (self._fast_scanner is None or
                self._fast_scanner_pid != self.target_pid):
            try:
                self._fast_scanner = FastScanner(self.target_pid)
                self._fast_scanner_pid = self.target_pid
            except Exception as e:
                print(f"[!] FastScanner init error: {e}")
                self._fast_scanner = None
        return self._fast_scanner

    def _show_scan_progress(self, show=True):
        try:
            if show:
                self.scan_progress.pack(fill=tk.X, padx=12, pady=(0, 8),
                                        before=self.memory_listbox.master)
                self.scan_progress['value'] = 0
            else:
                self.scan_progress.pack_forget()
        except Exception:
            pass

    def _on_scan_progress(self, done, total):
        try:
            if total > 0:
                pct = (done / total) * 100
                self.root.after(0, lambda: self.scan_progress.configure(value=pct))
        except Exception:
            pass

    # ==================== MEMORY SCAN ====================
    def scan_values(self):
        if not self.target_pid:
            messagebox.showwarning("Warning", "Select a process first")
            return

        try:
            scan_type = self.scan_type_var.get()
            value_str = self.scan_value_entry.get().strip()
            if not value_str and scan_type != "POINTER":
                messagebox.showwarning("Warning", "Enter a value")
                return
        except Exception:
            return

        if FAST_SCANNER_AVAILABLE and self.use_fast_scan_var.get():
            self._start_fast_scan(scan_type, value_str)
        else:
            self._start_slow_scan(scan_type, value_str)

    def _start_fast_scan(self, scan_type, value_str):
        fs = self._get_fast_scanner()
        if fs is None:
            self._start_slow_scan(scan_type, value_str)
            return

        self._show_scan_progress(True)
        self.status_text.configure(text="Fast scan...", fg=Theme.WARNING)
        self.status_dot.configure(fg=Theme.WARNING)
        self.memory_listbox.delete(0, tk.END)

        def do_scan():
            try:
                t0 = time.time()
                addrs = []

                if scan_type == "INT":
                    addrs = fs.search_int(int(value_str), size=4, signed=True)
                elif scan_type == "INT64":
                    addrs = fs.search_int(int(value_str), size=8, signed=True)
                elif scan_type == "WORD":
                    addrs = fs.search_int(int(value_str), size=2, signed=True)
                elif scan_type == "BYTE":
                    addrs = fs.search_int(int(value_str), size=1, signed=True)
                elif scan_type == "FLOAT":
                    addrs = fs.search_float(float(value_str))
                elif scan_type == "DOUBLE":
                    addrs = fs.search_double(float(value_str))
                elif scan_type == "STRING":
                    addrs = fs.search_string(value_str)
                elif scan_type == "UTF16":
                    addrs = fs.search_utf16(value_str)
                elif scan_type == "AOB":
                    addrs = fs.search_aob(value_str)
                elif scan_type == "POINTER":
                    try:
                        target = int(value_str, 16)
                    except ValueError:
                        self.root.after(0, lambda: messagebox.showerror(
                            "Error", "Pointer icin hex adres gerek (0x...)"))
                        return
                    addrs = fs.search_bytes(target.to_bytes(8, 'little'))

                elapsed = time.time() - t0

                results = []
                limit = min(len(addrs), 5000)
                for i, a in enumerate(addrs[:limit]):
                    v = fs.read_value(a, scan_type.lower() if scan_type != "AOB" else 'byte')
                    if v is not None:
                        results.append((a, v))
                    if i % 500 == 0:
                        self._on_scan_progress(i, limit)

                self.scan_results = results
                self.filtered_results = results.copy()

                def finish():
                    self._show_scan_progress(False)
                    self.update_memory_listbox()
                    self.status_text.configure(
                        text=f"{len(results)} results in {elapsed:.2f}s",
                        fg=Theme.SUCCESS
                    )
                    self.status_dot.configure(fg=Theme.SUCCESS)

                self.root.after(0, finish)
            except Exception as e:
                err = str(e)
                def err_finish():
                    self._show_scan_progress(False)
                    self.status_text.configure(text="Scan error", fg=Theme.ERROR)
                    messagebox.showerror("Scan Error", err)
                self.root.after(0, err_finish)

        threading.Thread(target=do_scan, daemon=True).start()

    def _start_slow_scan(self, scan_type, value_str):
        try:
            self.value_scanner = UltraValueScanner(self.target_pid)
            self.scan_results = self.value_scanner.scan(scan_type, value_str)
            self.filtered_results = self.scan_results.copy()
            self.update_memory_listbox()
        except Exception as e:
            messagebox.showerror("Scan Error", str(e))

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
            value_str = self.scan_value_entry.get().strip()
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
        for item in self.filtered_results[:5000]:
            try:
                addr, value = item
                self.memory_listbox.insert(tk.END, f"  0x{addr:X}  =  {value}")
            except Exception:
                continue

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
            messagebox.showinfo("Copy", f"{len(lines)} items copied")
        except Exception:
            pass

    def apply_memory_change(self):
        selections = self.memory_listbox.curselection()
        if not selections:
            messagebox.showwarning("Warning", "Select an address first")
            return
        try:
            new_value = self.new_value_entry.get()
            scan_type = self.scan_type_var.get()
            self.memory_engine = MemoryEngine(self.target_pid)
            self.memory_engine.open()
            success = 0
            for idx in selections:
                try:
                    addr = int(self.memory_listbox.get(idx).split("  =  ")[0].strip(), 16)
                    if self._write_by_type(addr, new_value, scan_type):
                        success += 1
                except Exception:
                    pass
            self.memory_engine.close()
            messagebox.showinfo("Success", f"{success} addresses written")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _write_by_type(self, addr, value_str, scan_type):
        try:
            if scan_type == "INT":
                v = int(value_str)
                if not (-2**31 <= v < 2**31):
                    return False
                return self.memory_engine.write_int(addr, v)
            elif scan_type == "INT64":
                v = int(value_str)
                if not (-2**63 <= v < 2**63):
                    return False
                return self.memory_engine.write_int64(addr, v)
            elif scan_type == "WORD":
                v = int(value_str, 0)
                if not (0 <= v <= 0xFFFF):
                    return False
                return self.memory_engine.write_bytes(addr, v.to_bytes(2, 'little'))
            elif scan_type == "BYTE":
                v = int(value_str, 0)
                if not (0 <= v <= 0xFF):
                    return False
                return self.memory_engine.write_byte(addr, v)
            elif scan_type == "FLOAT":
                return self.memory_engine.write_float(addr, float(value_str))
            elif scan_type == "DOUBLE":
                return self.memory_engine.write_double(addr, float(value_str))
            elif scan_type == "STRING":
                return self.memory_engine.write_string(addr, value_str)
        except Exception:
            pass
        return False

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
                    addr = int(self.memory_listbox.get(i).split("  =  ")[0].strip(), 16)
                    if self._write_by_type(addr, new_value, scan_type):
                        success += 1
                except Exception:
                    pass
            self.memory_engine.close()
            messagebox.showinfo("Success", f"{success}/{total} written")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ==================== FREEZE ====================
    def freeze_selected(self):
        selections = self.memory_listbox.curselection()
        if not selections:
            messagebox.showwarning("Warning", "Select an address first")
            return

        self.frozen_addresses = []
        for idx in selections:
            try:
                text = self.memory_listbox.get(idx)
                addr = int(text.split("  =  ")[0].strip(), 16)
                val_str = text.split("  =  ")[1].strip()
                try:
                    value = int(val_str)
                except ValueError:
                    value = float(val_str)
                self.frozen_addresses.append((addr, value))
            except Exception:
                pass

        if not self.frozen_addresses:
            return

        self.is_freezing = True
        threading.Thread(target=self._freeze_loop, daemon=True).start()
        messagebox.showinfo("Freeze", f"{len(self.frozen_addresses)} addresses frozen")

    def _freeze_loop(self):
        engine = MemoryEngine(self.target_pid)
        engine.open()
        scan_type = self.scan_type_var.get()
        while self.is_freezing and self.frozen_addresses:
            for addr, value in self.frozen_addresses:
                try:
                    if scan_type == "FLOAT":
                        engine.write_float(addr, float(value))
                    elif scan_type == "DOUBLE":
                        engine.write_double(addr, float(value))
                    else:
                        engine.write_int(addr, int(value))
                except Exception:
                    pass
            time.sleep(0.05)
        engine.close()

    def stop_freeze(self):
        self.is_freezing = False
        self.frozen_addresses = []
        messagebox.showinfo("Unfreeze", "Freeze stopped")

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