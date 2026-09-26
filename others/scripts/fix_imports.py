#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — Import Fixer v2
Klasör yapısı değişti → tüm import'ları otomatik güncelle

FIX v2:
- IMPORT_MAP tüm v3.x modülleriyle tamamlandı
- `import X, Y, Z` desteği (satır parçalanır)
- UTF-8 BOM desteği (utf-8-sig ile okuma)
- SKIP_DIRS: HookEngine build klasörü eklendi
- Atlanan satırlar için uyarı listesi (verbose)
- Ölü kod temizlendi

KULLANIM:
    python fix_imports.py
"""

import os
import re
import sys
import shutil
from datetime import datetime

# ==================== AYARLAR ====================
BACKUP_SUFFIX = "_backup_imports"

# Alt paket isimleri — bunlarla başlayan import'lar "zaten qualified" sayılır
TOP_LEVEL_PACKAGES = [
    'core', 'hook', 'ht', 'injector', 'report', 'installer',
    'ui', 'utils', 'widgets'  # ileride açabileceğin klasörler
]

# ==================== IMPORT EŞLEMESİ ====================
# Format: 'eski_modül_adı': 'yeni_tam_yol'
# Yeni modül ekledikçe buraya satır ekle.
IMPORT_MAP = {
    # -------- core/ --------
    'lang':             'core.lang',
    'memory_engine':    'core.memory_engine',
    'process_manager':  'core.process_manager',
    'value_scanner':    'core.value_scanner',
    'fast_scanner':     'core.fast_scanner',
    'vip':              'core.vip',

    # -------- hook/ --------
    'hook_scanner':     'hook.hook_scanner',
    'who_writes':       'hook.who_writes',
    'who_writes_ui':    'hook.who_writes_ui',
    'who_writes_veh':   'hook.who_writes_veh',

    # -------- ht/ --------
    'ht_v3':            'ht.ht_v3',
    'ht_resolver':      'ht.ht_resolver',
    'ht_engine':        'ht.ht_engine',
    'ht_lua':           'ht.ht_lua',
    'ht_injector':      'ht.ht_injector',
    'ht_ui_v3':         'ht.ht_ui_v3',
    'ht_editor':        'ht.ht_editor',
    # eski/legacy isimler
    'ht_table':         'ht.ht_table',
    'ht_table_ui':      'ht.ht_table_ui',

    # -------- injector/ --------
    'dll_injector':     'injector.dll_injector',

    # -------- report/ --------
    'report_generator': 'report.report_generator',

    # -------- installer/ --------
    'installer':        'installer.installer',
}


# ==================== SATIR DÜZELTİCİ ====================

def _is_qualified(module: str) -> bool:
    """Modül zaten alt paketle başlıyor mu? (core.x, hook.x, ...)"""
    return any(module == p or module.startswith(p + '.') for p in TOP_LEVEL_PACKAGES)


def _rewrite_from_import(line: str):
    """
    `from X import ...` satırını düzelt.
    Dönüş: (new_line, changed) — değişiklik yoksa (line, False)
    """
    m = re.match(r'^(\s*)from\s+([\w\.]+)\s+import\s+(.+?)(\s*#.*)?(\r?\n?)$', line)
    if not m:
        return line, False

    indent, module, imports_part, comment, eol = m.groups()
    comment = comment or ''
    eol = eol or '\n'

    # Zaten qualified
    if _is_qualified(module):
        return line, False

    # Relative import (`.core`) — dokunma
    if module.startswith('.'):
        return line, False

    if module in IMPORT_MAP:
        new_module = IMPORT_MAP[module]
        new_line = f"{indent}from {new_module} import {imports_part}{comment}{eol}"
        return new_line, True

    return line, False


def _rewrite_plain_import(line: str):
    """
    `import X` ve `import X, Y, Z` satırlarını düzelt.
    Birden fazla modül varsa satır parçalara ayrılır.
    Dönüş: (list_of_lines, changed)
    """
    # `import X, Y as Z` — tüm satırı yakala
    m = re.match(r'^(\s*)import\s+(.+?)(\s*#.*)?(\r?\n?)$', line)
    if not m:
        return [line], False

    indent, items_str, comment, eol = m.groups()
    comment = comment or ''
    eol = eol or '\n'

    # Virgülle ayır — import satırlarında string literal olmaz, güvenli
    items = [i.strip() for i in items_str.split(',') if i.strip()]

    new_lines = []
    changed = False

    for item in items:
        # `os` veya `os as o` formatı
        alias = ''
        module = item
        if ' as ' in item:
            module, alias = item.split(' as ', 1)
            module = module.strip()
            alias = alias.strip()
            alias_suffix = f" as {alias}"
        else:
            alias_suffix = ''

        # Zaten qualified?
        if _is_qualified(module):
            new_lines.append(f"{indent}import {item}")
            continue

        # Relative import?
        if module.startswith('.'):
            new_lines.append(f"{indent}import {item}")
            continue

        if module in IMPORT_MAP:
            new_module = IMPORT_MAP[module]
            parent, leaf = new_module.rsplit('.', 1)
            new_lines.append(f"{indent}from {parent} import {leaf}{alias_suffix}")
            changed = True
        else:
            new_lines.append(f"{indent}import {item}")

    if not changed:
        return [line], False

    # Comment'i ilk satıra koy, satır sonlarını ekle
    if comment:
        new_lines[0] = new_lines[0] + comment
    result = [new_lines[0] + eol]
    for l in new_lines[1:]:
        result.append(l + eol)
    return result, True


# ==================== DOSYA DÜZELTİCİ ====================

def fix_file(filepath, dry_run=False):
    """
    Bir dosyadaki import'ları düzelt.
    Dönüş: (changes_count, error_str_or_None, skipped_lines)
    """
    try:
        # utf-8-sig → BOM varsa temizler, yazarken BOM eklemez
        with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
            lines = f.readlines()
    except Exception as e:
        return 0, f"OKUNAMADI: {e}", []

    changes = 0
    new_lines = []
    skipped = []

    for lineno, line in enumerate(lines, 1):
        # Önce `from X import ...` dene
        new_line, changed = _rewrite_from_import(line)
        if changed:
            new_lines.append(new_line)
            changes += 1
            continue

        # Sonra `import X[, Y]` dene
        result_lines, changed = _rewrite_plain_import(line)
        if changed:
            new_lines.extend(result_lines)
            changes += 1
            continue

        # Atlanan şüpheli satırlar (import içeriyor ama dokunulmadı)
        stripped = line.strip()
        if re.match(r'^(import|from)\s', stripped):
            # Sadece zaten qualified olanlar skip edilmeli
            # Diğer "atlananlar" şüpheli olabilir
            m = re.match(r'^from\s+([\w\.]+)\s+import', stripped)
            if m and not _is_qualified(m.group(1)) and not m.group(1).startswith('.'):
                if m.group(1) not in IMPORT_MAP:
                    skipped.append((lineno, stripped, f"bilinmeyen modül: {m.group(1)}"))
            else:
                m2 = re.match(r'^import\s+([\w\.]+)', stripped)
                if m2 and not _is_qualified(m2.group(1)) and not m2.group(1).startswith('.'):
                    if m2.group(1) not in IMPORT_MAP:
                        skipped.append((lineno, stripped, f"bilinmeyen modül: {m2.group(1)}"))

        new_lines.append(line)

    if changes > 0 and not dry_run:
        # Yedek al
        try:
            shutil.copy2(filepath, filepath + BACKUP_SUFFIX)
        except Exception:
            pass

        # Yeni içeriği yaz (BOM'suz, LF/CRLF orijinali korunur)
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.writelines(new_lines)
        except Exception as e:
            return 0, f"YAZILAMADI: {e}", []

    return changes, None, skipped


# ==================== TARAYICI ====================

def scan_and_fix(root_dir, dry_run=False):
    print("=" * 70)
    print(f"  HookEngine — Import Fixer v2")
    print(f"  Klasör: {root_dir}")
    print(f"  Mod:    {'DRY-RUN (test)' if dry_run else 'GERÇEK DÜZELTME'}")
    print("=" * 70)
    print()

    total_files = 0
    total_changes = 0
    errors = []
    all_skipped = []

    SKIP_DIRS = {
        '__pycache__', 'build', 'dist', '.git', '.venv', 'venv', 'env',
        'hook_results', 'backup', 'node_modules', '.vscode', '.idea',
        'HookEngine', 'garbage', 'scripts',  # <- build output + tooling
    }

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.endswith(BACKUP_SUFFIX)
        ]

        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            if filename.endswith(BACKUP_SUFFIX):
                continue

            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_dir)

            changes, error, skipped = fix_file(filepath, dry_run=dry_run)

            if error:
                errors.append(f"  X {rel_path}: {error}")
            elif changes > 0:
                print(f"  OK {rel_path}: {changes} satır güncellendi")
                total_files += 1
                total_changes += changes

            if skipped:
                for lineno, text, reason in skipped:
                    all_skipped.append((rel_path, lineno, text, reason))

    print()
    print("=" * 70)
    print(f"  ÖZET: {total_files} dosya, {total_changes} satır düzeltildi")
    print("=" * 70)

    if all_skipped:
        print()
        print("  ATLANAN SATIRLAR (manuel kontrol gerekli):")
        print("-" * 70)
        for rel, lineno, text, reason in all_skipped[:50]:
            print(f"  {rel}:{lineno}  [{reason}]")
            print(f"      {text}")
        if len(all_skipped) > 50:
            print(f"  ... ve {len(all_skipped) - 50} satır daha")
        print("-" * 70)

    if errors:
        print()
        print("  HATALAR:")
        for e in errors:
            print(e)

    print()


def create_backup(root_dir):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(
        os.path.dirname(root_dir), f"HookTool_backup_{timestamp}"
    )

    print(f"Yedek alınıyor: {backup_dir}")
    try:
        shutil.copytree(
            root_dir, backup_dir,
            ignore=shutil.ignore_patterns(
                '__pycache__', 'build', 'dist', '*.pyc',
                'garbage', 'hook_results', 'HookEngine',
            )
        )
        print(f"OK Yedek alındı\n")
        return backup_dir
    except Exception as e:
        print(f"X Yedek alınamadı: {e}\n")
        return None


# ==================== ENTRY POINT ====================

def main():
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = os.path.dirname(os.path.abspath(__file__))

    if not os.path.isdir(root):
        print(f"Klasör bulunamadı: {root}")
        return 1

    print("=" * 70)
    print("  HookEngine — Import Fixer v2")
    print("=" * 70)
    print()
    print("  Ne yapmak istiyorsun?")
    print("    [1] Test (dry-run) — değişiklikleri göster, uygula değil")
    print("    [2] Yedek al + Düzelt — güvenli mod")
    print("    [3] Direkt düzelt (yedek alma)")
    print("    [4] Çıkış")
    print()

    choice = input("  Seçim [1-4]: ").strip()

    if choice == '1':
        scan_and_fix(root, dry_run=True)
    elif choice == '2':
        backup = create_backup(root)
        if backup:
            scan_and_fix(root, dry_run=False)
            print(f"Yedek: {backup}")
            print("Sorun çıkarsa buradan geri yükle.")
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