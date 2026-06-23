"""
build_exe.py - Package GBT AI Workstation as Windows desktop EXE (onedir slim build)
Output: dist/GBTWorkstation/GBTWorkstation.exe
Run: python build_exe.py
"""
import os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "GBTWorkstation"
ENTRY = os.path.join(ROOT, "entry.py")
ICON = os.path.join(ROOT, "gbt", "icon.ico")

PYTHON = r"C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe"
if not os.path.exists(PYTHON):
    PYTHON = sys.executable

EXCLUDES = [
    "torch", "torchvision", "torchaudio",
    "tensorflow", "jax", "jaxlib",
    "sklearn", "skimage", "easyocr",
    "numba", "matplotlib", "pyarrow",
    "botocore", "boto3", "sqlalchemy",
    "pytest", "lxml", "openpyxl",
    "PIL._tkinter_finder",
]

cmd = [
    PYTHON, "-m", "PyInstaller",
    "--name", NAME,
    "--onedir",
    "--console",
    "--clean",
    "--noconfirm",
    "--noupx",
    "--hidden-import", "gbt.web_api",
    "--hidden-import", "gbt.capabilities",
    "--hidden-import", "gbt.skills",
    "--hidden-import", "gbt.adapters",
    "--collect-submodules", "gbt.skills",
]
for mod in EXCLUDES:
    cmd.extend(["--exclude-module", mod])

cmd += [
    "--add-data", os.path.join(ROOT, "gbt", "dashboard.html") + ";gbt",
    "--add-data", os.path.join(ROOT, "README.md") + ";.",
    "--add-data", os.path.join(ROOT, ".env.example") + ";.",
    "--add-data", os.path.join(ROOT, "vendor", "nanobrowser") + ";vendor\\nanobrowser",
    "--add-data", os.path.join(ROOT, "vendor", "cradle") + ";vendor\\cradle",
    ENTRY,
]
if os.path.exists(ICON):
    cmd.extend(["--icon", ICON])

print("Building EXE (onedir slim)...")
print(" ".join(cmd))
subprocess.check_call(cmd)
print(f"\nBuild complete: {os.path.join(ROOT, 'dist', NAME, NAME+'.exe')}")
