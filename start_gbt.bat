@echo off
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
start "GBT-Server" python desktop_app.py
echo Waiting for server...
timeout /t 4 /nobreak >nul
echo Starting Nanobrowser...
cd /d C:\Users\ADMIN\nanobrowser
python nanobrowser.py
