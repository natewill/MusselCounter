# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all hidden imports for ML libraries
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'uvicorn',
    'fastapi',
    'starlette',
    'pydantic',
    'aiosqlite',
    'aiofiles',
    'torch',
    'torchvision',
    'ultralytics',
    'PIL',
    'cv2',
    'numpy',
    'certifi',
    'pathvalidate',
    'filetype',
    'slowapi',
    'secure',
    'accelerate',
    'python_multipart',
]

# Add ultralytics submodules (YOLO)
hiddenimports += collect_submodules('ultralytics')

# Add our own routers and utils
hiddenimports += [
    'api',
    'api.routers',
    'api.routers.collections',
    'api.routers.models',
    'api.routers.runs',
    'api.routers.system',
    'api.routers.images',
    'api.error_handlers',
    'db',
    'config',
    'utils',
]

# Collect data files needed at runtime
datas = [
    # Include schema.sql from backend directory
    ('schema.sql', '.'),
]
datas += collect_data_files('ultralytics')

a = Analysis(
    ['main_entry.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mussel-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep True for logging; backend runs headless
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
