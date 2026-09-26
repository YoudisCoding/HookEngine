@echo off
cd /d "%~dp0\.."

echo ========================================
echo HookEngine v3.0 - BUILD
echo ========================================
echo.

echo [0/7] Current directory: %CD%
echo.

echo [1/7] Installing dependencies...
pip install -r requirements.txt 2>nul

echo [2/7] Checking icon files...
if exist "ico\YoudHook.ico" (
    echo [+] YoudHook.ico found
) else (
    echo [-] YoudHook.ico NOT FOUND - put it in ico\ folder!
    pause
    exit /b
)

set VIP_ICON_ARG=
if exist "ico\YoudHookVIP.ico" (
    echo [+] YoudHookVIP.ico found
    set VIP_ICON_ARG=--add-data "ico\YoudHookVIP.ico;ico"
) else (
    echo [!] YoudHookVIP.ico not found - VIP logo will use default
)

echo [3/7] Moving old build to garbage...
if not exist "garbage" mkdir garbage
if exist "HookEngine" (
    if exist "garbage\HookEngine_old" rmdir /s /q "garbage\HookEngine_old"
    move "HookEngine" "garbage\HookEngine_old" >nul 2>nul
)
if exist "HookEngine.spec" move "HookEngine.spec" "garbage\" >nul 2>nul

echo [4/7] Building with PyInstaller...
python -m PyInstaller --onefile --windowed ^
  --icon="ico\YoudHook.ico" ^
  --name "HookEngine" ^
  --distpath "HookEngine" ^
  --workpath "garbage\build" ^
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
  --add-data "ico\YoudHook.ico;ico" ^
  %VIP_ICON_ARG% ^
  --add-data "core;core" ^
  --add-data "hook;hook" ^
  --add-data "ht;ht" ^
  --add-data "injector;injector" ^
  --add-data "report;report" ^
  --add-data "kernel;kernel" ^
  main.py

echo [5/7] Cleaning up...
if exist "garbage\build" rmdir /s /q "garbage\build" 2>nul
if exist "HookEngine.spec" move "HookEngine.spec" "garbage\" >nul 2>nul

echo [6/7] Checking output...
if exist "HookEngine\HookEngine.exe" (
    echo [+] Build successful!
    echo [+] Output: HookEngine\HookEngine.exe
) else (
    echo [-] Build FAILED - no exe created
    echo [!] Try running with --console to see errors
)

echo [7/7] Done.
echo.
echo ========================================
echo EXE: HookEngine\HookEngine.exe
echo ========================================
pause