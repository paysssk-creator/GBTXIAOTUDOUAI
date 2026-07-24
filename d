@echo off
cd /d %~dp0
echo GBT Pro v2.2 Deploying...

if not exist gbt mkdir gbt

echo Downloading browser_trader.py...
powershell -c "iwr 'https://raw.githubusercontent.com/paysssk-creator/GBTXIAOTUDOUAI/main/gbt/browser_trader.py' -OutFile 'gbt\browser_trader.py' -UseBasicParsing"

echo Downloading browser_desk.py...
powershell -c "iwr 'https://raw.githubusercontent.com/paysssk-creator/GBTXIAOTUDOUAI/main/gbt/browser_desk.py' -OutFile 'gbt\browser_desk.py' -UseBasicParsing"

echo Done! Files:
dir gbt\browser_*.py
echo.
echo Run: launch_trader.bat
pause
