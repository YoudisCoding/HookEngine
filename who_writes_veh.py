#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — Who Writes (Hardware Breakpoint) v3.1

FIX v3.1:
- Eski VEH iskeleti KALDIRILDI (process crash ediyordu)
- DebugActiveProcess + WaitForDebugEvent tabanlı güvenli debugger
- Hardware breakpoint (DR0) exception yakalanır, process ölmez
- HWBP action: WRITE / READWRITE / EXECUTE
- Basit ve sağlam: tek thread async loop
"""

import ctypes
import ctypes.wintypes as wt
import threading
import time

# ==================== CONSTANTS ====================
PROCESS_ALL_ACCESS = 0x1FFFFF

DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7
OUTPUT_DEBUG_STRING_EVENT = 8
RIP_EVENT = 9

EXCEPTION_SINGLE_STEP = 0x80000004
EXCEPTION_BREAKPOINT = 0x80000003

INFINITE = 0xFFFFFFFF

# Hardware breakpoint condition codes (DR7 RWn)
HW_ACCESS_BREAK = 0     # EXECUTE
HW_WRITE_BREAK = 1      # WRITE
HW_IO_BREAK = 2
HW_READWRITE_BREAK = 3  # READ/WRITE

# Length codes (DR7 LENn)
HW_LEN_1 = 0b00
HW_LEN_2 = 0b01
HW_LEN_8 = 0b10
HW_LEN_4 = 0b11


# ==================== STRUCTS ====================
class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ("dwDebugEventCode", wt.DWORD),
        ("dwProcessId", wt.DWORD),
        ("dwThreadId", wt.DWORD),
        ("u", ctypes.c_byte * 160),
    ]


# 64-bit CONTEXT offsets
CONTEXT64_SIZE = 1232
CONTEXT64_RIP_OFFSET = 0xF8
CONTEXT64_EFLAGS_OFFSET = 0x68
CONTEXT64_DR0_OFFSET = 0x48
CONTEXT64_DR6_OFFSET = 0x68
CONTEXT64_DR7_OFFSET = 0x70

CONTEXT_AMD64 = 0x00100000
CONTEXT_AMD64_DEBUG_REGISTERS = CONTEXT_AMD64 | 0x00000010
CONTEXT_AMD64_FULL = CONTEXT_AMD64 | 0x0000000B


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


TH32CS_SNAPTHREAD = 0x00000004


class WhoWritesHWBP:
    """
    Hardware breakpoint + DebugActiveProcess.
    Process'in debugger'ı olur, EXCEPTION_SINGLE_STEP yakalar.
    Process çökmez, çünkü debugger exception'ı handle eder.
    """

    def __init__(self, pid, address, size=4,
                 action=HW_WRITE_BREAK, on_event=None, debug=False):
        self.pid = pid
        self.address = address
        self.size = size
        self.action = action
        self.on_event = on_event or (lambda rec: None)
        self.debug = debug

        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self._setup_ctypes()

        self.running = False
        self._thread = None
        self.records = []
        self._armed = False

    def _setup_ctypes(self):
        k = self.kernel32
        k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k.OpenProcess.restype = wt.HANDLE
        k.OpenThread.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k.OpenThread.restype = wt.HANDLE
        k.CloseHandle.argtypes = [wt.HANDLE]
        k.CloseHandle.restype = wt.BOOL

        k.DebugActiveProcess.argtypes = [wt.DWORD]
        k.DebugActiveProcess.restype = wt.BOOL
        k.DebugActiveProcessStop.argtypes = [wt.DWORD]
        k.DebugActiveProcessStop.restype = wt.BOOL

        k.WaitForDebugEvent.argtypes = [ctypes.c_void_p, wt.DWORD]
        k.WaitForDebugEvent.restype = wt.BOOL
        k.ContinueDebugEvent.argtypes = [wt.DWORD, wt.DWORD, wt.DWORD]
        k.ContinueDebugEvent.restype = wt.BOOL

        k.GetThreadContext.argtypes = [wt.HANDLE, ctypes.c_void_p]
        k.GetThreadContext.restype = wt.BOOL
        k.SetThreadContext.argtypes = [wt.HANDLE, ctypes.c_void_p]
        k.SetThreadContext.restype = wt.BOOL

        k.SuspendThread.argtypes = [wt.HANDLE]
        k.SuspendThread.restype = wt.DWORD
        k.ResumeThread.argtypes = [wt.HANDLE]
        k.ResumeThread.restype = wt.DWORD

        k.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
        k.CreateToolhelp32Snapshot.restype = wt.HANDLE
        k.Thread32First.argtypes = [wt.HANDLE, ctypes.c_void_p]
        k.Thread32First.restype = wt.BOOL
        k.Thread32Next.argtypes = [wt.HANDLE, ctypes.c_void_p]
        k.Thread32Next.restype = wt.BOOL

    def _dbg(self, msg):
        if self.debug:
            print(f"[HWBP] {msg}", flush=True)

    def _get_threads(self):
        threads = []
        snap = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
        if not snap or snap == ctypes.c_void_p(-1).value:
            return threads
        te = THREADENTRY32()
        te.dwSize = ctypes.sizeof(THREADENTRY32)
        if self.kernel32.Thread32First(snap, ctypes.byref(te)):
            while True:
                if te.th32OwnerProcessID == self.pid:
                    threads.append(te.th32ThreadID)
                if not self.kernel32.Thread32Next(snap, ctypes.byref(te)):
                    break
        self.kernel32.CloseHandle(snap)
        return threads

    def _set_dr(self, h_thread, enable):
        """DR0'ı set/clear et — debugger aktifken."""
        try:
            buf_size = CONTEXT64_SIZE
            dr0_off = CONTEXT64_DR0_OFFSET
            dr7_off = CONTEXT64_DR7_OFFSET

            buf = ctypes.create_string_buffer(buf_size)
            ctypes.memset(buf, 0, buf_size)

            flags = ctypes.c_uint32(CONTEXT_AMD64_DEBUG_REGISTERS)
            ctypes.memmove(buf, ctypes.byref(flags), 4)

            ok = self.kernel32.GetThreadContext(h_thread, buf)
            if not ok:
                return False

            # DR0 = address
            addr_val = ctypes.c_uint64(self.address)
            ctypes.memmove(ctypes.byref(buf, dr0_off),
                           ctypes.byref(addr_val), 8)

            # DR7
            if enable:
                len_bits = {1: HW_LEN_1, 2: HW_LEN_2,
                            4: HW_LEN_4, 8: HW_LEN_8}.get(self.size, HW_LEN_4)
                rw_bits = self.action & 0x3
                dr7 = ((rw_bits << 16) | (len_bits << 18) | 1)
            else:
                dr7 = 0

            cur = ctypes.c_uint64(0)
            ctypes.memmove(ctypes.byref(cur), ctypes.byref(buf, dr7_off), 8)
            cur.value = (cur.value & ~0xF0003) | dr7
            ctypes.memmove(ctypes.byref(buf, dr7_off), ctypes.byref(cur), 8)

            ctypes.memmove(buf, ctypes.byref(flags), 4)

            return bool(self.kernel32.SetThreadContext(h_thread, buf))
        except Exception as e:
            self._dbg(f"DR set fail: {e}")
            return False

    def _arm_all(self):
        armed = 0
        for tid in self._get_threads():
            h = self.kernel32.OpenThread(0x1F03FF, False, tid)
            if not h:
                continue
            try:
                if self.kernel32.SuspendThread(h) != 0xFFFFFFFF:
                    if self._set_dr(h, True):
                        armed += 1
                    self.kernel32.ResumeThread(h)
            finally:
                self.kernel32.CloseHandle(h)
        self._dbg(f"Armed {armed} threads")
        return armed

    def _disarm_all(self):
        for tid in self._get_threads():
            h = self.kernel32.OpenThread(0x1F03FF, False, tid)
            if not h:
                continue
            try:
                if self.kernel32.SuspendThread(h) != 0xFFFFFFFF:
                    self._set_dr(h, False)
                    self.kernel32.ResumeThread(h)
            finally:
                self.kernel32.CloseHandle(h)

    def _capture_rip(self, tid):
        h = self.kernel32.OpenThread(0x1F03FF, False, tid)
        if not h:
            return None
        try:
            buf = ctypes.create_string_buffer(CONTEXT64_SIZE)
            ctypes.memset(buf, 0, CONTEXT64_SIZE)
            flags = ctypes.c_uint32(CONTEXT_AMD64_FULL)
            ctypes.memmove(buf, ctypes.byref(flags), 4)
            if not self.kernel32.GetThreadContext(h, buf):
                return None
            import struct as _s
            rip_bytes = buf.raw[CONTEXT64_RIP_OFFSET:CONTEXT64_RIP_OFFSET + 8]
            return _s.unpack('<Q', rip_bytes)[0]
        finally:
            self.kernel32.CloseHandle(h)

    def _debug_loop(self):
        """WaitForDebugEvent döngüsü — exception'ları yakalar."""
        evt = DEBUG_EVENT()

        while self.running:
            if not self.kernel32.WaitForDebugEvent(ctypes.byref(evt), 100):
                continue

            code = evt.dwDebugEventCode
            cont_status = DBG_CONTINUE

            try:
                if code == EXCEPTION_DEBUG_EVENT:
                    # exception kayıt bilgisini oku (ilk 4 byte = ExceptionCode)
                    exc_code = ctypes.c_uint32.from_buffer(evt.u, 0).value
                    first_chance = ctypes.c_uint32.from_buffer(evt.u, 4).value

                    if exc_code == EXCEPTION_SINGLE_STEP and first_chance:
                        rip = self._capture_rip(evt.dwThreadId)
                        if rip is not None:
                            rec = {
                                'tid': evt.dwThreadId,
                                'rip': rip,
                                'address': self.address,
                                'time': time.time(),
                            }
                            self.records.append(rec)
                            try:
                                self.on_event(rec)
                            except Exception as e:
                                self._dbg(f"on_event exception: {e}")
                        # DR6'yı temizle ve devam et
                        self._clear_dr6(evt.dwThreadId)
                        cont_status = DBG_CONTINUE
                    elif exc_code == EXCEPTION_BREAKPOINT:
                        cont_status = DBG_CONTINUE
                    else:
                        cont_status = DBG_EXCEPTION_NOT_HANDLED
            except Exception as e:
                self._dbg(f"debug loop exception: {e}")

            try:
                self.kernel32.ContinueDebugEvent(
                    evt.dwProcessId, evt.dwThreadId, cont_status
                )
            except Exception:
                pass

    def _clear_dr6(self, tid):
        """DR6'yı sıfırla — breakpoint tekrar tetiklenebilsin."""
        h = self.kernel32.OpenThread(0x1F03FF, False, tid)
        if not h:
            return
        try:
            buf = ctypes.create_string_buffer(CONTEXT64_SIZE)
            ctypes.memset(buf, 0, CONTEXT64_SIZE)
            flags = ctypes.c_uint32(CONTEXT_AMD64_DEBUG_REGISTERS)
            ctypes.memmove(buf, ctypes.byref(flags), 4)
            if self.kernel32.GetThreadContext(h, buf):
                zero = ctypes.c_uint64(0)
                ctypes.memmove(ctypes.byref(buf, CONTEXT64_DR6_OFFSET),
                               ctypes.byref(zero), 8)
                ctypes.memmove(buf, ctypes.byref(flags), 4)
                self.kernel32.SetThreadContext(h, buf)
        finally:
            self.kernel32.CloseHandle(h)

    def start(self):
        if self.running:
            return False

        # 1) Debugger ol
        if not self.kernel32.DebugActiveProcess(self.pid):
            err = ctypes.get_last_error()
            raise RuntimeError(f"DebugActiveProcess failed — err={err} (admin? başka debugger?)")

        self.running = True

        # 2) Debug loop'u başlat
        self._thread = threading.Thread(target=self._debug_loop, daemon=True)
        self._thread.start()

        # 3) DebugActiveProcess tamamlanınca initial breakpoint gelir,
        #    debug loop onu handle eder. Kısa bir bekle.
        time.sleep(0.3)

        # 4) Tüm thread'lere DR0 kur
        armed = self._arm_all()
        self._armed = armed > 0
        return self._armed

    def stop(self):
        self.running = False
        try:
            if self._armed:
                self._disarm_all()
        except Exception:
            pass
        try:
            self.kernel32.DebugActiveProcessStop(self.pid)
        except Exception:
            pass
        if self._thread:
            try:
                self._thread.join(timeout=1.5)
            except Exception:
                pass
            self._thread = None
        self._armed = False

    def get_records(self):
        return list(self.records)

    def clear(self):
        self.records = []