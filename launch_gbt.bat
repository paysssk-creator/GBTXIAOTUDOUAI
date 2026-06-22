@echo off
title GBT Pro Launcher
cd /d "%~dp0"

rem 查找Python
set PY=
if exist "C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe" set PY=C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe
if "%PY%"=="" for %%p in (python.exe python3.exe) do for %%d in ("%LOCALAPPDATA%\Programs\Python\Python312" "%ProgramFiles%\Python312" "%LOCALAPPDATA%\Microsoft\WindowsApps") do if exist "%%~d\%%p" set PY=%%~d\%%p
if "%PY%"=="" where python >nul 2>&1 && set PY=python
if "%PY%"=="" (echo Python not found! Install from https://python.org && pause && exit /b 1)

start "" /B "%PY%" -m gbt.desktop_app
