@echo off
cd /d "C:\Users\ADMIN\Desktop\GBT-local-new"
echo GBT Pro v2.1 starting...
echo Server: http://localhost:8765
echo.
start "GBT-Pro-Server" /MIN "C:\Users\ADMIN\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" "C:\Users\ADMIN\Desktop\GBT-local-new\desktop\app.py" --browser
timeout /t 10 /nobreak >nul
start http://localhost:8766
echo Done. Visit http://localhost:8766 if browser does not open.
pause