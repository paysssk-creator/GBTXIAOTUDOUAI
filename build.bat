@echo off
REM ═══════════════════════════════════════════════════════
REM  GBT 全家桶 — 一键专业构建脚本
REM  产出: dist\GBT.exe (单文件) + dist\installer\GBT-Setup-v*.exe
REM ═══════════════════════════════════════════════════════
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║     GBT 全家桶 专业构建 v1.5.1           ║
echo   ╚══════════════════════════════════════════╝
echo.

REM ─── Step 1: 环境检查 ───
echo [1/5] 检查环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ERROR: Python 未找到，请安装 Python 3.10+
    pause & exit /b 1
)
echo   Python: OK

REM ─── Step 2: 安装构建依赖 ───
echo.
echo [2/5] 安装构建依赖...
pip install pyinstaller>=6.0 -q
if %errorlevel% neq 0 (
    echo   ERROR: PyInstaller 安装失败
    pause & exit /b 1
)
echo   PyInstaller: OK

REM ─── Step 3: PyInstaller 打包 ───
echo.
echo [3/5] PyInstaller 打包中... (约 2-5 分钟)
pyinstaller --clean --noconfirm gbt.spec
if %errorlevel% neq 0 (
    echo   ERROR: PyInstaller 构建失败，查看日志
    pause & exit /b 1
)

if not exist "dist\GBT.exe" (
    echo   ERROR: dist\GBT.exe 未生成
    pause & exit /b 1
)

for %%A in ("dist\GBT.exe") do set size=%%~zA
set /a size_mb=%size%/1048576
echo   SUCCESS: dist\GBT.exe (%size_mb% MB)

REM ─── Step 4: Inno Setup 安装包 (可选) ───
echo.
echo [4/5] 检查 Inno Setup...
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if exist "%ISCC%" (
    echo   正在生成安装包...
    "%ISCC%" /Q "installer\gbt.iss"
    if %errorlevel%==0 (
        echo   SUCCESS: dist\installer\GBT-Setup-v1.5.1.exe
    ) else (
        echo   WARNING: 安装包生成失败 (EXE已就绪)
    )
) else (
    echo   SKIP: Inno Setup 未安装，仅生成 EXE
    echo   下载: https://jrsoftware.org/isdl.php
)

REM ─── Step 5: 输出总结 ───
echo.
echo   ╔══════════════════════════════════════════╗
echo   ║           构建完成!                       ║
echo   ╠══════════════════════════════════════════╣
dir dist\GBT.exe 2>nul && echo   ║  EXE:   dist\GBT.exe
dir "dist\installer\GBT-Setup-*.exe" 2>nul && echo   ║  安装包: dist\installer\GBT-Setup-v1.5.1.exe
echo   ╚══════════════════════════════════════════╝
echo.
pause
