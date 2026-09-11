#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — HT Resolver
read alanını gerçek bellek adresine çevirir + okuma/yazma
"""

import ctypes
import ctypes.wintypes as wt
import struct
import psutil
import os


# ==================== RESOLVER ====================
class HTResolver:
    def __init__(self, pid):
        self.pid = pid
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.h_process = None
        self.is_64 = True
        self._module_cache = {}

    def open(self):
        if self.h_process:
            return True
        PROCESS_ALL_ACCESS = 0x1F0FFF
        self.h_process = self.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, self.pid)
        if not self.h_process:
            return False
        # x86/x64 tespit
        try:
            h = self.kernel32.OpenProcess(0x0400, False, self.pid)
            if h:
                b = wt.BOOL()
                self.kernel32.IsWow64Process(h, ctypes.byref(b))
                self.is_64 = not bool(b.value)
                self.kernel32.CloseHandle(h)
        except Exception:
            pass
        return True

    def close(self):
        if self.h_process:
            self.kernel32.CloseHandle(self.h_process)
            self.h_process = None

    # ---------- MODULE ----------
    def _get_modules(self):
        """Tüm modülleri listele: [(name, base, size), ...]"""
        if self._module_cache:
            return self._module_cache.get('list', [])

        modules = []
        try:
            proc = psutil.Process(self.pid)
            for m in proc.memory_maps():
                path = m.path or ""
                if not path:
                    continue
                name = os.path.basename(path).lower()
                base = m.addr
                size = m.size
                if base and size:
                    modules.append((name, base, size))
        except Exception:
            pass

        self._module_cache['list'] = modules
        return modules

    def find_module_base(self, module_name):
        """Modül base adresini bul (case-insensitive)"""
        module_name = module_name.lower()
        for name, base, size in self._get_modules():
            if name == module_name:
                return base
        return None

    def find_module_by_address(self, address):
        """Adresi içeren modülü bul: (name, base, offset)"""
        for name, base, size in self._get_modules():
            if base <= address < base + size:
                return name, base, address - base
        return None

    # ---------- READ PARSE ----------
    def parse_read(self, read):
        """read alanını parse et → [step1, step2, ...]"""
        if isinstance(read, str):
            read = [read]
        if not read:
            return None

        steps = []
        for i, part in enumerate(read):
            part = part.strip()
            if not part:
                continue

            if i == 0:
                # Base: "module+offset" veya "0xADDR"
                if '+' in part:
                    mod, off = part.rsplit('+', 1)
                    try:
                        offset = int(off, 16)
                    except ValueError:
                        return None
                    steps.append(('module', mod.strip(), offset))
                elif part.lower().startswith('0x'):
                    try:
                        addr = int(part, 16)
                    except ValueError:
                        return None
                    steps.append(('absolute', addr, 0))
                else:
                    # Modül tek başına (base)
                    steps.append(('module', part, 0))
            else:
                # Chain: "+offset"
                if part.startswith('+'):
                    try:
                        offset = int(part[1:], 16)
                    except ValueError:
                        return None
                    steps.append(('offset', offset, 0))
                elif part.lower().startswith('0x'):
                    try:
                        addr = int(part, 16)
                    except ValueError:
                        return None
                    steps.append(('absolute', addr, 0))
                else:
                    return None

        return steps

    # ---------- RESOLVE ----------
    def resolve(self, read):
        """read alanını gerçek adrese çevir"""
        if not self.open():
            return None

        steps = self.parse_read(read)
        if not steps:
            return None

        # İlk adım
        first = steps[0]
        if first[0] == 'module':
            base = self.find_module_base(first[1])
            if base is None:
                return None
            addr = base + first[2]
        elif first[0] == 'absolute':
            addr = first[1]
        else:
            return None

        # Zincir
        for step in steps[1:]:
            if step[0] == 'offset':
                ptr = self._read_ptr(addr)
                if ptr is None or ptr == 0:
                    return None
                addr = ptr + step[1]
            elif step[0] == 'absolute':
                addr = step[1]

        return addr

    def _read_ptr(self, address):
        """Pointer oku (x86: 4 byte, x64: 8 byte)"""
        size = 8 if self.is_64 else 4
        data = self._read_bytes(address, size)
        if not data:
            return None
        if self.is_64:
            return struct.unpack('<Q', data)[0]
        return struct.unpack('<I', data)[0]

    def _read_bytes(self, address, size):
        if not self.h_process:
            return None
        try:
            buf = ctypes.create_string_buffer(size)
            read = ctypes.c_size_t(0)
            ok = self.kernel32.ReadProcessMemory(
                self.h_process, ctypes.c_void_p(address),
                buf, size, ctypes.byref(read)
            )
            if ok and read.value == size:
                return buf.raw
        except Exception:
            pass
        return None

    def _write_bytes(self, address, data):
        if not self.h_process:
            return False
        try:
            buf = ctypes.create_string_buffer(data)
            written = ctypes.c_size_t(0)
            ok = self.kernel32.WriteProcessMemory(
                self.h_process, ctypes.c_void_p(address),
                buf, len(data), ctypes.byref(written)
            )
            return bool(ok and written.value == len(data))
        except Exception:
            return False

    # ---------- READ/WRITE VALUE ----------
    def read(self, address, value_type):
        if value_type == 'int':
            d = self._read_bytes(address, 4)
            return struct.unpack('<i', d)[0] if d else None
        elif value_type == 'int64':
            d = self._read_bytes(address, 8)
            return struct.unpack('<q', d)[0] if d else None
        elif value_type == 'float':
            d = self._read_bytes(address, 4)
            return struct.unpack('<f', d)[0] if d else None
        elif value_type == 'double':
            d = self._read_bytes(address, 8)
            return struct.unpack('<d', d)[0] if d else None
        elif value_type == 'byte':
            d = self._read_bytes(address, 1)
            return struct.unpack('<B', d)[0] if d else None
        elif value_type == 'string':
            d = self._read_bytes(address, 256)
            if d:
                return d.split(b'\x00')[0].decode('utf-8', errors='ignore')
        return None

    def write(self, address, value, value_type):
        try:
            if value_type == 'int':
                return self._write_bytes(address, struct.pack('<i', int(value)))
            elif value_type == 'int64':
                return self._write_bytes(address, struct.pack('<q', int(value)))
            elif value_type == 'float':
                return self._write_bytes(address, struct.pack('<f', float(value)))
            elif value_type == 'double':
                return self._write_bytes(address, struct.pack('<d', float(value)))
            elif value_type == 'byte':
                return self._write_bytes(address, struct.pack('<B', int(value) & 0xFF))
            elif value_type == 'string':
                return self._write_bytes(address, str(value).encode('utf-8') + b'\x00')
        except Exception:
            pass
        return False

    def read_entry(self, entry):
        """HTEntry'yi oku"""
        addr = self.resolve(entry.read)
        if addr is None:
            return None
        return self.read(addr, entry.type)

    def write_entry(self, entry, value=None):
        """HTEntry'ye yaz"""
        addr = self.resolve(entry.read)
        if addr is None:
            return False
        v = value if value is not None else entry.value
        return self.write(addr, v, entry.type)