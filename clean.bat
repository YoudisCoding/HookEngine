@echo off
cd /d "%~dp0\.."

echo ========================================
echo HookEngine - TEMIZLIK
echo ========================================
echo.

if not exist "garbage" mkdir garbage

echo [1/5] Python cache temizleniyor...
if exist "__pycache__" (
    if exist "garbage\__pycache__" rmdir /s /q "garbage\__pycache__"
    move "__pycache__" "garbage\__pycache__" >nul 2>nul
)
if exist "core\__pycache__" (
    if exist "garbage\core_pycache" rmdir /s /q "garbage\core_pycache"
    move "core\__pycache__" "garbage\core_pycache" >nul 2>nul
)
if exist "hook\__pycache__" (
    if exist "garbage\hook_pycache" rmdir /s /q "garbage\hook_pycache"
    move "hook\__pycache__" "garbage\hook_pycache" >nul 2>nul
)
if exist "ht\__pycache__" (
    if exist "garbage\ht_pycache" rmdir /s /q "garbage\ht_pycache"
    move "ht\__pycache__" "garbage\ht_pycache" >nul 2>nul
)
if exist "injector\__pycache__" (
    if exist "garbage\injector_pycache" rmdir /s /q "garbage\injector_pycache"
    move "injector\__pycache__" "garbage\injector_pycache" >nul 2>nul
)
if exist "report\__pycache__" (
    if exist "garbage\report_pycache" rmdir /s /q "garbage\report_pycache"
    move "report\__pycache__" "garbage\report_pycache" >nul 2>nul
)
if exist "installer\__pycache__" (
    if exist "garbage\installer_pycache" rmdir /s /q "garbage\installer_pycache"
    move "installer\__pycache__" "garbage\installer_pycache" >nul 2>nul
)

echo [2/5] PyInstaller ciktilari...
if exist "build" (
    if exist "garbage\build" rmdir /s /q "garbage\build"
    move "build" "garbage\build" >nul 2>nul
)
if exist "dist" (
    if exist "garbage\dist" rmdir /s /q "garbage\dist"
    move "dist" "garbage\dist" >nul 2>nul
)

echo [3/5] Spec dosyalari...
if exist "*.spec" move "*.spec" "garbage\" >nul 2>nul
if exist "HookEngine.spec" move "HookEngine.spec" "garbage\" >nul 2>nul

echo [4/5] Gecici dosyalar...
if exist "*.log" move "*.log" "garbage\" >nul 2>nul
if exist "*.tmp" move "*.tmp" "garbage\" >nul 2>nul
if exist "*.bak" move "*.bak" "garbage\" >nul 2>nul
if exist "*.old" move "*.old" "garbage\" >nul 2>nul

echo [5/5] Garbage boyutu:
dir "garbage" /s 2>nul | findstr "File(s)"

echo.
echo ========================================
echo TEMIZLIK TAMAMLANDI
echo Cop dosyalar: garbage\
echo ========================================
pause