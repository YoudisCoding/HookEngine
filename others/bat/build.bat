@echo off
cd /d "%~dp0\..\.."
color 0A

echo ========================================
echo   HookEngine v3.1 - BUILD
echo ========================================
echo.
echo [0/8] Root: %CD%
echo.

REM ==================== 1) DEPS ====================
echo [1/8] Installing dependencies...
pip install -r requirements.txt 2>nul

REM ==================== 2) ICON CHECK ====================
echo [2/8] Checking icon files...
if not exist "ico\YoudHook.ico" (
    echo [-] ico\YoudHook.ico NOT FOUND
    pause
    exit /b 1
)
echo [+] YoudHook.ico found

set VIP_ICON_ARG=
if exist "ico\YoudHookVIP.ico" (
    echo [+] YoudHookVIP.ico found
    set VIP_ICON_ARG=--add-data "ico\YoudHookVIP.ico;ico"
) else (
    echo [!] YoudHookVIP.ico not found
)

REM ==================== 3) CLEAN OLD ====================
echo [3/8] Moving old build to garbage...
if not exist "others\garbage" mkdir "others\garbage"
if exist "HookEngine" rmdir /s /q "HookEngine"
if exist "HookEngine.spec" del /q "HookEngine.spec"

REM ==================== 4) PRE-CHECK ====================
echo [4/8] Pre-check...
if not exist "main.py" (
    echo [-] main.py NOT FOUND
    pause
    exit /b 1
)
if not exist "src\core" (
    echo [-] src\core NOT FOUND
    pause
    exit /b 1
)

REM ==================== 5) BUILD ====================
echo [5/8] Building with PyInstaller...
python -m PyInstaller --onefile --windowed ^
  --icon="ico\YoudHook.ico" ^
  --name "HookEngine" ^
  --distpath "HookEngine" ^
  --workpath "others\garbage\build" ^
  --paths "src" ^
  --paths "others" ^
  --collect-all lupa ^
  --collect-all keystone ^
  --collect-all PIL ^
  --hidden-import lupa ^
  --hidden-import lupa.lua54 ^
  --hidden-import keystone ^
  --hidden-import PIL ^
  --hidden-import PIL.Image ^
  --hidden-import PIL.ImageTk ^
  --hidden-import PIL.ImageDraw ^
  --hidden-import core.lang ^
  --hidden-import core.memory_engine ^
  --hidden-import core.process_manager ^
  --hidden-import core.value_scanner ^
  --hidden-import core.fast_scanner ^
  --hidden-import core.vip ^
  --hidden-import hook.hook_scanner ^
  --hidden-import hook.who_writes ^
  --hidden-import hook.who_writes_ui ^
  --hidden-import hook.who_writes_veh ^
  --hidden-import ht.ht_v3 ^
  --hidden-import ht.ht_resolver ^
  --hidden-import ht.ht_engine ^
  --hidden-import ht.ht_lua ^
  --hidden-import ht.ht_injector ^
  --hidden-import ht.ht_ui_v3 ^
  --hidden-import ht.ht_editor ^
  --hidden-import injector.dll_injector ^
  --hidden-import report.report_generator ^
  --add-data "ico;ico" ^
  --add-data "src;src" ^
  %VIP_ICON_ARG% ^
  main.py

REM ==================== 6) CLEANUP ====================
echo [6/8] Cleaning up...
if exist "others\garbage\build" rmdir /s /q "others\garbage\build" 2>nul
if exist "HookEngine.spec" move "HookEngine.spec" "others\garbage\" >nul 2>nul

REM ==================== 7) VERIFY ====================
echo [7/8] Checking output...
if exist "HookEngine\HookEngine.exe" (
    echo [+] Build successful!
    echo [+] Output: HookEngine\HookEngine.exe
) else (
    echo [-] Build FAILED
)

echo [8/8] Done.
echo.
echo ========================================
echo   EXE: HookEngine\HookEngine.exe
echo ========================================
pause