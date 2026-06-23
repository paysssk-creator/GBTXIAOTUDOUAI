"""
build_exe.py - Package GBT AI Workstation as Windows desktop EXE
Output: dist/GBTWorkstation.exe
Run: python build_exe.py
"""
import os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "GBTWorkstation"
ENTRY = os.path.join(ROOT, "entry.py")
ICON = os.path.join(ROOT, "gbt", "icon.ico")

# Force Python 3.12 which has PyInstaller installed
PYTHON = r"C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe"
if not os.path.exists(PYTHON):
    PYTHON = sys.executable

cmd = [
    PYTHON, "-m", "PyInstaller",
    "--name", NAME,
    "--onefile",
    "--console",
    "--clean",
    "--noconfirm",
    "--noupx",
    "--hidden-import", "gbt.web_api",
    "--hidden-import", "gbt.capabilities",
    "--hidden-import", "gbt.skills",
    "--hidden-import", "gbt.adapters",
    "--collect-submodules", "gbt.skills",
    "--exclude-module", "torch",
    "--exclude-module", "torchvision",
    "--exclude-module", "torchaudio",
    "--exclude-module", "tensorflow",
    "--exclude-module", "jax",
    "--add-data", os.path.join(ROOT, "gbt", "dashboard.html") + ";gbt",
    "--add-data", os.path.join(ROOT, "README.md") + ";.",
    "--add-data", os.path.join(ROOT, ".env.example") + ";.",
    "--add-data", os.path.join(ROOT, "vendor", "nanobrowser") + ";vendor\\nanobrowser",
    "--add-data", os.path.join(ROOT, "vendor", "cradle") + ";vendor\\cradle",
    ENTRY,
]
if os.path.exists(ICON):
    cmd.extend(["--icon", ICON])

print("Building EXE...")
print(" ".join(cmd))
subprocess.check_call(cmd)
print(f"\nBuild complete: {os.path.join(ROOT, 'dist', NAME+'.exe')}")
