# -*- mode: python ; coding: utf-8 -*-
# GBT AI Workstation — Tauri sidecar PyInstaller spec
# Builds a console-less onefile executable meant to be bundled as a Tauri sidecar.
# Usage: pyinstaller gbt-sidecar.spec
import os, sys

ROOT = os.path.abspath(SPECPATH)

# Windows-specific version info is only available on Windows
if sys.platform == 'win32':
    from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
    VERSION_INFO = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=(1, 5, 1, 0),
            prodvers=(1, 5, 1, 0),
            mask=0x3f,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0)
        ),
        kids=[
            StringFileInfo([StringTable(u'040904B0', [
                StringStruct(u'CompanyName', u'GBTxiaotudou'),
                StringStruct(u'FileDescription', u'GBT AI Workstation Sidecar'),
                StringStruct(u'FileVersion', u'1.5.1.0'),
                StringStruct(u'InternalName', u'GBT'),
                StringStruct(u'LegalCopyright', u'MIT (C) 2026 GBTxiaotudou'),
                StringStruct(u'OriginalFilename', u'gbt-sidecar.exe'),
                StringStruct(u'ProductName', u'GBT xiaotudou'),
                StringStruct(u'ProductVersion', u'1.5.1'),
            ])]),
            VarFileInfo([VarStruct(u'Translation', [0x0409, 0x04B0])]),
        ]
    )
else:
    VERSION_INFO = None

# Exclude heavy ML/desktop-only libs not needed for the Web API sidecar
EXCLUDES = [
    'easyocr','tesserocr','paddleocr','paddle',
    'sklearn','scipy','librosa','numba','llvmlite',
    'matplotlib','seaborn','plotly','bokeh',
    'torch','torchvision','torchaudio','transformers',
    'tensorflow','keras','jax',
    'jupyter','IPython','ipykernel','notebook',
    'selenium',
    'sqlalchemy','alembic','psycopg2','pymysql',
]

HIDDEN_IMPORTS = [
    'gbt','gbt.llm','gbt.providers','gbt.router','gbt.reasoner',
    'gbt.guard','gbt.evolve','gbt.mirror','gbt.mcp',
    'gbt.winctl','gbt.desktop_ctl',
    'gbt.trader','gbt.strategies','gbt.tech_analysis','gbt.scraper','gbt.backtest','gbt.risk_ctrl',
    'gbt.agent','gbt.agents','gbt.react','gbt.autopilot','gbt.brain',
    'gbt.memory','gbt.knowledge_base','gbt.database','gbt.keydb','gbt.cloud_kv',
    'gbt.protocol','gbt.message','gbt.tool',
    'gbt.watcher','gbt.watcher_agent',
    'gbt.account','gbt.capabilities','gbt.llm_metrics','gbt.paper_account','gbt.setup_glm4v',
    'gbt.ocr','gbt.screen_ai','gbt.gcc.ai_trader',
    'gbt.ai_operator','gbt.web_api','gbt.key_manager','gbt.llm_reasoner',
    'gbt.task_engine','gbt.vision','gbt.device_caps',
    'gbt.skills','gbt.skills.base','gbt.skills.screen_ocr','gbt.skills.browser_open',
    'gbt.skills.web_search','gbt.skills.maximize','gbt.skills.screenshot','gbt.skills.stock_lookup',
    'gbt.skills.scan_market','gbt.skills.trade','gbt.skills.watchlist','gbt.skills.system_status',
    'gbt.skills.watcher_check','gbt.skills.account_query','gbt.skills.auto_pipeline',
    'gbt.skills.code_exec','gbt.skills.file_operation','gbt.skills.login_detect',
    'gbt.skills.notify','gbt.skills.precision_scrape','gbt.skills.voice_speak',
    'gbt.skills.cradle_task','gbt.skills.screenpipe_monitor',
    'gbt.adapters','gbt.adapters.nanobrowser','gbt.adapters.cradle','gbt.adapters.screenpipe',
    'openai','ollama','tiktoken','httpx','pydantic',
    'PIL','pyautogui','pyperclip','psutil','pyttsx3',
    'speech_recognition','flask','requests','dotenv','numpy',
    'json','threading','logging','sqlite3','asyncio',
    # Device capability libraries required for voice/mic/bluetooth/WiFi/camera/keyboard/mouse
    'cv2','bleak','screeninfo',
    'pyaudio','edge_tts',
] + (
    [
        'pycaw','pycaw.pycaw','win10toast','comtypes','comtypes.client',
        'win32api','win32con','win32gui',
        'winrt','winrt.windows.devices.bluetooth','winrt.windows.devices.bluetooth.advertisement',
        'winrt.windows.devices.bluetooth.genericattributeprofile','winrt.windows.devices.enumeration',
        'winrt.windows.devices.radios','winrt.windows.foundation','winrt.windows.foundation.collections',
        'winrt.windows.storage.streams',
        'ahk','pydirectinput',
    ] if sys.platform == 'win32' else []
)

ICON_PATH = os.path.join(ROOT, 'gbt.ico')
if not os.path.exists(ICON_PATH):
    print("WARNING: gbt.ico not found")
    ICON_PATH = None

a = Analysis(
    [os.path.join(ROOT, 'entry.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, '.env.example'), '.'),
        (os.path.join(ROOT, 'gbt', 'dashboard.html'), 'gbt'),
    ] if os.path.exists(os.path.join(ROOT, '.env.example')) else [(os.path.join(ROOT, 'gbt', 'dashboard.html'), 'gbt')],
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='gbt-sidecar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # No console window for desktop app
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
    versioninfo=VERSION_INFO,
    uac_admin=False,
    uac_uiaccess=False,
)
