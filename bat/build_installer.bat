@echo off
cd /d "%~dp0\.."

echo ========================================
echo HookEngine INSTALLER - DERLEME
echo ========================================
echo.

echo [0/5] Mevcut klasor: %CD%
echo.

echo [1/5] Gerekli dosyalar kontrol ediliyor...
if not exist "HookEngine\HookEngine.exe" (
    echo [-] HookEngine\HookEngine.exe BULUNAMADI!
    echo [+] Once bat\build.bat ile ana tool'u derleyin!
    pause
    exit
)

if not exist "ico\YoudHook.ico" (
    echo [-] ico\YoudHook.ico BULUNAMADI!
    pause
    exit
)

if not exist "installer\installer.py" (
    echo [-] installer\installer.py BULUNAMADI!
    pause
    exit
)

echo [2/5] Eski installer garbage'a tasiniyor...
if not exist "garbage" mkdir garbage
if exist "HookEngine\HookEngine_Setup.exe" (
    if exist "garbage\HookEngine_Setup_old.exe" del /q "garbage\HookEngine_Setup_old.exe"
    move "HookEngine\HookEngine_Setup.exe" "garbage\HookEngine_Setup_old.exe" >nul 2>nul
)

echo [3/5] Installer derleniyor...
python -m PyInstaller --onefile --windowed ^
    --icon="ico\YoudHook.ico" ^
    --name "HookEngine_Setup" ^
    --distpath "HookEngine" ^
    --workpath "garbage\build_installer" ^
    --specpath "garbage" ^
    --add-data "HookEngine\HookEngine.exe;." ^
    --add-data "ico\YoudHook.ico;." ^
    installer\installer.py

echo [4/5] Temizlik...
if exist "garbage\build_installer" rmdir /s /q "garbage\build_installer" 2>nul
if exist "garbage\HookEngine_Setup.spec" del /q "garbage\HookEngine_Setup.spec" 2>nul

echo [5/5] Tamamlandi!
echo.
echo ========================================
echo INSTALLER: HookEngine\HookEngine_Setup.exe
echo ========================================
pause