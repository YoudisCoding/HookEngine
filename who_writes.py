#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — Who Writes (User-Mode) v3.1
Polling + thread snapshot.

FIX v3.1:
- PROCESS_ALL_ACCESS doğru değer (0x1FFFFF)
- Snapshot ve okuma yarışlarına lock eklendi
- Windows 11 için ek access flag'leri
"""

import ctypes
import ctypes.wintypes as wt
import struct
import threading
import time
from datetime import datetime

# ==================== CONSTANTS ====================
PROCESS_ALL_ACCESS = 0x1FFFFF
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_SUSPEND_RESUME = 0x0800

THREAD_SUSPEND_RESUME = 0x0002
THREAD_GET_CONTEXT = 0x0008
THREAD_SET_CONTEXT = 0x0010
THREAD_QUERY_INFORMATION = 0x0040
THREAD_ACCESS = (THREAD_SUSPEND_RESUME |
                 THREAD_GET_CONTEXT |
                 THREAD_SET_CONTEXT |
                 THREAD_QUERY_INFORMATION)

TH32CS_SNAPTHREAD = 0x00000004
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

# 32-bit CONTEXT
CONTEXT32_EIP_OFFSET = 0xB8
CONTEXT32_SIZE = 716

# 64-bit CONTEXT
CONTEXT64_RIP_OFFSET = 0xF8
CONTEXT64_SIZE = 1232

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ThreadID", wt.DWORD),
        ("th32OwnerProcessID", wt.DWORD),
        ("tpBasePri", ctypes.c_long),
        ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", wt.DWORD),
    ]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("th32ModuleID", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD),
        ("ProccntUsage", wt.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wt.DWORD),
        ("hModule", wt.HMODULE),
        ("szModule", ctypes.c_char * 256),
        ("szExePath", ctypes.c_char * 260),
    ]


class WhoWrites:
    """Polling-based memory watcher."""

    VALUE_SIZES = {
        'byte': 1, 'int8': 1, 'uint8': 1,
        'word': 2, 'int16': 2, 'uint16': 2,
        'dword': 4, 'int': 4, 'uint': 4,
        'int32': 4, 'uint32': 4, 'float': 4,
        'qword': 8, 'int64': 8, 'uint64': 8, 'double': 8,
    }

    VALUE_FORMATS = {
        'byte': '<B', 'int8': '<b', 'uint8': '<B',
        'word': '<H', 'int16': '<h', 'uint16': '<H',
        'dword': '<I', 'int': '<i', 'uint': '<I',
        'int32': '<i', 'uint32': '<I', 'float': '<f',
        'qword': '<Q', 'int64': '<q', 'uint64': '<Q', 'double': '<d',
    }

    def __init__(self, pid, address, value_type='int', interval_ms=20,
                 on_event=None, debug=False):
        self.pid = pid
        self.address = address
        self.value_type = (value_type or 'int').lower()
        self.interval_ms = max(1, int(interval_ms))
        self.on_event = on_event or (lambda rec: None)
        self.debug = debug

        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self._setup_ctypes()

        self.h_process = None
        self.is_64 = False
        self.running = False
        self.thread = None

        self.last_value = None
        self.records = []
        self._module_cache = None
        self._snapshot_lock = threading.Lock()
        self._read_lock = threading.Lock()

        self._size = self.VALUE_SIZES.get(self.value_type, 4)
        self._fmt = self.VALUE_FORMATS.get(self.value_type)

        self._snapshot_count = 0
        self._read_count = 0
        self._error_count = 0

    def _setup_ctypes(self):
        k = self.kernel32
        try:
            k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
            k.OpenProcess.restype = wt.HANDLE

            k.OpenThread.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
            k.OpenThread.restype = wt.HANDLE

            k.SuspendThread.argtypes = [wt.HANDLE]
            k.SuspendThread.restype = wt.DWORD

            k.ResumeThread.argtypes = [wt.HANDLE]
            k.ResumeThread.restype = wt.DWORD

            k.GetThreadContext.argtypes = [wt.HANDLE, ctypes.c_void_p]
            k.GetThreadContext.restype = wt.BOOL

            try:
                k.Wow64GetThreadContext.argtypes = [wt.HANDLE, ctypes.c_void_p]
                k.Wow64GetThreadContext.restype = wt.BOOL
            except Exception:
                pass

            k.CloseHandle.argtypes = [wt.HANDLE]
            k.CloseHandle.restype = wt.BOOL

            k.ReadProcessMemory.argtypes = [
                wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
            ]
            k.ReadProcessMemory.restype = wt.BOOL

            k.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
            k.CreateToolhelp32Snapshot.restype = wt.HANDLE

            k.Module32First.argtypes = [wt.HANDLE, ctypes.c_void_p]
            k.Module32First.restype = wt.BOOL

            k.Module32Next.argtypes = [wt.HANDLE, ctypes.c_void_p]
            k.Module32Next.restype = wt.BOOL

            k.Thread32First.argtypes = [wt.HANDLE, ctypes.c_void_p]
            k.Thread32First.restype = wt.BOOL

            k.Thread32Next.argtypes = [wt.HANDLE, ctypes.c_void_p]
            k.Thread32Next.restype = wt.BOOL

            k.IsWow64Process.argtypes = [wt.HANDLE, ctypes.POINTER(wt.BOOL)]
            k.IsWow64Process.restype = wt.BOOL
        except Exception as e:
            self._dbg(f"argtypes setup FAIL: {e}")

    def _dbg(self, msg):
        if self.debug:
            try:
                ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                print(f"[SNAP {ts}] {msg}", flush=True)
            except Exception:
                pass

    def _open(self):
        try:
            self.h_process = self.kernel32.OpenProcess(
                PROCESS_ALL_ACCESS, False, self.pid
            )
        except Exception as e:
            self._dbg(f"OpenProcess exception: {e}")
            self.h_process = None

        if not self.h_process:
            try:
                access = (PROCESS_QUERY_INFORMATION |
                          PROCESS_QUERY_LIMITED_INFORMATION |
                          PROCESS_VM_READ |
                          PROCESS_VM_WRITE |
                          PROCESS_VM_OPERATION |
                          PROCESS_SUSPEND_RESUME)
                self.h_process = self.kernel32.OpenProcess(access, False, self.pid)
            except Exception:
                self.h_process = None

        if not self.h_process:
            err = ctypes.get_last_error()
            self._dbg(f"OpenProcess FAIL err={err}")
            return False

        try:
            h = self.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, self.pid
            )
            if h:
                b = wt.BOOL()
                if self.kernel32.IsWow64Process(h, ctypes.byref(b)):
                    self.is_64 = not bool(b.value)
                self.kernel32.CloseHandle(h)
        except Exception as e:
            self._dbg(f"IsWow64Process exception: {e}")

        self._dbg(f"Process opened. PID={self.pid} is_64={self.is_64}")
        return True

    def _close(self):
        if self.h_process:
            try:
                self.kernel32.CloseHandle(self.h_process)
            except Exception:
                pass
            self.h_process = None
            self._dbg("Process handle closed")

    def _read_value(self):
        if not self.h_process:
            return None
        with self._read_lock:
            try:
                buf = ctypes.create_string_buffer(self._size)
                read = ctypes.c_size_t(0)
                ok = self.kernel32.ReadProcessMemory(
                    self.h_process,
                    ctypes.c_void_p(self.address),
                    buf, self._size,
                    ctypes.byref(read),
                )
                if not ok or read.value != self._size:
                    return None

                data = buf.raw
                if self._fmt:
                    try:
                        return struct.unpack(self._fmt, data)[0]
                    except struct.error:
                        return None
                else:
                    return data.hex()
            except Exception as e:
                self._error_count += 1
                if self._error_count < 5:
                    self._dbg(f"ReadProcessMemory exception: {e}")
                return None

    def _get_modules(self):
        if self._module_cache is not None:
            return self._module_cache

        mods = []
        snap = None
        try:
            snap = self.kernel32.CreateToolhelp32Snapshot(
                TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid,
            )
            if not snap or snap == INVALID_HANDLE_VALUE:
                return mods

            module = MODULEENTRY32()
            module.dwSize = ctypes.sizeof(MODULEENTRY32)

            if self.kernel32.Module32First(snap, ctypes.byref(module)):
                while True:
                    name = bytes(module.szModule).split(b'\0', 1)[0].decode(
                        errors='replace'
                    )
                    base = ctypes.cast(module.modBaseAddr, ctypes.c_void_p).value
                    size = int(module.modBaseSize)
                    if name and base and size:
                        mods.append((name, base, size))
                    if not self.kernel32.Module32Next(snap, ctypes.byref(module)):
                        break
        except Exception as e:
            self._dbg(f"Module enum exception: {e}")
        finally:
            if snap and snap != INVALID_HANDLE_VALUE:
                try:
                    self.kernel32.CloseHandle(snap)
                except Exception:
                    pass

        self._module_cache = sorted(mods, key=lambda item: item[1])
        return self._module_cache

    def _find_module(self, address):
        if not address:
            return None
        mods = self._get_modules()
        if not mods:
            return None

        lo, hi = 0, len(mods) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            name, base, size = mods[mid]
            if address < base:
                hi = mid - 1
            elif address >= base + size:
                lo = mid + 1
            else:
                return name, base, address - base
        return None

    def _get_threads(self):
        threads = []
        snap = None
        try:
            snap = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
            if not snap or snap == INVALID_HANDLE_VALUE:
                return threads

            te = THREADENTRY32()
            te.dwSize = ctypes.sizeof(THREADENTRY32)

            if self.kernel32.Thread32First(snap, ctypes.byref(te)):
                while True:
                    if te.th32OwnerProcessID == self.pid:
                        threads.append(te.th32ThreadID)
                    if not self.kernel32.Thread32Next(snap, ctypes.byref(te)):
                        break
        except Exception as e:
            self._dbg(f"Thread enum exception: {e}")
        finally:
            if snap and snap != INVALID_HANDLE_VALUE:
                try:
                    self.kernel32.CloseHandle(snap)
                except Exception:
                    pass

        return sorted(threads)

    def _capture_rip_raw(self, tid, use_full=False):
        h = None
        suspended = False
        try:
            h = self.kernel32.OpenThread(THREAD_ACCESS, False, tid)
            if not h:
                err = ctypes.get_last_error()
                return None, f"OpenThread err={err}"

            prev = self.kernel32.SuspendThread(h)
            if prev == 0xFFFFFFFF:
                err = ctypes.get_last_error()
                return None, f"SuspendThread err={err}"
            suspended = True

            if use_full:
                flags_value = 0x0010000B if self.is_64 else 0x00010007
            else:
                flags_value = 0x00100001 if self.is_64 else 0x00010001

            if self.is_64:
                buf_size = CONTEXT64_SIZE
                rip_offset = CONTEXT64_RIP_OFFSET
                fmt = '<Q'
            else:
                buf_size = CONTEXT32_SIZE
                rip_offset = CONTEXT32_EIP_OFFSET
                fmt = '<I'

            buf = ctypes.create_string_buffer(buf_size)
            ctypes.memset(buf, 0, buf_size)

            flags = ctypes.c_uint32(flags_value)
            ctypes.memmove(buf, ctypes.byref(flags), 4)

            if not self.is_64:
                try:
                    ok = self.kernel32.Wow64GetThreadContext(h, buf)
                    if not ok:
                        ok2 = self.kernel32.GetThreadContext(h, buf)
                        if not ok2:
                            err2 = ctypes.get_last_error()
                            return None, f"GetContext err={err2}"
                except Exception:
                    ok = self.kernel32.GetThreadContext(h, buf)
                    if not ok:
                        err = ctypes.get_last_error()
                        return None, f"GetThreadContext err={err}"
            else:
                ok = self.kernel32.GetThreadContext(h, buf)
                if not ok:
                    err = ctypes.get_last_error()
                    return None, f"GetThreadContext err={err}"

            try:
                rip_bytes = buf.raw[rip_offset:rip_offset + (8 if self.is_64 else 4)]
                rip = struct.unpack(fmt, rip_bytes)[0]
            except Exception as e:
                return None, f"unpack failed: {e}"

            return rip, None

        except Exception as e:
            return None, f"Exception: {e}"

        finally:
            if h:
                if suspended:
                    try:
                        self.kernel32.ResumeThread(h)
                    except Exception:
                        pass
                try:
                    self.kernel32.CloseHandle(h)
                except Exception:
                    pass

    def _snapshot_threads(self):
        with self._snapshot_lock:
            self._snapshot_count += 1
            results = []
            threads = self._get_threads()

            self._dbg(
                f"=== SNAPSHOT #{self._snapshot_count} START — "
                f"{len(threads)} threads, is_64={self.is_64} ==="
            )

            if not threads:
                self._dbg("No threads found")
                return results

            for tid in threads:
                rip, err = self._capture_rip_raw(tid, use_full=False)
                if err and "GetThreadContext" in err:
                    rip, err = self._capture_rip_raw(tid, use_full=True)

                if err:
                    self._dbg(f"tid={tid} FAIL: {err}")
                    continue

                if not rip:
                    self._dbg(f"tid={tid} RIP=0 (skip)")
                    continue

                mod = self._find_module(rip)
                if mod:
                    name, base, off = mod
                    results.append({
                        'tid': tid, 'rip': rip,
                        'module': name, 'base': base, 'offset': off,
                    })
                    self._dbg(f"tid={tid} RIP=0x{rip:X} → {name}+0x{off:X}")
                else:
                    results.append({
                        'tid': tid, 'rip': rip,
                        'module': 'unknown', 'base': 0, 'offset': rip,
                    })
                    self._dbg(f"tid={tid} RIP=0x{rip:X} (no module)")

            results.sort(key=lambda r: (r['module'].casefold(), r['offset']))
            self._dbg(
                f"=== SNAPSHOT #{self._snapshot_count} END — "
                f"captured {len(results)}/{len(threads)} ==="
            )
            return results

    def _loop(self):
        self.last_value = self._read_value()

        while self.running:
            value = self._read_value()
            self._read_count += 1

            if value is not None and self.last_value is not None:
                if value != self.last_value:
                    snap = self._snapshot_threads()
                    rec = {
                        'old': self.last_value,
                        'new': value,
                        'address': self.address,
                        'threads': snap,
                        'time': time.time(),
                        'seq': self._snapshot_count,
                    }
                    self.records.append(rec)
                    try:
                        self.on_event(rec)
                    except Exception as e:
                        self._dbg(f"on_event exception: {e}")

            self.last_value = value

            try:
                time.sleep(self.interval_ms / 1000.0)
            except Exception:
                pass

    def start(self):
        if self.running:
            return False
        if not self._open():
            raise RuntimeError("OpenProcess failed — run as Administrator")
        self._get_modules()
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.running = False
        if self.thread:
            try:
                self.thread.join(timeout=2.0)
            except Exception:
                pass
            self.thread = None
        self._close()

    def get_records(self):
        return list(self.records)

    def clear(self):
        self.records = []
        self._snapshot_count = 0
        self._read_count = 0
        self._error_count = 0

    def get_status(self):
        return {
            'running': self.running,
            'pid': self.pid,
            'address': self.address,
            'value_type': self.value_type,
            'interval_ms': self.interval_ms,
            'is_64': self.is_64,
            'records': len(self.records),
            'snapshots': self._snapshot_count,
            'reads': self._read_count,
            'errors': self._error_count,
        }