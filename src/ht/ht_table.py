#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOUD HT TABLE SYSTEM — .ht v2.0 file format + reader/writer
Supports: groups, entries, actions (write/toggle/freeze/nop), hotkeys
"""

import json
import os
from datetime import datetime


HT_VERSION = "2.0"


class HTEntry:
    """Single entry in an HT table"""
    def __init__(self, label="", address="0x0", value=0, entry_type="int",
                 mode="action", action="write", description="",
                 hotkey="", checked=False, group="Default"):
        self.label = label
        self.address = address
        self.value = value
        self.entry_type = entry_type  # int/float/double/byte/string
        self.mode = mode              # action / toggle / freeze
        self.action = action          # write / nop / increment
        self.description = description
        self.hotkey = hotkey
        self.checked = checked
        self.group = group

    def to_dict(self):
        return {
            "label": self.label,
            "address": self.address,
            "value": self.value,
            "type": self.entry_type,
            "mode": self.mode,
            "action": self.action,
            "description": self.description,
            "hotkey": self.hotkey,
            "checked": self.checked,
        }

    @staticmethod
    def from_dict(d, group="Default"):
        e = HTEntry()
        e.label = d.get("label", "")
        e.address = d.get("address", "0x0")
        e.value = d.get("value", 0)
        e.entry_type = d.get("type", "int")
        e.mode = d.get("mode", "action")
        e.action = d.get("action", "write")
        e.description = d.get("description", "")
        e.hotkey = d.get("hotkey", "")
        e.checked = d.get("checked", False)
        e.group = group
        return e


class HTGroup:
    """Group of entries"""
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
            g.entries.append(HTEntry.from_dict(ed, group=g.name))
        return g


class HTTable:
    """Full HT table — groups + metadata"""
    def __init__(self):
        self.version = HT_VERSION
        self.target_dll = ""
        self.target_pid = 0
        self.saved_at = ""
        self.language = "en"
        self.groups = []

    def add_group(self, name, color="#00ff00"):
        g = HTGroup(name, color)
        self.groups.append(g)
        return g

    def to_dict(self):
        return {
            "version": self.version,
            "target_dll": self.target_dll,
            "target_pid": self.target_pid,
            "saved_at": self.saved_at or datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            "language": self.language,
            "groups": [g.to_dict() for g in self.groups],
        }

    def save(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return True

    @staticmethod
    def load(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # v1 fallback (old format — flat addresses list)
        if "addresses" in data and "groups" not in data:
            return HTTable._from_v1(data)

        t = HTTable()
        t.version = data.get("version", HT_VERSION)
        t.target_dll = data.get("target_dll", "")
        t.target_pid = data.get("target_pid", 0)
        t.saved_at = data.get("saved_at", "")
        t.language = data.get("language", "en")
        for gd in data.get("groups", []):
            t.groups.append(HTGroup.from_dict(gd))
        return t

    @staticmethod
    def _from_v1(data):
        """Convert old v1 format (addresses array) into v2 groups"""
        t = HTTable()
        t.target_dll = data.get("target_dll", "")
        t.target_pid = data.get("target_pid", 0)
        t.saved_at = data.get("saved_at", "")
        g = t.add_group("Imported", "#00aaff")
        for line in data.get("addresses", []):
            try:
                addr, val = line.split(" = ")
                e = HTEntry(
                    label=f"Addr {addr}",
                    address=addr,
                    value=int(val) if val.isdigit() else val,
                    entry_type="int",
                    mode="action",
                    action="write",
                    description=""
                )
                g.add(e)
            except Exception:
                pass
        return t


# ==================== DEFAULT TEMPLATE ====================
def default_template():
    """A sample .ht table for users to see structure"""
    t = HTTable()
    t.language = "tr"

    g1 = t.add_group("Player Stats", "#ff5555")
    g1.add(HTEntry(
        label="Health Full", address="0x0", value=100, entry_type="int",
        mode="action", action="write",
        description="Canını 100 yapar", hotkey="H"
    ))
    g1.add(HTEntry(
        label="Infinite Ammo", address="0x0", value=999, entry_type="int",
        mode="toggle", action="write",
        description="Mermi tükenmez", hotkey="M"
    ))

    g2 = t.add_group("Movement", "#55aaff")
    g2.add(HTEntry(
        label="Fly Mode", address="0x0", value=1, entry_type="byte",
        mode="toggle", action="write",
        description="Uçma modu aktif", hotkey="F"
    ))
    g2.add(HTEntry(
        label="Super Speed", address="0x0", value=5, entry_type="float",
        mode="action", action="write",
        description="Hızı 5x yapar", hotkey=""
    ))

    g3 = t.add_group("Visuals", "#55ff55")
    g3.add(HTEntry(
        label="ESP Box", address="0x0", value=1, entry_type="byte",
        mode="toggle", action="write",
        description="Düşmanları kutu içine alır", hotkey=""
    ))
    g3.add(HTEntry(
        label="Wallhack", address="0x0", value=1, entry_type="byte",
        mode="toggle", action="write",
        description="Duvarları görmezden gel", hotkey=""
    ))

    return t