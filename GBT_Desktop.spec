# -*- mode: python ; coding: utf-8 -*-
"""GBT Desktop PyInstaller Spec"""
import sys, os

project_root = r"C:\Users\ADMIN\GBTXIAOTUDOUAI"
sys.path.insert(0, project_root)

# All hidden imports
hidden_imports = [
    "tkinter", "tkinter.ttk", "tkinter.messagebox",
    "sqlite3", "threading", "json", "webbrowser", "hashlib", "base64",
    "PIL", "PIL.Image", "PIL.ImageGrab",
    "cv2", "numpy", "numpy.core", "openai", "httpx", "httpcore",
    "pyautogui", "pydirectinput", "pynput", "keyboard", "mouse",
    "pyaudio", "speech_recognition", "pyttsx3", "pyttsx3.drivers",
    "edge_tts", "asyncio", "aiohttp",
    "pytesseract", "easyocr",
    "pycaw", "comtypes", "ctypes",
    "bleak", "plyer", "win10toast", "screeninfo",
    "dotenv", "python-dotenv",
]

# Additional data files
added_files = [
    (os.path.join(project_root, ".gbt_keys.db"), "."),
    (os.path.join(project_root, ".env"), "."),
]

a = Analysis(
    ['frozen_main.py'],
    pathex=[project_root],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "pandas", "torch", "tensorflow"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    [],
    name='GBT_Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
