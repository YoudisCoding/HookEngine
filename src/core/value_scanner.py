#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOUD ULTRA VALUE SCANNER v3.0
Aşırı Güçlü Bellek Tarama — AOB, Pointer, Filtreleme
"""

import struct
import threading
from ctypes import *
from ctypes.wintypes import *
from core.memory_engine import MemoryEngine

class UltraValueScanner:
    def __init__(self, pid):
        self.pid = pid
        self.memory_engine = MemoryEngine(pid)
        self.found_addresses = []
        self.scan_results = []

    # ==================== TEMEL TARAMA ====================

    def scan(self, scan_type, value_str):
        self.found_addresses = []

        try:
            if scan_type == "INT":
                target = struct.pack('<i', int(value_str))
                return self._scan_binary(target, 4, scan_type, value_str)

            elif scan_type == "FLOAT":
                target = struct.pack('<f', float(value_str))
                return self._scan_binary(target, 4, scan_type, value_str)

            elif scan_type == "DOUBLE":
                target = struct.pack('<d', float(value_str))
                return self._scan_binary(target, 8, scan_type, value_str)

            elif scan_type == "STRING":
                target = value_str.encode('utf-8')
                return self._scan_binary(target, len(target), scan_type, value_str)

            elif scan_type == "BYTE":
                target = struct.pack('<B', int(value_str, 16))
                return self._scan_binary(target, 1, scan_type, value_str)

            elif scan_type == "AOB":
                return self.scan_aob(value_str)

            elif scan_type == "POINTER":
                return self.scan_pointer(int(value_str, 16))

        except Exception:
            pass

        return []

    def _scan_binary(self, target_bytes, target_size, scan_type, original_value=None):
        results = []
        address = 0
        chunk_size = 256 * 1024

        self.memory_engine.open()

        while address < 0x7FFFFFFF:
            data = self.memory_engine.read_bytes(address, chunk_size)

            if data:
                position = data.find(target_bytes)

                while position != -1:
                    addr = address + position

                    if scan_type == "INT":
                        value = struct.unpack('<i', data[position:position+4])[0]
                    elif scan_type == "FLOAT":
                        value = struct.unpack('<f', data[position:position+4])[0]
                    elif scan_type == "DOUBLE":
                        value = struct.unpack('<d', data[position:position+8])[0]
                    elif scan_type == "STRING":
                        value = original_value if original_value is not None else ""
                    elif scan_type == "BYTE":
                        value = data[position]
                    else:
                        value = 0

                    results.append((addr, value))
                    position = data.find(target_bytes, position + 1)

                    if len(results) >= 100000:
                        self.memory_engine.close()
                        return results

            address += chunk_size

        self.memory_engine.close()
        return results
    
    # ==================== AOB SCAN ====================
    
    def scan_aob(self, pattern_str):
        """Array of Bytes tarama — hex pattern"""
        results = []
        
        try:
            # Pattern'i parse et
            pattern = self._parse_aob_pattern(pattern_str)
            
            if not pattern:
                return results
            
            address = 0
            chunk_size = 128 * 1024
            
            self.memory_engine.open()
            
            while address < 0x7FFFFFFF:
                data = self.memory_engine.read_bytes(address, chunk_size)
                
                if data:
                    matches = self._find_aob_match(data, pattern)
                    
                    for match_offset in matches:
                        addr = address + match_offset
                        results.append((addr, pattern_str))
                    
                    if len(results) >= 10000:
                        break
            
                address += chunk_size
            
            self.memory_engine.close()
            
        except Exception as e:
            pass
        
        return results
    
    def _parse_aob_pattern(self, pattern_str):
        """AOB pattern'ini parse et — '48 8B ?? ?? E9' gibi"""
        pattern = []
        
        try:
            parts = pattern_str.replace('?', '?').split()
            
            for part in parts:
                if part == '??' or part == '?':
                    pattern.append(None)
                else:
                    pattern.append(int(part, 16))
        except:
            return []
        
        return pattern
    
    def _find_aob_match(self, data, pattern):
        """AOB pattern'ini data içinde bul"""
        matches = []
        pattern_len = len(pattern)
        
        for i in range(len(data) - pattern_len):
            match = True
            
            for j in range(pattern_len):
                if pattern[j] is not None and data[i+j] != pattern[j]:
                    match = False
                    break
            
            if match:
                matches.append(i)
        
        return matches
    
    # ==================== POINTER SCAN ====================
    
    def scan_pointer(self, target_address, max_offset=0x1000, max_depth=3):
        """Pointer tarama — hedef adrese işaret eden pointer'ları bul"""
        results = []
        
        try:
            address = 0
            chunk_size = 256 * 1024
            ptr_size = 8  # 64-bit varsayılan
            
            self.memory_engine.open()
            
            while address < 0x7FFFFFFF:
                data = self.memory_engine.read_bytes(address, chunk_size)
                
                if data:
                    # 8 byte'lık pointer'ları tara
                    for i in range(0, len(data) - 8, 8):
                        ptr_value = struct.unpack('<Q', data[i:i+8])[0]
                        
                        # Pointer hedefe işaret ediyor mu?
                        if target_address - max_offset <= ptr_value <= target_address + max_offset:
                            results.append((address + i, ptr_value))
                    
                    if len(results) >= 10000:
                        break
                
                address += chunk_size
            
            self.memory_engine.close()
            
        except Exception as e:
            pass
        
        return results
    
    # ==================== FİLTRELEME ====================
    
    def scan_increased(self, previous_results):
        """Değeri artan adresleri filtrele"""
        filtered = []
        
        self.memory_engine.open()
        
        for addr, old_value in previous_results:
            try:
                current_value = self.memory_engine.read_int(addr)
                
                if current_value is not None and current_value > old_value:
                    filtered.append((addr, current_value))
            except:
                pass
        
        self.memory_engine.close()
        return filtered
    
    def scan_decreased(self, previous_results):
        """Değeri azalan adresleri filtrele"""
        filtered = []
        
        self.memory_engine.open()
        
        for addr, old_value in previous_results:
            try:
                current_value = self.memory_engine.read_int(addr)
                
                if current_value is not None and current_value < old_value:
                    filtered.append((addr, current_value))
            except:
                pass
        
        self.memory_engine.close()
        return filtered
    
    def scan_unchanged(self, previous_results):
        """Değeri değişmeyen adresleri filtrele"""
        filtered = []
        
        self.memory_engine.open()
        
        for addr, old_value in previous_results:
            try:
                current_value = self.memory_engine.read_int(addr)
                
                if current_value is not None and current_value == old_value:
                    filtered.append((addr, current_value))
            except:
                pass
        
        self.memory_engine.close()
        return filtered
    
    def scan_changed(self, previous_results):
        """Değeri değişen adresleri filtrele"""
        filtered = []
        
        self.memory_engine.open()
        
        for addr, old_value in previous_results:
            try:
                current_value = self.memory_engine.read_int(addr)
                
                if current_value is not None and current_value != old_value:
                    filtered.append((addr, current_value))
            except:
                pass
        
        self.memory_engine.close()
        return filtered