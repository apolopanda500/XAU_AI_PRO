# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app/main.py'],
    pathex=['C:/Users/Micro/Downloads/XAU_AI_PRO'],
    binaries=[],
    datas=[('MQL5', 'MQL5'), ('Python', 'Python')],
    hiddenimports=['app.core', 'app.config_manager', 'app.market_data', 'app.mt5_robot', 'app.learning_engine', 'app.utils.paths', 'app.tabs.dashboard', 'app.tabs.market', 'app.tabs.positions', 'app.tabs.robot', 'app.tabs.training', 'app.tabs.settings', 'app.tabs.assistant', 'app.tabs.tools', 'app.components.cards', 'app.components.sidebar', 'app.components.tables', 'app.components.charts', 'app.theme.mexc', 'MetaTrader5', 'numpy', 'numpy._core.multiarray', 'numpy._core._multiarray_umath', 'pandas'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy', 'sklearn', 'xgboost', 'matplotlib', 'torch', 'torchvision', 'tensorflow', 'yfinance', 'pyarrow', 'sqlalchemy', 'jinja2'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='XAU_AI_PRO',
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
    icon=['app/assets/icon.ico'],
)
