<div align="center">

# 🔧 HookEngine v3.1

### Modern Game Hacking & Reverse Engineering Suite

**Hook Analysis · Memory Editor · HT Tables · Lua Scripting · Hardware Breakpoint Debugger · Code Injection**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6.svg)]()
[![Version](https://img.shields.io/badge/Version-3.1.0-green.svg)]()
[![Arch](https://img.shields.io/badge/Arch-x86%20%7C%20x64-lightgrey.svg)]()
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

*Cheat Engine alternative — modern UI, multi-threaded scanner, hardware breakpoint debugger, and a JSON-based cheat table format built for Unity / IL2CPP / GoldSrc / Source.*

[Overview](#-overview) · [Features](#-features) · [Installation](#-installation) · [Quick Start](#-quick-start) · [HT Format](#-ht-format) · [Architecture](#-architecture) · [Troubleshooting](#-troubleshooting) · [Changelog](#-changelog) · [License](#-license)

</div>

---

## 📖 Overview

**HookEngine** is a modern, open-source, Python-based alternative to Cheat Engine. It ships a full toolkit for game memory analysis, hook detection, and runtime manipulation — wrapped in a dark, native-feeling UI.

Designed for **reverse engineers, CTF players, and game-modding enthusiasts** who want:

- A **readable codebase** (pure Python, modular, one concern per file)
- A **scriptable** cheat engine (Lua + HT tables)
- **Deep visibility** into process internals (hooks, threads, modules, writes)
- **Zero-friction** packaging (single EXE via PyInstaller)

> ⚠️ **For educational and authorized reverse-engineering purposes only.** Test only on processes and games you own or have explicit permission to modify.

---

## ✨ Features

### 🎯 Hook Analysis

Detects and reports **7 classes** of runtime hooks across loaded modules:

| Type | Description |
|---|---|
| **IAT** | Import Address Table redirection |
| **EAT** | Export Address Table corruption |
| **Inline** | JMP / CALL / PUSH-RET patches |
| **VTable** | C++ virtual table overwrites |
| **Detour** | Microsoft Detours signatures |
| **Syscall** | ntdll SSN tampering |
| **Anti-Debug** | `IsDebuggerPresent`, `NtQueryInformationProcess`, timing checks |

Plus: **HOTPATCH**, **INT3** breakpoints, **PUSH RET** trampolines.

### 🧠 Memory Editor

Multi-type scanner with region-aware enumeration and multi-threaded search.

**Supported types:**

`INT` · `INT64` · `WORD` · `BYTE` · `FLOAT` · `DOUBLE` · `STRING` · `UTF16` · `AOB` · `POINTER`

**Scan filters:**

- **INCREASED / DECREASED / UNCHANGED / CHANGED**
- **Pointer scan** (multi-level chains)
- **AOB pattern** with wildcards (`E9 ?? ?? ?? ?? 90`)

**Operations:**

- Freeze (loop-write), Apply (batch write), Copy, HT export

### 📋 HT Table System

A proprietary, **JSON-based** cheat table format (`.ht`) — simpler than CE's `.CT` and AI-friendly.

- **Groups** with color tags
- **Entries** with pointer chains, hotkeys, repeat loops
- **8 execution modes**: `toggle`, `action`, `freeze`, `script`, `inject`, `formula`, `condition`, `multi`
- **Visual editor** built in

### 🧬 Who Writes? (Hardware Breakpoint Debugger)

Find **exactly which instruction** writes to a memory address.

- **HWBP (DR0)** via `DebugActiveProcess` — process-safe, no crashes
- Configurable **access type**: `WRITE` / `READWRITE` / `EXECUTE`
- Configurable **length**: 1 / 2 / 4 / 8 bytes
- Live thread snapshot with module+offset mapping

Also supports classic **polling mode** (`WhoWrites`) for cases where debugging is not allowed.

### 💉 DLL Injection

Three methods shipped out of the box:

1. **LoadLibrary** — classic, reliable
2. **Manual Map** — no `LoadLibrary`, no disk trace
3. **Thread Hijacking** — stealthier alternative

### 🐍 Lua Scripting

Embedded Lua engine (via `lupa`) with a rich API:

```lua
-- Auto-heal example
while true do
    local hp = readFloat(0x7FF6A1B2C3D4)
    if hp < 50 then
        writeFloat(0x7FF6A1B2C3D4, 100.0)
        log("healed")
    end
    sleep(100)
end
```

Available functions: `read*` / `write*` for every type, `resolve`, `sleep`, `log`.

### 💉 Code Injection

Inline hooks via **Keystone assembler** — write your own ASM payload, HookEngine builds the trampoline.

- **x86 / x64** support
- **Relative JMP** when in range
- **Absolute JMP (FF 25)** fallback for far addresses
- Original bytes preserved in trampoline — clean uninstall

### 🌐 Multilingual

Full **Turkish + English** UI, persistent via Windows registry.

### 🛡️ Admin Elevation

Auto-prompts UAC on startup — no manual right-click required.

### ⚡ Fast Scanner

Region-aware `VirtualQueryEx` enumeration + `ThreadPoolExecutor` parallel search.

- **256 KB chunk** streaming
- **N worker threads** (default `CPU × 2`, capped at 16)
- Up to **8× faster** than naive scanning on large process images

---

## 🚀 Installation

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| **Windows** | 10 / 11 (64-bit) | Win 7+ may work but untested |
| **Python** | 3.11+ (3.13 recommended) | [python.org](https://www.python.org/downloads/) |
| **Privileges** | Administrator | Required for memory operations |

### Quick Start

```bash
# 1) Clone
git clone https://github.com/YoudisCoding/HookEngine.git
cd HookEngine

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run as Administrator
python main.py
```

### Build Standalone EXE

```bash
bat\build.bat
# Output: HookEngine\HookEngine.exe

bat\build_installer.bat
# Output: HookEngine\HookEngine_Setup.exe
```

---

## 🎮 Quick Start

### 1. Attach to a process

```
[Left panel] → search for target → click SELECT
```

The status bar turns green and shows `Attached`.

### 2. Scan memory

```
[MEMORY tab]
  Type  = INT
  Value = 100
  Click SCAN
```

Now change the value in-game (e.g., take damage). Rescan with the new value.

```
Value = 75
Click SCAN
```

Repeat until few results remain → **FREEZE** or **APPLY**.

### 3. Find what writes

```
[MEMORY tab] → copy the address
[WHO WRITES tab]
  Address = 0x7FF6...
  Type    = int
  Mode    = Debugger (HWBP)
  Click START
```

Interact with the value in-game. The debugger pauses and reports the **RIP** of the writing instruction.

### 4. Build a cheat table

```
[HT TABLE tab]
  Ekle (Add)     → load an existing .ht
  HT CREATOR     → build a new one from scratch
  Tamam (OK)     → activate
```

---

## 📋 HT Format

### Minimal example

```json
{
  "version": "3.0",
  "name": "Half-Life Trainer",
  "author": "Youd",
  "game": "hl.exe",
  "language": "en",
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
          "description": "Health locked at 999",
          "repeat": 100
        }
      ]
    }
  ]
}
```

### Field reference

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique entry ID (auto-generated if omitted) |
| `label` | string | Display name |
| `read` | string[] | Address or pointer chain: `["module+offset", "+offset", ...]` |
| `addresses` | string[] | Alternative: multiple absolute addresses (for `multi` mode) |
| `type` | string | `int`, `int64`, `uint`, `uint64`, `float`, `double`, `byte`, `word`, `string` |
| `value` | any | Value to write |
| `mode` | string | See modes below |
| `hotkey` | string | Single-key shortcut (optional) |
| `repeat` | int | Loop interval in ms (0 = no loop) |
| `condition` | string | For `condition` mode: `current < 50` |
| `formula` | string | For `formula` mode: `current * 2` |
| `script` | string | For `script` mode: Lua code |
| `inject` | string | For `inject` mode: assembly payload |
| `hook_target` | string | For `inject` mode: `module+offset` |

### Modes

| Mode | Behavior |
|---|---|
| `toggle` | Write once on enable; loop if `repeat > 0` |
| `action` | Write once, done |
| `freeze` | Loop-write continuously |
| `script` | Run Lua script in a thread |
| `inject` | Install assembly inline hook |
| `formula` | Read → apply formula → write (loop) |
| `condition` | Write only when condition is true |
| `multi` | Write to multiple addresses simultaneously |

---

## 🏗️ Architecture

```
HookEngine/
├── main.py                      # Entry point (Tkinter UI + orchestration)
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
│
├── core/                        # Core engine
│   ├── __init__.py
│   ├── lang.py                  # TR/EN i18n (registry-persisted)
│   ├── process_manager.py       # psutil wrapper
│   ├── memory_engine.py         # ReadProcessMemory / WriteProcessMemory
│   ├── value_scanner.py         # UltraValueScanner (sequential)
│   ├── fast_scanner.py          # FastScanner (region-aware + parallel)
│   └── vip.py                   # Offline key + HWID + registry
│
├── hook/                        # Hook detection + write-tracing
│   ├── __init__.py
│   ├── hook_scanner.py          # ProfessionalHookScannerV5
│   ├── who_writes.py            # Polling-based watcher
│   ├── who_writes_ui.py         # UI tab for WhoWrites
│   └── who_writes_veh.py        # HWBP debugger (DebugActiveProcess)
│
├── ht/                          # HT Table system
│   ├── __init__.py
│   ├── ht_v3.py                 # Format v3 schema + validation
│   ├── ht_resolver.py           # Pointer chain resolver
│   ├── ht_engine.py             # Entry executor (8 modes)
│   ├── ht_lua.py                # Lua scripting engine
│   ├── ht_injector.py           # Inline hook + trampoline
│   ├── ht_ui_v3.py              # HT Table tab
│   └── ht_editor.py             # Visual HT editor
│
├── injector/                    # DLL injection
│   ├── __init__.py
│   └── dll_injector.py          # LoadLibrary / ManualMap / ThreadHijack
│
├── report/                      # Process report
│   ├── __init__.py
│   └── report_generator.py
│
├── installer/                   # Standalone installer
│   └── installer.py
│
├── bat/                         # Build scripts
│   ├── build.bat
│   ├── build_installer.bat
│   └── clean.bat
│
├── ico/
│   ├── YoudHook.ico
│   └── YoudHookVIP.ico
│
└── garbage/                     # Build leftovers (.gitignore'd)
```

### Design principles

- **One concern per file** — modules never span responsibilities
- **No hidden global state** — everything lives in explicit classes
- **Failures are values** — functions return `None` / `False` instead of throwing
- **Thread-safe where it matters** — locks protect shared handles and result buffers
- **Tk-safe** — long operations run on daemon threads, UI updates via `root.after`
- **Clean exit** — every injected hook, allocated region, and opened handle is tracked

---

## 🖥️ System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 (1809+) | Windows 11 22H2+ |
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Python | 3.11 | 3.13 |
| Privileges | Administrator | Administrator |
| Disk | 200 MB | 500 MB |

### Python dependencies

```
psutil>=5.9.8          # Process / thread enumeration
pywin32>=306           # Windows API helpers (shortcuts)
pefile>=2023.2.7       # PE header parsing
capstone>=5.0.1        # Disassembler
keystone-engine>=0.9.2 # Assembler (for injection)
lupa>=2.0              # Lua runtime
Pillow>=10.0           # Icon loading
pyinstaller>=6.0       # EXE packaging (dev only)
```

---

## ⚠️ Windows Warnings (NORMAL!)

**HookEngine.exe is not signed with an EV certificate.** Expect:

- **SmartScreen** → "Windows protected your PC"
- **Smart App Control** → "This app has been blocked"
- **Defender** → false-positive `Trojan:Win32/Wacatac.B!ml` (heuristic on PyInstaller bundles)
- **UAC** → Administrator prompt on launch

**This is normal for all game-modding tools** (Cheat Engine, Synapse, Script-Ware, etc.). EV certificates cost **$300–500/year**.

### Run anyway

**SmartScreen:**

```
Click "More info" → "Run anyway"
```

**Smart App Control (if blocking):**

```
Windows Security → App & browser control
  → Smart App Control → Settings → Off
```

**Defender exclusion:**

```
Windows Security → Virus & threat protection
  → Manage settings → Exclusions
  → Add folder → HookEngine\
```

**Prefer no warnings?** Run via Python — `python main.py`.

---

## 🔍 Troubleshooting

<details>
<summary><b>"Windows protected your PC" (SmartScreen)</b></summary>

Normal. Click **More info** → **Run anyway**. Add a Defender exclusion if it keeps triggering.

</details>

<details>
<summary><b>"This app has been blocked by Smart App Control"</b></summary>

SAC blocks unsigned binaries system-wide. Either:

- Disable SAC (Windows Security → App & browser control → SAC → Off)
- Or run from source: `python main.py`

Note: once disabled, SAC cannot be re-enabled without reinstalling Windows.

</details>

<details>
<summary><b>"OpenProcess failed" / "Access is denied"</b></summary>

Run HookEngine **as Administrator**. For protected games (EasyAntiCheat, BattlEye, Vanguard), the handle will still fail — this is by design of those anti-cheats.

</details>

<details>
<summary><b>ModuleNotFoundError: No module named 'lupa' / 'keystone'</b></summary>

```bash
pip install lupa keystone-engine
```

If running from a frozen EXE, rebuild with `bat\build.bat` after installing.

</details>

<details>
<summary><b>VCRUNTIME140.dll not found</b></summary>

Install the [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) (2015–2022).

</details>

<details>
<summary><b>Who Writes (HWBP) crashes the game</b></summary>

HWBP mode requires:

- Administrator privileges
- No other debugger attached (x64dbg, WinDbg, VS)
- Target not protected by an anti-debug (EasyAntiCheat, BattlEye, Hyperion)

If it still fails, fall back to **Polling mode** (slower but zero risk).

</details>

<details>
<summary><b>Hook injection reports "JMP too long"</b></summary>

The target address is more than ±2 GB from any allocatable region. HookEngine tries `VirtualAllocEx` near the target first, then falls back to a 14-byte absolute JMP (`FF 25 [rip+0]`). If both fail, the module's layout is unusual — report it as an issue.

</details>

<details>
<summary><b>UAC prompt appears every launch</b></summary>

By design — memory operations require `PROCESS_ALL_ACCESS`. Disable UAC globally only if you accept the security trade-off.

</details>

---

## 📝 Changelog

### v3.1.0 — Stability & Correctness Pass

**Fixes**

- `ht_resolver` — restored missing `import time`; class body cleaned
- `ht_resolver` — `_read_ptr` now sanity-checks pointer range (prevents garbage chain derefs)
- `ht_resolver` — added `read_batch()` for multi-entry polling
- `who_writes` — correct `PROCESS_ALL_ACCESS` (`0x1FFFFF`) + Windows 11 access flags
- `who_writes_veh` — **rewrote as real debugger** (`DebugActiveProcess` + `WaitForDebugEvent`); previous half-VEH version could crash the target
- `ht_injector` — proper trampoline: original bytes preserved, absolute JMP fallback, protection restored
- `fast_scanner` — zero-size region guard (infinite-loop fix)
- `ht_engine` — `action` mode now registers in `active_entries` for consistent toggling
- `ht_ui_v3` — `_update_values` uses batch read; refresh interval bumped to 800 ms
- `main.py` — WORD / BYTE overflow guards in `_write_by_type`; HT save now uses v3 schema

**Added**

- `HTResolver.read_batch()` — bulk read API
- `HTInjector._alloc_near()` — allocation within ±2 GB of target
- `WhoWritesHWBP` — hardware breakpoint debugger class

### v3.0.0 — HT v3 + Fast Scanner

- New HT format (groups + entries + 8 modes)
- `FastScanner` — parallel region-aware scanning
- HWBP + VEH experimentation
- Multi-language UI (TR / EN)
- VIP system (offline key + HWID)
- Installer + build scripts

### v2.0.0 — Modular refactor

- Split monolithic `main.py` into `core/`, `hook/`, `ht/`, `injector/`, `report/`
- HT format v2 (groups, colors, hotkeys)

### v1.0.0 — Initial release

- Memory scanner
- Basic hook detection

---

## 🛣️ Roadmap

- [ ] **RTTI scanner** — reconstruct C++ class hierarchies
- [ ] **IL2CPP metadata parser** — Unity Mono/IL2CPP symbol recovery
- [ ] **Signature maker** — auto-generate AOB signatures from addresses
- [ ] **Script recorder** — record/replay hotkey-driven cheats
- [ ] **Snapshot diff** — save process state, diff between two points
- [ ] **Vulkan / DX12 overlay** — in-game HUD for HT entries
- [ ] **Linux (Wine)** — best-effort compatibility
- [ ] **PySide6 UI port** — better HiDPI, native dark mode

---

## 🎯 Supported Games (tested)

| Game | Engine | Status | Notes |
|---|---|---|---|
| Half-Life | GoldSrc | ✅ Working | Static addresses stable |
| Half-Life 2 | Source | ✅ Working | Pointer chains required |
| Among Us | Unity IL2CPP | ✅ Working | Use `GameAssembly.dll` base |
| Phasmophobia | Unity IL2CPP | ✅ Working | IL2CPP metadata helpful |
| Any Unity Mono | Unity Mono | ✅ Working | Assembly-CSharp.dll |
| Any Unity IL2CPP | Unity IL2CPP | ✅ Working | Requires `GameAssembly.dll` |

**Not supported:** Any game protected by kernel-level anti-cheat (Vanguard, EasyAntiCheat, BattlEye, Hyperion/Byfron).

---

## 🛠️ Development

### Setup

```bash
git clone https://github.com/YoudisCoding/HookEngine.git
cd HookEngine
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Test imports

```bash
python -c "import core.lang, core.fast_scanner, hook.hook_scanner, hook.who_writes_veh, ht.ht_v3, ht.ht_resolver, ht.ht_engine, ht.ht_injector, injector.dll_injector, report.report_generator; print('OK')"
```

### Smoke test

```bash
python main.py
# Verify:
#  - Window opens, admin badge is green
#  - Process list populates
#  - Selecting a process updates the info bar
#  - Each tab renders without exceptions
```

### Code style

- **PEP 8** — enforced by convention
- **Type hints** — on public APIs
- **Comments** — only where the *why* is non-obvious
- **No dead code** — delete, don't comment out

### Build pipeline

```bash
bat\clean.bat            # clear caches + old builds
bat\build.bat            # PyInstaller → HookEngine\HookEngine.exe
bat\build_installer.bat  # Installer → HookEngine\HookEngine_Setup.exe
```

---

## 🤝 Contributing

1. Fork it
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Ways to contribute

- 🐛 Report bugs — [Issues](https://github.com/YoudisCoding/HookEngine/issues)
- 💡 Suggest features — [Issues](https://github.com/YoudisCoding/HookEngine/issues)
- 📝 Improve docs
- 🔧 Submit code
- 🎮 Share `.ht` files for games you've mapped
- 🌐 Add translations (currently TR / EN)

---

## 📜 License

**MIT License** — see [LICENSE](LICENSE) for full text.

---

## ⚠️ Disclaimer & Legal Notice

**HookEngine is provided for educational and authorized reverse-engineering purposes only.**

### All responsibility belongs to the user

By downloading, installing, or using HookEngine, you acknowledge that:

- You are **solely responsible** for how you use this software.
- You assume **all risks** — account bans, HWID bans, legal consequences, data loss, system damage, or ToS violations.
- The **developers and contributors are not liable** for any damage, illegal use, or consequences.
- You will **comply with all applicable laws** and **respect third-party ToS**.

### 🚫 Do not use HookEngine to

- Cheat in **online multiplayer** (violates ToS, causes bans)
- Bypass anti-cheat in competitive environments
- Harm, harass, or exploit other users
- Distribute malware or engage in illegal activity

### ✅ Acceptable uses

- Learn reverse engineering and memory manipulation
- Test on **your own** processes and applications
- Experiment in **single-player / offline** environments
- Develop your own games and tools
- Research software security and vulnerability analysis

### 🚨 Third-party distribution

If this software was modified, shared, or redistributed by a third party without authorization:

- The **original developers are not responsible** for any modifications
- The modified version **is not HookEngine** and may contain malicious code
- Only download from the **official GitHub repository**
- Redistribution must retain this license and disclaimer

### Legal agreement

By using HookEngine, you agree that:

1. You are at least 18 years old (or have parental consent)
2. You take full responsibility for your actions
3. You will not hold the developers liable
4. HookEngine is provided **"AS IS"** without warranty
5. You alone bear the consequences of use

---

**THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. IN NO EVENT SHALL THE AUTHORS, DEVELOPERS, OR CONTRIBUTORS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.**

**KULLANIMDAN DOĞAN TÜM SORUMLULUK KULLANICIYA AİTTİR.**

**BU YAZILIMI DEĞİŞTİRİP BAŞKASINA VEREN KİŞİNİN SORUMLULUĞU KENDİSİNE AİTTİR. ORİJİNAL GELİŞTİRİCİLER SORUMLU DEĞİLDİR.**

---

## 🙏 Credits

- **Youd** — creator, architect
- All contributors
- Reverse engineering community: **UnknownCheats**, **GuidedHacking**, **FearlessRevolution**, **ReClass.NET**

### Built with

- Python + Tkinter
- [psutil](https://github.com/giampaolo/psutil)
- [capstone](https://www.capstone-engine.org/)
- [keystone](https://www.keystone-engine.org/)
- [lupa](https://github.com/scoder/lupa)
- [pefile](https://github.com/erocarrera/pefile)

---

## 📞 Contact

- **GitHub:** [@YoudisCoding](https://github.com/YoudisCoding)
- **Discord:** `heisenberg_what`
- **Issues:** [github.com/YoudisCoding/HookEngine/issues](https://github.com/YoudisCoding/HookEngine/issues)

---

<div align="center">

**⭐ If HookEngine is useful to you, star the repo — it keeps the project alive. ⭐**

Made with ❤️ by reverse engineers, for reverse engineers.

</div>