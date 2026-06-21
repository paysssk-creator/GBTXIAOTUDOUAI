@echo off
cd /d "%~dp0"
echo ===================================
echo   GBT Pro v2.1 ¡ª Server Mode
echo ===================================
echo.
echo Starting Flask on http://localhost:8765
echo Press Ctrl+C to stop
echo.
python desktop\app.py --server
pause