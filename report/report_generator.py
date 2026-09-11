#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOUD Report Generator — Fixed: os import + ProfessionalHookScannerV5
"""

import os
from core.process_manager import ProcessManager
from hook.hook_scanner import ProfessionalHookScannerV5


class ReportGenerator:
    def __init__(self, pid):
        self.pid = pid
        self.process_manager = ProcessManager()
        self.hook_scanner = ProfessionalHookScannerV5(pid)

    def generate_full_report(self):
        report = []
        report.append("=" * 70)
        report.append("YOUD PROFESSIONAL TOOL — FULL REPORT")
        report.append(f"Process ID: {self.pid}")
        report.append("=" * 70)
        report.append("")

        proc_info = self.process_manager.get_process_info(self.pid)
        if proc_info:
            report.append("--- PROCESS INFO ---")
            report.append(f"Name: {proc_info['name']}")
            report.append(f"PID: {proc_info['pid']}")
            report.append(f"EXE: {proc_info['exe']}")
            report.append(f"CWD: {proc_info['cwd']}")
            report.append(f"Status: {proc_info['status']}")
            report.append(f"User: {proc_info['username']}")
            report.append(f"Created: {proc_info['create_time']}")
            report.append(f"CPU: {proc_info['cpu_percent']}%")
            report.append(f"Memory: {proc_info['memory']} MB")
            report.append(f"Threads: {proc_info['threads']}")
            report.append(f"Connections: {proc_info['connections']}")
            report.append("")

        modules = self.process_manager.get_process_modules(self.pid)
        if modules:
            report.append("--- LOADED MODULES ---")
            for module in modules:
                report.append(f"[MODULE] {os.path.basename(module['path'])}")
                report.append(f"  Path: {module['path']}")
                report.append(f"  Base: 0x{module['base']:X}")
                report.append(f"  Size: {module['size']} bytes")
                report.append("")

        threads = self.process_manager.get_process_threads(self.pid)
        if threads:
            report.append("--- THREADS ---")
            for i, thread in enumerate(threads):
                report.append(f"Thread {i}: ID={thread['id']}")
                report.append(f"  User Time: {thread['user_time']}")
                report.append(f"  System Time: {thread['system_time']}")
                report.append("")

        connections = self.process_manager.get_process_connections(self.pid)
        if connections:
            report.append("--- NETWORK CONNECTIONS ---")
            for conn in connections:
                report.append(f"{conn['local']} -> {conn['remote']} ({conn['status']})")
            report.append("")

        report.append("--- HOOK ANALYSIS ---")
        try:
            hook_results, _ = self.hook_scanner.scan_all()
            for result in hook_results:
                report.append(result)
        except Exception as e:
            report.append(f"[HOOK ERROR] {e}")
        report.append("")

        report.append("=" * 70)
        report.append("END OF REPORT")
        report.append("=" * 70)
        return "\n".join(report)