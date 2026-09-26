#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — Fast Multi-Threaded Scanner v3.1
VirtualQueryEx + ThreadPool

FIX v3.1:
- Zero-size region sonsuz loop guard'ı eklendi
- Kullanılmayan _results_lock kaldırıldı
- search_bytes_parallel daha temiz lock kullanımı
"""

import ctypes
import ctypes.wintypes as wt
import struct
import threading
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


PROCESS_ALL_ACCESS = 0x1FFFFF
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008

MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
MEM_IMAGE = 0x1000000
MEM_MAPPED = 0x40000

PAGE_NOACCESS = 0x01
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE = 0x10
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_GUARD = 0x100

READABLE_PROTECTIONS = (
    PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY |
    PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
)

MAX_ADDRESS_64 = 0x7FFFFFFFFFFF
MAX_ADDRESS_32 = 0x7FFFFFFF

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_ulonglong),
        ("AllocationBase", ctypes.c_ulonglong),
        ("AllocationProtect", wt.DWORD),
        ("__alignment1", wt.DWORD),
        ("RegionSize", ctypes.c_ulonglong),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
        ("__alignment2", wt.DWORD),
    ]


class MEMORY_BASIC_INFORMATION32(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", wt.DWORD),
        ("AllocationBase", wt.DWORD),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize", wt.DWORD),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
    ]


class FastScanner:

    CHUNK_SIZE = 256 * 1024
    MAX_RESULTS = 500_000

    def __init__(self, pid, workers=None, is_64=None):
        self.pid = pid
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.h_process = None
        self.is_64 = is_64 if is_64 is not None else self._detect_arch()
        self.workers = workers or min(16, (os.cpu_count() or 4) * 2)
        self.cancelled = False
        self._setup_ctypes()

    def _setup_ctypes(self):
        k = self.kernel32
        k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k.OpenProcess.restype = wt.HANDLE
        k.CloseHandle.argtypes = [wt.HANDLE]
        k.CloseHandle.restype = wt.BOOL
        k.ReadProcessMemory.argtypes = [
            wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
        ]
        k.ReadProcessMemory.restype = wt.BOOL
        k.VirtualQueryEx.argtypes = [
            wt.HANDLE, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_size_t
        ]
        k.VirtualQueryEx.restype = ctypes.c_size_t
        k.IsWow64Process.argtypes = [wt.HANDLE, ctypes.POINTER(wt.BOOL)]
        k.IsWow64Process.restype = wt.BOOL

    def _detect_arch(self):
        try:
            h = self.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, self.pid
            )
            if not h:
                return True
            b = wt.BOOL()
            ok = self.kernel32.IsWow64Process(h, ctypes.byref(b))
            self.kernel32.CloseHandle(h)
            if ok and b.value:
                return False
            return True
        except Exception:
            return True

    def open(self):
        if self.h_process:
            return True
        access = (PROCESS_ALL_ACCESS | PROCESS_QUERY_INFORMATION |
                  PROCESS_QUERY_LIMITED_INFORMATION |
                  PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION)
        self.h_process = self.kernel32.OpenProcess(access, False, self.pid)
        if not self.h_process:
            self.h_process = self.kernel32.OpenProcess(
                PROCESS_QUERY_INFORMATION | PROCESS_QUERY_LIMITED_INFORMATION |
                PROCESS_VM_READ, False, self.pid
            )
        return bool(self.h_process)

    def close(self):
        if self.h_process:
            try:
                self.kernel32.CloseHandle(self.h_process)
            except Exception:
                pass
            self.h_process = None

    # ==================== REGION ENUM ====================
    def enum_regions(self, include_image=True, include_mapped=False,
                     only_writable=False):
        regions = []
        if not self.h_process:
            return regions

        if self.is_64:
            mbi = MEMORY_BASIC_INFORMATION64()
            mbi_size = ctypes.sizeof(MEMORY_BASIC_INFORMATION64)
            max_addr = MAX_ADDRESS_64
        else:
            mbi = MEMORY_BASIC_INFORMATION32()
            mbi_size = ctypes.sizeof(MEMORY_BASIC_INFORMATION32)
            max_addr = MAX_ADDRESS_32

        addr = 0
        consecutive_fail = 0

        while addr < max_addr:
            ret = self.kernel32.VirtualQueryEx(
                self.h_process,
                ctypes.c_void_p(addr),
                ctypes.byref(mbi),
                mbi_size,
            )
            if ret == 0:
                consecutive_fail += 1
                if consecutive_fail > 4:
                    break
                addr += 0x1000
                continue
            consecutive_fail = 0

            base = mbi.BaseAddress
            size = mbi.RegionSize
            state = mbi.State
            protect = mbi.Protect
            mtype = mbi.Type

            # GUARD: size == 0 ise addr ilerlemez → sonsuz loop
            if not size or size <= 0:
                addr = base + 0x1000
                continue

            if state != MEM_COMMIT:
                addr = base + size
                continue

            if protect & PAGE_GUARD or protect & PAGE_NOACCESS:
                addr = base + size
                continue

            if not (protect & READABLE_PROTECTIONS):
                addr = base + size
                continue

            if mtype == MEM_IMAGE and not include_image:
                addr = base + size
                continue
            if mtype == MEM_MAPPED and not include_mapped:
                addr = base + size
                continue

            if only_writable and not (
                protect & (PAGE_READWRITE | PAGE_EXECUTE_READWRITE | PAGE_WRITECOPY)
            ):
                addr = base + size
                continue

            regions.append((base, size, protect, mtype))
            addr = base + size

        return regions

    # ==================== READ ====================
    def _read_chunk(self, addr, size):
        try:
            buf = ctypes.create_string_buffer(size)
            read = ctypes.c_size_t(0)
            ok = self.kernel32.ReadProcessMemory(
                self.h_process,
                ctypes.c_void_p(addr),
                buf, size,
                ctypes.byref(read),
            )
            if ok and read.value == size:
                return buf.raw
            if ok and read.value > 0:
                return buf.raw[:read.value]
        except Exception:
            pass
        return None

    # ==================== SEARCH ====================
    def search_bytes(self, pattern: bytes, mask: bytes = None,
                     on_progress=None, cancel_check=None):
        if not self.open():
            return []

        regions = self.enum_regions()
        total = len(regions)
        results = []
        plen = len(pattern)

        for idx, (base, size, protect, mtype) in enumerate(regions):
            if self.cancelled or (cancel_check and cancel_check()):
                break

            offset = 0
            while offset < size:
                chunk = min(self.CHUNK_SIZE, size - offset)
                data = self._read_chunk(base + offset, chunk)
                if data:
                    pos = self._find_pattern(data, pattern, mask)
                    for p in pos:
                        results.append(base + offset + p)
                        if len(results) >= self.MAX_RESULTS:
                            self.close()
                            return results
                offset += chunk

            if on_progress:
                try:
                    on_progress(idx + 1, total)
                except Exception:
                    pass

        self.close()
        return results

    @staticmethod
    def _find_pattern(data, pattern, mask):
        results = []
        plen = len(pattern)
        dlen = len(data)

        if mask is None:
            start = 0
            while True:
                pos = data.find(pattern, start)
                if pos == -1:
                    break
                results.append(pos)
                start = pos + 1
                if len(results) > 10000:
                    break
        else:
            for i in range(dlen - plen + 1):
                match = True
                for j in range(plen):
                    if mask[j] and data[i + j] != pattern[j]:
                        match = False
                        break
                if match:
                    results.append(i)
                    if len(results) > 10000:
                        break
        return results

    # ==================== TYPED SCAN ====================
    def search_int(self, value, size=4, signed=True):
        if size == 4:
            fmt = '<i' if signed else '<I'
        elif size == 2:
            fmt = '<h' if signed else '<H'
        elif size == 8:
            fmt = '<q' if signed else '<Q'
        elif size == 1:
            fmt = '<b' if signed else '<B'
        else:
            return []
        return self.search_bytes(struct.pack(fmt, int(value)))

    def search_float(self, value):
        return self.search_bytes(struct.pack('<f', float(value)))

    def search_double(self, value):
        return self.search_bytes(struct.pack('<d', float(value)))

    def search_string(self, text, encoding='utf-8', null_terminate=False):
        data = text.encode(encoding)
        if null_terminate:
            data += b'\x00'
        return self.search_bytes(data)

    def search_utf16(self, text):
        return self.search_bytes(text.encode('utf-16-le'))

    def search_aob(self, pattern_str):
        parts = pattern_str.split()
        pattern = bytearray()
        mask = bytearray()
        for p in parts:
            if p in ('??', '?', 'xx', 'XX'):
                pattern.append(0)
                mask.append(0)
            else:
                pattern.append(int(p, 16))
                mask.append(0xFF)
        return self.search_bytes(bytes(pattern), bytes(mask))

    # ==================== PARALLEL ====================
    def search_bytes_parallel(self, pattern: bytes, mask: bytes = None,
                              on_progress=None, cancel_check=None):
        if not self.open():
            return []

        regions = self.enum_regions()
        total = len(regions)
        if total == 0:
            self.close()
            return []

        results = []
        lock = threading.Lock()
        counter = {'done': 0}

        def scan_region(region):
            if self.cancelled or (cancel_check and cancel_check()):
                return []
            base, size, protect, mtype = region
            local = []
            offset = 0
            while offset < size:
                if self.cancelled:
                    break
                chunk = min(self.CHUNK_SIZE, size - offset)
                data = self._read_chunk(base + offset, chunk)
                if data:
                    pos = self._find_pattern(data, pattern, mask)
                    for p in pos:
                        local.append(base + offset + p)
                        if len(local) > 5000:
                            break
                offset += chunk
                if len(local) > 5000:
                    break
            return local

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = {ex.submit(scan_region, r): r for r in regions}
            for fut in as_completed(futures):
                try:
                    local = fut.result()
                except Exception:
                    local = []
                if local:
                    with lock:
                        results.extend(local)
                with lock:
                    counter['done'] += 1
                    if on_progress:
                        try:
                            on_progress(counter['done'], total)
                        except Exception:
                            pass

        self.close()
        return results

    # ==================== VALUE READ ====================
    def read_value(self, addr, value_type):
        if not self.open():
            return None
        try:
            if value_type == 'int':
                d = self._read_chunk(addr, 4)
                return struct.unpack('<i', d)[0] if d else None
            if value_type == 'uint':
                d = self._read_chunk(addr, 4)
                return struct.unpack('<I', d)[0] if d else None
            if value_type == 'int64':
                d = self._read_chunk(addr, 8)
                return struct.unpack('<q', d)[0] if d else None
            if value_type == 'uint64':
                d = self._read_chunk(addr, 8)
                return struct.unpack('<Q', d)[0] if d else None
            if value_type == 'float':
                d = self._read_chunk(addr, 4)
                return struct.unpack('<f', d)[0] if d else None
            if value_type == 'double':
                d = self._read_chunk(addr, 8)
                return struct.unpack('<d', d)[0] if d else None
            if value_type == 'byte':
                d = self._read_chunk(addr, 1)
                return d[0] if d else None
            if value_type == 'word':
                d = self._read_chunk(addr, 2)
                return struct.unpack('<H', d)[0] if d else None
        except Exception:
            pass
        return None

    def read_many(self, addresses, value_type):
        if not self.open():
            return []
        out = []
        for a in addresses:
            v = self.read_value(a, value_type)
            if v is not None:
                out.append((a, v))
        return out

    def read_many_parallel(self, addresses, value_type):
        if not self.open():
            return []

        def read_one(a):
            v = self.read_value(a, value_type)
            return (a, v) if v is not None else None

        out = []
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            for res in ex.map(read_one, addresses):
                if res:
                    out.append(res)
        return out