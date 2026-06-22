@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    set PY=.venv\Scripts\python.exe
) else (
    set PY=python
)
echo ===================================
echo   GBT Pro v2.1 — Desktop App
echo ===================================
echo.
echo Starting native desktop window...
echo.
%PY% desktop_app.py
echo.
echo Press any key to exit...
pause >nul
