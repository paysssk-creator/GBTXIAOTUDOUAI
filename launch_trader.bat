@echo off
chcp 65001 >nul
title GBT Pro A股AI操盘终端 v2.2

echo.
echo   ╔══════════════════════════════════════╗
echo   ║   GBT Pro v2.2 — AI驱动A股操盘终端  ║
echo   ║   指纹浏览器 + VLM分析 + 自动交易    ║
echo   ╚══════════════════════════════════════╝
echo.

:: 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 未安装
    pause & exit /b 1
)

:: 安装依赖(首次)
echo [1/3] 检查依赖...
pip install seleniumbase playwright mss pillow pyautogui -q 2>nul
playwright install chromium 2>nul

:: 拉取最新代码
echo [2/3] 拉取最新代码...
git pull origin main 2>nul

:: 启动
echo [3/3] 启动操盘引擎...
echo.
echo  选择模式:
echo    [1] 浏览器操盘 (推荐)
echo    [2] CLI命令行
echo    [3] 综合驾驶舱
echo    [4] 市场情绪扫描
echo.
set /p mode="请输入选项 (1-4): "

if "%mode%"=="1" (
    python -c "from gbt.browser_trader import BrowserTrader; t=BrowserTrader(); t.scan_market()"
)
if "%mode%"=="2" (
    python main.py
)
if "%mode%"=="3" (
    python -c "from gbt.browser_desk import create_bridge; b=create_bridge(); print(b.cockpit())"
)
if "%mode%"=="4" (
    python -c "from gbt.browser_trader import BrowserTrader; t=BrowserTrader(); r=t.scan_market(); print(r)"
)

pause
