# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

datas = [('config.json', '.')]

a = Analysis(
    ['app_main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'config_store', 'market_live', 'mt5_integration', 'themes',
        'wallpaper', 'assistant', 'daily_tools', 'integrations',
        'design_system', 'gui', 'requests', 'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Libs pesadas desnecessarias - importadas lazy (fallback silencioso)
        'yfinance', 'MetaTrader5', 'matplotlib', 'scipy', 'pandas',
        'numpy', 'tensorflow', 'torch', 'keras', 'sklearn', 'scikit-learn',
        'streamlit', 'fastapi', 'uvicorn', 'pydantic',
        'pip', 'setuptools', 'wheel', 'distutils', 'test', 'unittest',
        'idlelib', 'tkinter.test', 'ctypes', 'win32api', 'pywintypes',
        'PIL', 'Pillow', 'cv2', 'IPython', 'jupyter', 'notebook',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'numba',
        'dask', 'cloudpickle', 'bottleneck', 'numexpr', 'pandas.io',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='XAU_AI_PRO', debug=False, bootloader_ignore_signals=False,
    strip=True, upx=True, upx_exclude=[], runtime_tmpdir=None,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
