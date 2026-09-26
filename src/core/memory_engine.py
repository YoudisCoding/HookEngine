#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOUD MEMORY ENGINE v3.0
Aşırı Güçlü Bellek Motoru
"""

import struct
from ctypes import *
from ctypes.wintypes import *

class MemoryEngine:
    PROCESS_ALL_ACCESS = 0x1F0FFF
    PROCESS_VM_READ = 0x0010
    PROCESS_VM_WRITE = 0x0020
    PROCESS_VM_OPERATION = 0x0008
    PROCESS_QUERY_INFORMATION = 0x0400
    
    MEM_COMMIT = 0x1000
    MEM_RESERVE = 0x2000
    MEM_RELEASE = 0x8000
    
    PAGE_READWRITE = 0x04
    PAGE_EXECUTE_READWRITE = 0x40
    
    def __init__(self, pid):
        self.pid = pid
        self.kernel32 = windll.kernel32
        self.hProcess = None
    
    def open(self):
        if not self.hProcess:
            self.hProcess = self.kernel32.OpenProcess(
                self.PROCESS_ALL_ACCESS, False, self.pid
            )
        return self.hProcess != 0
    
    def close(self):
        if self.hProcess:
            self.kernel32.CloseHandle(self.hProcess)
            self.hProcess = None
    
    # ==================== OKUMA ====================
    
    def read_bytes(self, address, size):
        if not self.open():
            return None
        try:
            buffer = create_string_buffer(size)
            bytesRead = c_size_t()
            result = self.kernel32.ReadProcessMemory(
                self.hProcess, c_void_p(address), buffer, size, byref(bytesRead)
            )
            if result and bytesRead.value == size:
                return buffer.raw
            return None
        except:
            return None
    
    def read_int(self, address):
        data = self.read_bytes(address, 4)
        if data:
            return struct.unpack('<i', data)[0]
        return None
    
    def read_uint(self, address):
        data = self.read_bytes(address, 4)
        if data:
            return struct.unpack('<I', data)[0]
        return None
    
    def read_float(self, address):
        data = self.read_bytes(address, 4)
        if data:
            return struct.unpack('<f', data)[0]
        return None
    
    def read_double(self, address):
        data = self.read_bytes(address, 8)
        if data:
            return struct.unpack('<d', data)[0]
        return None
    
    def read_int64(self, address):
        data = self.read_bytes(address, 8)
        if data:
            return struct.unpack('<q', data)[0]
        return None
    
    def read_string(self, address, max_length=256):
        data = self.read_bytes(address, max_length)
        if data:
            return data.split(b'\x00')[0].decode('utf-8', errors='ignore')
        return None
    
    def read_byte(self, address):
        data = self.read_bytes(address, 1)
        if data:
            return struct.unpack('<B', data)[0]
        return None
    
    # ==================== YAZMA ====================
    
    def write_bytes(self, address, data):
        if not self.open():
            return False
        try:
            buffer = create_string_buffer(data)
            bytesWritten = c_size_t()
            result = self.kernel32.WriteProcessMemory(
                self.hProcess, c_void_p(address), buffer, len(data), byref(bytesWritten)
            )
            return result != 0 and bytesWritten.value == len(data)
        except:
            return False
    
    def write_int(self, address, value):
        return self.write_bytes(address, struct.pack('<i', value))
    
    def write_uint(self, address, value):
        return self.write_bytes(address, struct.pack('<I', value))
    
    def write_float(self, address, value):
        return self.write_bytes(address, struct.pack('<f', value))
    
    def write_double(self, address, value):
        return self.write_bytes(address, struct.pack('<d', value))
    
    def write_int64(self, address, value):
        return self.write_bytes(address, struct.pack('<q', value))
    
    def write_string(self, address, value):
        return self.write_bytes(address, value.encode('utf-8') + b'\x00')
    
    def write_byte(self, address, value):
        return self.write_bytes(address, struct.pack('<B', value & 0xFF))
    
    # ==================== BELLEK YÖNETİMİ ====================
    
    def allocate(self, size):
        if not self.open():
            return None
        try:
            addr = self.kernel32.VirtualAllocEx(
                self.hProcess, None, size,
                self.MEM_COMMIT | self.MEM_RESERVE,
                self.PAGE_EXECUTE_READWRITE
            )
            return addr if addr else None
        except:
            return None
    
    def free(self, address):
        if not self.open():
            return False
        try:
            result = self.kernel32.VirtualFreeEx(
                self.hProcess, address, 0, self.MEM_RELEASE
            )
            return result != 0
        except:
            return False
    
    def protect(self, address, size, protection):
        if not self.open():
            return False
        try:
            old_protect = c_ulong()
            result = self.kernel32.VirtualProtectEx(
                self.hProcess, c_void_p(address), size, protection, byref(old_protect)
            )
            return result != 0
        except:
            return False
    
    # ==================== PATTERN TARAMA ====================
    
    def find_pattern(self, pattern_bytes, start_address=0, max_address=0x7FFFFFFF):
        """Bellekte pattern ara"""
        results = []
        chunk_size = 128 * 1024
        address = start_address
        
        self.open()
        
        while address < max_address:
            data = self.read_bytes(address, chunk_size)
            
            if data:
                position = data.find(pattern_bytes)
                
                while position != -1:
                    results.append(address + position)
                    position = data.find(pattern_bytes, position + 1)
            
            address += chunk_size
        
        self.close()
        return results