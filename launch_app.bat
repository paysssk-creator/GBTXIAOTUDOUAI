@echo off
cd /d "%~dp0"
echo ===================================
echo   GBT Pro v2.1 — Desktop App
echo ===================================
echo.
echo Starting native desktop window...
echo.
python desktop_app.py
echo.
echo Press any key to exit...
pause >nul
