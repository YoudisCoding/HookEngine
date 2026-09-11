#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOUD WHO WRITES — Hardware breakpoint debugger in Python
Runs in background thread, reports every instruction that writes to target address
"""

import ctypes
import ctypes.wintypes as wt
import struct
import threading
import time

# ==================== WINDOWS CONSTANTS ====================
PROCESS_ALL_ACCESS = 0x1F0FFF
TH32CS_SNAPTHREAD = 0x00000004
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

DBG_CONTINUE = 0x00010002

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7
OUTPUT_DEBUG_STRING_EVENT = 8

EXCEPTION_SINGLE_STEP = 0x80000004
EXCEPTION_BREAKPOINT = 0x80000003

CONTEXT_AMD64 = 0x00100000
CONTEXT_i386 = 0x00010000
CONTEXT64_DEBUG_REGISTERS = CONTEXT_AMD64 | 0x10
CONTEXT64_FULL = CONTEXT_AMD64 | 0x1 | 0x2 | 0x8 | 0x10
CONTEXT32_DEBUG_REGISTERS = CONTEXT_i386 | 0x10
CONTEXT32_FULL = CONTEXT_i386 | 0x1 | 0x2 | 0x4 | 0x8 | 0x10


# ==================== STRUCTS ====================
class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
        ("th32ThreadID", wt.DWORD), ("th32OwnerProcessID", wt.DWORD),
        ("tpBasePri", ctypes.c_long), ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", wt.DWORD),
    ]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD),
        ("th32ProcessID", wt.DWORD), ("GlblcntUsage", wt.DWORD),
        ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE),
        ("szModule", ctypes.c_char * 256), ("szExePath", ctypes.c_char * 260),
    ]


class XMM_SAVE_AREA32(ctypes.Structure):
    _fields_ = [("dummy", ctypes.c_byte * 512)]


class M128A(ctypes.Structure):
    _fields_ = [("Low", ctypes.c_ulonglong), ("High", ctypes.c_longlong)]


class CONTEXT64(ctypes.Structure):
    _pack_ = 16
    _fields_ = [
        ("P1Home", ctypes.c_ulonglong), ("P2Home", ctypes.c_ulonglong),
        ("P3Home", ctypes.c_ulonglong), ("P4Home", ctypes.c_ulonglong),
        ("P5Home", ctypes.c_ulonglong), ("P6Home", ctypes.c_ulonglong),
        ("ContextFlags", wt.DWORD), ("MxCsr", wt.DWORD),
        ("SegCs", wt.WORD), ("SegDs", wt.WORD), ("SegEs", wt.WORD),
        ("SegFs", wt.WORD), ("SegGs", wt.WORD), ("SegSs", wt.WORD),
        ("EFlags", wt.DWORD),
        ("Dr0", ctypes.c_ulonglong), ("Dr1", ctypes.c_ulonglong),
        ("Dr2", ctypes.c_ulonglong), ("Dr3", ctypes.c_ulonglong),
        ("Dr6", ctypes.c_ulonglong), ("Dr7", ctypes.c_ulonglong),
        ("Rax", ctypes.c_ulonglong), ("Rcx", ctypes.c_ulonglong),
        ("Rdx", ctypes.c_ulonglong), ("Rbx", ctypes.c_ulonglong),
        ("Rsp", ctypes.c_ulonglong), ("Rbp", ctypes.c_ulonglong),
        ("Rsi", ctypes.c_ulonglong), ("Rdi", ctypes.c_ulonglong),
        ("R8", ctypes.c_ulonglong), ("R9", ctypes.c_ulonglong),
        ("R10", ctypes.c_ulonglong), ("R11", ctypes.c_ulonglong),
        ("R12", ctypes.c_ulonglong), ("R13", ctypes.c_ulonglong),
        ("R14", ctypes.c_ulonglong), ("R15", ctypes.c_ulonglong),
        ("Rip", ctypes.c_ulonglong),
        ("FltSave", XMM_SAVE_AREA32),
        ("VectorRegister", M128A * 26),
        ("VectorControl", ctypes.c_ulonglong),
        ("DebugControl", ctypes.c_ulonglong),
        ("LastBranchToRip", ctypes.c_ulonglong),
        ("LastBranchFromRip", ctypes.c_ulonglong),
        ("LastExceptionToRip", ctypes.c_ulonglong),
        ("LastExceptionFromRip", ctypes.c_ulonglong),
    ]


class CONTEXT32(ctypes.Structure):
    _fields_ = [
        ("ContextFlags", wt.DWORD),
        ("Dr0", wt.DWORD), ("Dr1", wt.DWORD), ("Dr2", wt.DWORD), ("Dr3", wt.DWORD),
        ("Dr6", wt.DWORD), ("Dr7", wt.DWORD),
        ("FloatSave", ctypes.c_byte * 112),
        ("SegGs", wt.DWORD), ("SegFs", wt.DWORD), ("SegEs", wt.DWORD), ("SegDs", wt.DWORD),
        ("Edi", wt.DWORD), ("Esi", wt.DWORD), ("Ebx", wt.DWORD), ("Edx", wt.DWORD),
        ("Ecx", wt.DWORD), ("Eax", wt.DWORD), ("Ebp", wt.DWORD), ("Eip", wt.DWORD),
        ("SegCs", wt.DWORD), ("EFlags", wt.DWORD), ("Esp", wt.DWORD), ("SegSs", wt.DWORD),
        ("ExtendedRegisters", ctypes.c_byte * 512),
    ]


class EXCEPTION_RECORD(ctypes.Structure):
    _fields_ = [
        ("ExceptionCode", wt.DWORD), ("ExceptionFlags", wt.DWORD),
        ("ExceptionRecord", ctypes.c_void_p), ("ExceptionAddress", ctypes.c_void_p),
        ("NumberParameters", wt.DWORD), ("ExceptionInformation", ctypes.c_void_p * 15),
    ]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("ExceptionRecord", EXCEPTION_RECORD), ("dwFirstChance", wt.DWORD)]


class CREATE_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("hThread", wt.HANDLE), ("lpThreadLocalBase", ctypes.c_void_p),
                ("lpStartAddress", ctypes.c_void_p)]


class CREATE_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hFile", wt.HANDLE), ("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
        ("lpBaseOfImage", ctypes.c_void_p), ("dwDebugInfoFileOffset", wt.DWORD),
        ("nDebugInfoSize", wt.DWORD), ("lpThreadLocalBase", ctypes.c_void_p),
        ("lpStartAddress", ctypes.c_void_p), ("lpImageName", ctypes.c_void_p),
        ("fUnicode", wt.WORD),
    ]


class EXIT_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("dwExitCode", wt.DWORD)]


class LOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hFile", wt.HANDLE), ("lpBaseOfDll", ctypes.c_void_p),
        ("dwDebugInfoFileOffset", wt.DWORD), ("nDebugInfoSize", wt.DWORD),
        ("lpImageName", ctypes.c_void_p), ("fUnicode", wt.WORD),
    ]


class OUTPUT_DEBUG_STRING_INFO(ctypes.Structure):
    _fields_ = [("lpDebugStringData", ctypes.c_void_p),
                ("fUnicode", wt.WORD), ("nDebugStringLength", wt.WORD)]


class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [
        ("Exception", EXCEPTION_DEBUG_INFO),
        ("CreateThread", CREATE_THREAD_DEBUG_INFO),
        ("CreateProcessInfo", CREATE_PROCESS_DEBUG_INFO),
        ("ExitThread", EXIT_THREAD_DEBUG_INFO),
        ("LoadDll", LOAD_DLL_DEBUG_INFO),
        ("OutputDebugString", OUTPUT_DEBUG_STRING_INFO),
        ("_pad", ctypes.c_byte * 160),
    ]


class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ("dwDebugEventCode", wt.DWORD), ("dwProcessId", wt.DWORD),
        ("dwThreadId", wt.DWORD), ("u", DEBUG_EVENT_UNION),
    ]


# ==================== DEBUGGER CLASS ====================
class WhoWritesDebugger:
    def __init__(self, pid, address, on_event=None):
        self.pid = pid
        self.address = address
        self.on_event = on_event  # callback(dict)
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.h_process = None
        self.is_64 = True
        self.dr_index = 0
        self.running = False
        self.thread = None
        self.records = []

    # -------- helpers --------
    def _is_wow64(self):
        h = self.kernel32.OpenProcess(0x0400, False, self.pid)
        if not h:
            return False
        b = wt.BOOL()
        self.kernel32.IsWow64Process(h, ctypes.byref(b))
        self.kernel32.CloseHandle(h)
        return bool(b.value)

    def _get_threads(self):
        threads = []
        snap = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
        if snap in (-1, 0):
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

    def _get_modules(self):
        mods = []
        snap = self.kernel32.CreateToolhelp32Snapshot(
            TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid)
        if snap in (-1, 0):
            return mods
        me = MODULEENTRY32()
        me.dwSize = ctypes.sizeof(MODULEENTRY32)
        if self.kernel32.Module32First(snap, ctypes.byref(me)):
            while True:
                try:
                    base = ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value
                    name = me.szModule.decode('utf-8', errors='ignore')
                    mods.append((name, base or 0, me.modBaseSize))
                except Exception:
                    pass
                if not self.kernel32.Module32Next(snap, ctypes.byref(me)):
                    break
        self.kernel32.CloseHandle(snap)
        return mods

    def _find_module(self, address):
        for name, base, size in self._get_modules():
            if base <= address < base + size:
                return name, base, address - base
        return None

    def _read_mem(self, address, size):
        h = self.kernel32.OpenProcess(0x0010, False, self.pid)
        if not h:
            return None
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t(0)
        ok = self.kernel32.ReadProcessMemory(
            h, ctypes.c_void_p(address), buf, size, ctypes.byref(read))
        self.kernel32.CloseHandle(h)
        if ok and read.value == size:
            return buf.raw
        return None

    # -------- breakpoint --------
    def _set_bp(self, tid):
        THREAD_GET_CONTEXT = 0x0008
        THREAD_SET_CONTEXT = 0x0010
        THREAD_SUSPEND_RESUME = 0x0002
        hThread = self.kernel32.OpenThread(
            THREAD_GET_CONTEXT | THREAD_SET_CONTEXT | THREAD_SUSPEND_RESUME,
            False, tid)
        if not hThread:
            return False
        self.kernel32.SuspendThread(hThread)

        if self.is_64:
            ctx = CONTEXT64()
            ctx.ContextFlags = CONTEXT64_DEBUG_REGISTERS
        else:
            ctx = CONTEXT32()
            ctx.ContextFlags = CONTEXT32_DEBUG_REGISTERS

        if not self.kernel32.GetThreadContext(hThread, ctypes.byref(ctx)):
            self.kernel32.ResumeThread(hThread)
            self.kernel32.CloseHandle(hThread)
            return False

        if self.dr_index == 0: ctx.Dr0 = self.address
        elif self.dr_index == 1: ctx.Dr1 = self.address
        elif self.dr_index == 2: ctx.Dr2 = self.address
        elif self.dr_index == 3: ctx.Dr3 = self.address

        dr7 = ctx.Dr7
        dr7 |= (1 << (self.dr_index * 2))
        shift = 16 + (self.dr_index * 4)
        dr7 &= ~(0xF << shift)
        dr7 |= (0x1 << shift)
        dr7 |= (0x3 << (shift + 2))
        ctx.Dr7 = dr7

        ok = self.kernel32.SetThreadContext(hThread, ctypes.byref(ctx))
        self.kernel32.ResumeThread(hThread)
        self.kernel32.CloseHandle(hThread)
        return bool(ok)

    def _apply_bp_all(self):
        for tid in self._get_threads():
            self._set_bp(tid)

    # -------- single step handler --------
    def _handle_step(self, dbg):
        tid = dbg.dwThreadId
        THREAD_GET_CONTEXT = 0x0008
        THREAD_SET_CONTEXT = 0x0010
        hThread = self.kernel32.OpenThread(
            THREAD_GET_CONTEXT | THREAD_SET_CONTEXT, False, tid)
        if not hThread:
            return

        if self.is_64:
            ctx = CONTEXT64()
            ctx.ContextFlags = CONTEXT64_FULL
        else:
            ctx = CONTEXT32()
            ctx.ContextFlags = CONTEXT32_FULL

        if self.kernel32.GetThreadContext(hThread, ctypes.byref(ctx)):
            rip = ctx.Rip if self.is_64 else ctx.Eip
            instr = self._read_mem(rip, 16)
            mod = self._find_module(rip)
            mod_name, mod_base, mod_off = mod if mod else ("unknown", 0, 0)

            # decode EAX/RCX value at time of write
            regs = {}
            if self.is_64:
                regs = {
                    'RAX': ctx.Rax, 'RCX': ctx.Rcx, 'RDX': ctx.Rdx,
                    'RBX': ctx.Rbx, 'RSP': ctx.Rsp, 'RBP': ctx.Rbp,
                    'RSI': ctx.Rsi, 'RDI': ctx.Rdi,
                }
            else:
                regs = {
                    'EAX': ctx.Eax, 'ECX': ctx.Ecx, 'EDX': ctx.Edx,
                    'EBX': ctx.Ebx, 'ESP': ctx.Esp, 'EBP': ctx.Ebp,
                    'ESI': ctx.Esi, 'EDI': ctx.Edi,
                }

            rec = {
                'thread': tid,
                'rip': rip,
                'module': mod_name,
                'base': mod_base,
                'offset': mod_off,
                'instruction': instr.hex() if instr else '',
                'regs': regs,
                'target': self.address,
            }
            self.records.append(rec)

            if self.on_event:
                try:
                    self.on_event(rec)
                except Exception:
                    pass

            # disable BP temporarily to avoid recursion
            ctx.Dr7 &= ~(1 << (self.dr_index * 2))
            self.kernel32.SetThreadContext(hThread, ctypes.byref(ctx))

        self.kernel32.CloseHandle(hThread)

    # -------- debug loop --------
    def _loop(self):
        dbg = DEBUG_EVENT()
        bp_seen = False
        while self.running:
            ok = self.kernel32.WaitForDebugEvent(ctypes.byref(dbg), 100)
            if not ok:
                continue

            status = DBG_CONTINUE
            code = dbg.dwDebugEventCode

            if code == CREATE_PROCESS_DEBUG_EVENT:
                hf = dbg.u.CreateProcessInfo.hFile
                if hf:
                    self.kernel32.CloseHandle(hf)

            elif code == CREATE_THREAD_DEBUG_EVENT:
                if not bp_seen:
                    self._set_bp(dbg.dwThreadId)

            elif code == EXIT_PROCESS_DEBUG_EVENT:
                self.running = False

            elif code == LOAD_DLL_DEBUG_EVENT:
                hf = dbg.u.LoadDll.hFile
                if hf:
                    self.kernel32.CloseHandle(hf)

            elif code == EXCEPTION_DEBUG_EVENT:
                exc = dbg.u.Exception.ExceptionRecord.ExceptionCode
                if exc == EXCEPTION_BREAKPOINT:
                    bp_seen = True
                elif exc == EXCEPTION_SINGLE_STEP:
                    self._handle_step(dbg)
                    self._apply_bp_all()

            self.kernel32.ContinueDebugEvent(dbg.dwProcessId, dbg.dwThreadId, status)

    # -------- public --------
    def start(self):
        self.is_64 = not self._is_wow64()
        self.h_process = self.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, self.pid)
        if not self.h_process:
            raise RuntimeError("OpenProcess failed — run as Administrator")

        if not self.kernel32.DebugActiveProcess(self.pid):
            self.kernel32.CloseHandle(self.h_process)
            raise RuntimeError("DebugActiveProcess failed — run as Administrator")

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

        time.sleep(0.5)
        self._apply_bp_all()
        return True

    def stop(self):
        self.running = False
        time.sleep(0.3)
        try:
            self.kernel32.DebugActiveProcessStop(self.pid)
        except Exception:
            pass
        try:
            if self.h_process:
                self.kernel32.CloseHandle(self.h_process)
        except Exception:
            pass