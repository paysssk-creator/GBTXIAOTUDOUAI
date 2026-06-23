@echo off
cd /d C:\Users\ADMIN\GBTXIAOTUDOUAI
pyinstaller --clean --noconfirm gbt.spec > build_log.txt 2>&1
echo DONE > build_done.txt
