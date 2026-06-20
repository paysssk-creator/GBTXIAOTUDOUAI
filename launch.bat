@echo off
cd /d "C:\Users\ADMIN\Desktop\GBT-local-new"
echo ===================================
echo   GBT Pro v2.1 — Server Mode
echo ===================================
echo.
echo Starting Flask on http://localhost:8765
echo Press Ctrl+C to stop
echo.
"C:\Users\ADMIN\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" "desktop\app.py" --server
pause