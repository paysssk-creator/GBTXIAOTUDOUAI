@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "desktop\app_launcher.py"
) else if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" "desktop\app_launcher.py"
) else (
    echo [ERROR] .venv not found! Run: uv venv --python 3.11
    echo         Then: uv pip install flask psutil
    pause
)
