import psutil
import os
import time

class ProcessManager:
    def __init__(self):
        self.processes = {}
    
    def get_all_processes(self):
        """Tüm process'leri listele"""
        process_list = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                process_list.append((proc.info['pid'], proc.info['name']))
            except:
                pass
        return sorted(process_list, key=lambda x: x[1].lower())
    
    def get_process_info(self, pid):
        """Process hakkında detaylı bilgi"""
        try:
            proc = psutil.Process(pid)
            info = {
                'pid': pid,
                'name': proc.name(),
                'exe': proc.exe(),
                'cwd': proc.cwd(),
                'status': proc.status(),
                'username': proc.username(),
                'create_time': time.ctime(proc.create_time()),
                'cpu_percent': proc.cpu_percent(),
                'memory': proc.memory_info().rss / 1024 / 1024,
                'threads': len(proc.threads()),
                'connections': len(proc.connections())
            }
            return info
        except:
            return None
    
    def get_process_modules(self, pid):
        """Process'in yüklü modüllerini al"""
        try:
            proc = psutil.Process(pid)
            modules = []
            for module in proc.memory_maps():
                if module.path.endswith('.dll') or module.path.endswith('.exe'):
                    modules.append({
                        'path': module.path,
                        'base': module.addr,
                        'size': module.size
                    })
            return modules
        except:
            return []
    
    def get_process_threads(self, pid):
        """Process'in thread'lerini al"""
        try:
            proc = psutil.Process(pid)
            threads = []
            for thread in proc.threads():
                threads.append({
                    'id': thread.id,
                    'user_time': thread.user_time,
                    'system_time': thread.system_time
                })
            return threads
        except:
            return []
    
    def get_process_connections(self, pid):
        """Process'in ağ bağlantılarını al"""
        try:
            proc = psutil.Process(pid)
            connections = []
            for conn in proc.connections():
                connections.append({
                    'local': str(conn.laddr),
                    'remote': str(conn.raddr) if conn.raddr else '',
                    'status': conn.status
                })
            return connections
        except:
            return []
    
    def is_process_running(self, pid):
        """Process çalışıyor mu?"""
        return psutil.pid_exists(pid)