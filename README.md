<div align="center">

# 🔧 HookEngine v3.0

### Modern Game Hacking Suite
**Hook Analysis · Memory Editor · HT Tables · Lua Scripting · Code Injection**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg)]()
[![Version](https://img.shields.io/badge/Version-3.0.0-green.svg)]()

*Cheat Engine alternative with modern UI, hook scanner, and Unity/IL2CPP support*

[Features](#-features) · [Installation](#-installation) · [Usage](#-usage) · [HT Format](#-ht-format) · [Troubleshooting](#-troubleshooting) · [Disclaimer](#-disclaimer--legal-notice)

</div>

---

## 📖 What is HookEngine?

**HookEngine** is a modern, open-source alternative to Cheat Engine, focused on:

- 🎯 **Hook Analysis** — IAT, EAT, Inline, VTable, Detour, Syscall, Anti-Debug detection
- 🧠 **Memory Editor** — Multi-type scanning, pointer scan, filtering
- 📋 **HT Tables** — Our own JSON-based cheat table format (`.ht`)
- 🎮 **Game Hacking** — For Unity, IL2CPP, and GoldSrc games
- 🌐 **Multilingual** — Turkish + English
- 🔌 **DLL Injection** — LoadLibrary, Manual Map, Thread Hijacking
- 🐍 **Lua Scripting** — Custom scripts for advanced automation
- 💉 **Code Injection** — Hook installation with Keystone assembler

> ⚠️ **For educational and reverse engineering purposes only. Use responsibly.**

---

## ✨ Features

### Core

| Feature | Status | Description |
|---|---|---|
| Hook Scanner | ✅ | 7 hook types detection |
| Memory Editor | ✅ | Multi-type value scanning + filtering |
| HT Table System | ✅ | Custom `.ht` format (JSON-based) |
| HT Editor | ✅ | Visual cheat table editor |
| DLL Injector | ✅ | 3 injection methods |
| Pointer Chain | ✅ | Multi-level pointer resolution |
| Lua Scripting | ✅ | Custom script engine (via lupa) |
| Code Injection | ✅ | Assembly injection with Keystone |
| Multilingual | ✅ | Turkish + English |
| Admin Elevation | ✅ | Automatic UAC prompt |

### Hook Types Detected

- **IAT** — Import Address Table hooks
- **EAT** — Export Address Table hooks
- **Inline** — JMP/CALL/PUSH-RET patterns
- **VTable** — Virtual table hooks
- **Detour** — Microsoft Detours signatures
- **Syscall** — ntdll syscall hooks
- **Anti-Debug** — Debugger detection APIs

### Value Types Supported

`INT` · `INT64` · `FLOAT` · `DOUBLE` · `BYTE` · `STRING` · `AOB` · `POINTER`

---

## 🚀 Installation

### Prerequisites

- **Windows 10/11** (64-bit)
- **Python 3.13+** ([Download](https://www.python.org/downloads/))
- **Administrator privileges** (required for memory operations)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/HookEngine.git
cd HookEngine

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run (as Administrator!)
python main.py
```

### Build EXE

```bash
# Build standalone executable
bat\build.bat

# Output: HookEngine\HookEngine.exe

# Build installer
bat\build_installer.bat

# Output: HookEngine\HookEngine_Setup.exe
```

---

## ⚠️ IMPORTANT — Windows Warnings (NORMAL!)

**HookEngine.exe is NOT signed with an EV (Extended Validation) certificate.**

**This means Windows will show warnings.** This is **NORMAL** and **EXPECTED** for all game hacking tools.

**Almost all cheat tools (Cheat Engine, Synapse, Script-Ware, etc.) are unsigned or self-signed.**

### 🛡️ Why the Warnings?

Windows uses several security layers to protect users:
- **SmartScreen** — Reputation-based blocking
- **Smart App Control (SAC)** — Signature-based blocking
- **Windows Defender** — Antivirus protection
- **UAC** — Administrator privilege prompts

**Unsigned tools** → trigger these systems → **warnings appear.**

**EV certificates cost $300-500/year** (~10.000-15.000 TL) — too expensive for free/open-source projects.

---

## 🔧 How to Run HookEngine (3 Methods)

### Method 1: "Run Anyway" (Fastest)

When SmartScreen warning appears:

1. Click **"More info"** (Daha fazla bilgi)
2. Click **"Run anyway"** (Yine de çalıştır)
3. UAC prompt appears → Click **"Yes"** (Evet)

**Done.** HookEngine will launch.

### Method 2: Disable Smart App Control

If Smart App Control blocks HookEngine:

1. **Start** → **Windows Security** (Windows Güvenliği)
2. **App & browser control** (Uygulama ve tarayıcı denetimi)
3. **Smart App Control** → **Settings** → **Off** (Kapalı)
4. Restart Windows

**Note:** Once disabled, Smart App Control cannot be re-enabled without reinstalling Windows.

### Method 3: Use Python (Recommended for Tech-Savvy Users)

If you have Python installed:

```bash
# 1. Download source
git clone https://github.com/YOUR_USERNAME/HookEngine.git
cd HookEngine

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

**Python interpreter** → **Microsoft-signed** → **no SmartScreen warnings** ✅

### Method 4: Add Windows Defender Exclusion

If Windows Defender blocks HookEngine:

1. **Windows Security** → **Virus & threat protection**
2. **Manage settings** → **Exclusions** → **Add exclusion**
3. **Add file** → `HookEngine.exe`
4. **Add folder** → `HookEngine\` folder

**Note:** Smart App Control is separate from Defender. If SAC is on, exclusions won't help.

---

## 🔍 Troubleshooting

### "Windows protected your PC" (SmartScreen)

**Normal.** Click **"More info" → "Run anyway"**.

### "This app has been blocked by Smart App Control"

**Normal.** Smart App Control blocks unsigned tools.
- **Option A:** Disable Smart App Control (Method 2 above)
- **Option B:** Run via Python (Method 3 above)

### "Windows Defender detected a threat"

**False positive.** Common with hacking tools.
- **Option A:** Add exclusion (Method 4 above)
- **Option B:** Temporarily disable Defender
- **Option C:** Upload to VirusTotal to verify

### "UAC prompt keeps appearing"

**Normal.** HookEngine requires Administrator for:
- Memory read/write
- Process manipulation
- DLL injection
- Registry access

### "lupa / keystone error on startup"

**If running from EXE:**
- Rebuild with latest `bat\build.bat`
- Or run via Python: `python main.py`

**If running from Python:**
- `pip install lupa keystone-engine`

### "ModuleNotFoundError: No module named 'X'"

Install missing dependency:
```bash
pip install -r requirements.txt
```

### "Access is denied" / "OpenProcess failed"

**Solution:** Run HookEngine as Administrator (right-click → Run as administrator).

### "VCRUNTIME140.dll not found"

Install **Microsoft Visual C++ Redistributable 2015-2022**:
- [Download from Microsoft](https://aka.ms/vs/17/release/vc_redist.x64.exe)

---

## 📖 Usage

### 1. Select a Process

```
1. Run HookEngine as Administrator
2. Find your target process in the left panel
3. Click SELECT
```

### 2. Memory Scanning

```
1. Go to MEMORY EDITOR tab
2. Choose type (INT, FLOAT, etc.)
3. Enter value (e.g. 100)
4. Click SCAN
5. In-game: change value (e.g. take damage → 75)
6. Enter new value (75), click SCAN again
7. Repeat until few results remain
8. Click APPLY or FREEZE
```

### 3. Hook Analysis

```
1. Go to HOOK ANALYSIS tab
2. Choose mode: QUICK / FULL / IMPORTANT / FILTERED
3. Click scan
4. Results appear in output panel
```

### 4. HT Tables

```
1. Go to HT TABLE tab
2. Click Ekle (Add) → select .ht file
3. Click Tamam (OK) → buttons appear
4. Toggle cheats on/off
```

### 5. HT Editor

```
1. Click HT OLUŞTURUCU (top nav)
2. Add groups and entries
3. Save as .ht file
```

---

## 📋 HT Format

HookEngine uses its own **JSON-based** cheat table format (`.ht`). Much simpler than Cheat Engine's `.CT`.

### Example

```json
{
  "version": "3.0",
  "name": "Half-Life Trainer",
  "author": "Youd",
  "game": "hl.exe",
  "language": "tr",
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
          "repeat": 100
        }
      ]
    }
  ]
}
```

### Key Fields

| Field | Type | Description |
|---|---|---|
| `read` | string[] | Address or pointer chain: `["module+offset", "+offset", ...]` |
| `type` | string | `int`, `int64`, `float`, `double`, `byte`, `string` |
| `value` | any | Value to write |
| `mode` | string | `toggle`, `action`, `freeze`, `script`, `inject`, `formula`, `condition` |
| `hotkey` | string | Keyboard shortcut (optional) |
| `repeat` | int | Loop interval in ms (optional, 0 = no loop) |
| `description` | string | Tooltip / description (optional) |

### Modes Explained

- **`toggle`** — Checkbox: write once on enable
- **`action`** — Button: write once, then stop
- **`freeze`** — Loop-write continuously
- **`script`** — Run Lua script
- **`inject`** — Install assembly hook
- **`formula`** — Dynamic value (e.g. `current * 2`)
- **`condition`** — Write only if condition met (e.g. `current < 50`)

---

## 🏗️ Project Structure

```
HookEngine/
├── main.py                  # Entry point
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
│
├── core/                    # Core modules
│   ├── lang.py
│   ├── memory_engine.py
│   ├── process_manager.py
│   └── value_scanner.py
│
├── hook/                    # Hook analysis
│   ├── hook_scanner.py
│   ├── who_writes.py
│   └── who_writes_ui.py
│
├── ht/                      # HT Table system
│   ├── ht_v3.py
│   ├── ht_resolver.py
│   ├── ht_engine.py
│   ├── ht_lua.py
│   ├── ht_injector.py
│   ├── ht_ui_v3.py
│   └── ht_editor.py
│
├── injector/                # DLL injection
│   └── dll_injector.py
│
├── report/                  # Report generation
│   └── report_generator.py
│
├── installer/               # Installer script
│   └── installer.py
│
├── bat/                     # Build scripts
│   ├── build.bat
│   ├── build_installer.bat
│   └── clean.bat
│
├── ico/                     # Icons
│   └── YoudHook.ico
│
└── garbage/                 # Build leftovers (.gitignore'd)
```

---

## 🎯 Supported Games

HookEngine works with **any Windows game or application** you have permission to modify. Tested with:

| Game | Engine | Status |
|---|---|---|
| Half-Life | GoldSrc | ✅ Working |
| Half-Life 2 | Source | ✅ Working |
| Among Us | Unity IL2CPP | ✅ Working |
| Phasmophobia | Unity IL2CPP | ✅ Working |
| Any Unity Mono game | Unity Mono | ✅ Working |
| Any Unity IL2CPP game | Unity IL2CPP | ✅ Working |

---

## 🛠️ Development

### Requirements

- Python 3.13+
- `psutil` — Process management
- `pywin32` — Windows API
- `pefile` — PE parsing
- `capstone` — Disassembly
- `lupa` — Lua scripting
- `keystone-engine` — Assembler
- `pyinstaller` — EXE packaging

### Code Style

- **Python** — PEP 8
- **Comments** — Only when necessary
- **Architecture** — Modular, one concern per file

### Testing

```bash
# Test imports
python -c "import core.lang; import hook.hook_scanner; import ht.ht_v3; print('OK')"

# Run main
python main.py
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Ways to Contribute

- 🐛 Report bugs (Issues)
- 💡 Suggest features (Issues)
- 📝 Improve documentation
- 🔧 Submit code (Pull Requests)
- 🎮 Share `.ht` files for games
- 🌐 Add translations

---

## 📜 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer & Legal Notice

**HookEngine is provided for educational and reverse engineering purposes only.**

### ⚖️ All Responsibility Belongs to the User

**By downloading, installing, or using HookEngine, you acknowledge and agree that:**

- ⚠️ **You are solely responsible** for how you use this software.
- ⚠️ **You assume all risks** associated with using HookEngine, including but not limited to:
  - Account bans or suspensions
  - Hardware bans (HWID bans)
  - Legal consequences
  - Data loss or system damage
  - Violation of any third-party terms of service
- ⚠️ **The developers, contributors, and maintainers of HookEngine** are **NOT responsible** for:
  - Any damage caused by this software
  - Any illegal use of this software
  - Any violation of laws or terms of service by users
  - Any consequences resulting from the use of this software
  - **Any distribution of this software by third parties**
  - **Any modification of this software by third parties**
  - **Any unauthorized sharing of this software**
- ⚠️ **You must comply with all applicable laws** in your jurisdiction.
- ⚠️ **You must respect the terms of service** of any software or game you interact with.

### 🚫 Prohibited Uses

**DO NOT use HookEngine to:**

- ❌ Cheat in **online multiplayer games** (violates ToS, causes bans)
- ❌ Harm, harass, or exploit other users
- ❌ Bypass anti-cheat systems in competitive environments
- ❌ Violate any law, regulation, or third-party agreement
- ❌ Distribute malware or engage in illegal activities

### ✅ Acceptable Uses

**You may use HookEngine to:**

- ✅ Learn **reverse engineering** and **memory manipulation**
- ✅ Test on **your own processes** and applications
- ✅ Experiment in **single-player / offline** environments
- ✅ Develop **your own games** and tools
- ✅ Research **software security** and **vulnerability analysis**

### 🚨 Third-Party Distribution Notice

**IMPORTANT:** If this software was **modified, shared, or distributed** by a third party without authorization:

- ⚠️ **The original developers are NOT responsible** for any modifications
- ⚠️ **The original developers are NOT responsible** for any consequences of unauthorized distribution
- ⚠️ **The modified version is NOT the original HookEngine** and may contain malicious code
- ⚠️ **Users should only download HookEngine from the official GitHub repository**
- ⚠️ **Any redistribution must retain this license and disclaimer intact**

**If someone secretly modified this software and gave it to you, the responsibility is entirely theirs — not the original developers'.**

### 📜 Legal Agreement

**BY USING HOOKENGINE, YOU AGREE THAT:**

1. You are at least **18 years old** (or have parental consent)
2. You take **full responsibility** for your actions
3. You will **not hold the developers liable** for any consequences
4. You understand that **HookEngine is provided "AS IS"** without warranty
5. You accept that **you alone** bear the consequences of using this software
6. You acknowledge that **any modified or redistributed versions are not the responsibility of the original developers**

---

**THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. IN NO EVENT SHALL THE AUTHORS, DEVELOPERS, OR CONTRIBUTORS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.**

**KULLANIMDAN DOĞAN TÜM SORUMLULUK KULLANICIYA AİTTİR.**

**BU YAZILIMI DEĞİŞTİRİP BAŞKASINA VEREN KİŞİNİN SORUMLULUĞU KENDİSİNE AİTTİR. ORİJİNAL GELİŞTİRİCİLER SORUMLU DEĞİLDİR.**

**All responsibility arising from use belongs to the user.**

**Any third party who modifies and redistributes this software assumes full responsibility.**

---

## 🙏 Credits

- **Youd** — Creator
- All contributors

### Thanks to

- Python community
- Reverse engineering community
- FearlessRevolution, UnknownCheats, GuidedHacking

---

## 📞 Contact

- **GitHub:** [@YoudisCoding](https://github.com/YoudisCoding)
- **Discord:** `heisenberg_what`
- **Issues:** [GitHub Issues](https://github.com/YoudisCoding/HookEngine/issues)

---

<div align="center">

**⭐ If you find HookEngine useful, please star the repository! ⭐**

Made with ❤️ by reverse engineers, for reverse engineers.

</div>