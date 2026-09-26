#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOUD HT TABLE UI — dynamic buttons from .ht file
Includes: HT TABLE tab + HT CREATOR dialog
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
from ht.ht_table import HTTable, HTEntry, default_template
from core.memory_engine import MemoryEngine
from core.lang import t as _t


class HTTableTab:
    """HT TABLE tab UI — CE-like cheat table"""

    def __init__(self, parent, app):
        self.parent = parent
        self.app = app  # reference to main app (for target_pid, target_dll)
        self.ht = None
        self.freeze_threads = {}
        self.freeze_stop_flags = {}
        self.entry_widgets = []  # (entry, checkbox_var, button_ref)
        self.hotkey_bindings = {}

        self.setup_ui()

    # ==================== UI SETUP ====================

    def setup_ui(self):
        # Header bar
        header = ttk.Frame(self.parent, style='Dark.TFrame')
        header.pack(fill=tk.X, padx=5, pady=5)

        self.exe_label = ttk.Label(
            header, text="Current EXE: (not selected)",
            style='Dark.TLabel', font=('Consolas', 10, 'bold')
        )
        self.exe_label.pack(side=tk.LEFT, padx=(0, 20))

        self.ht_label = ttk.Label(
            header, text="Hack Table: (none)",
            style='Dark.TLabel', font=('Consolas', 10)
        )
        self.ht_label.pack(side=tk.LEFT)

        # Control buttons
        ctrl = ttk.Frame(self.parent, style='Dark.TFrame')
        ctrl.pack(fill=tk.X, padx=5, pady=(0, 5))

        ttk.Button(ctrl, text="Ekle", command=self.add_ht,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Tamam", command=self.apply_ht,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Temizle", command=self.clear_all,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="HT CREATOR", command=self.open_creator,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Yenile", command=self.reload_widgets,
                   style='Dark.TButton').pack(side=tk.LEFT, padx=2)

        # Info line
        self.info_label = ttk.Label(
            self.parent,
            text="Oyunu aç → soldan exe seç → Ekle ile .ht seç → Tamam'a bas",
            style='Dark.TLabel', font=('Consolas', 9)
        )
        self.info_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

        # Scrollable area for groups
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

        # Mouse wheel scroll
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        # Update exe label periodically
        self.update_exe_label()
        self.parent.after(1000, self._periodic_update)

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _periodic_update(self):
        self.update_exe_label()
        self.parent.after(1000, self._periodic_update)

    def update_exe_label(self):
        pid = getattr(self.app, 'target_pid', None)
        if pid:
            try:
                import psutil
                proc = psutil.Process(pid)
                self.exe_label.config(text=f"Current EXE: {proc.name()}  (PID: {pid})")
            except Exception:
                self.exe_label.config(text="Current EXE: (not selected)")
        else:
            self.exe_label.config(text="Current EXE: (not selected)")

    # ==================== FILE OPERATIONS ====================

    def add_ht(self):
        """Add .ht file — opens file dialog and stages it"""
        path = filedialog.askopenfilename(
            title="Select Hack Table",
            filetypes=[("YOUD Hack Table", "*.ht"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.ht = HTTable.load(path)
            filename = path.split("/")[-1].split("\\")[-1]
            self.ht_label.config(text=f"Hack Table: {filename}")
            self.info_label.config(
                text=f"✓ Loaded: {filename} — {len(self.ht.groups)} group(s). "
                     f"Press 'Tamam' to activate."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Could not load .ht:\n{e}")

    def apply_ht(self):
        """Tamam — render buttons from loaded ht"""
        if not self.ht:
            messagebox.showwarning("Warning", "No .ht file loaded. Click 'Ekle' first.")
            return

        if not getattr(self.app, 'target_pid', None):
            messagebox.showwarning("Warning", "Select a target process from the left panel first.")
            return

        self.clear_widgets()
        self.render_groups()

    def clear_all(self):
        """Clear everything"""
        self.stop_all_freezes()
        self.ht = None
        self.ht_label.config(text="Hack Table: (none)")
        self.clear_widgets()
        self.info_label.config(
            text="Oyunu aç → soldan exe seç → Ekle ile .ht seç → Tamam'a bas"
        )

    def clear_widgets(self):
        for w in self.groups_frame.winfo_children():
            w.destroy()
        self.entry_widgets = []
        # Remove hotkeys
        for hk, seq in self.hotkey_bindings.items():
            try:
                self.app.root.unbind_all(seq)
            except Exception:
                pass
        self.hotkey_bindings = {}

    def reload_widgets(self):
        if self.ht:
            self.clear_widgets()
            self.render_groups()

    # ==================== RENDER ====================

    def render_groups(self):
        if not self.ht:
            return

        for group in self.ht.groups:
            self.render_group(group)

    def render_group(self, group):
        # Group frame
        gf = tk.Frame(self.groups_frame, bg='#0f0f0f',
                      highlightbackground=group.color, highlightthickness=1)
        gf.pack(fill=tk.X, padx=4, pady=6)

        # Group header
        header = tk.Frame(gf, bg='#0f0f0f')
        header.pack(fill=tk.X, padx=6, pady=(6, 3))

        tk.Label(header, text=f"▶ {group.name}", bg='#0f0f0f',
                 fg=group.color, font=('Consolas', 11, 'bold')).pack(side=tk.LEFT)

        # Group action buttons
        btn_frame = tk.Frame(header, bg='#0f0f0f')
        btn_frame.pack(side=tk.RIGHT)

        tk.Button(btn_frame, text="✓ Enable All",
                  bg='#1a3a1a', fg='#00ff00', font=('Consolas', 8),
                  bd=0, padx=6,
                  command=lambda g=group: self.enable_all(g)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="✗ Disable All",
                  bg='#3a1a1a', fg='#ff5555', font=('Consolas', 8),
                  bd=0, padx=6,
                  command=lambda g=group: self.disable_all(g)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="❄ Freeze All",
                  bg='#1a2a3a', fg='#55aaff', font=('Consolas', 8),
                  bd=0, padx=6,
                  command=lambda g=group: self.freeze_all(g)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="❄ Unfreeze",
                  bg='#2a2a2a', fg='#aaaaaa', font=('Consolas', 8),
                  bd=0, padx=6,
                  command=lambda g=group: self.unfreeze_all(g)).pack(side=tk.LEFT, padx=2)

        # Entries
        for entry in group.entries:
            self.render_entry(gf, entry)

    def render_entry(self, parent, entry):
        row = tk.Frame(parent, bg='#0f0f0f')
        row.pack(fill=tk.X, padx=6, pady=3)

        # Checkbox (for toggle/action visibility)
        var = tk.BooleanVar(value=entry.checked)
        chk = tk.Checkbutton(
            row, variable=var, bg='#0f0f0f', fg='#00ff00',
            activebackground='#0f0f0f', activeforeground='#00ff00',
            selectcolor='#000000', bd=0
        )
        chk.pack(side=tk.LEFT)

        # Label
        label_text = f"{entry.label}"
        if entry.hotkey:
            label_text += f"  [{entry.hotkey}]"
        tk.Label(row, text=label_text, bg='#0f0f0f', fg='#cccccc',
                 font=('Consolas', 10), width=22, anchor='w').pack(side=tk.LEFT, padx=4)

        # Address
        tk.Label(row, text=entry.address, bg='#0f0f0f', fg='#666666',
                 font=('Consolas', 9), width=14, anchor='w').pack(side=tk.LEFT)

        # Description
        tk.Label(row, text=f"→ {entry.description}", bg='#0f0f0f', fg='#888888',
                 font=('Consolas', 9), anchor='w').pack(side=tk.LEFT, padx=4)

        # Action button (for toggle mode, button toggles state)
        if entry.mode == "toggle":
            def on_toggle(e=entry, v=var):
                e.checked = v.get()
                if e.checked:
                    self.write_value(e)
                else:
                    self.write_value(e, revert=True)
            chk.config(command=on_toggle)
        else:
            # For "action" mode — button also triggers
            def on_toggle(e=entry, v=var):
                e.checked = v.get()
                if e.checked:
                    self.write_value(e)
            chk.config(command=on_toggle)

        # Manual "Execute" button (for action mode)
        if entry.mode in ("action", "freeze"):
            exe_btn_text = "Dondur" if entry.mode == "freeze" else "Çalıştır"
            tk.Button(
                row, text=exe_btn_text,
                bg='#1a3a1a', fg='#00ff00', font=('Consolas', 8),
                bd=0, padx=8,
                command=lambda e=entry: self.execute_entry(e)
            ).pack(side=tk.RIGHT, padx=2)

        self.entry_widgets.append((entry, var, chk))

        # Bind hotkey
        if entry.hotkey:
            try:
                self.app.root.bind_all(
                    f"<{entry.hotkey}>",
                    lambda ev, e=entry, v=var: self.hotkey_trigger(e, v)
                )
                self.hotkey_bindings[entry.hotkey] = f"<{entry.hotkey}>"
            except Exception:
                pass

    # ==================== ACTIONS ====================

    def hotkey_trigger(self, entry, var):
        if entry.mode == "toggle":
            new_state = not var.get()
            var.set(new_state)
            entry.checked = new_state
            if new_state:
                self.write_value(entry)
            else:
                self.write_value(entry, revert=True)
        else:
            self.execute_entry(entry)

    def execute_entry(self, entry):
        if entry.mode == "freeze":
            self.toggle_freeze(entry)
        else:
            self.write_value(entry)

    def write_value(self, entry, revert=False):
        """Write entry.value to entry.address. If revert, writes 0 or original."""
        if not getattr(self.app, 'target_pid', None):
            return False
        try:
            engine = MemoryEngine(self.app.target_pid)
            engine.open()
            addr = int(entry.address, 16)
            val = 0 if revert else entry.value

            if entry.entry_type == "int":
                engine.write_int(addr, int(val))
            elif entry.entry_type == "float":
                engine.write_float(addr, float(val))
            elif entry.entry_type == "double":
                engine.write_double(addr, float(val))
            elif entry.entry_type == "byte":
                engine.write_byte(addr, int(val))
            elif entry.entry_type == "string":
                engine.write_string(addr, str(val))
            engine.close()
            return True
        except Exception:
            return False

    def toggle_freeze(self, entry):
        key = f"{entry.address}_{entry.label}"
        if key in self.freeze_threads:
            # stop
            self.freeze_stop_flags[key] = True
            return
        # start
        self.freeze_stop_flags[key] = False
        t = threading.Thread(
            target=self._freeze_loop, args=(entry, key), daemon=True
        )
        self.freeze_threads[key] = t
        t.start()

    def _freeze_loop(self, entry, key):
        engine = MemoryEngine(self.app.target_pid)
        engine.open()
        addr = int(entry.address, 16)
        while not self.freeze_stop_flags.get(key, True):
            try:
                if entry.entry_type == "int":
                    engine.write_int(addr, int(entry.value))
                elif entry.entry_type == "float":
                    engine.write_float(addr, float(entry.value))
                elif entry.entry_type == "double":
                    engine.write_double(addr, float(entry.value))
                elif entry.entry_type == "byte":
                    engine.write_byte(addr, int(entry.value))
            except Exception:
                pass
            time.sleep(0.05)
        engine.close()
        self.freeze_threads.pop(key, None)

    def stop_all_freezes(self):
        for key in list(self.freeze_stop_flags.keys()):
            self.freeze_stop_flags[key] = True

    def enable_all(self, group):
        for entry in group.entries:
            if entry.mode == "toggle":
                entry.checked = True
                self.write_value(entry)
        self.reload_widgets()

    def disable_all(self, group):
        for entry in group.entries:
            if entry.mode == "toggle":
                entry.checked = False
                self.write_value(entry, revert=True)
        self.reload_widgets()

    def freeze_all(self, group):
        for entry in group.entries:
            key = f"{entry.address}_{entry.label}"
            if key not in self.freeze_threads:
                self.toggle_freeze(entry)

    def unfreeze_all(self, group):
        for entry in group.entries:
            key = f"{entry.address}_{entry.label}"
            if key in self.freeze_threads:
                self.freeze_stop_flags[key] = True

    # ==================== HT CREATOR ====================

    def open_creator(self):
        HT_CreatorDialog(self.parent, self.app, on_save=self.on_creator_save)

    def on_creator_save(self, ht):
        self.ht = ht
        self.ht_label.config(text=f"Hack Table: (created — {len(ht.groups)} groups)")
        self.info_label.config(text="✓ Created new table. Press 'Tamam' to activate.")


# ==================== HT CREATOR DIALOG ====================

class HT_CreatorDialog:
    """Form-based HT table creator/editor"""

    def __init__(self, parent, app, on_save=None):
        self.app = app
        self.on_save = on_save
        self.ht = HTTable()

        self.win = tk.Toplevel(parent)
        self.win.title("HT CREATOR — YOUD")
        self.win.geometry("900x700")
        self.win.configure(bg='#0a0a0a')

        self.setup_ui()

    def setup_ui(self):
        # Top bar
        top = tk.Frame(self.win, bg='#0a0a0a')
        top.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(top, text="HT CREATOR", bg='#0a0a0a', fg='#ff3030',
                 font=('Consolas', 16, 'bold')).pack(side=tk.LEFT)

        tk.Button(top, text="Boş Şablon", bg='#1a3a1a', fg='#00ff00',
                  font=('Consolas', 10), bd=0, padx=10, pady=6,
                  command=self.new_empty).pack(side=tk.RIGHT, padx=3)
        tk.Button(top, text="Örnek Yükle", bg='#1a3a1a', fg='#00ff00',
                  font=('Consolas', 10), bd=0, padx=10, pady=6,
                  command=self.load_template).pack(side=tk.RIGHT, padx=3)
        tk.Button(top, text=".ht Aç", bg='#1a3a1a', fg='#00ff00',
                  font=('Consolas', 10), bd=0, padx=10, pady=6,
                  command=self.load_ht).pack(side=tk.RIGHT, padx=3)

        # Scrollable group area
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

        # Bottom buttons
        bottom = tk.Frame(self.win, bg='#0a0a0a')
        bottom.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(bottom, text="+ Grup Ekle", bg='#1a2a3a', fg='#55aaff',
                  font=('Consolas', 11, 'bold'), bd=0, padx=15, pady=8,
                  command=self.add_group).pack(side=tk.LEFT, padx=3)

        tk.Button(bottom, text=".ht Kaydet", bg='#1a3a1a', fg='#00ff00',
                  font=('Consolas', 11, 'bold'), bd=0, padx=20, pady=8,
                  command=self.save_ht).pack(side=tk.RIGHT, padx=3)

        tk.Button(bottom, text="Kapat", bg='#3a1a1a', fg='#ff5555',
                  font=('Consolas', 11, 'bold'), bd=0, padx=20, pady=8,
                  command=self.win.destroy).pack(side=tk.RIGHT, padx=3)

    def new_empty(self):
        self.ht = HTTable()
        self.render()

    def load_template(self):
        self.ht = default_template()
        self.render()

    def load_ht(self):
        path = filedialog.askopenfilename(
            filetypes=[("YOUD Hack Table", "*.ht")]
        )
        if not path:
            return
        try:
            self.ht = HTTable.load(path)
            self.render()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_group(self):
        name = f"Group {len(self.ht.groups) + 1}"
        self.ht.add_group(name, "#00ff00")
        self.render()

    def save_ht(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".ht",
            filetypes=[("YOUD Hack Table", "*.ht")],
            initialfile="my_table.ht"
        )
        if not path:
            return
        try:
            self.ht.save(path)
            messagebox.showinfo("Saved", f"Saved: {path}")
            if self.on_save:
                self.on_save(self.ht)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def render(self):
        for w in self.groups_frame.winfo_children():
            w.destroy()

        for gi, group in enumerate(self.ht.groups):
            self.render_group_editor(gi, group)

    def render_group_editor(self, gi, group):
        gf = tk.LabelFrame(
            self.groups_frame, text=f"  {group.name}  ",
            bg='#0f0f0f', fg=group.color,
            font=('Consolas', 11, 'bold'), bd=1
        )
        gf.pack(fill=tk.X, padx=4, pady=6)

        # Group name edit
        name_row = tk.Frame(gf, bg='#0f0f0f')
        name_row.pack(fill=tk.X, padx=6, pady=3)

        tk.Label(name_row, text="Grup Adı:", bg='#0f0f0f', fg='#888888',
                 font=('Consolas', 9)).pack(side=tk.LEFT)
        name_var = tk.StringVar(value=group.name)
        tk.Entry(name_row, textvariable=name_var, bg='#000000', fg='#00ff00',
                 font=('Consolas', 10), width=25,
                 insertbackground='#00ff00').pack(side=tk.LEFT, padx=5)

        tk.Label(name_row, text="Renk:", bg='#0f0f0f', fg='#888888',
                 font=('Consolas', 9)).pack(side=tk.LEFT, padx=(20, 0))
        color_var = tk.StringVar(value=group.color)
        tk.Entry(name_row, textvariable=color_var, bg='#000000', fg='#00ff00',
                 font=('Consolas', 10), width=10,
                 insertbackground='#00ff00').pack(side=tk.LEFT, padx=5)

        def update_name(*_):
            group.name = name_var.get()
        def update_color(*_):
            group.color = color_var.get()

        name_var.trace_add('write', update_name)
        color_var.trace_add('write', update_color)

        tk.Button(name_row, text="✗ Grubu Sil", bg='#3a1a1a', fg='#ff5555',
                  font=('Consolas', 9), bd=0, padx=8,
                  command=lambda: self.delete_group(gi)).pack(side=tk.RIGHT)

        # Entries header
        hdr = tk.Frame(gf, bg='#0f0f0f')
        hdr.pack(fill=tk.X, padx=6, pady=(5, 2))
        for text, w in [("Label", 18), ("Address", 14), ("Type", 8),
                        ("Mode", 10), ("Value", 10), ("Hotkey", 6)]:
            tk.Label(hdr, text=text, bg='#0f0f0f', fg='#666666',
                     font=('Consolas', 8, 'bold'), width=w, anchor='w'
                     ).pack(side=tk.LEFT)
        tk.Label(hdr, text="Description", bg='#0f0f0f', fg='#666666',
                 font=('Consolas', 8, 'bold'), width=25, anchor='w'
                 ).pack(side=tk.LEFT)

        # Entries
        for ei, entry in enumerate(group.entries):
            self.render_entry_editor(gf, gi, ei, entry)

        # Add entry button
        tk.Button(gf, text="+ Entry Ekle", bg='#1a2a3a', fg='#55aaff',
                  font=('Consolas', 9), bd=0, padx=10, pady=4,
                  command=lambda g=group: self.add_entry(g)).pack(pady=5)

    def render_entry_editor(self, parent, gi, ei, entry):
        row = tk.Frame(parent, bg='#0f0f0f')
        row.pack(fill=tk.X, padx=6, pady=2)

        label_var = tk.StringVar(value=entry.label)
        addr_var = tk.StringVar(value=entry.address)
        type_var = tk.StringVar(value=entry.entry_type)
        mode_var = tk.StringVar(value=entry.mode)
        value_var = tk.StringVar(value=str(entry.value))
        hotkey_var = tk.StringVar(value=entry.hotkey)
        desc_var = tk.StringVar(value=entry.description)

        def make_entry(var, width):
            return tk.Entry(row, textvariable=var, bg='#000000', fg='#00ff00',
                            font=('Consolas', 9), width=width,
                            insertbackground='#00ff00')

        make_entry(label_var, 18).pack(side=tk.LEFT, padx=1)
        make_entry(addr_var, 14).pack(side=tk.LEFT, padx=1)

        ttk.Combobox(row, textvariable=type_var,
                     values=["int", "float", "double", "byte", "string"],
                     width=7, font=('Consolas', 9)).pack(side=tk.LEFT, padx=1)

        ttk.Combobox(row, textvariable=mode_var,
                     values=["action", "toggle", "freeze"],
                     width=9, font=('Consolas', 9)).pack(side=tk.LEFT, padx=1)

        make_entry(value_var, 10).pack(side=tk.LEFT, padx=1)
        make_entry(hotkey_var, 6).pack(side=tk.LEFT, padx=1)
        make_entry(desc_var, 25).pack(side=tk.LEFT, padx=1)

        def update(*_):
            entry.label = label_var.get()
            entry.address = addr_var.get()
            entry.entry_type = type_var.get()
            entry.mode = mode_var.get()
            try:
                entry.value = int(value_var.get())
            except ValueError:
                try:
                    entry.value = float(value_var.get())
                except ValueError:
                    entry.value = value_var.get()
            entry.hotkey = hotkey_var.get()
            entry.description = desc_var.get()

        for v in (label_var, addr_var, type_var, mode_var,
                  value_var, hotkey_var, desc_var):
            v.trace_add('write', update)

        tk.Button(row, text="✗", bg='#3a1a1a', fg='#ff5555',
                  font=('Consolas', 9), bd=0, padx=6,
                  command=lambda g=self.ht.groups[gi], e=entry:
                  self.delete_entry(g, e)).pack(side=tk.RIGHT, padx=2)

    def add_entry(self, group):
        e = HTEntry(
            label="New Entry",
            address="0x0",
            value=0,
            entry_type="int",
            mode="action",
            action="write",
            description=""
        )
        group.add(e)
        self.render()

    def delete_entry(self, group, entry):
        if entry in group.entries:
            group.entries.remove(entry)
        self.render()

    def delete_group(self, gi):
        if 0 <= gi < len(self.ht.groups):
            del self.ht.groups[gi]
        self.render()