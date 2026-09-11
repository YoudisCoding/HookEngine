#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine Installer v2.0
"""

import os
import sys
import time
import shutil
import winreg
import ctypes
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# ==================== APP INFO ====================
APP_NAME = "HookEngine"
APP_VERSION = "3.0.0"
INSTALL_DIR = os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\'), "HookEngine")
EXE_NAME = "HookEngine.exe"
ICON_NAME = "YoudHook.ico"

# ==================== LANGUAGE STRINGS ====================
STRINGS = {
    'tr': {
        'window_title':     "HookEngine — Kurulum",
        'lang_prompt':      "Lütfen kurulum dilini seçin:",
        'continue':         "Devam Et",
        'cancel':           "İptal",
        'install_title':    "Kurulum",
        'installing':       "Kurulum başlıyor...",
        'step_1':           "[1/9] Kurulum klasörü oluşturuluyor...",
        'step_2':           "[2/9] EXE dosyası kopyalanıyor...",
        'step_3':           "[3/9] İkon kopyalanıyor...",
        'step_4':           "[4/9] Klasör gizleniyor...",
        'step_5':           "[5/9] Masaüstü kısayolu...",
        'step_6':           "[6/9] Başlat menüsü...",
        'step_7':           "[7/9] Registry kayıtları...",
        'step_8':           "[8/9] .ht dosya ilişkilendirmesi...",
        'step_9':           "[9/9] Explorer yenileniyor...",
        'done':             "KURULUM TAMAMLANDI!",
        'done_path':        "Kurulum yeri:",
        'done_desktop':     "Masaüstü kısayolu:",
        'done_lang':        "Dil tercihi:",
        'error_exe':        "[HATA] EXE bulunamadı!",
        'error_exe_fix':    "ÇÖZÜM: HookEngine.exe dosyasını installer'ın yanına koyun.",
        'warn_icon':        "[UYARI] İkon bulunamadı",
        'warn_shortcut':    "[UYARI] Kısayol oluşturulamadı",
        'warn_registry':    "[HATA] Registry:",
        'copy_ok':          "→ Kopyalandı:",
        'hidden_ok':        "→ Gizlendi",
        'shortcut_ok':      "→ Oluşturuldu:",
        'registry_ok':      "→ Tamamlandı",
        'explorer_ok':      "→ Tamamlandı",
        'close':            "Kapat",
        'uninstalling':     "Kaldırılıyor...",
        'uninstall_done':   "Kaldırma tamamlandı!",
        'uninstall_title':  "Kaldırma",
        'ask_uninstall':    "HookEngine kaldırılsın mı?",
        'already_title':    "Zaten Kurulu",
        'already_msg':      "HookEngine bu sistemde zaten kurulu.\n\nNe yapmak istersiniz?",
        'repair':           "Onar",
        'uninstall':        "Kaldır",
    },
    'en': {
        'window_title':     "HookEngine — Installer",
        'lang_prompt':      "Please select installation language:",
        'continue':         "Continue",
        'cancel':           "Cancel",
        'install_title':    "Installation",
        'installing':       "Installation starting...",
        'step_1':           "[1/9] Creating install directory...",
        'step_2':           "[2/9] Copying EXE file...",
        'step_3':           "[3/9] Copying icon...",
        'step_4':           "[4/9] Hiding folder...",
        'step_5':           "[5/9] Desktop shortcut...",
        'step_6':           "[6/9] Start menu...",
        'step_7':           "[7/9] Registry entries...",
        'step_8':           "[8/9] .ht file association...",
        'step_9':           "[9/9] Refreshing explorer...",
        'done':             "INSTALLATION COMPLETE!",
        'done_path':        "Install location:",
        'done_desktop':     "Desktop shortcut:",
        'done_lang':        "Language preference:",
        'error_exe':        "[ERROR] EXE not found!",
        'error_exe_fix':    "FIX: Place HookEngine.exe next to installer.",
        'warn_icon':        "[WARNING] Icon not found",
        'warn_shortcut':    "[WARNING] Could not create shortcut",
        'warn_registry':    "[ERROR] Registry:",
        'copy_ok':          "→ Copied:",
        'hidden_ok':        "→ Hidden",
        'shortcut_ok':      "→ Created:",
        'registry_ok':      "→ Done",
        'explorer_ok':      "→ Done",
        'close':            "Close",
        'uninstalling':     "Uninstalling...",
        'uninstall_done':   "Uninstall complete!",
        'uninstall_title':  "Uninstall",
        'ask_uninstall':    "Uninstall HookEngine?",
        'already_title':    "Already Installed",
        'already_msg':      "HookEngine is already installed.\n\nWhat would you like to do?",
        'repair':           "Repair",
        'uninstall':        "Uninstall",
    }
}


def get_string(lang, key):
    return STRINGS.get(lang, STRINGS['en']).get(key, STRINGS['en'].get(key, key))


# ==================== HELPERS ====================
def get_resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def create_shortcut(target_path, shortcut_path, icon_path=None, working_dir=None):
    try:
        import pythoncom  # noqa
        from win32com.client import Dispatch
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_path
        shortcut.WorkingDirectory = working_dir or os.path.dirname(target_path)
        if icon_path and os.path.exists(icon_path):
            shortcut.IconLocation = icon_path
        shortcut.save()
        return True
    except Exception:
        try:
            ps_cmd = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_path}"
$Shortcut.WorkingDirectory = "{working_dir or os.path.dirname(target_path)}"
$Shortcut.IconLocation = "{icon_path or target_path}"
$Shortcut.Save()
'''
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, timeout=15
            )
            return os.path.exists(shortcut_path)
        except Exception:
            return False


def refresh_explorer():
    try:
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        pass


def _check_installed():
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\HookEngine")
        ver, _ = winreg.QueryValueEx(k, "Version")
        install_path, _ = winreg.QueryValueEx(k, "InstallPath")
        winreg.CloseKey(k)
        if os.path.exists(install_path):
            return ver
        return None
    except Exception:
        return None


# ==================== INSTALL ====================
def run_install(lang, log_callback):
    s = lambda k: get_string(lang, k)

    log_callback(f"HookEngine v{APP_VERSION}")
    log_callback("=" * 60)
    log_callback(s('installing'))
    log_callback("")

    # Step 1: Install dir
    log_callback(s('step_1'))
    os.makedirs(INSTALL_DIR, exist_ok=True)
    log_callback(f"  → {INSTALL_DIR}")

    # Step 2: Copy EXE
    log_callback(s('step_2'))
    exe_dest = os.path.join(INSTALL_DIR, EXE_NAME)
    candidates = [
        get_resource_path(EXE_NAME),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), EXE_NAME),
    ]
    if hasattr(sys, 'frozen'):
        candidates.insert(0, os.path.join(sys._MEIPASS, EXE_NAME))
    exe_source = next((c for c in candidates if os.path.exists(c)), None)
    if not exe_source:
        log_callback(f"  {s('error_exe')}")
        log_callback(f"  {s('error_exe_fix')}")
        return False
    shutil.copy2(exe_source, exe_dest)
    log_callback(f"  {s('copy_ok')} {exe_dest}")

    # Step 3: Copy icon
    log_callback(s('step_3'))
    icon_dest = os.path.join(INSTALL_DIR, ICON_NAME)
    icon_candidates = [
        get_resource_path(ICON_NAME),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ICON_NAME),
    ]
    if hasattr(sys, 'frozen'):
        icon_candidates.insert(0, os.path.join(sys._MEIPASS, ICON_NAME))
    icon_source = next((c for c in icon_candidates if os.path.exists(c)), None)
    if icon_source:
        shutil.copy2(icon_source, icon_dest)
        log_callback(f"  {s('copy_ok')} {icon_dest}")
    else:
        log_callback(f"  {s('warn_icon')}")

    # Step 4: Hide folder
    log_callback(s('step_4'))
    try:
        ctypes.windll.kernel32.SetFileAttributesW(INSTALL_DIR, 0x02)
        log_callback(f"  {s('hidden_ok')}")
    except Exception:
        pass

    # Step 5: Desktop shortcut
    log_callback(s('step_5'))
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, f"{APP_NAME}.lnk")
    if create_shortcut(exe_dest, shortcut_path, icon_dest, INSTALL_DIR):
        log_callback(f"  {s('shortcut_ok')} {shortcut_path}")
    else:
        log_callback(f"  {s('warn_shortcut')}")

    # Step 6: Start menu
    log_callback(s('step_6'))
    start_menu = os.path.join(
        os.environ.get('APPDATA', ''),
        "Microsoft", "Windows", "Start Menu", "Programs"
    )
    start_shortcut = os.path.join(start_menu, f"{APP_NAME}.lnk")
    if create_shortcut(exe_dest, start_shortcut, icon_dest, INSTALL_DIR):
        log_callback(f"  {s('shortcut_ok')} {start_shortcut}")

    # Step 7: Registry
    log_callback(s('step_7'))
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\HookEngine")
        winreg.SetValueEx(key, "InstallPath", 0, winreg.REG_SZ, INSTALL_DIR)
        winreg.SetValueEx(key, "Version", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Language", 0, winreg.REG_SZ, lang)
        winreg.SetValueEx(key, "ExePath", 0, winreg.REG_SZ, exe_dest)
        winreg.SetValueEx(key, "IconPath", 0, winreg.REG_SZ, icon_dest)
        winreg.CloseKey(key)
        log_callback(f"  {s('registry_ok')} ({s('done_lang')} {lang.upper()})")
    except Exception as e:
        log_callback(f"  {s('warn_registry')} {e}")

    # Step 8: .ht association
    log_callback(s('step_8'))
    try:
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.ht")
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "HookEngine.Table")
        winreg.CloseKey(k)

        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\HookEngine.Table")
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "HookEngine Table")
        winreg.CloseKey(k)

        if os.path.exists(icon_dest):
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Classes\HookEngine.Table\DefaultIcon")
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f"{icon_dest},0")
            winreg.CloseKey(k)

        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Classes\HookEngine.Table\shell\open\command")
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe_dest}" "%1"')
        winreg.CloseKey(k)

        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.ht\ShellNew")
        winreg.SetValueEx(k, "NullFile", 0, winreg.REG_SZ, "")
        winreg.CloseKey(k)

        log_callback(f"  {s('registry_ok')}")
    except Exception as e:
        log_callback(f"  {s('warn_registry')} {e}")

    # Step 9: Refresh explorer
    log_callback(s('step_9'))
    refresh_explorer()
    log_callback(f"  {s('explorer_ok')}")

    log_callback("")
    log_callback("=" * 60)
    log_callback(s('done'))
    log_callback(f"{s('done_path')} {INSTALL_DIR}")
    log_callback(f"{s('done_desktop')} {shortcut_path}")
    log_callback(f"{s('done_lang')} {lang.upper()}")
    log_callback("=" * 60)
    return True


def run_uninstall(lang, log_callback):
    s = lambda k: get_string(lang, k)
    log_callback(s('uninstalling'))

    if os.path.exists(INSTALL_DIR):
        try:
            ctypes.windll.kernel32.SetFileAttributesW(INSTALL_DIR, 0x80)
        except Exception:
            pass
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut = os.path.join(desktop, f"{APP_NAME}.lnk")
    if os.path.exists(shortcut):
        os.remove(shortcut)

    start_menu = os.path.join(
        os.environ.get('APPDATA', ''),
        "Microsoft", "Windows", "Start Menu", "Programs"
    )
    start_shortcut = os.path.join(start_menu, f"{APP_NAME}.lnk")
    if os.path.exists(start_shortcut):
        os.remove(start_shortcut)

    keys = [
        r"Software\Classes\.ht\ShellNew",
        r"Software\Classes\HookEngine.Table\DefaultIcon",
        r"Software\Classes\HookEngine.Table\shell\open\command",
        r"Software\Classes\HookEngine.Table\shell\open",
        r"Software\Classes\HookEngine.Table\shell",
        r"Software\Classes\HookEngine.Table",
        r"Software\Classes\.ht",
        r"Software\HookEngine",
    ]
    for path in keys:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except Exception:
            pass

    refresh_explorer()
    log_callback(s('uninstall_done'))
    return True


# ==================== GUI ====================
class InstallerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("HookEngine Installer")
        self.root.geometry("700x520")
        self.root.configure(bg='#0a0a0a')
        self.root.resizable(False, False)

        icon_path = get_resource_path(ICON_NAME)
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.lang = 'en'
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\HookEngine")
            saved, _ = winreg.QueryValueEx(k, "Language")
            winreg.CloseKey(k)
            if saved in ('tr', 'en'):
                self.lang = saved
        except Exception:
            pass

        self.mode = 'install'
        self.installed_version = _check_installed()

        if len(sys.argv) > 1 and sys.argv[1] == '--uninstall':
            self.mode = 'uninstall'

        self.setup_styles()

        if self.mode == 'uninstall':
            self.build_uninstall_ui()
        elif self.installed_version:
            self.build_already_installed_ui()
        else:
            self.build_language_ui()

    def setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('Dark.TFrame', background='#0a0a0a')
        style.configure('Dark.TLabel', background='#0a0a0a', foreground='#00ff00',
                        font=('Consolas', 11))
        style.configure('Title.TLabel', background='#0a0a0a', foreground='#ff3030',
                        font=('Consolas', 18, 'bold'))
        style.configure('Sub.TLabel', background='#0a0a0a', foreground='#888888',
                        font=('Consolas', 10))
        style.configure('Dark.TButton', background='#1a3a1a', foreground='#00ff00',
                        font=('Consolas', 11, 'bold'), padding=8)
        style.configure('Dark.TRadiobutton', background='#0a0a0a', foreground='#00ff00',
                        font=('Consolas', 12))

    def clear_window(self):
        for w in self.root.winfo_children():
            w.destroy()

    def build_language_ui(self):
        self.clear_window()
        self.root.title("HookEngine Installer — Language")

        frame = ttk.Frame(self.root, style='Dark.TFrame')
        frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)

        ttk.Label(frame, text="HookEngine v3.0",
                  style='Title.TLabel').pack(pady=(20, 5))
        ttk.Label(frame, text="Installer / Kurulum",
                  style='Sub.TLabel').pack(pady=(0, 30))

        ttk.Label(frame,
                  text="Please select installation language:\nLütfen kurulum dilini seçin:",
                  style='Dark.TLabel', justify=tk.CENTER).pack(pady=(10, 20))

        self.lang_var = tk.StringVar(value=self.lang)

        rb_frame = ttk.Frame(frame, style='Dark.TFrame')
        rb_frame.pack(pady=10)

        ttk.Radiobutton(rb_frame, text="  English",
                        variable=self.lang_var, value='en',
                        style='Dark.TRadiobutton').pack(anchor=tk.W, pady=4)
        ttk.Radiobutton(rb_frame, text="  Türkçe",
                        variable=self.lang_var, value='tr',
                        style='Dark.TRadiobutton').pack(anchor=tk.W, pady=4)

        btn_frame = ttk.Frame(frame, style='Dark.TFrame')
        btn_frame.pack(pady=40)

        ttk.Button(btn_frame, text="Continue / Devam Et",
                   command=self.on_language_selected,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Cancel / İptal",
                   command=self.root.destroy,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=8)

    def on_language_selected(self):
        self.lang = self.lang_var.get()
        self.build_install_ui()

    def build_already_installed_ui(self):
        self.clear_window()
        self.root.title("HookEngine — Already Installed")

        frame = ttk.Frame(self.root, style='Dark.TFrame')
        frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)

        ttk.Label(frame, text="HookEngine",
                  style='Title.TLabel').pack(pady=(20, 5))
        ttk.Label(frame,
                  text=f"v{self.installed_version} already installed / zaten kurulu",
                  style='Sub.TLabel').pack(pady=(0, 30))

        info = ("HookEngine is already installed on this system.\n"
                "HookEngine bu sistemde zaten kurulu.\n\n"
                "What would you like to do?\n"
                "Ne yapmak istersiniz?")

        ttk.Label(frame, text=info, style='Dark.TLabel',
                  justify=tk.CENTER).pack(pady=(10, 30))

        btn_frame = ttk.Frame(frame, style='Dark.TFrame')
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Repair / Onar",
                   command=self.build_install_ui,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Uninstall / Kaldır",
                   command=self.on_uninstall_confirm,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancel / İptal",
                   command=self.root.destroy,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=6)

    def on_uninstall_confirm(self):
        if messagebox.askyesno("Uninstall / Kaldır",
                               "Uninstall HookEngine?\nHookEngine kaldırılsın mı?"):
            self.build_uninstall_ui()

    def build_install_ui(self):
        self.clear_window()
        s = lambda k: get_string(self.lang, k)
        self.root.title(s('window_title'))

        frame = ttk.Frame(self.root, style='Dark.TFrame')
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(frame, text=s('install_title'),
                  style='Title.TLabel').pack(pady=(5, 15))

        self.progress = ttk.Progressbar(frame, mode='indeterminate', length=600)
        self.progress.pack(pady=(0, 15))
        self.progress.start(10)

        log_frame = ttk.Frame(frame, style='Dark.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, bg='#000000', fg='#00ff00',
                                font=('Consolas', 9), wrap=tk.WORD,
                                insertbackground='#00ff00')
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=sb.set)

        self.close_btn = ttk.Button(frame, text=s('close'),
                                     command=self.root.destroy,
                                     style='Dark.TButton')
        self.close_btn.pack(pady=15)
        self.close_btn.config(state=tk.DISABLED)

        threading.Thread(target=self.do_install, daemon=True).start()

    def log(self, text):
        def _write():
            self.log_text.insert(tk.END, text + "\n")
            self.log_text.see(tk.END)
        self.root.after(0, _write)

    def do_install(self):
        try:
            run_install(self.lang, self.log)
        except Exception as e:
            self.log(f"[FATAL] {e}")
            import traceback
            self.log(traceback.format_exc())

        def _finish():
            self.progress.stop()
            self.progress.config(mode='determinate', value=100)
            self.close_btn.config(state=tk.NORMAL)
        self.root.after(0, _finish)

    def build_uninstall_ui(self):
        self.clear_window()
        s = lambda k: get_string(self.lang, k)
        self.root.title(s('uninstall_title'))
        self.root.geometry("600x400")

        frame = ttk.Frame(self.root, style='Dark.TFrame')
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(frame, text=s('uninstall_title'),
                  style='Title.TLabel').pack(pady=(5, 15))

        log_frame = ttk.Frame(frame, style='Dark.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, bg='#000000', fg='#00ff00',
                                font=('Consolas', 9), wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=sb.set)

        self.close_btn = ttk.Button(frame, text=s('close'),
                                     command=self.root.destroy,
                                     style='Dark.TButton')
        self.close_btn.pack(pady=15)
        self.close_btn.config(state=tk.DISABLED)

        threading.Thread(target=self.do_uninstall, daemon=True).start()

    def do_uninstall(self):
        try:
            run_uninstall(self.lang, self.log)
        except Exception as e:
            self.log(f"[FATAL] {e}")
        self.root.after(0, lambda: self.close_btn.config(state=tk.NORMAL))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        app = InstallerGUI()
        app.run()
    except Exception as e:
        try:
            err_log = os.path.join(os.environ.get('TEMP', '.'), 'hookengine_installer_error.log')
            with open(err_log, 'w', encoding='utf-8') as f:
                f.write(f"FATAL: {e}\n")
                import traceback
                f.write(traceback.format_exc())
        except Exception:
            pass
        sys.exit(1)