#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOUD PROFESSIONAL HOOK SCANNER v8.0
HIZLI SCAN + 4 MOD + HEDEF DLL + ÇÖKME KORUMASI
"""

import struct
import os
import sys
import time
import psutil
from ctypes import *
from ctypes.wintypes import *
from datetime import datetime

# ==================== SABİTLER ====================
PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_VM_READ = 0x0010
TH32CS_SNAPMODULE = 0x00000008
IMAGE_DOS_SIGNATURE = 0x5A4D
IMAGE_NT_SIGNATURE = 0x00004550

# ==================== STRUCTURE ====================
class MODULEENTRY32(Structure):
    _fields_ = [
        ("dwSize", c_uint32),
        ("th32ModuleID", c_uint32),
        ("th32ProcessID", c_uint32),
        ("GlblcntUsage", c_uint32),
        ("ProccntUsage", c_uint32),
        ("modBaseAddr", POINTER(c_byte)),
        ("modBaseSize", c_uint32),
        ("hModule", c_void_p),
        ("szModule", c_char * 256),
        ("szExePath", c_char * 260)
    ]


class ProfessionalHookScannerV5:
    def __init__(self, pid):
        self.pid = pid
        self.kernel32 = windll.kernel32
        self.hProcess = None
        self.modules = []
        self.process_bits = 64
        self.all_results = []
        self.output_file = None
        self.mode = "full"
        self.target_dll = None
    
    # ==================== MOD ====================
    
    def set_mode(self, mode):
        if mode in ["full", "important", "filtered", "memory", "quick"]:
            self.mode = mode
    
    def set_target_dll(self, dll_name):
        self.target_dll = dll_name.lower() if dll_name else None
    
    def should_skip_module(self, module_name):
        module_lower = module_name.lower()
        
        if self.target_dll:
            return module_lower != self.target_dll
        
        if self.mode in ["memory", "quick", "filtered"]:
            skip = [
                'ntdll.dll', 'kernel32.dll', 'kernelbase.dll', 'user32.dll',
                'gdi32.dll', 'advapi32.dll', 'ws2_32.dll', 'wininet.dll',
                'CoreUIComponents.dll', 'CoreMessaging.dll', 'combase.dll',
                'msvcrt.dll', 'ucrtbase.dll', 'shell32.dll', 'ole32.dll',
                'shlwapi.dll', 'rpcrt4.dll', 'sechost.dll', 'bcrypt.dll',
                'crypt32.dll', 'wintrust.dll', 'msvcp_win.dll', 'dwmapi.dll',
                'uxtheme.dll', 'd3d11.dll', 'dxgi.dll', 'dcomp.dll',
                'windows.storage.dll', 'powrprof.dll', 'profapi.dll',
                'cfgmgr32.dll', 'devobj.dll', 'win32u.dll', 'gdi32full.dll',
                'imm32.dll', 'clbcatq.dll', 'msctf.dll', 'oleaut32.dll',
                'setupapi.dll', 'version.dll', 'userenv.dll', 'wldp.dll',
                'nvwgf2umx.dll', 'nvgpucomp64.dll', 'nvppex.dll',
                'NvMessageBus.dll', 'NvMemMapStoragex.dll', 'gdiplus.dll',
                'OPENGL32.dll', 'd3d9.dll', 'EVR.dll', 'dxva2.dll',
                'dinput8.dll', 'textinputframework.dll', 'twinapi.appcore.dll',
                'inputhost.dll', 'devenum.dll', 'COMCTL32.dll',
                'DNSAPI.dll', 'IPHLPAPI.DLL', 'wshbth.dll', 'wtsapi32.dll',
                'winsta.dll', 'DSPARSE.dll', 'cryptbase.dll', 'SspiCli.dll',
                'ntmarta.dll', 'rsaenh.dll', 'directxdatabasehelper.dll',
                'drvstore.dll', 'fwpuclnt.dll', 'dhcpcsvc.DLL', 'winrnr.dll',
                'MFPlat.DLL', 'WindowsCodecs.dll', 'wintypes.dll', 'shcore.dll',
                'COMDLG32.dll', 'dbghelp.dll', 'imagehlp.dll', 'psapi.dll',
                'verifier.dll', 'UMPDC.dll', 'CRYPTSP.dll', 'ncrypt.dll',
                'NTASN1.dll', 'GPAPI.dll', 'kernel.appcore.dll', 'bcryptPrimitives.dll'
            ]
            return module_lower in skip
        
        return False
    
    def should_report_int3(self):
        return self.mode == "full"
    
    # ==================== SONUÇ ====================
    
    def add_result(self, text):
        if not text:
            return
        self.all_results.append(text)
        if self.output_file:
            try:
                self.output_file.write(text + '\n')
                self.output_file.flush()
            except:
                pass
    
    def add_separator(self, title="", char="=", width=70):
        if title:
            self.add_result("")
            self.add_result(char * width)
            self.add_result(title)
            self.add_result(char * width)
        else:
            self.add_result(char * width)
    
    # ==================== PROCESS ====================
    
    def open_process(self):
        try:
            if not self.hProcess:
                self.hProcess = self.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, self.pid)
            return self.hProcess != 0
        except:
            return False
    
    def close_process(self):
        try:
            if self.hProcess:
                self.kernel32.CloseHandle(self.hProcess)
                self.hProcess = None
        except:
            pass
    
    def get_process_bits(self):
        try:
            process_machine = c_ushort()
            native_machine = c_ushort()
            result = self.kernel32.IsWow64Process2(self.hProcess, byref(process_machine), byref(native_machine))
            if result:
                if native_machine.value == 0x8664:
                    self.process_bits = 64
                elif native_machine.value == 0x14C:
                    self.process_bits = 32
                return self.process_bits
        except:
            pass
        return 64
    
    # ==================== BELLEK OKUMA ====================
    
    def read_memory(self, address, size):
        if not self.hProcess or address == 0 or size <= 0:
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
    
    def read_uint32(self, address):
        data = self.read_memory(address, 4)
        return struct.unpack('<I', data)[0] if data else None
    
    def read_uint64(self, address):
        data = self.read_memory(address, 8)
        return struct.unpack('<Q', data)[0] if data else None
    
    def read_pointer(self, address):
        if self.process_bits == 64:
            return self.read_uint64(address)
        return self.read_uint32(address)
    
    def read_ascii_string(self, address, max_length=256):
        data = self.read_memory(address, max_length)
        if data:
            try:
                return data.split(b'\x00')[0].decode('ascii', errors='ignore')
            except:
                return ""
        return ""
    
    # ==================== MODÜL ====================
    
    def get_all_modules(self):
        self.modules = []
        if not self.hProcess:
            return self.modules
        try:
            snapshot = self.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, self.pid)
            if snapshot == -1 or snapshot == 0:
                return self.modules
            
            module_entry = MODULEENTRY32()
            module_entry.dwSize = sizeof(MODULEENTRY32)
            
            if self.kernel32.Module32First(snapshot, byref(module_entry)):
                while True:
                    try:
                        base_addr = cast(module_entry.modBaseAddr, c_void_p).value
                        module_info = {
                            'name': module_entry.szModule.decode('utf-8', errors='ignore'),
                            'path': module_entry.szExePath.decode('utf-8', errors='ignore'),
                            'base': base_addr or 0,
                            'size': module_entry.modBaseSize
                        }
                        if module_info['base'] > 0 and module_info['size'] > 0:
                            self.modules.append(module_info)
                    except:
                        pass
                    
                    if not self.kernel32.Module32Next(snapshot, byref(module_entry)):
                        break
            
            self.kernel32.CloseHandle(snapshot)
        except:
            pass
        return self.modules
    
    def get_module_by_address(self, address):
        if address == 0:
            return None
        for module in self.modules:
            try:
                if module['base'] <= address < module['base'] + module['size']:
                    return module
            except:
                pass
        return None
    
    def get_module_by_name(self, name):
        name_lower = name.lower()
        for module in self.modules:
            if module.get('name', '').lower() == name_lower:
                return module
        return None
    
    # ==================== PE PARSER ====================
    
    def parse_pe(self, module_base):
        result = {'valid': False, 'is_64': False, 'sections': [], 'data_directories': []}
        if module_base == 0:
            return result
        try:
            dos_data = self.read_memory(module_base, 64)
            if not dos_data:
                return result
            
            dos_magic = struct.unpack('<H', dos_data[0:2])[0]
            if dos_magic != IMAGE_DOS_SIGNATURE:
                return result
            
            e_lfanew = struct.unpack('<I', dos_data[0x3C:0x40])[0]
            nt_sig = self.read_uint32(module_base + e_lfanew)
            if nt_sig != IMAGE_NT_SIGNATURE:
                return result
            
            file_header_off = module_base + e_lfanew + 4
            file_header = self.read_memory(file_header_off, 20)
            if not file_header:
                return result
            
            machine = struct.unpack('<H', file_header[0:2])[0]
            num_sections = struct.unpack('<H', file_header[2:4])[0]
            size_opt = struct.unpack('<H', file_header[16:18])[0]
            is_64 = machine == 0x8664
            
            opt_off = file_header_off + 20
            opt_data = self.read_memory(opt_off, min(size_opt, 240))
            if not opt_data:
                return result
            
            if is_64:
                num_rva = struct.unpack('<I', opt_data[108:112])[0]
                dd_off = opt_off + 112
            else:
                num_rva = struct.unpack('<I', opt_data[92:96])[0]
                dd_off = opt_off + 96
            
            data_dirs = []
            for i in range(min(num_rva, 16)):
                dd = self.read_memory(dd_off + i * 8, 8)
                if dd:
                    data_dirs.append({
                        'va': struct.unpack('<I', dd[0:4])[0],
                        'size': struct.unpack('<I', dd[4:8])[0]
                    })
                else:
                    data_dirs.append({'va': 0, 'size': 0})
            
            section_off = opt_off + size_opt
            sections = []
            for i in range(min(num_sections, 100)):
                sh = self.read_memory(section_off + i * 40, 40)
                if sh:
                    name = sh[0:8].split(b'\x00')[0].decode('ascii', errors='ignore')
                    va = struct.unpack('<I', sh[12:16])[0]
                    size_raw = struct.unpack('<I', sh[16:20])[0]
                    sections.append({'name': name, 'va': va, 'size_raw': size_raw})
            
            result['valid'] = True
            result['is_64'] = is_64
            result['sections'] = sections
            result['data_directories'] = data_dirs
        except:
            pass
        return result
    
    # ==================== IAT PARSER ====================
    
    def parse_iat(self, module_base, pe_info):
        imports = []
        try:
            data_dirs = pe_info.get('data_directories', [])
            if len(data_dirs) <= 1:
                return imports
            
            import_dir = data_dirs[1]
            import_rva = import_dir.get('va', 0)
            if import_rva == 0:
                return imports
            
            import_va = module_base + import_rva
            is_64 = pe_info.get('is_64', True)
            thunk_size = 8 if is_64 else 4
            
            offset = 0
            while offset < 2000:
                desc = self.read_memory(import_va + offset, 20)
                if not desc:
                    break
                
                name_rva = struct.unpack('<I', desc[12:16])[0]
                first_thunk = struct.unpack('<I', desc[16:20])[0]
                if name_rva == 0 and first_thunk == 0:
                    break
                
                dll_name = self.read_ascii_string(module_base + name_rva)
                iat_va = module_base + first_thunk
                thunk_off = 0
                
                while thunk_off < 800:
                    func_addr = self.read_pointer(iat_va + thunk_off)
                    if not func_addr or func_addr == 0:
                        break
                    
                    if is_64:
                        is_ordinal = func_addr & 0x8000000000000000
                    else:
                        is_ordinal = func_addr & 0x80000000
                    
                    if is_ordinal:
                        func_name = f"Ordinal_{func_addr & 0xFFFF}"
                        function_address = None
                    else:
                        function_address = func_addr
                        func_name = self.read_ascii_string(module_base + func_addr + 2, 256)
                    
                    imports.append({
                        'dll': dll_name,
                        'function': func_name,
                        'iat_address': iat_va + thunk_off,
                        'function_address': function_address,
                        'is_ordinal': bool(is_ordinal)
                    })
                    thunk_off += thunk_size
                
                offset += 20
        except:
            pass
        return imports
    
    # ==================== HIZLI SCAN ====================
    
    def scan_quick(self):
        """HIZLI SCAN — Max 500 hook, sadece JMP/CALL"""
        results = []
        results.append("=" * 50)
        results.append("HIZLI HOOK SCAN")
        results.append("=" * 50)
        
        if not self.open_process():
            results.append("[HATA] Process açılamadı")
            return results, None
        
        self.get_process_bits()
        modules = self.get_all_modules()
        max_hooks = 500
        total = 0
        
        for module in modules:
            if total >= max_hooks:
                break
            try:
                base = module.get('base', 0)
                name = module.get('name', 'Unknown')
                size = min(module.get('size', 0), 1 * 1024 * 1024)
                
                if base == 0 or size == 0:
                    continue
                if self.should_skip_module(name):
                    continue
                
                data = self.read_memory(base, size)
                if not data:
                    continue
                
                for i in range(len(data) - 8):
                    if total >= max_hooks:
                        break
                    
                    abs_addr = base + i
                    
                    if data[i] == 0xE9:  # JMP
                        rel = struct.unpack('<i', data[i+1:i+5])[0]
                        target = abs_addr + 5 + rel
                        target_mod = self.get_module_by_address(target)
                        if target_mod and target_mod['name'] != name:
                            results.append(f"[JMP] {name} → {target_mod['name']} @ 0x{abs_addr:X}")
                            total += 1
                    
                    elif data[i] == 0xE8:  # CALL
                        rel = struct.unpack('<i', data[i+1:i+5])[0]
                        target = abs_addr + 5 + rel
                        target_mod = self.get_module_by_address(target)
                        if target_mod and target_mod['name'] != name:
                            results.append(f"[CALL] {name} → {target_mod['name']} @ 0x{abs_addr:X}")
                            total += 1
            except:
                continue
        
        results.append(f"[ÖZET] {total} hook bulundu")
        self.close_process()
        return results, None
    
    # ==================== TAM TARAMA ====================
    
    def scan_iat_hooks(self):
        self.add_separator("IAT HOOK ANALİZİ", "=")
        if not self.open_process():
            self.add_result("[HATA] Process açılamadı")
            return
        self.get_process_bits()
        modules = self.get_all_modules()
        total_imports = 0
        total_hooks = 0
        
        for module in modules:
            try:
                module_base = module.get('base', 0)
                module_name = module.get('name', 'Unknown')
                if module_base == 0:
                    continue
                if self.should_skip_module(module_name):
                    continue
                
                pe_info = self.parse_pe(module_base)
                if not pe_info['valid']:
                    continue
                
                imports = self.parse_iat(module_base, pe_info)
                total_imports += len(imports)
                
                for imp in imports:
                    if imp['function_address'] is None:
                        continue
                    func_module = self.get_module_by_address(imp['function_address'])
                    if func_module:
                        if func_module['name'].lower() != imp['dll'].lower():
                            self.add_result(f"[IAT HOOK] {module_name}")
                            self.add_result(f"  DLL: {imp['dll']}")
                            self.add_result(f"  Fonksiyon: {imp['function']}")
                            self.add_result(f"  IAT: 0x{imp['iat_address']:X}")
                            self.add_result(f"  Gerçek: {func_module['name']}")
                            self.add_result("")
                            total_hooks += 1
                    else:
                        self.add_result(f"[ŞÜPHELİ] {module_name} → {imp['dll']}")
                        self.add_result(f"  Adres: 0x{imp['function_address']:X}")
                        self.add_result("")
                        total_hooks += 1
            except:
                continue
        
        self.add_result(f"[ÖZET] Import: {total_imports} | Hook: {total_hooks}")
        self.close_process()
    
    def scan_inline_hooks(self):
        self.add_separator("INLINE HOOK ANALİZİ", "=")
        if not self.open_process():
            self.add_result("[HATA] Process açılamadı")
            return
        self.get_process_bits()
        modules = self.get_all_modules()
        total_patterns = 0
        
        for module in modules:
            try:
                module_base = module.get('base', 0)
                module_name = module.get('name', 'Unknown')
                module_size = module.get('size', 0)
                if module_base == 0 or module_size == 0:
                    continue
                if self.should_skip_module(module_name):
                    continue
                
                scan_size = min(module_size, 2 * 1024 * 1024)
                chunk_size = 32 * 1024
                
                for offset in range(0, scan_size, chunk_size):
                    read_size = min(chunk_size, scan_size - offset)
                    data = self.read_memory(module_base + offset, read_size)
                    if not data:
                        continue
                    
                    for i in range(len(data) - 12):
                        abs_addr = module_base + offset + i
                        
                        if data[i] == 0xE9:
                            rel = struct.unpack('<i', data[i+1:i+5])[0]
                            target = abs_addr + 5 + rel
                            target_mod = self.get_module_by_address(target)
                            if target_mod and target_mod['name'] != module_name:
                                self.add_result(f"[JMP] 0x{abs_addr:X} → 0x{target:X} ({target_mod['name']})")
                                self.add_result(f"  Kaynak: {module_name}")
                                self.add_result("")
                                total_patterns += 1
                        
                        elif data[i] == 0xE8:
                            rel = struct.unpack('<i', data[i+1:i+5])[0]
                            target = abs_addr + 5 + rel
                            target_mod = self.get_module_by_address(target)
                            if target_mod and target_mod['name'] != module_name:
                                self.add_result(f"[CALL] 0x{abs_addr:X} → 0x{target:X} ({target_mod['name']})")
                                self.add_result(f"  Kaynak: {module_name}")
                                self.add_result("")
                                total_patterns += 1
                        
                        elif data[i] == 0x68 and i + 5 < len(data) and data[i+5] == 0xC3:
                            push_val = struct.unpack('<I', data[i+1:i+5])[0]
                            self.add_result(f"[PUSH RET] 0x{abs_addr:X} → 0x{push_val:X}")
                            self.add_result("")
                            total_patterns += 1
                        
                        elif data[i] == 0x8B and data[i+1] == 0xFF and i + 7 < len(data) and data[i+2] == 0xE9:
                            rel = struct.unpack('<i', data[i+3:i+7])[0]
                            target = abs_addr + 7 + rel
                            self.add_result(f"[HOTPATCH] 0x{abs_addr:X} → 0x{target:X}")
                            self.add_result("")
                            total_patterns += 1
                        
                        elif self.should_report_int3() and data[i] == 0xCC:
                            self.add_result(f"[INT3] 0x{abs_addr:X}")
                            total_patterns += 1
            except:
                continue
        
        self.add_result(f"[ÖZET] Inline Pattern: {total_patterns}")
        self.close_process()
    
    def scan_vtable_hooks(self):
        self.add_separator("VTABLE HOOK ANALİZİ", "=")
        if not self.open_process():
            self.add_result("[HATA] Process açılamadı")
            return
        self.get_process_bits()
        modules = self.get_all_modules()
        ptr_size = 8 if self.process_bits == 64 else 4
        total_vtables = 0
        total_hooks = 0
        
        for module in modules:
            try:
                module_base = module.get('base', 0)
                module_name = module.get('name', 'Unknown')
                if module_base == 0:
                    continue
                if self.should_skip_module(module_name):
                    continue
                
                pe_info = self.parse_pe(module_base)
                if not pe_info['valid']:
                    continue
                
                for section in pe_info.get('sections', []):
                    section_name = section.get('name', '').lower()
                    if '.data' not in section_name and '.rdata' not in section_name:
                        continue
                    
                    section_va = module_base + section['va']
                    section_size = min(section['size_raw'], 256 * 1024)
                    data = self.read_memory(section_va, section_size)
                    if not data:
                        continue
                    
                    for i in range(0, len(data) - ptr_size * 3, ptr_size):
                        try:
                            ptrs = []
                            for j in range(3):
                                if self.process_bits == 64:
                                    ptrs.append(struct.unpack('<Q', data[i+j*8:i+j*8+8])[0])
                                else:
                                    ptrs.append(struct.unpack('<I', data[i+j*4:i+j*4+4])[0])
                            
                            if all(p > 0x10000 for p in ptrs):
                                mods = [self.get_module_by_address(p) for p in ptrs]
                                if all(mods) and len(set(m['name'] for m in mods if m)) == 1:
                                    total_vtables += 1
                                    for j in range(min(len(ptrs), 5)):
                                        func_mod = mods[j]
                                        if func_mod and func_mod['name'] != module_name:
                                            self.add_result(f"[VTABLE HOOK] {module_name}")
                                            self.add_result(f"  VTable: 0x{section_va + i:X}")
                                            self.add_result(f"  Fonksiyon: 0x{ptrs[j]:X} ({func_mod['name']})")
                                            self.add_result("")
                                            total_hooks += 1
                                            break
                        except:
                            continue
            except:
                continue
        
        self.add_result(f"[ÖZET] VTable: {total_vtables} | Hook: {total_hooks}")
        self.close_process()
    
    def scan_detour_hooks(self):
        self.add_separator("DETOUR HOOK ANALİZİ", "=")
        if not self.open_process():
            self.add_result("[HATA] Process açılamadı")
            return
        modules = self.get_all_modules()
        patterns = [
            (b'\xE9\x00\x00\x00\x00\x90\x90', 'JMP + NOP'),
            (b'\xEB\xF9', 'Infinite Loop'),
            (b'\x68\x00\x00\x00\x00\xC3', 'PUSH + RET'),
        ]
        total = 0
        
        for module in modules:
            try:
                base = module.get('base', 0)
                name = module.get('name', 'Unknown')
                size = min(module.get('size', 0), 1 * 1024 * 1024)
                if base == 0 or size == 0:
                    continue
                if self.should_skip_module(name):
                    continue
                
                data = self.read_memory(base, size)
                if not data:
                    continue
                
                for sig, desc in patterns:
                    for i in range(len(data) - len(sig)):
                        if data[i:i+len(sig)] == sig:
                            self.add_result(f"[DETOUR] {name} @ 0x{base+i:X} — {desc}")
                            self.add_result("")
                            total += 1
            except:
                continue
        
        self.add_result(f"[ÖZET] Detour: {total}")
        self.close_process()
    
    def scan_syscall_hooks(self):
        self.add_separator("SYSCALL HOOK ANALİZİ", "=")
        if not self.open_process():
            self.add_result("[HATA] Process açılamadı")
            return
        modules = self.get_all_modules()
        ntdll = self.get_module_by_name('ntdll.dll')
        if not ntdll:
            self.add_result("[HATA] ntdll.dll bulunamadı")
            self.close_process()
            return
        
        base = ntdll['base']
        size = min(ntdll['size'], 256 * 1024)
        data = self.read_memory(base, size)
        if not data:
            self.close_process()
            return
        
        total_syscalls = 0
        total_hooks = 0
        
        for i in range(len(data) - 12):
            if data[i] == 0x4C and data[i+1] == 0x8B and data[i+2] == 0xD1 and data[i+3] == 0xB8:
                syscall_num = struct.unpack('<I', data[i+4:i+8])[0]
                total_syscalls += 1
                if i + 10 < len(data):
                    if not (data[i+8] == 0x0F and data[i+9] == 0x05):
                        self.add_result(f"[SYSCALL HOOK] 0x{base+i:X} — #{syscall_num}")
                        self.add_result("")
                        total_hooks += 1
        
        self.add_result(f"[ÖZET] Syscall: {total_syscalls} | Hook: {total_hooks}")
        self.close_process()
    
    def scan_anti_debug(self):
        self.add_separator("ANTI-DEBUG ANALİZİ", "=")
        if not self.open_process():
            self.add_result("[HATA] Process açılamadı")
            return
        modules = self.get_all_modules()
        apis = ['IsDebuggerPresent', 'CheckRemoteDebuggerPresent', 'NtQueryInformationProcess',
                'OutputDebugStringA', 'OutputDebugStringW', 'GetTickCount', 'QueryPerformanceCounter']
        found = []
        
        for module in modules:
            try:
                base = module.get('base', 0)
                name = module.get('name', 'Unknown')
                if base == 0:
                    continue
                if self.should_skip_module(name):
                    continue
                
                pe_info = self.parse_pe(base)
                if not pe_info['valid']:
                    continue
                
                imports = self.parse_iat(base, pe_info)
                for imp in imports:
                    if imp['function'] in apis:
                        found.append(f"{name} → {imp['dll']}!{imp['function']}")
            except:
                continue
        
        if found:
            for f in found:
                self.add_result(f"  {f}")
        else:
            self.add_result("[OK] Anti-debug API bulunamadı")
        self.close_process()
    
    # ==================== ANA TARAMA ====================
    
    def scan_all(self):
        output_path = None
        try:
            process_name = f"PID_{self.pid}"
            try:
                proc = psutil.Process(self.pid)
                process_name = proc.name().replace('.exe', '')
            except:
                pass
            
            output_dir = "hook_results"
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mode_suffix = self.mode.upper()
            dll_suffix = f"_{self.target_dll}" if self.target_dll else ""
            output_path = os.path.join(output_dir, f"{process_name}_{mode_suffix}{dll_suffix}_{timestamp}.txt")
            
            self.output_file = open(output_path, 'w', encoding='utf-8')
            
            self.add_separator("", "=")
            self.add_result("YOUD HOOK SCANNER v8.0")
            self.add_result(f"Hedef: {process_name} (PID: {self.pid})")
            self.add_result(f"Mod: {self.mode.upper()}")
            if self.target_dll:
                self.add_result(f"DLL: {self.target_dll}")
            self.add_result(f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
            self.add_separator("", "=")
            self.add_result("")
            
            try:
                self.scan_iat_hooks()
                self.add_result("")
            except:
                pass
            
            try:
                self.scan_inline_hooks()
                self.add_result("")
            except:
                pass
            
            try:
                self.scan_vtable_hooks()
                self.add_result("")
            except:
                pass
            
            try:
                self.scan_detour_hooks()
                self.add_result("")
            except:
                pass
            
            try:
                self.scan_syscall_hooks()
                self.add_result("")
            except:
                pass
            
            try:
                self.scan_anti_debug()
                self.add_result("")
            except:
                pass
            
            self.add_separator("ANALİZ TAMAMLANDI", "=")
            self.add_result(f"Sonuç: {len(self.all_results)} satır")
            self.add_result(f"Kayıt: {output_path}")
            self.add_separator("", "=")
            
        except:
            pass
        finally:
            if self.output_file:
                try:
                    self.output_file.close()
                except:
                    pass
                self.output_file = None
        
        return self.all_results, output_path