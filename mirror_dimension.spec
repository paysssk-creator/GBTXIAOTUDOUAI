# -*- mode: python ; coding: utf-8 -*-
"""镜像多维度空间 — PyInstaller 单文件桌面 EXE"""
import os, sys
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo,
    StringTable, StringStruct, VarFileInfo, VarStruct,
)

ROOT = os.path.abspath(SPECPATH)

VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(filevers=(2,0,0,0), prodvers=(2,0,0,0),
                      mask=0x3f, flags=0x0, OS=0x40004,
                      fileType=0x1, subtype=0x0, date=(0,0)),
    kids=[
        StringFileInfo([StringTable(u'040904B0', [
            StringStruct(u'CompanyName', u'GBTxiaotudou'),
            StringStruct(u'FileDescription', u'GBT小土豆'),
            StringStruct(u'FileVersion', u'2.0.0.0'),
            StringStruct(u'InternalName', u'MirrorDimension'),
            StringStruct(u'LegalCopyright', u'MIT 2026 GBTxiaotudou'),
            StringStruct(u'OriginalFilename', u'GBT_MirrorDimension.exe'),
            StringStruct(u'ProductName', u'GBT小土豆'),
            StringStruct(u'ProductVersion', u'2.0.0'),
        ])]),
        VarFileInfo([VarStruct(u'Translation', [0x0409, 0x04B0])]),
    ]
)

ICON = os.path.join(ROOT, 'gbt.ico')
if not os.path.exists(ICON):
    ICON = None

a = Analysis(
    [os.path.join(ROOT, 'mirror_dimension_desktop.py')],
    pathex=[ROOT],
    binaries=[], datas=[
        ('gbt_logo_32.png', '.'),
        ('gbt_logo_64.png', '.'),
    ],
    hiddenimports=[
        'customtkinter','darkdetect','PIL','PIL.Image',
        'tkinter','tkinter.filedialog','tkinter.messagebox',
        'mirror_dimension','mirror_dimension.scanner','mirror_dimension.auditor',
        'mirror_dimension.fixer','mirror_dimension.dimensions',
        'mirror_dimension.pipeline','mirror_dimension.mindmap_guide',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=[
        'flask','werkzeug','jinja2','markupsafe','click','itsdangerous',
        'cv2','opencv','easyocr','pytesseract','paddleocr',
        'sklearn','scipy','librosa','numba','llvmlite',
        'matplotlib','seaborn','plotly','bokeh',
        'torch','torchvision','torchaudio','transformers',
        'tensorflow','keras','jax','jupyter','IPython',
        'selenium','bleak','pycaw','screeninfo','win10toast',
        'sqlalchemy','alembic','psycopg2','pymysql',
        'pyautogui','pyttsx3','speech_recognition',
        'numpy','ollama','PIL','pillow',
    ],
    win_no_prefer_redirects=False, win_private_assemblies=False, noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name='GBT_MirrorDimension',
    debug=False, strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=False,
    disable_windowed_traceback=False,
    icon=ICON, versioninfo=VERSION_INFO,
    uac_admin=False, uac_uiaccess=False,
)
