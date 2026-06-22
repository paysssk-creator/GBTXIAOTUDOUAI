# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for GBT Pro v2.1 Desktop App — Standalone Windows .exe

Build command:
    pyinstaller --clean GBT_Desktop.spec
    Output: dist/GBT_Pro.exe

Requirements before build:
    pip install pyinstaller pywebview flask psutil python-dotenv Pillow
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # SPECPATH = directory containing this .spec file
BLOCK_CIPHER = None  # Set to a key object for encryption

# ── Collect all gbt package modules ──
gbt_pkg = ROOT / "gbt"
hidden_imports = [
    # Flask core
    'flask', 'flask.json', 'flask.app', 'flask.helpers',
    'jinja2', 'jinja2.ext', 'markupsafe',
    'werkzeug', 'werkzeug.serving',
    # Webview
    'webview', 'webview.platforms.winforms', 'webview.js', 'webview.util',
    # GBT engine modules
    'gbt', 'gbt.llm', 'gbt.providers', 'gbt.tool', 'gbt.message',
    'gbt.agent', 'gbt.mcp', 'gbt.evolve', 'gbt.guard', 'gbt.mirror',
    'gbt.memory', 'gbt.react', 'gbt.reasoner', 'gbt.winctl', 'gbt.ocr',
    'gbt.router', 'gbt.agents', 'gbt.capabilities', 'gbt.protocol',
    # GBT subsystems
    'gbt.desktop_ctl', 'gbt.llm_metrics', 'gbt.paper_account',
    'gbt.trader', 'gbt.watcher', 'gbt.watcher_agent', 'gbt.brain',
    'gbt.account', 'gbt.database', 'gbt.strategies', 'gbt.backtest',
    'gbt.risk_ctrl', 'gbt.screen_ai', 'gbt.tech_analysis', 'gbt.scraper',
    # GBT connectors
    'gbt.connectors', 'gbt.connectors.market', 'gbt.connectors.web_search',
    'gbt.connectors.github', 'gbt.connectors.git_local',
    'gbt.connectors.filesystem', 'gbt.connectors.network',
    'gbt.connectors.pypi', 'gbt.connectors.registry',
    'gbt.connectors.terminal', 'gbt.connectors.weather',
    'gbt.connectors.wifi', 'gbt.connectors.cloud',
    'gbt.connectors.device', 'gbt.connectors.wregistry',
    # GBT knowledge
    'gbt.knowledge', 'gbt.knowledge.inject',
    'gbt.knowledge.ashare', 'gbt.knowledge.desktop',
    # GBT GCC
    'gbt.gcc', 'gbt.gcc.ai_trader', 'gbt.gcc.gcc_runner',
    'gbt.gcc.screenshot_reasoner', 'gbt.gcc.self_reflection',
    'gbt.gcc.skill_curation',
    # Agents
    'agents', 'agents.gbt_agent',
    # Tools
    'tools', 'tools.mcp_tools',
    # PyWin32 (Windows API)
    'win32com', 'win32com.client',
    'pythoncom',
    # System
    'ctypes', 'tkinter', 'json', 'http', 'urllib',
    'threading', 'subprocess', 'queue',
    # Other deps
    'psutil', 'dotenv', 'requests', 'PIL', 'PIL.Image',
    'pyttsx3', 'pyautogui', 'pyperclip', 'speech_recognition',
    'ollama',
]

# ── Collect data files ──
datas = []
# Templates
tmpl_dir = ROOT / "desktop" / "templates"
if tmpl_dir.is_dir():
    for f in tmpl_dir.iterdir():
        if f.is_file():
            datas.append((str(f), f"desktop/templates"))

# Icons / logos
icon_file = ROOT / "desktop" / "GBT.ico"
logo_file = ROOT / "desktop" / "GBT_logo.png"

# ── Exclude problematic modules ──
excludes = [
    'tkinter.test', 'unittest', 'test', 'pydoc',
    'pip',
    'matplotlib', 'numpy', 'scipy', 'pandas',
    'notebook', 'jupyter', 'ipykernel',
    'tensorflow', 'torch',
    'email.mime',
]

# ── Tkinter data (needed for message boxes) ──
import tkinter
tk_root = Path(tkinter.__file__).parent.parent
if tk_root.exists():
    for pattern in ['tcl', 'tk', 'demos']:
        sub = tk_root / pattern
        if sub.is_dir() and any(sub.iterdir()):
            datas.append((str(sub), str(sub.relative_to(tk_root.parent))))

a = Analysis(
    [str(ROOT / 'frozen_main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=BLOCK_CIPHER,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=BLOCK_CIPHER)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GBT_Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file.is_file() else None,
)
