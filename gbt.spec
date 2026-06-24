# -*- mode: python ; coding: utf-8 -*-
# ══════════════════════════════════════════════════════════�?#  GBT 全家�?�?PyInstaller 专业构建 Spec v3.0
#  参照: VS Code / OBS Studio / PyCharm 打包标准
# ══════════════════════════════════════════════════════════�?import os, sys
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

ROOT = os.path.abspath(SPECPATH)

# ── 嵌入�?Version Info (Windows 文件属�?�?版本) ──
VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1,5,1,0),
        prodvers=(1,5,1,0),
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0,0)
    ),
    kids=[
        StringFileInfo([StringTable(u'040904B0', [
            StringStruct(u'CompanyName', u'GBTxiaotudou'),
            StringStruct(u'FileDescription', u'GBT AI Full-Stack Agent'),
            StringStruct(u'FileVersion', u'1.5.1.0'),
            StringStruct(u'InternalName', u'GBT'),
            StringStruct(u'LegalCopyright', u'MIT (C) 2026 GBTxiaotudou'),
            StringStruct(u'OriginalFilename', u'GBT.exe'),
            StringStruct(u'ProductName', u'GBT xiaotudou'),
            StringStruct(u'ProductVersion', u'1.5.1'),
        ])]),
        VarFileInfo([VarStruct(u'Translation', [0x0409, 0x04B0])]),
    ]
)

# ── 排除重型 C 扩展 ──
EXCLUDES = [
    'cv2','opencv','easyocr','tesserocr','paddleocr','paddle',
    'sklearn','scipy','librosa','numba','llvmlite',
    'matplotlib','seaborn','plotly','bokeh',
    'torch','torchvision','torchaudio','transformers',
    'tensorflow','keras','jax',
    'jupyter','IPython','ipykernel','notebook',
    'selenium','bleak','pycaw','screeninfo','win10toast',
    'sqlalchemy','alembic','psycopg2','pymysql',
]

HIDDEN_IMPORTS = [
    'gbt','gbt.llm','gbt.providers','gbt.router','gbt.reasoner',
    'gbt.guard','gbt.evolve','gbt.mirror','gbt.mcp',
    'gbt.winctl','gbt.desktop_ctl','gbt.desktop_app',
    'gbt.trader','gbt.strategies','gbt.tech_analysis','gbt.scraper','gbt.backtest','gbt.risk_ctrl',
    'gbt.agent','gbt.agents','gbt.react','gbt.autopilot','gbt.brain',
    'gbt.memory','gbt.knowledge_base','gbt.database','gbt.keydb','gbt.cloud_kv',
    'gbt.protocol','gbt.message','gbt.tool',
    'gbt.watcher','gbt.watcher_agent',
    'gbt.account','gbt.capabilities','gbt.llm_metrics','gbt.paper_account','gbt.setup_glm4v',
    'gbt.ocr','gbt.screen_ai','gbt.gcc.ai_trader',
    'gbt.ai_operator','gbt.web_api','gbt.key_manager','gbt.llm_reasoner',
    'gbt.task_engine','gbt.vision',
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
    'tkinter','tkinter.ttk','tkinter.scrolledtext','tkinter.simpledialog',
]

ICON_PATH = os.path.join(ROOT, 'gbt.ico')
if not os.path.exists(ICON_PATH):
    print("WARNING: gbt.ico not found")
    ICON_PATH = None

# ── Analysis ──
a = Analysis(
    [os.path.join(ROOT, 'entry.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[(os.path.join(ROOT, '.env.example'), '.')] if os.path.exists(os.path.join(ROOT, '.env.example')) else [],
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

# ── PYZ (压缩 Python 字节�? ──
pyz = PYZ(a.pure, a.zipped_data)

# ── EXE (单文件输出，参照 VS Code 做法) ──
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='GBT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,        # False �?保留 traceback 可读
    upx=True,           # UPX 压缩 (需安装 upx)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # True �?开发模式可见日志；False �?发布模式
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,           # 图标嵌入
    versioninfo=VERSION_INFO,  # 版本信息嵌入
    uac_admin=False,          # 不强制管理员
    uac_uiaccess=False,
)
