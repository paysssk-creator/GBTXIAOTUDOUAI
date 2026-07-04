@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "APP_NAME=GBT Pro"
set "APP_VERSION=v1.1.18"
set "SOURCE_DIR=%~dp0"
set "SOURCE_EXE=%SOURCE_DIR%GBT_Pro_%APP_VERSION%.exe"

if not exist "%SOURCE_EXE%" (
    echo [X] Installer payload missing: %SOURCE_EXE%
    pause
    exit /b 1
)

if defined GBT_INSTALL_ROOT (
    set "INSTALL_ROOT=%GBT_INSTALL_ROOT%"
) else (
    set "INSTALL_ROOT=%LOCALAPPDATA%\GBT Pro"
)

set "INSTALL_DIR=%INSTALL_ROOT%\%APP_VERSION%"
set "LAUNCHER=%INSTALL_ROOT%\Launch GBT Pro.bat"
set "UNINSTALLER=%INSTALL_ROOT%\Uninstall GBT Pro.bat"

if defined GBT_DESKTOP_DIR (
    set "DESKTOP_DIR=%GBT_DESKTOP_DIR%"
) else (
    set "DESKTOP_DIR=%USERPROFILE%\Desktop"
)

echo.
echo ===========================================================
echo   %APP_NAME% %APP_VERSION% User Setup
echo ===========================================================
echo.
echo [1/4] Preparing install directories...
if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo [2/4] Copying application files...
copy /Y "%SOURCE_EXE%" "%INSTALL_DIR%\GBT_Pro_%APP_VERSION%.exe" >nul
if errorlevel 1 (
    echo [X] Failed to copy application file.
    pause
    exit /b 1
)

echo [3/4] Writing launcher and uninstaller...
(
    echo @echo off
    echo cd /d "%%~dp0\%APP_VERSION%"
    echo start "" "%%~dp0\%APP_VERSION%\GBT_Pro_%APP_VERSION%.exe"
) > "%LAUNCHER%"

(
    echo @echo off
    echo setlocal
    echo set "INSTALL_ROOT=%%~dp0"
    echo set "DESKTOP_LINK=%DESKTOP_DIR%\GBT Pro.lnk"
    echo if exist "%%DESKTOP_LINK%%" del /f /q "%%DESKTOP_LINK%%" ^>nul 2^>nul
    echo rmdir /s /q "%%INSTALL_ROOT%%\%APP_VERSION%" ^>nul 2^>nul
    echo del /f /q "%%~f0" ^>nul 2^>nul
    echo echo GBT Pro has been removed from this computer.
    echo pause
) > "%UNINSTALLER%"

echo [4/4] Creating desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$shortcut = $ws.CreateShortcut('%DESKTOP_DIR%\GBT Pro.lnk'); " ^
  "$shortcut.TargetPath = '%LAUNCHER%'; " ^
  "$shortcut.WorkingDirectory = '%INSTALL_ROOT%'; " ^
  "$shortcut.IconLocation = '%INSTALL_DIR%\GBT_Pro_%APP_VERSION%.exe,0'; " ^
  "$shortcut.Save()"
if errorlevel 1 (
    echo [X] Failed to create desktop shortcut.
    pause
    exit /b 1
)

echo.
echo [OK] Install complete.
echo      App dir : %INSTALL_DIR%
echo      Shortcut: %DESKTOP_DIR%\GBT Pro.lnk
echo.

if /I "%GBT_SKIP_LAUNCH%"=="1" exit /b 0

start "" "%LAUNCHER%"
exit /b 0
