#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — VIP System
Offline key kontrolü + registry + HWID
"""

import os
import hashlib
import winreg
import ctypes
import ctypes.wintypes as wt
import subprocess


REG_PATH = r"Software\HookEngine"
VIP_KEY_REG = "VipKey"
VIP_HWID_REG = "VipHWID"
VIP_ACTIVATED_REG = "VipActivated"


# ==================== KEY HAVUZU ====================
# Her key SHA256 hash olarak saklanır.
# Test key: HOOKENGINEPREMIUMTEST
KEY_HASHES = {
    "05cdb30e36d52c0e1d4fbb24d48267183e50f923f9a03c7d3ddb04cda6a5d183": "test_key_001",
}


# ==================== HWID ====================
def get_hwid():
    """Makine kimliği — CPU + Volume Serial + Hostname"""
    try:
        cpu = ""
        try:
            out = subprocess.check_output(
                "wmic cpu get ProcessorId",
                shell=True, stderr=subprocess.DEVNULL
            ).decode(errors='ignore')
            lines = [l.strip() for l in out.split('\n')
                     if l.strip() and 'ProcessorId' not in l]
            if lines:
                cpu = lines[0]
        except Exception:
            pass

        vol = ""
        try:
            serial = wt.DWORD()
            ctypes.windll.kernel32.GetVolumeInformationW(
                "C:\\", None, 0, ctypes.byref(serial), None, None, None, 0
            )
            vol = str(serial.value)
        except Exception:
            pass

        hostname = os.environ.get('COMPUTERNAME', '')

        raw = f"{cpu}|{vol}|{hostname}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
    except Exception:
        return "unknown"


# ==================== REGISTRY ====================
def _read_reg(name):
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        val, _ = winreg.QueryValueEx(k, name)
        winreg.CloseKey(k)
        return val
    except Exception:
        return None


def _write_reg(name, value):
    try:
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, str(value))
        winreg.CloseKey(k)
        return True
    except Exception:
        return False


def _delete_reg(name):
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                           winreg.KEY_SET_VALUE)
        winreg.DeleteValue(k, name)
        winreg.CloseKey(k)
        return True
    except Exception:
        return False


# ==================== HASH ====================
def hash_key(key):
    return hashlib.sha256(key.strip().encode()).hexdigest()


# ==================== KEY KONTROL ====================
def is_vip():
    """Şu an VIP mi?"""
    activated = _read_reg(VIP_ACTIVATED_REG)
    if activated != "1":
        return False

    saved_hash = _read_reg(VIP_KEY_REG)
    saved_hwid = _read_reg(VIP_HWID_REG)
    current_hwid = get_hwid()

    if not saved_hash or not saved_hwid:
        return False

    if saved_hwid != current_hwid:
        return False

    if saved_hash not in KEY_HASHES:
        return False

    return True


def activate_key(user_key):
    """
    Key'i aktive et.
    Dönüş: (success: bool, message: str)
    """
    user_key = user_key.strip().upper()

    if not user_key:
        return False, "Key boş"

    if len(user_key) < 8:
        return False, "Key çok kısa"

    key_hash = hash_key(user_key)

    if key_hash not in KEY_HASHES:
        return False, "Geçersiz key"

    if is_vip():
        saved_hash = _read_reg(VIP_KEY_REG)
        if saved_hash == key_hash:
            return True, "Zaten aktif"
        else:
            return False, "Başka bir key aktif"

    hwid = get_hwid()

    ok1 = _write_reg(VIP_KEY_REG, key_hash)
    ok2 = _write_reg(VIP_HWID_REG, hwid)
    ok3 = _write_reg(VIP_ACTIVATED_REG, "1")

    if not (ok1 and ok2 and ok3):
        return False, "Kayıt başarısız"

    return True, "VIP aktif edildi"


def deactivate_key():
    """VIP'i kapat (test için)"""
    _delete_reg(VIP_KEY_REG)
    _delete_reg(VIP_HWID_REG)
    _delete_reg(VIP_ACTIVATED_REG)
    return True


def get_vip_info():
    """VIP bilgisi"""
    if not is_vip():
        return None
    return {
        'hwid': _read_reg(VIP_HWID_REG),
        'key_id': KEY_HASHES.get(_read_reg(VIP_KEY_REG), 'unknown'),
    }