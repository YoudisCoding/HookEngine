#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — Import Fixer
Klasör yapısı değişti → tüm import'ları otomatik güncelle

KULLANIM:
    python fix_imports.py

Önce yedek al!
"""

import os
import re
import sys
import shutil
from datetime import datetime

# ==================== AYARLAR ====================
BACKUP_SUFFIX = "_backup_imports"

# ==================== IMPORT EŞLEMESİ ====================
# Format: 'eski_modül_adı': 'yeni_tam_yol'
IMPORT_MAP = {
    # core/
    'lang':             'core.lang',
    'memory_engine':    'core.memory_engine',
    'process_manager':  'core.process_manager',
    'value_scanner':    'core.value_scanner',

    # hook/
    'hook_scanner':     'hook.hook_scanner',
    'who_writes':       'hook.who_writes',
    'who_writes_ui':    'hook.who_writes_ui',

    # ht/
    'ht_table':         'ht.ht_table',
    'ht_table_ui':      'ht.ht_table_ui',

    # injector/
    'dll_injector':     'injector.dll_injector',

    # report/
    'report_generator': 'report.report_generator',

    # installer/ — dikkat: installer.py içindeki import'lar değişmeyebilir
    'installer':        'installer.installer',
}

# ==================== DÜZELTME KURALLARI ====================
# 3 format destekleniyor:
#   from X import Y
#   from X import Y as Z
#   from X import (Y, Z, W)

def fix_line(line):
    """Tek satırı düzelt. Değişiklik varsa (new_line, changed) döner."""
    stripped = line.strip()

    # "from X import ..." kontrolü
    match = re.match(r'^(\s*)from\s+([\w\.]+)\s+import\s+(.+?)(\s*#.*)?$', line)
    if match:
        indent, module, imports_part, comment = match.groups()
        comment = comment or ''

        # Zaten prefix'li mi? (core., hook., ht., vs.)
        if any(module.startswith(p + '.') for p in ['core', 'hook', 'ht', 'injector', 'report', 'installer']):
            return line, False

        # Modül haritada mı?
        if module in IMPORT_MAP:
            new_module = IMPORT_MAP[module]
            new_line = f"{indent}from {new_module} import {imports_part}{comment}\n"
            return new_line, True

    # "import X" kontrolü (tek modül)
    match2 = re.match(r'^(\s*)import\s+([\w\.]+)(\s+as\s+\w+)?(\s*#.*)?$', line)
    if match2:
        indent, module, as_part, comment = match2.groups()
        as_part = as_part or ''
        comment = comment or ''

        if any(module.startswith(p + '.') for p in ['core', 'hook', 'ht', 'injector', 'report']):
            return line, False

        if module in IMPORT_MAP:
            new_module = IMPORT_MAP[module]
            # "import X" → "from core import X" formatına çevir
            parent = new_module.rsplit('.', 1)[0]  # core.lang → core
            leaf = new_module.rsplit('.', 1)[1]    # core.lang → lang
            new_line = f"{indent}from {parent} import {leaf}{as_part}{comment}\n"
            return new_line, True

    return line, False


def fix_file(filepath, dry_run=False):
    """Bir dosyadaki import'ları düzelt."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return 0, f"OKUNAMADI: {e}"

    changes = 0
    new_lines = []

    for line in lines:
        new_line, changed = fix_line(line)
        if changed:
            changes += 1
        new_lines.append(new_line)

    if changes > 0 and not dry_run:
        # Yedek al
        backup_path = filepath + BACKUP_SUFFIX
        try:
            shutil.copy2(filepath, backup_path)
        except Exception:
            pass

        # Yeni içeriği yaz
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        except Exception as e:
            return 0, f"YAZILAMADI: {e}"

    return changes, None


def scan_and_fix(root_dir, dry_run=False):
    """Tüm .py dosyalarını tara ve düzelt."""
    print("=" * 60)
    print(f"HookEngine — Import Fixer")
    print(f"Klasör: {root_dir}")
    print(f"Mod: {'DRY-RUN (test)' if dry_run else 'GERÇEK DÜZELTME'}")
    print("=" * 60)
    print()

    total_files = 0
    total_changes = 0
    errors = []

    # Atlanacak klasörler
    SKIP_DIRS = {'__pycache__', 'build', 'dist', '.git', 'hook_results',
                 'backup', 'node_modules', '.vscode', '.idea'}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Atlanacak klasörleri çıkar
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith(BACKUP_SUFFIX)]

        for filename in filenames:
            if not filename.endswith('.py'):
                continue

            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_dir)

            changes, error = fix_file(filepath, dry_run=dry_run)

            if error:
                errors.append(f"  ✗ {rel_path}: {error}")
            elif changes > 0:
                print(f"  ✓ {rel_path}: {changes} import güncellendi")
                total_files += 1
                total_changes += changes

    print()
    print("=" * 60)
    print(f"ÖZET: {total_files} dosya, {total_changes} import düzeltildi")
    if errors:
        print()
        print("HATALAR:")
        for e in errors:
            print(e)
    print("=" * 60)


def create_backup(root_dir):
    """Tüm projeyi yedekle."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(os.path.dirname(root_dir), f"HookTool_backup_{timestamp}")

    print(f"Yedek alınıyor: {backup_dir}")
    try:
        shutil.copytree(root_dir, backup_dir,
                        ignore=shutil.ignore_patterns('__pycache__', 'build', 'dist', '*.pyc'))
        print(f"✓ Yedek alındı")
        return backup_dir
    except Exception as e:
        print(f"✗ Yedek alınamadı: {e}")
        return None


def main():
    # Root klasörü bul
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = os.path.dirname(os.path.abspath(__file__))

    if not os.path.isdir(root):
        print(f"Klasör bulunamadı: {root}")
        return 1

    # Mod seçimi
    print("=" * 60)
    print("HookEngine — Import Fixer")
    print("=" * 60)
    print()
    print("Ne yapmak istiyorsun?")
    print("  [1] Test (dry-run) — değişiklikleri göster ama uygula değil")
    print("  [2] Yedek al + Düzelt — güvenli mod")
    print("  [3] Direkt düzelt (yedek alma)")
    print("  [4] Çıkış")
    print()

    choice = input("Seçim [1-4]: ").strip()

    if choice == '1':
        scan_and_fix(root, dry_run=True)
    elif choice == '2':
        backup = create_backup(root)
        if backup:
            scan_and_fix(root, dry_run=False)
            print(f"\nYedek: {backup}")
            print("Bir sorun çıkarsa bu klasörden geri yükleyebilirsin.")
    elif choice == '3':
        scan_and_fix(root, dry_run=False)
    elif choice == '4':
        print("İptal edildi.")
        return 0
    else:
        print("Geçersiz seçim.")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())