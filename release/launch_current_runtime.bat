@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\.."

set "CFG_PATH=%CD%\release\current_runtime.ini"
set "APP_NAME=GBT Pro"
set "APP_VERSION="
set "RELEASE_TAG="
set "RUNTIME_DIR="
set "RUNTIME_EXE="

if exist "%CFG_PATH%" (
    for /f "usebackq tokens=1* delims==" %%A in ("%CFG_PATH%") do (
        if /I "%%~A"=="APP_NAME" set "APP_NAME=%%~B"
        if /I "%%~A"=="APP_VERSION" set "APP_VERSION=%%~B"
        if /I "%%~A"=="RELEASE_TAG" set "RELEASE_TAG=%%~B"
        if /I "%%~A"=="RUNTIME_DIR" set "RUNTIME_DIR=%%~B"
        if /I "%%~A"=="RUNTIME_EXE" set "RUNTIME_EXE=%%~B"
    )
)

if defined RUNTIME_DIR set "RUNTIME_DIR_ABS=%CD%\%RUNTIME_DIR%"
if defined RUNTIME_EXE set "RUNTIME_EXE_ABS=%CD%\%RUNTIME_EXE%"
if not defined APP_VERSION set "APP_VERSION=v1.1.17"
if not defined RELEASE_TAG set "RELEASE_TAG=%APP_VERSION%-desktop-runtime"
set "GBT_ROLE=desktop"
set "BUILD_HASH=%APP_VERSION%"
set "GBT_RELEASE_TAG=%RELEASE_TAG%"
set "GBT_DATA_DIR=%CD%\data"
set "GBT_LOG_DIR=%CD%\logs"

rem 原子切换：先清理旧实例占用的端口，避免 current_runtime.ini 已切换但实际仍跑旧包
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /c:":8765 " ^| findstr /c:"LISTENING"') do (
    taskkill /PID %%P /F >nul 2>nul
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /c:":8766 " ^| findstr /c:"LISTENING"') do (
    taskkill /PID %%P /F >nul 2>nul
)
timeout /t 1 /nobreak >nul

if defined RUNTIME_EXE_ABS if exist "%RUNTIME_EXE_ABS%" (
    title %APP_NAME% %APP_VERSION%
    start "" "%RUNTIME_EXE_ABS%"
    exit /b 0
)

if exist ".venv\Scripts\pythonw.exe" (
    title %APP_NAME% %APP_VERSION%
    start "" ".venv\Scripts\pythonw.exe" "desktop_app.py"
    exit /b 0
)

if exist ".venv\Scripts\python.exe" (
    title %APP_NAME% %APP_VERSION%
    start "" ".venv\Scripts\python.exe" "desktop_app.py"
    exit /b 0
)

echo [X] %APP_NAME% launch failed.
echo     release\current_runtime.ini points to: %RUNTIME_EXE%
echo     No current runtime and no Python fallback were found.
exit /b 1
