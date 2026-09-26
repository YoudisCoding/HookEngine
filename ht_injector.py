#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — HT Injector v3.1
Assembly kod injection + hook yönetimi

FIX v3.1:
- Trampoline doğru implement edildi:
  [orijinal 5 byte] + [JMP target+5]  →  trampoline
  [JMP trampoline]                    →  target_addr
- x64 için absolute JMP (FF 25) — ±2GB limiti yok
- VirtualProtectEx restore ediliyor (eski protection geri yazılıyor)
"""

import ctypes
import ctypes.wintypes as wt
import struct

try:
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_MODE_64
    KEYSTONE_AVAILABLE = True
except ImportError:
    KEYSTONE_AVAILABLE = False

from ht.ht_resolver import HTResolver


MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_READ = 0x20
PAGE_READWRITE = 0x04


class HTInjector:
    """Kod injection motoru."""

    def __init__(self, pid, on_log=None):
        self.pid = pid
        self.on_log = on_log or (lambda msg: None)
        self.resolver = HTResolver(pid)
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.h_process = None
        self.is_64 = False
        self.hooks = {}

        if not KEYSTONE_AVAILABLE:
            self.log("[!] keystone not installed — injection disabled")
            self.log("    Install: pip install keystone-engine")

    def log(self, msg):
        self.on_log(msg)

    def open(self):
        if self.h_process:
            return True
        PROCESS_ALL_ACCESS = 0x1FFFFF
        self.h_process = self.kernel32.OpenProcess(
            PROCESS_ALL_ACCESS, False, self.pid
        )
        if not self.h_process:
            return False
        try:
            h = self.kernel32.OpenProcess(0x1000, False, self.pid)
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
            try:
                self.kernel32.CloseHandle(self.h_process)
            except Exception:
                pass
            self.h_process = None

    # ==================== ASSEMBLE ====================
    def assemble(self, asm_code):
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
        if not self.h_process:
            return None
        addr = self.kernel32.VirtualAllocEx(
            self.h_process, None, size,
            MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE
        )
        return addr if addr else None

    def _free(self, addr):
        if not self.h_process or not addr:
            return False
        return bool(self.kernel32.VirtualFreeEx(
            self.h_process, ctypes.c_void_p(addr), 0, MEM_RELEASE
        ))

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
        """Returns previous protection or 0 on failure."""
        if not self.h_process:
            return 0
        try:
            old = wt.DWORD(0)
            ok = self.kernel32.VirtualProtectEx(
                self.h_process, ctypes.c_void_p(addr), size,
                protection, ctypes.byref(old)
            )
            return old.value if ok else 0
        except Exception:
            return 0

    # ==================== JMP ENCODING ====================
    def _make_jmp(self, from_addr, to_addr, instruction_len=5):
        """
        from_addr → to_addr atlayan JMP üret.
        x86: E9 rel32 (5 byte)
        x64: rel32 sığıyorsa E9, sığmıyorsa FF 25 (14 byte)
        Dönüş: (bytes, instruction_len_actual)
        """
        if not self.is_64:
            rel = to_addr - (from_addr + 5)
            if -2**31 <= rel < 2**31:
                return b'\xE9' + struct.pack('<i', rel), 5
            raise ValueError("x86 JMP rel32 out of range")

        # x64: önce rel32 dene
        rel = to_addr - (from_addr + 5)
        if -2**31 <= rel < 2**31:
            return b'\xE9' + struct.pack('<i', rel), 5

        # Absolute: FF 25 00 00 00 00 [addr64]  → 14 byte
        return b'\xFF\x25\x00\x00\x00\x00' + struct.pack('<Q', to_addr), 14

    # ==================== HOOK ====================
    def install_hook(self, hook_id, hook_target, asm_code):
        """
        Basit inline hook:
        1. target_addr'dan N byte orijinal kod oku
        2. Trampoline ayır: [orijinal N byte] + [JMP target+N]
        3. target_addr'a [JMP trampoline] yaz
        """
        if not KEYSTONE_AVAILABLE:
            self.log("[!] Keystone gerekli")
            return False
        if not self.open():
            self.log("[!] Process açılamadı")
            return False

        target_addr = self._resolve_target(hook_target)
        if not target_addr:
            self.log(f"[!] Hook target resolve failed: {hook_target}")
            return False

        new_code = self.assemble(asm_code)
        if not new_code:
            self.log("[!] Assembly failed")
            return False

        # Ne kadar orijinal byte okuyacağız?
        # x64 absolute JMP 14 byte ise trampoline "far" olabilir; basitlik için
        # önce kendi kodumuzu target'a yakın bir yere koyalım — bu sayede E9 (5 byte) yeter.
        # Strateji: VirtualAllocEx ile target yakınında yer bulmayı dene.
        # Basit + sağlam: rel32 menzilinde alloc. Olmazsa 14-byte absolute kullan.

        # 1) Orijinal kodu oku — 5 byte (E9 rel32 için yeter)
        #    Eğer absolute gerekiyorsa 14 byte okumak zorundayız (kısmi instruction okuma riski).
        #    Modern Windows'ta 2GB içinde alloc başarılı olur — E9 yolu izlenecek.
        trampoline_size = 5

        original = self._read(target_addr, trampoline_size)
        if not original or len(original) < trampoline_size:
            self.log("[!] Could not read original code")
            return False

        # 2) Trampoline için yakın yer ayır
        new_mem = self._alloc_near(target_addr, len(new_code) + 32)
        if not new_mem:
            self.log("[!] Could not allocate near memory")
            return False

        # 3) Trampoline içeriği: [orijinal 5 byte] + [JMP target+5]
        back_addr = target_addr + trampoline_size
        back_jmp_bytes, _ = self._make_jmp(
            new_mem + len(original), back_addr
        )
        trampoline = original + back_jmp_bytes

        if not self._write(new_mem, trampoline):
            self._free(new_mem)
            self.log("[!] Write trampoline failed")
            return False

        # 4) Hook'un kendisi: [JMP new_mem]
        hook_jmp, hook_len = self._make_jmp(target_addr, new_mem)
        if hook_len > trampoline_size:
            self._free(new_mem)
            self.log(f"[!] Hook JMP too long ({hook_len} > {trampoline_size})")
            return False

        # 5) Sayfayı RWX yap
        old_protect = self._protect(target_addr, trampoline_size, PAGE_EXECUTE_READWRITE)
        if not old_protect:
            self._free(new_mem)
            self.log("[!] VirtualProtectEx failed")
            return False

        # 6) Hook'u yaz
        if not self._write(target_addr, hook_jmp):
            self._protect(target_addr, trampoline_size, old_protect)
            self._free(new_mem)
            self.log("[!] Write hook JMP failed")
            return False

        # 7) Protection'ı geri koy
        self._protect(target_addr, trampoline_size, old_protect)

        self.hooks[hook_id] = {
            'target_addr': target_addr,
            'original': original,
            'trampoline_addr': new_mem,
            'hook_size': trampoline_size,
            'old_protect': old_protect,
        }
        self.log(f"[+] Hook installed: {hook_target} @ 0x{target_addr:X}")
        return True

    def _alloc_near(self, target_addr, size):
        """target_addr'ın ±2GB menzilinde bellek ayır (E9 için)."""
        if not self.is_64:
            return self._alloc(size)

        # Önce rastgele dene
        addr = self._alloc(size)
        if addr:
            rel = addr - (target_addr + 5)
            if -2**31 <= rel < 2**31:
                return addr
            self._free(addr)

        # Step scan: target çevresinde 64KB hizalı dene
        base = target_addr & ~0xFFFF
        for delta in range(0x10000, 0x7FFF0000, 0x10000):
            for cand in (base + delta, base - delta):
                if cand <= 0 or cand > 0x7FFFFFFFFFFF:
                    continue
                result = self.kernel32.VirtualAllocEx(
                    self.h_process,
                    ctypes.c_void_p(cand),
                    size,
                    MEM_COMMIT | MEM_RESERVE,
                    PAGE_EXECUTE_READWRITE,
                )
                if result:
                    rel = result - (target_addr + 5)
                    if -2**31 <= rel < 2**31:
                        return result
                    self._free(result)
        return None

    def remove_hook(self, hook_id):
        info = self.hooks.pop(hook_id, None)
        if not info:
            return False
        try:
            old = self._protect(
                info['target_addr'], info['hook_size'], PAGE_EXECUTE_READWRITE
            )
            self._write(info['target_addr'], info['original'])
            if old:
                self._protect(info['target_addr'], info['hook_size'], old)
            self._free(info['trampoline_addr'])
            self.log(f"[+] Hook removed: {hook_id}")
            return True
        except Exception as e:
            self.log(f"[!] remove_hook error: {e}")
            return False

    def remove_all_hooks(self):
        for hid in list(self.hooks.keys()):
            self.remove_hook(hid)

    # ==================== UTILITY ====================
    def _resolve_target(self, hook_target):
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