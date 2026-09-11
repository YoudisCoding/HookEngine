#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HookEngine — HT v3.0 Format
Kendine özgü, esnek, AI-dostu format

Format:
{
  "version": "3.0",
  "name": "Half-Life Trainer",
  "author": "Youd",
  "game": "hl.exe",
  "language": "tr",
  "created": "2026-09-11",
  "groups": [
    {
      "name": "Player Stats",
      "color": "#ff5555",
      "entries": [
        {
          "id": "health",
          "label": "Health 999",
          "read": ["client.dll+0x992E4", "+0x7C", "+0x04", "+0x160"],
          "type": "float",
          "value": 999.0,
          "mode": "toggle",
          "hotkey": "H",
          "description": "Can 999",
          "repeat": 100,
          "enabled_by_default": false
        }
      ]
    }
  ]
}
"""

import json
import os
from datetime import datetime


HT_VERSION = "3.0"

# ==================== ENTRY MODES ====================
MODE_TOGGLE = "toggle"          # Aç/kapat
MODE_ACTION = "action"          # Tek seferlik
MODE_FREEZE = "freeze"          # Sürekli dondur
MODE_SCRIPT = "script"          # Lua script
MODE_INJECT = "inject"          # Kod injection
MODE_FORMULA = "formula"        # Formül
MODE_CONDITION = "condition"    # Koşullu

VALID_MODES = [MODE_TOGGLE, MODE_ACTION, MODE_FREEZE,
               MODE_SCRIPT, MODE_INJECT, MODE_FORMULA, MODE_CONDITION]

# ==================== VALUE TYPES ====================
TYPE_INT = "int"
TYPE_INT64 = "int64"
TYPE_FLOAT = "float"
TYPE_DOUBLE = "double"
TYPE_BYTE = "byte"
TYPE_STRING = "string"

VALID_TYPES = [TYPE_INT, TYPE_INT64, TYPE_FLOAT, TYPE_DOUBLE,
               TYPE_BYTE, TYPE_STRING]


# ==================== ENTRY ====================
class HTEntry:
    def __init__(self):
        self.id = ""
        self.label = ""
        self.read = []          # ["modül+offset", "+offset", "+offset", ...]
        self.type = TYPE_INT
        self.value = 0
        self.mode = MODE_TOGGLE
        self.hotkey = ""
        self.description = ""
        self.repeat = 0         # 0 = yok, >0 = ms
        self.condition = ""     # Lua-like condition
        self.formula = ""       # Dinamik değer
        self.script = ""        # Lua script
        self.inject = ""        # Assembly
        self.hook_target = ""   # inject için
        self.enabled_by_default = False
        self.group = ""

    def to_dict(self):
        d = {
            "id": self.id,
            "label": self.label,
            "read": self.read if len(self.read) > 1 else (self.read[0] if self.read else ""),
            "type": self.type,
            "value": self.value,
            "mode": self.mode,
        }
        if self.hotkey:
            d["hotkey"] = self.hotkey
        if self.description:
            d["description"] = self.description
        if self.repeat:
            d["repeat"] = self.repeat
        if self.condition:
            d["condition"] = self.condition
        if self.formula:
            d["formula"] = self.formula
        if self.script:
            d["script"] = self.script
        if self.inject:
            d["inject"] = self.inject
        if self.hook_target:
            d["hook_target"] = self.hook_target
        if self.enabled_by_default:
            d["enabled_by_default"] = True
        return d

    @staticmethod
    def from_dict(d, group=""):
        e = HTEntry()
        e.id = d.get("id", "")
        e.label = d.get("label", "")
        read = d.get("read", "")
        if isinstance(read, str):
            e.read = [read] if read else []
        elif isinstance(read, list):
            e.read = read
        else:
            e.read = []
        e.type = d.get("type", TYPE_INT)
        e.value = d.get("value", 0)
        e.mode = d.get("mode", MODE_TOGGLE)
        e.hotkey = d.get("hotkey", "")
        e.description = d.get("description", "")
        e.repeat = d.get("repeat", 0)
        e.condition = d.get("condition", "")
        e.formula = d.get("formula", "")
        e.script = d.get("script", "")
        e.inject = d.get("inject", "")
        e.hook_target = d.get("hook_target", "")
        e.enabled_by_default = d.get("enabled_by_default", False)
        e.group = group
        return e

    def validate(self):
        """Hatayı (varsa) döndür, yoksa None"""
        if not self.label:
            return "Entry label boş"
        if not self.id:
            self.id = self.label.lower().replace(" ", "_")
        if self.mode not in VALID_MODES:
            return f"Geçersiz mode: {self.mode}"
        if self.type not in VALID_TYPES:
            return f"Geçersiz type: {self.type}"
        if self.mode in (MODE_TOGGLE, MODE_ACTION, MODE_FREEZE):
            if not self.read:
                return "read alanı boş"
        if self.mode == MODE_SCRIPT and not self.script:
            return "script mode için script gerekli"
        if self.mode == MODE_INJECT and not self.inject:
            return "inject mode için inject gerekli"
        return None


# ==================== GROUP ====================
class HTGroup:
    def __init__(self, name="Default", color="#00ff00"):
        self.name = name
        self.color = color
        self.entries = []

    def add(self, entry):
        entry.group = self.name
        self.entries.append(entry)

    def to_dict(self):
        return {
            "name": self.name,
            "color": self.color,
            "entries": [e.to_dict() for e in self.entries],
        }

    @staticmethod
    def from_dict(d):
        g = HTGroup(d.get("name", "Default"), d.get("color", "#00ff00"))
        for ed in d.get("entries", []):
            e = HTEntry.from_dict(ed, group=g.name)
            g.entries.append(e)
        return g


# ==================== HT TABLE ====================
class HTTable:
    def __init__(self):
        self.version = HT_VERSION
        self.name = "Untitled"
        self.author = ""
        self.game = ""
        self.language = "tr"
        self.created = datetime.now().strftime("%Y-%m-%d")
        self.groups = []

    def add_group(self, name, color="#00ff00"):
        g = HTGroup(name, color)
        self.groups.append(g)
        return g

    def find_group(self, name):
        for g in self.groups:
            if g.name == name:
                return g
        return None

    def find_entry(self, entry_id):
        for g in self.groups:
            for e in g.entries:
                if e.id == entry_id:
                    return e
        return None

    def to_dict(self):
        return {
            "version": self.version,
            "name": self.name,
            "author": self.author,
            "game": self.game,
            "language": self.language,
            "created": self.created,
            "groups": [g.to_dict() for g in self.groups],
        }

    def save(self, path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[HT] Save error: {e}")
            return False

    @staticmethod
    def load(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[HT] Load error: {e}")
            return None

        # v1 fallback
        if "addresses" in data and "groups" not in data:
            return HTTable._from_v1(data)

        # v2 fallback (groups var ama version yok)
        if "version" not in data:
            data["version"] = "2.0"

        t = HTTable()
        t.version = data.get("version", HT_VERSION)
        t.name = data.get("name", "Untitled")
        t.author = data.get("author", "")
        t.game = data.get("game", data.get("target_dll", ""))
        t.language = data.get("language", "tr")
        t.created = data.get("created", data.get("saved_at", ""))

        for gd in data.get("groups", []):
            t.groups.append(HTGroup.from_dict(gd))

        return t

    @staticmethod
    def _from_v1(data):
        """v1 (sadece addresses listesi) → v3"""
        t = HTTable()
        t.name = "Imported v1"
        t.game = data.get("target_dll", "")
        g = t.add_group("Imported", "#00aaff")
        for line in data.get("addresses", []):
            try:
                addr, val = line.split(" = ")
                e = HTEntry()
                e.id = f"addr_{addr.replace('0x', '')}"
                e.label = f"Addr {addr}"
                e.read = [addr]
                e.type = TYPE_INT
                e.value = int(val) if val.isdigit() else 0
                e.mode = MODE_TOGGLE
                g.add(e)
            except Exception:
                pass
        return t

    def validate(self):
        """Tüm entry'leri doğrula. Hataları liste olarak döndür."""
        errors = []
        for g in self.groups:
            for e in g.entries:
                err = e.validate()
                if err:
                    errors.append(f"{g.name} / {e.label}: {err}")
        return errors


# ==================== TEMPLATE ====================
def default_template():
    """Örnek HT şablonu"""
    t = HTTable()
    t.name = "Example Template"
    t.author = "Youd"
    t.game = "hl.exe"

    g1 = t.add_group("Player Stats", "#ff5555")
    e = HTEntry()
    e.id = "health"
    e.label = "Health 999"
    e.read = ["client.dll+0x992E4", "+0x7C", "+0x04", "+0x160"]
    e.type = TYPE_FLOAT
    e.value = 999.0
    e.mode = MODE_TOGGLE
    e.hotkey = "H"
    e.description = "Can 999"
    e.repeat = 100
    g1.add(e)

    g2 = t.add_group("Movement", "#55aaff")
    e = HTEntry()
    e.id = "fly"
    e.label = "Fly Mode (Noclip)"
    e.read = ["client.dll+0x992E4", "+0x7C", "+0x04", "+0x108"]
    e.type = TYPE_INT
    e.value = 8
    e.mode = MODE_TOGGLE
    e.hotkey = "F"
    e.description = "Uçma modu"
    e.repeat = 50
    g2.add(e)

    return t