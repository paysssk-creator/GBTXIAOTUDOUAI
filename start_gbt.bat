@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    set PY=.venv\Scripts\python.exe
) else (
    set PY=python
)
title GBT Pro v2.1 + Nanobrowser
echo.
echo ╔══════════════════════════════════════════╗
echo ║   GBT Pro v2.1 — Production Launch      ║
echo ╠══════════════════════════════════════════╣
echo ║  Server: http://localhost:8765           ║
echo ║  Nano  : native Python browser           ║
echo ╚══════════════════════════════════════════╝
echo.
echo Starting GBT Server...
start "GBT-Server" %PY% desktop_app.py
echo Waiting for server...
timeout /t 4 /nobreak >nul
echo Starting Nanobrowser...
cd /d C:\Users\ADMIN\nanobrowser
%PY% nanobrowser.py
