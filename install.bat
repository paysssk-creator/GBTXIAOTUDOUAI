@echo off
chcp 65001 >nul
REM ==========================================================
REM  GBT Pro · 一键安装脚本 · Windows 10/11 · 开发者: 自由的风
REM  严格遵守"密钥不打包"铁律：FUTURAPAY_* 必从环境变量读
REM  按 SOP v1.1 三步走：
REM    1. 环境探测（Python 版本 + 网络）
REM    2. 同构安装（按 requirements.txt 锁版本）
REM    3. 密钥隔离（提示用户输入而非从 .env 复制）
REM ==========================================================

setlocal enabledelayedexpansion
set "APP_VERSION="
set "RELEASE_TAG="
if exist "release\current_runtime.ini" (
    for /f "usebackq tokens=1* delims==" %%A in ("release\current_runtime.ini") do (
        if /I "%%~A"=="APP_VERSION" set "APP_VERSION=%%~B"
        if /I "%%~A"=="RELEASE_TAG" set "RELEASE_TAG=%%~B"
    )
)
if not defined APP_VERSION set "APP_VERSION=v1.1.17"
if not defined RELEASE_TAG set "RELEASE_TAG=%APP_VERSION%-desktop-runtime"
title GBT Pro · 一键安装 %APP_VERSION%

echo.
echo ===========================================================
echo   GBT Pro %APP_VERSION% - AI 驱动 A 股自主交易终端
echo   开发者: 自由的风 · 生产同构一键安装
echo   Release Tag: %RELEASE_TAG%
echo ===========================================================
echo.

REM ---------- [1/3] 环境预检 ----------
echo [1/3] 环境预检 ...

REM 1.1 Python
where python >nul 2>&1
if errorlevel 1 (
    echo   [X] 未检测到 Python，请先安装 Python 3.11+
    echo       下载: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo   [OK] Python !PY_VER!

REM 1.2 网络
ping -n 1 pypi.org >nul 2>&1
if errorlevel 1 (
    echo   [WARN] 无法连接 pypi.org，请检查网络代理
    echo          或运行: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    echo   [OK] 网络可用
)

REM 1.3 虚拟环境
if not exist ".venv\" (
    echo   [..] 创建虚拟环境 .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo   [X] 虚拟环境创建失败
        pause
        exit /b 1
    )
)
echo   [OK] 虚拟环境 .venv 就绪

REM ---------- [2/3] 同构安装 ----------
echo.
echo [2/3] 按 requirements.txt 安装依赖 ...

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo   [X] 依赖安装失败，请查看上方错误
    pause
    exit /b 1
)
echo   [OK] 依赖安装完成（按 requirements.txt 锁版本）

REM ---------- [3/3] 密钥隔离配置 ----------
echo.
echo [3/3] 密钥隔离配置（绝不进 git / 不进打包）...

if not exist ".env" (
    echo   [..] 首次运行，引导创建 .env ...
    echo.
    echo       请按提示输入 Futurapay 凭证（去 https://futurapay.com/ 后台获取）
    echo       注意：这些密钥只存于本机 .env，绝不入库绝不上传
    echo.

    set /p SITE_ID="   FUTURAPAY_SITE_ID: "
    set /p API_KEY="   FUTURAPAY_API_KEY: "
    set /p MERCHANT_KEY="   FUTURAPAY_MERCHANT_KEY: "

    (
        echo # GBT Pro 生产环境配置 - 开发者: 自由的风
        echo # 密钥绝不入 git / 绝不入打包镜像
        echo FUTURAPAY_SITE_ID=!SITE_ID!
        echo FUTURAPAY_API_KEY_LOCAL=!API_KEY!
        echo FUTURAPAY_MERCHANT_KEY=!MERCHANT_KEY!
        echo FUTURAPAY_LIVE=false
        echo.
        echo # 行情锚定
        echo FUTURAPAY_USD_RATE=12000
        echo FUTURAPAY_CNY_RATE=1650
        echo.
        echo # 运行时
        echo FLASK_ENV=production
        echo PORT=8765
    ) > .env
    echo   [OK] .env 已写入（路径：%CD%\.env）
) else (
    echo   [OK] .env 已存在，跳过引导
)

REM ---------- 启动 ----------
echo.
echo ===========================================================
echo   [OK] GBT Pro 安装完成
echo.
echo   正式桌面入口（唯一）：
echo     1. release\launch_current_runtime.bat
echo     2. 启动GBT.bat  ^(它只转发到上面的正式入口^)
echo.
echo   开发辅助入口（仅开发调试使用）：
echo     3. .venv\Scripts\python.exe desktop_app.py
echo     4. .venv\Scripts\python.exe -m waitress --port=8765 desktop_app:app
echo     5. 健康检查: 浏览器打开 http://127.0.0.1:8765/api/status
echo.
echo   一键打包（PyInstaller → 单 exe）：
echo     .venv\Scripts\python.exe build_exe.py
echo ===========================================================
echo.
pause
