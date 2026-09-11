#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — HT Engine
HT entry'lerini çalıştırır, döngü, koşul, hotkey yönetimi
"""

import threading
import time
from ht.ht_v3 import (
    HTTable, HTEntry, MODE_TOGGLE, MODE_ACTION, MODE_FREEZE,
    MODE_SCRIPT, MODE_INJECT, MODE_FORMULA, MODE_CONDITION
)
from ht.ht_resolver import HTResolver

try:
    from ht.ht_lua import HTLuaEngine
except ImportError:
    HTLuaEngine = None

try:
    from ht.ht_injector import HTInjector
except ImportError:
    HTInjector = None


class HTEngine:
    """HT Table çalıştırıcı"""

    def __init__(self, pid, on_log=None):
        self.pid = pid
        self.on_log = on_log or (lambda msg: None)
        self.resolver = HTResolver(pid)
        self.lua = HTLuaEngine(pid) if HTLuaEngine else None
        self.injector = HTInjector(pid) if HTInjector else None

        self.table = None
        self.active_entries = {}    # entry_id → {'thread':..., 'stop':...}
        self.hotkeys = {}           # key → entry_id
        self.running = False

    def log(self, msg):
        self.on_log(msg)

    # ==================== LOAD / UNLOAD ====================

    def load(self, table):
        """HT Table'ı yükle"""
        self.unload()
        self.table = table
        self.resolver.open()

        errors = table.validate()
        if errors:
            self.log(f"[!] {len(errors)} validation error(s):")
            for e in errors:
                self.log(f"    {e}")
            return False

        self.log(f"[+] Loaded: {table.name} ({len(table.groups)} groups)")
        return True

    def unload(self):
        """Tüm aktif entry'leri durdur"""
        self.stop_all()
        self.resolver.close()
        self.table = None

    # ==================== ENTRY CONTROL ====================

    def enable(self, entry):
        """Entry'yi aktif et"""
        if entry.id in self.active_entries:
            return

        self.log(f"[+] Enabling: {entry.label}")

        if entry.mode == MODE_TOGGLE:
            self._enable_toggle(entry)
        elif entry.mode == MODE_ACTION:
            self._enable_action(entry)
        elif entry.mode == MODE_FREEZE:
            self._enable_freeze(entry)
        elif entry.mode == MODE_SCRIPT:
            self._enable_script(entry)
        elif entry.mode == MODE_INJECT:
            self._enable_inject(entry)
        elif entry.mode == MODE_FORMULA:
            self._enable_formula(entry)
        elif entry.mode == MODE_CONDITION:
            self._enable_condition(entry)

    def disable(self, entry):
        """Entry'yi pasif et"""
        info = self.active_entries.pop(entry.id, None)
        if not info:
            return
        self.log(f"[-] Disabling: {entry.label}")

        # Durdurma bayrağı
        info['stop'] = True

        # Thread varsa bekle
        t = info.get('thread')
        if t and t.is_alive():
            t.join(timeout=0.5)

        # Dondurulan değer varsa eski değere döndür
        if entry.mode in (MODE_TOGGLE, MODE_FREEZE):
            # Aktif bırakmak istemiyorsak: değeri "eski" hale getir
            # (şimdilik: sadece durdur, geri alma işlemi yok)
            pass

        # Inject kaldır
        if entry.mode == MODE_INJECT and self.injector:
            self.injector.remove_hook(entry.id)

        # Lua durdur
        if entry.mode == MODE_SCRIPT and self.lua:
            self.lua.stop(entry.id)

    def toggle(self, entry):
        """Aç/kapat"""
        if entry.id in self.active_entries:
            self.disable(entry)
        else:
            self.enable(entry)

    def stop_all(self):
        """Tüm aktif entry'leri durdur"""
        for eid in list(self.active_entries.keys()):
            if self.table:
                entry = self.table.find_entry(eid)
                if entry:
                    self.disable(entry)

    # ==================== MODE HANDLERS ====================

    def _enable_toggle(self, entry):
        """Toggle: bir kere yaz, sonra gerekirse repeat"""
        addr = self.resolver.resolve(entry.read)
        if addr is None:
            self.log(f"[!] Resolve failed: {entry.label}")
            return
        ok = self.resolver.write(addr, entry.value, entry.type)
        self.log(f"  → {'✓' if ok else '✗'} Write {entry.value} to 0x{addr:X}")

        # Repeat varsa döngüye al
        if entry.repeat and entry.repeat > 0:
            info = {'stop': False}
            t = threading.Thread(target=self._loop_write, args=(entry, info), daemon=True)
            info['thread'] = t
            self.active_entries[entry.id] = info
            t.start()
        else:
            self.active_entries[entry.id] = {'stop': False}

    def _enable_action(self, entry):
        """Action: bir kere yaz, bitir"""
        addr = self.resolver.resolve(entry.read)
        if addr is None:
            self.log(f"[!] Resolve failed: {entry.label}")
            return
        ok = self.resolver.write(addr, entry.value, entry.type)
        self.log(f"  → {'✓' if ok else '✗'} Action executed")

    def _enable_freeze(self, entry):
        """Freeze: sürekli yaz (repeat veya default 50ms)"""
        info = {'stop': False}
        t = threading.Thread(target=self._loop_write, args=(entry, info), daemon=True)
        info['thread'] = t
        self.active_entries[entry.id] = info
        t.start()
        self.log(f"  → Freezing")

    def _enable_script(self, entry):
        """Lua script çalıştır"""
        if not self.lua:
            self.log("[!] Lua engine not available")
            return
        info = {'stop': False}
        t = threading.Thread(target=self._loop_script, args=(entry, info), daemon=True)
        info['thread'] = t
        self.active_entries[entry.id] = info
        t.start()

    def _enable_inject(self, entry):
        """Kod injection"""
        if not self.injector:
            self.log("[!] Injector not available")
            return
        if not entry.hook_target:
            self.log("[!] hook_target required for inject")
            return
        ok = self.injector.install_hook(
            entry.id,
            entry.hook_target,
            entry.inject
        )
        if ok:
            self.active_entries[entry.id] = {'stop': False}
            self.log(f"  → Hook installed")
        else:
            self.log(f"  → Hook failed")

    def _enable_formula(self, entry):
        """Formül: mevcut değeri oku → formül uygula → yaz"""
        info = {'stop': False}
        t = threading.Thread(target=self._loop_formula, args=(entry, info), daemon=True)
        info['thread'] = t
        self.active_entries[entry.id] = info
        t.start()

    def _enable_condition(self, entry):
        """Koşul: koşul sağlanınca yaz"""
        info = {'stop': False}
        t = threading.Thread(target=self._loop_condition, args=(entry, info), daemon=True)
        info['thread'] = t
        self.active_entries[entry.id] = info
        t.start()

    # ==================== LOOPS ====================

    def _loop_write(self, entry, info):
        """Sürekli yazma döngüsü"""
        addr = self.resolver.resolve(entry.read)
        if addr is None:
            self.log(f"[!] Loop resolve failed: {entry.label}")
            return
        interval = (entry.repeat or 50) / 1000.0
        while not info['stop']:
            try:
                self.resolver.write(addr, entry.value, entry.type)
            except Exception:
                pass
            time.sleep(interval)

    def _loop_script(self, entry, info):
        """Lua script döngüsü"""
        if not self.lua:
            return
        try:
            self.lua.run(entry.id, entry.script)
        except Exception as e:
            self.log(f"[!] Lua error: {e}")

    def _loop_formula(self, entry, info):
        """Formül döngüsü"""
        addr = self.resolver.resolve(entry.read)
        if addr is None:
            return
        interval = (entry.repeat or 100) / 1000.0
        while not info['stop']:
            try:
                current = self.resolver.read(addr, entry.type)
                if current is not None:
                    new_val = self._eval_formula(entry.formula, current)
                    if new_val is not None:
                        self.resolver.write(addr, new_val, entry.type)
            except Exception:
                pass
            time.sleep(interval)

    def _loop_condition(self, entry, info):
        """Koşul döngüsü"""
        addr = self.resolver.resolve(entry.read)
        if addr is None:
            return
        interval = (entry.repeat or 100) / 1000.0
        while not info['stop']:
            try:
                current = self.resolver.read(addr, entry.type)
                if current is not None:
                    if self._eval_condition(entry.condition, current):
                        self.resolver.write(addr, entry.value, entry.type)
            except Exception:
                pass
            time.sleep(interval)

    def _eval_formula(self, formula, current):
        """Formül değerlendir: 'current * 2' gibi"""
        if not formula:
            return None
        try:
            # Basit ve güvenli eval (sadece sayısal + operatörler)
            allowed = set('0123456789.+-*/() _current')
            if not all(c in allowed for c in formula):
                return None
            return eval(formula, {"__builtins__": {}}, {"current": current})
        except Exception:
            return None

    def _eval_condition(self, condition, current):
        """Koşul değerlendir: 'current < 50' gibi"""
        if not condition:
            return False
        try:
            allowed = set('0123456789.+-*/()<>!=&| _current')
            if not all(c in allowed for c in condition):
                return False
            return bool(eval(condition, {"__builtins__": {}}, {"current": current}))
        except Exception:
            return False

    # ==================== HOTKEYS ====================

    def register_hotkey(self, key, entry, callback=None):
        """Kısayol kaydet (pywin32 veya tkinter tarafından çağrılır)"""
        self.hotkeys[key.lower()] = {
            'entry': entry,
            'callback': callback
        }

    def unregister_hotkey(self, key):
        self.hotkeys.pop(key.lower(), None)

    def trigger_hotkey(self, key):
        """Kısayol tetiklendiğinde çağrılır"""
        info = self.hotkeys.get(key.lower())
        if not info:
            return
        entry = info['entry']
        cb = info['callback']
        if cb:
            cb(entry)
        else:
            self.toggle(entry)