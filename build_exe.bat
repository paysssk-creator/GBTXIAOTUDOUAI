@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title GBT Pro v2.1 - Build Standalone EXE

echo.
echo ╔══════════════════════════════════════════════╗
echo ║   GBT Pro v2.1 -- PyInstaller Build Tool    ║
echo ╠══════════════════════════════════════════════╣
echo ║  Output: dist\GBT_Pro.exe                    ║
echo ╚══════════════════════════════════════════════╝
echo.

:: Step 0: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH!
    pause & exit /b 1
)
echo [1/5] Python found: 
python --version

:: Step 1: Install build deps
echo.
echo [2/5] Installing build dependencies...
pip install pyinstaller pywebview flask psutil python-dotenv Pillow pyautogui ^
    pyttsx3 SpeechRecognition pyperclip ollama openai requests ^
    2>&1 | findstr /v "already satisfied Requirement"

:: Step 2: Check .env exists (warn if not)
echo.
echo [3/5] Checking configuration...
if not exist ".env" (
    echo [WARNING] .env file not found! Copy .env.example to .env and configure API keys.
    echo          Without API keys, LLM features will not work.
    echo.
)

if exist ".env.example" if not exist ".env" (
    copy /y ".env.example" ".env" >nul 2>&1
    echo [INFO] Created .env from .env.example. Please edit .env with your API keys.
)

:: Step 3: Clean previous builds
echo.
echo [4/5] Cleaning previous build...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" (
    for %%f in ("GBT_Pro_*.spec") do del /f /q "%%f" 2>nul
)

:: Step 4: Build with PyInstaller
echo.
echo [5/5] Building GBT_Pro.exe (this may take 3-10 minutes)...
echo.
pyinstaller --clean --noconfirm GBT_Desktop.spec

if errorlevel 1 (
    echo.
    echo ╔══════════════════════════════════════════════╗
    echo ║   BUILD FAILED!                              ║
    echo ╠══════════════════════════════════════════════╣
    echo ║  Check errors above.                         ║
    echo ║  Try: pip install --upgrade pyinstaller      ║
    echo ╚══════════════════════════════════════════════╝
    pause
    exit /b 1
)

:: Step 5: Verify output
if exist "dist\GBT_Pro.exe" (
    for %%A in ("dist\GBT_Pro.exe") do set "SIZE=%%~zA"
    set /a SIZE_MB=!SIZE!/1048576
    echo.
    echo ╔══════════════════════════════════════════════╗
    echo ║   BUILD SUCCESS!                             ║
    echo ╠══════════════════════════════════════════════╣
    echo ║  dist\GBT_Pro.exe  (!SIZE_MB! MB)              ║
    echo ║                                              ║
    echo ║  Distribute this file to users.              ║
    echo ║  They need: Windows 10+, no Python needed.   ║
    echo ╚══════════════════════════════════════════════╝
) else (
    echo [ERROR] dist\GBT_Pro.exe not found! Build may have silently failed.
)

echo.
echo ════════════════════════════════════════════════════
echo   PIP package build: python -m build
echo   Upload to PyPI:    twine upload dist/*
echo ════════════════════════════════════════════════════
pause
