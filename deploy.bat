@echo off
REM GBT Pro 开发服务管理脚本（非正式桌面入口）
REM Usage: deploy.bat [start|stop|restart|status|test]
REM 正式桌面 APP 只认: release\launch_current_runtime.bat
setlocal enabledelayedexpansion
set "PY=C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe"
set "ROOT=%~dp0"

if "%1"=="test" goto test
if "%1"=="stop" goto stop_only

REM === STOP ===
:stop
echo Stopping services...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /c:":8765 " ^| findstr /c:"LISTENING"') do taskkill /PID %%a /F 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /c:":8766 " ^| findstr /c:"LISTENING"') do taskkill /PID %%a /F 2>nul
timeout /t 1 /nobreak >nul
if "%1"=="stop" goto :eof

REM === MIGRATE ===
echo Running database migrations...
"%PY%" "%ROOT%gbt\migrate.py" migrate
if %ERRORLEVEL% neq 0 (
    echo ERROR: Migration failed
    exit /b 1
)

REM === START ===
echo Starting GBT API (port 8765)...
start "GBT-API" /MIN "%PY%" "%ROOT%start_demo.py"
echo Starting Voice Bridge (port 8766)...
start "GBT-Voice" /MIN "%PY%" "%ROOT%gbt\voice_web.py"

echo Waiting for services...
timeout /t 5 /nobreak >nul

REM === STATUS ===
echo.
echo ========================================
echo   GBT v2.0 Services
echo ========================================
netstat -ano | findstr /c:":8765 " | findstr /c:"LISTENING" >nul && echo   [OK] GBT API       http://127.0.0.1:8765
netstat -ano | findstr /c:":8766 " | findstr /c:"LISTENING" >nul && echo   [OK] Voice Bridge  http://127.0.0.1:8766
echo ========================================
echo.
if "%1"=="status" goto :eof
goto :eof

REM === STOP ONLY ===
:stop_only
echo Stopping services...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /c:":8765 " ^| findstr /c:"LISTENING"') do taskkill /PID %%a /F 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /c:":8766 " ^| findstr /c:"LISTENING"') do taskkill /PID %%a /F 2>nul
echo All stopped.
goto :eof

REM === TEST ===
:test
echo Running tests...
"%PY%" -m pytest tests/test_ea_engine.py tests/test_a_share_rules.py -v
"%PY%" tests/test_router.py
echo.
echo Done.
goto :eof
