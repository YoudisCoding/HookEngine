#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — HT Injector
Assembly kod injection + hook yönetimi
"""

import ctypes
import ctypes.wintypes as wt
import struct
import psutil

try:
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_MODE_64
    KEYSTONE_AVAILABLE = True
except ImportError:
    KEYSTONE_AVAILABLE = False

from ht.ht_resolver import HTResolver


class HTInjector:
    """Kod injection motoru"""

    def __init__(self, pid, on_log=None):
        self.pid = pid
        self.on_log = on_log or (lambda msg: None)
        self.resolver = HTResolver(pid)
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.h_process = None
        self.is_64 = False
        self.hooks = {}   # hook_id → {...}
        self._code_cave = None

        if not KEYSTONE_AVAILABLE:
            self.log("[!] keystone not installed — injection disabled")
            self.log("    Install: pip install keystone-engine")

    def log(self, msg):
        self.on_log(msg)

    def open(self):
        if self.h_process:
            return True
        PROCESS_ALL_ACCESS = 0x1F0FFF
        self.h_process = self.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, self.pid)
        if not self.h_process:
            return False
        # Bit kontrolü
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

    # ==================== ASSEMBLE ====================
    def assemble(self, asm_code):
        """Assembly kodunu byte'a çevir"""
        if not KEYSTONE_AVAILABLE:
            return None
        try:
            mode = KS_MODE_64 if self.is_64 else KS_MODE_32
            ks = Ks(KS_ARCH_X86, mode)
            encoding, count = ks.asm(asm_code)
            return bytes(encoding) if encoding else None
        except Exception as e:
            self.log(f"[Asm Error] {e}")
            return None

    # ==================== MEMORY ====================
    def _alloc(self, size):
        """Hedef process'te bellek ayır"""
        if not self.h_process:
            return None
        MEM_COMMIT = 0x1000
        MEM_RESERVE = 0x2000
        PAGE_EXECUTE_READWRITE = 0x40
        addr = self.kernel32.VirtualAllocEx(
            self.h_process, None, size,
            MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE
        )
        return addr if addr else None

    def _free(self, addr):
        if not self.h_process or not addr:
            return False
        MEM_RELEASE = 0x8000
        return bool(self.kernel32.VirtualFreeEx(self.h_process, addr, 0, MEM_RELEASE))

    def _write(self, addr, data):
        if not self.h_process:
            return False
        try:
            buf = ctypes.create_string_buffer(data)
            written = ctypes.c_size_t(0)
            ok = self.kernel32.WriteProcessMemory(
                self.h_process, ctypes.c_void_p(addr),
                buf, len(data), ctypes.byref(written)
            )
            return bool(ok and written.value == len(data))
        except Exception:
            return False

    def _read(self, addr, size):
        if not self.h_process:
            return None
        try:
            buf = ctypes.create_string_buffer(size)
            read = ctypes.c_size_t(0)
            ok = self.kernel32.ReadProcessMemory(
                self.h_process, ctypes.c_void_p(addr),
                buf, size, ctypes.byref(read)
            )
            if ok and read.value == size:
                return buf.raw
        except Exception:
            pass
        return None

    def _protect(self, addr, size, protection):
        if not self.h_process:
            return False
        try:
            old = wt.DWORD(0)
            ok = self.kernel32.VirtualProtectEx(
                self.h_process, ctypes.c_void_p(addr), size,
                protection, ctypes.byref(old)
            )
            return bool(ok)
        except Exception:
            return False

    # ==================== HOOK ====================
    def install_hook(self, hook_id, hook_target, asm_code):
        """Basit JMP hook"""
        if not KEYSTONE_AVAILABLE:
            self.log("[!] Keystone gerekli")
            return False
        if not self.open():
            self.log("[!] Process açılamadı")
            return False

        # Hedef adresi çöz
        target_addr = self._resolve_target(hook_target)
        if not target_addr:
            self.log(f"[!] Hook target resolve failed: {hook_target}")
            return False

        # Yeni kodu assemble et
        new_code = self.assemble(asm_code)
        if not new_code:
            self.log("[!] Assembly failed")
            return False

        # x86: 5 byte JMP, x64: 5 byte near JMP (32-bit displacement)
        trampoline_size = 5

        # Hedef adresi oku (orijinal kod)
        original = self._read(target_addr, trampoline_size)
        if not original:
            self.log("[!] Could not read original code")
            return False

        # Yeni kod bölgesi ayır
        new_mem = self._alloc(len(new_code) + 16)
        if not new_mem:
            self.log("[!] Could not allocate memory")
            return False

        # Yeni kod + geri JMP
        # JMP back: E9 [displacement]
        # displacement = target_addr + trampoline_size - (new_mem + len(new_code) + 5)
        back_jmp_addr = new_mem + len(new_code)
        disp = target_addr + trampoline_size - (back_jmp_addr + 5)
        back_jmp = b'\xE9' + struct.pack('<i', disp)
        full_code = new_code + back_jmp

        # Yeni kodu yaz
        if not self._write(new_mem, full_code):
            self._free(new_mem)
            self.log("[!] Write new code failed")
            return False

        # Orijinal kodu koru (protect)
        # PAGE_EXECUTE_READWRITE = 0x40
        self._protect(target_addr, trampoline_size, 0x40)

        # Hedef adrese JMP yaz
        jmp_disp = new_mem - (target_addr + 5)
        jmp = b'\xE9' + struct.pack('<i', jmp_disp)
        if not self._write(target_addr, jmp):
            self.log("[!] Write JMP failed")
            self._free(new_mem)
            return False

        # Kaydet
        self.hooks[hook_id] = {
            'target_addr': target_addr,
            'original': original,
            'new_mem': new_mem,
            'trampoline_size': trampoline_size,
            'new_mem_size': len(new_code) + 16,
        }

        self.log(f"[+] Hook installed: {hook_target} @ 0x{target_addr:X}")
        return True

    def remove_hook(self, hook_id):
        """Hook kaldır"""
        info = self.hooks.pop(hook_id, None)
        if not info:
            return False

        # Orijinal kodu geri yaz
        self._protect(info['target_addr'], info['trampoline_size'], 0x40)
        self._write(info['target_addr'], info['original'])

        # Yeni kodu serbest bırak
        self._free(info['new_mem'])

        self.log(f"[+] Hook removed: {hook_id}")
        return True

    def remove_all_hooks(self):
        for hid in list(self.hooks.keys()):
            self.remove_hook(hid)

    # ==================== UTILITY ====================
    def _resolve_target(self, hook_target):
        """hook_target formatı: 'module+offset' veya '0xADDR'"""
        if not hook_target:
            return None
        hook_target = hook_target.strip()
        if hook_target.lower().startswith('0x'):
            try:
                return int(hook_target, 16)
            except ValueError:
                return None
        if '+' in hook_target:
            mod, off = hook_target.rsplit('+', 1)
            try:
                offset = int(off, 16)
            except ValueError:
                return None
            base = self.resolver.find_module_base(mod.strip())
            if base is None:
                return None
            return base + offset
        return None