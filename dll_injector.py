import struct
import os
from ctypes import *
from ctypes.wintypes import *

class ProfessionalDLLInjector:
    PROCESS_ALL_ACCESS = 0x1F0FFF
    MEM_COMMIT = 0x1000
    MEM_RESERVE = 0x2000
    MEM_RELEASE = 0x8000
    PAGE_READWRITE = 0x04
    PAGE_EXECUTE_READWRITE = 0x40
    
    def __init__(self, pid):
        self.pid = pid
        self.kernel32 = windll.kernel32
        self.ntdll = windll.ntdll
        self.hProcess = None
    
    def open_process(self):
        if not self.hProcess:
            self.hProcess = self.kernel32.OpenProcess(
                self.PROCESS_ALL_ACCESS, False, self.pid
            )
        return self.hProcess != 0
    
    def close_process(self):
        if self.hProcess:
            self.kernel32.CloseHandle(self.hProcess)
            self.hProcess = None
    
    def inject_loadlibrary(self, dll_path):
        """Standart LoadLibrary enjeksiyonu"""
        if not self.open_process():
            return False
        
        dll_path = os.path.abspath(dll_path)
        dll_path_bytes = dll_path.encode('utf-8') + b'\x00'
        
        # Bellek ayır
        remote_memory = self.kernel32.VirtualAllocEx(
            self.hProcess, None, len(dll_path_bytes),
            self.MEM_COMMIT | self.MEM_RESERVE, self.PAGE_READWRITE
        )
        
        if not remote_memory:
            self.close_process()
            return False
        
        # DLL path'ini yaz
        bytes_written = c_size_t()
        self.kernel32.WriteProcessMemory(
            self.hProcess, remote_memory, dll_path_bytes, 
            len(dll_path_bytes), byref(bytes_written)
        )
        
        # LoadLibraryA adresini al
        kernel32_handle = self.kernel32.GetModuleHandleA(b"kernel32.dll")
        load_library_addr = self.kernel32.GetProcAddress(kernel32_handle, b"LoadLibraryA")
        
        # Remote thread oluştur
        thread_id = c_ulong()
        hThread = self.kernel32.CreateRemoteThread(
            self.hProcess, None, 0, load_library_addr, 
            remote_memory, 0, byref(thread_id)
        )
        
        if not hThread:
            self.kernel32.VirtualFreeEx(self.hProcess, remote_memory, 0, self.MEM_RELEASE)
            self.close_process()
            return False
        
        # Thread'in bitmesini bekle
        self.kernel32.WaitForSingleObject(hThread, 15000)
        
        # Thread exit code'unu al
        exit_code = c_ulong()
        self.kernel32.GetExitCodeThread(hThread, byref(exit_code))
        
        # Temizlik
        self.kernel32.CloseHandle(hThread)
        self.kernel32.VirtualFreeEx(self.hProcess, remote_memory, 0, self.MEM_RELEASE)
        self.close_process()
        
        return exit_code.value != 0
    
    def inject_manual_map(self, dll_path):
        """Manual Map enjeksiyonu — basitleştirilmiş"""
        if not self.open_process():
            return False
        
        dll_path = os.path.abspath(dll_path)
        
        # DLL dosyasını oku
        try:
            with open(dll_path, 'rb') as f:
                dll_data = f.read()
        except:
            self.close_process()
            return False
        
        # PE başlıklarını parse et
        dos_header = struct.unpack('<H', dll_data[0:2])[0]
        if dos_header != 0x5A4D:  # MZ
            self.close_process()
            return False
        
        e_lfanew = struct.unpack('<I', dll_data[0x3C:0x40])[0]
        nt_header = struct.unpack('<I', dll_data[e_lfanew:e_lfanew+4])[0]
        
        if nt_header != 0x00004550:  # PE
            self.close_process()
            return False
        
        # Image size'ı al
        size_of_image = struct.unpack('<I', dll_data[e_lfanew+0x38:e_lfanew+0x3C])[0]
        
        # Bellek ayır
        remote_base = self.kernel32.VirtualAllocEx(
            self.hProcess, None, size_of_image,
            self.MEM_COMMIT | self.MEM_RESERVE, self.PAGE_EXECUTE_READWRITE
        )
        
        if not remote_base:
            self.close_process()
            return False
        
        # Headers'ı yaz
        size_of_headers = struct.unpack('<I', dll_data[e_lfanew+0x34:e_lfanew+0x38])[0]
        
        bytes_written = c_size_t()
        self.kernel32.WriteProcessMemory(
            self.hProcess, remote_base, dll_data, 
            size_of_headers, byref(bytes_written)
        )
        
        # Section'ları yaz
        num_sections = struct.unpack('<H', dll_data[e_lfanew+6:e_lfanew+8])[0]
        section_header_offset = e_lfanew + 24 + struct.unpack('<H', dll_data[e_lfanew+20:e_lfanew+22])[0]
        
        for i in range(num_sections):
            section_offset = section_header_offset + i * 40
            
            virtual_address = struct.unpack('<I', dll_data[section_offset+12:section_offset+16])[0]
            size_of_raw_data = struct.unpack('<I', dll_data[section_offset+16:section_offset+20])[0]
            pointer_to_raw_data = struct.unpack('<I', dll_data[section_offset+20:section_offset+24])[0]
            
            if size_of_raw_data > 0:
                section_data = dll_data[pointer_to_raw_data:pointer_to_raw_data+size_of_raw_data]
                self.kernel32.WriteProcessMemory(
                    self.hProcess, 
                    c_void_p(remote_base + virtual_address),
                    section_data, size_of_raw_data, byref(bytes_written)
                )
        
        self.close_process()
        return True
    
    def inject_thread_hijack(self, dll_path):
        """Thread Hijacking enjeksiyonu"""
        if not self.open_process():
            return False
        
        # Hedef process'te bir thread bul
        thread_id = self.find_thread()
        if not thread_id:
            self.close_process()
            return False
        
        dll_path = os.path.abspath(dll_path)
        dll_path_bytes = dll_path.encode('utf-8') + b'\x00'
        
        # Bellek ayır
        remote_memory = self.kernel32.VirtualAllocEx(
            self.hProcess, None, len(dll_path_bytes),
            self.MEM_COMMIT | self.MEM_RESERVE, self.PAGE_READWRITE
        )
        
        if not remote_memory:
            self.close_process()
            return False
        
        # DLL path'ini yaz
        bytes_written = c_size_t()
        self.kernel32.WriteProcessMemory(
            self.hProcess, remote_memory, dll_path_bytes,
            len(dll_path_bytes), byref(bytes_written)
        )
        
        # LoadLibraryA adresini al
        kernel32_handle = self.kernel32.GetModuleHandleA(b"kernel32.dll")
        load_library_addr = self.kernel32.GetProcAddress(kernel32_handle, b"LoadLibraryA")
        
        # Thread'i suspend et
        hThread = self.kernel32.OpenThread(0x0002, False, thread_id)  # THREAD_SUSPEND_RESUME
        if not hThread:
            self.close_process()
            return False
        
        self.kernel32.SuspendThread(hThread)
        
        # Thread context'ini al
        context = CONTEXT()
        context.ContextFlags = 0x100000  # CONTEXT_CONTROL
        
        if not self.kernel32.GetThreadContext(hThread, byref(context)):
            self.kernel32.ResumeThread(hThread)
            self.kernel32.CloseHandle(hThread)
            self.close_process()
            return False
        
        # RIP'i LoadLibraryA'ya yönlendir
        # x64: RCX = dll_path, RIP = LoadLibraryA
        
        # Burada x64 shellcode gerekli
        # Basitleştirilmiş versiyon için LoadLibrary enjeksiyonuna fallback
        self.kernel32.ResumeThread(hThread)
        self.kernel32.CloseHandle(hThread)
        self.close_process()
        
        return self.inject_loadlibrary(dll_path)
    
    def find_thread(self):
        """Hedef process'te bir thread bul"""
        # Toolhelp32 ile thread listesi
        class THREADENTRY32(Structure):
            _fields_ = [
                ("dwSize", c_ulong),
                ("cntUsage", c_ulong),
                ("th32ThreadID", c_ulong),
                ("th32OwnerProcessID", c_ulong),
                ("tpBasePri", c_long),
                ("tpDeltaPri", c_long),
                ("dwFlags", c_ulong)
            ]
        
        snapshot = self.kernel32.CreateToolhelp32Snapshot(0x00000004, 0)  # TH32CS_SNAPTHREAD
        thread_entry = THREADENTRY32()
        thread_entry.dwSize = sizeof(THREADENTRY32)
        
        if self.kernel32.Thread32First(snapshot, byref(thread_entry)):
            while self.kernel32.Thread32Next(snapshot, byref(thread_entry)):
                if thread_entry.th32OwnerProcessID == self.pid:
                    self.kernel32.CloseHandle(snapshot)
                    return thread_entry.th32ThreadID
        
        self.kernel32.CloseHandle(snapshot)
        return None