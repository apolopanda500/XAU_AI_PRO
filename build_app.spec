"""
Build spec para PyInstaller do app XAU_AI_PRO v1.2.0.
"""
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

a = Analysis(
    ['app/main.py'],
    pathex=[r'C:\Users\Micro\Downloads\XAU_AI_PRO'],
    binaries=[],
    datas=[
        ('app/assets', 'app/assets'),
        ('MQL5', 'MQL5'),
        ('Python', 'Python'),
    ],
    hiddenimports=[
        'MetaTrader5', 'yfinance', 'requests', 'pandas', 'numpy',
        'sklearn', 'xgboost', 'matplotlib', 'PIL',
        'app.core', 'app.config_manager', 'app.market_data',
        'app.mt5_robot', 'app.learning_engine', 'app.utils.paths',
        'app.tabs.dashboard', 'app.tabs.market', 'app.tabs.positions',
        'app.tabs.robot', 'app.tabs.training', 'app.tabs.settings',
        'app.tabs.assistant', 'app.tabs.tools',
        'app.components.cards', 'app.components.sidebar',
        'app.components.tables', 'app.components.charts',
        'app.theme.mexc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    icon=r'C:\Users\Micro\Downloads\XAU_AI_PRO\app\assets\icon.ico',
)
