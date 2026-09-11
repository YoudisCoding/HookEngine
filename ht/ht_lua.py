#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — HT Lua Engine
Lua script çalıştırma + HT API
"""

import threading
import time
import struct

try:
    import lupa
    from lupa import LuaRuntime
    LUPA_AVAILABLE = True
except ImportError:
    LUPA_AVAILABLE = False

from ht.ht_resolver import HTResolver


class HTLuaEngine:
    """Lua script motoru"""

    def __init__(self, pid, on_log=None):
        self.pid = pid
        self.on_log = on_log or (lambda msg: None)
        self.resolver = HTResolver(pid)
        self.scripts = {}   # entry_id → {'runtime':..., 'stop':..., 'thread':...}

        if not LUPA_AVAILABLE:
            self.log("[!] lupa not installed — Lua scripts disabled")
            self.log("    Install: pip install lupa")

    def log(self, msg):
        self.on_log(msg)

    def _setup_api(self, lua):
        """Lua'ya HT API'sini ekle"""
        api = {
            'readByte':   lambda addr: self._read(addr, 'byte'),
            'readInt':    lambda addr: self._read(addr, 'int'),
            'readInt64':  lambda addr: self._read(addr, 'int64'),
            'readFloat':  lambda addr: self._read(addr, 'float'),
            'readDouble': lambda addr: self._read(addr, 'double'),
            'readString': lambda addr: self._read(addr, 'string'),

            'writeByte':   lambda addr, v: self._write(addr, v, 'byte'),
            'writeInt':    lambda addr, v: self._write(addr, v, 'int'),
            'writeInt64':  lambda addr, v: self._write(addr, v, 'int64'),
            'writeFloat':  lambda addr, v: self._write(addr, v, 'float'),
            'writeDouble': lambda addr, v: self._write(addr, v, 'double'),
            'writeString': lambda addr, v: self._write(addr, v, 'string'),

            'resolve':    lambda read: self._resolve(read),
            'sleep':      lambda ms: time.sleep(ms / 1000.0),
            'log':        lambda msg: self.log(f"[Lua] {msg}"),
        }
        for k, v in api.items():
            lua.globals()[k] = v

    def _read(self, addr, t):
        try:
            if isinstance(addr, str):
                addr = self._resolve(addr)
            if addr is None:
                return None
            return self.resolver.read(addr, t)
        except Exception:
            return None

    def _write(self, addr, value, t):
        try:
            if isinstance(addr, str):
                addr = self._resolve(addr)
            if addr is None:
                return False
            return self.resolver.write(addr, value, t)
        except Exception:
            return False

    def _resolve(self, read):
        """read alanını çöz"""
        try:
            if isinstance(read, str):
                # "module+off | +off" → list
                if '|' in read:
                    parts = [p.strip() for p in read.split('|')]
                else:
                    parts = [read]
            elif isinstance(read, list):
                parts = read
            else:
                return None
            return self.resolver.resolve(parts)
        except Exception:
            return None

    def run(self, script_id, code):
        """Script çalıştır"""
        if not LUPA_AVAILABLE:
            self.log("[!] Lua unavailable")
            return False

        try:
            lua = LuaRuntime(unpack_returned_tuples=True)
            self._setup_api(lua)
            self.resolver.open()

            # Basit çalıştırma (döngü kullanıcı tarafından)
            lua.execute(code)

            # Script içinde sonsuz döngü olabilir → thread gerekmez
            # Kullanıcı `while true do ... end` yazarsa bu bloklar
            # Bunu engellemek için: sandbox + timeout (opsiyonel)

            self.scripts[script_id] = {
                'runtime': lua,
                'stop': False,
            }
            return True
        except Exception as e:
            self.log(f"[Lua Error] {e}")
            return False

    def stop(self, script_id):
        """Script durdur"""
        info = self.scripts.pop(script_id, None)
        if info:
            info['stop'] = True
            # lupa'da tam durdurma zor; runtime'ı temizle
            info['runtime'] = None