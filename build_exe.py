"""
build_exe.py — 打包 GBT AI Workstation 为 Windows 桌面 EXE
输出: dist/GBTWorkstation.exe
"""
import os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "GBTWorkstation"
ENTRY = os.path.join(ROOT, "entry.py")
ICON = os.path.join(ROOT, "gbt", "icon.ico")  # 如果有图标文件

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--name", NAME,
    "--onefile",
    "--windowed",
    "--clean",
    "--noconfirm",
    "--hidden-import", "gbt.web_api",
    "--hidden-import", "gbt.capabilities",
    "--hidden-import", "gbt.skills",
    "--hidden-import", "gbt.adapters",
    "--add-data", os.path.join(ROOT, "gbt", "dashboard.html") + ";gbt",
    "--add-data", os.path.join(ROOT, "README.md") + ";.",
    "--add-data", os.path.join(ROOT, ".env.example") + ";.",
    "--add-data", os.path.join(ROOT, "vendor", "nanobrowser") + ";vendor\\nanobrowser",
    "--add-data", os.path.join(ROOT, "vendor", "cradle") + ";vendor\\cradle",
    ENTRY,
]

if os.path.exists(ICON):
    cmd.extend(["--icon", ICON])

print("Building EXE with command:")
print(" ".join(cmd))
subprocess.check_call(cmd)
print(f"\nBuild complete: {os.path.join(ROOT, 'dist', NAME+'.exe')}")
