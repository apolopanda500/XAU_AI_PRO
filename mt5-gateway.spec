# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs

datas = []
binaries = []
datas += collect_data_files('MetaTrader5')
binaries += collect_dynamic_libs('MetaTrader5')
numpy_binaries = collect_dynamic_libs('numpy')
binaries += numpy_binaries


a = Analysis(
    ['backend/fastapi_gateway.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=['MetaTrader5', 'numpy', 'fastapi', 'uvicorn', 'uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on_event', 'pydantic', 'starlette'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='mt5-gateway',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='mt5-gateway',
)
