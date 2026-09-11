@echo off
cd /d "%~dp0\.."

echo ========================================
echo HookEngine v3.0 - DERLEME
echo ========================================
echo.

echo [0/6] Mevcut klasor: %CD%
echo.

echo [1/6] Kutuphaneler...
pip install -r requirements.txt 2>nul

echo [2/6] Ikon kontrol...
if exist "ico\YoudHook.ico" (
    echo [+] Ikon bulundu
) else (
    echo [-] Ikon YOK - ico\YoudHook.ico dosyasini koyun!
    pause
    exit
)

echo [3/6] Eski cikti garbage'a tasiniyor...
if not exist "garbage" mkdir garbage
if exist "HookEngine" (
    if exist "garbage\HookEngine_old" rmdir /s /q "garbage\HookEngine_old"
    move "HookEngine" "garbage\HookEngine_old" >nul 2>nul
)
if exist "HookEngine.spec" move "HookEngine.spec" "garbage\" >nul 2>nul

echo [4/6] PyInstaller ile derleniyor...
python -m PyInstaller --onefile --windowed --icon="ico\YoudHook.ico" --name "HookEngine" --distpath "HookEngine" --workpath "garbage\build" --collect-all lupa --hidden-import lupa --hidden-import lupa.lua54 --hidden-import keystone --collect-all keystone --add-data "ico\YoudHook.ico;ico" --add-data "core;core" --add-data "hook;hook" --add-data "ht;ht" --add-data "injector;injector" --add-data "report;report" main.py

echo [5/6] Temizlik...
if exist "garbage\build" rmdir /s /q "garbage\build" 2>nul
if exist "HookEngine.spec" move "HookEngine.spec" "garbage\" >nul 2>nul

echo [6/6] Tamamlandi!
echo.
echo ========================================
echo EXE: HookEngine\HookEngine.exe
echo ========================================
pause