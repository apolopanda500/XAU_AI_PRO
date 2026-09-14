# -*- mode: python ; coding: utf-8 -*-
"""
Spec ENXUTA GUI-ONLY do EXE do XAU_AI_PRO v1.3.2+ (build 2026).

Entry point: Python/launcher.py (GUI nativa Tkinter + comandos CLI simples).

Estrategia GUI-ONLY (objetivo 40-60 MB):
  1) NO embute Streamlit/Altair/Uvicorn/OpenAI: o dashboard web foi retirado
     do EXE (o desktop usa so a interface nativa app/core.py). Isso elimina
     ~120 MB do binario anterior (~185 MB).
  2) Embute so app/ (Tree) + Tkinter, MetaTrader5, Pillow e numpy/pandas/
     sklearn/joblib/sentry_sdk (runtime do CLI/IA).
  3) O comando 'dashboard' detecta a ausencia de Streamlit e mostra un aviso
     claro en vez de falhar silenciosamente.

console=False evita uma janela de terminal ao abrir a interface nativa.
"""
from PyInstaller.building.build_main import Analysis, PYZ, EXE
from PyInstaller.utils.hooks import collect_submodules

import os

# Raiz do projeto = pasta onde este .spec esta (portavel: local e CI).
# SPECPATH e fornecido pelo PyInstaller apontando para o diretorio do spec.
_ROOT = SPECPATH
_ICON = os.path.join(_ROOT, 'app', 'assets', 'icon.ico')

# INTERFACE NATIVA (Tkinter): embute o diretorio inteiro app/ (core.py, tabs/,
# banners, assets, etc.) para que o EXE funcione sem depender do disco.
# IMPORTANTE: app/ nao e um pacote Python (sem __init__.py), entao usamos
# Tree manualmente em vez de collect_data_files (que pula diretorios nao-pacote).
from PyInstaller.building.datastruct import Tree as _Tree
_raw_app = _Tree(os.path.join(_ROOT, 'app'), prefix='app')
# PyInstaller 6.x Tree retorna tuplas (dest_abs, src, type); Analysis espera (dest_rel_dir, src)
_APP_DATAS = []
for dest_abs, src, _ in _raw_app:
    rel = os.path.relpath(dest_abs, _ROOT).replace(os.sep, '/')
    dest_dir = os.path.dirname(rel) or '.'
    _APP_DATAS.append((src, dest_dir))

a = Analysis(
    [os.path.join(_ROOT, 'Python', 'launcher.py')],
    pathex=[_ROOT, os.path.join(_ROOT, 'Python')],
    binaries=[],
    datas=_APP_DATAS,  # app/ (GUI nativa)
    hiddenimports=[
        # libs de runtime do CLI/IA (numpy/pandas/sklearn/joblib/sentry_sdk)
        'numpy', 'pandas', 'sklearn', 'joblib', 'sentry_sdk',
        # INTERFACE NATIVA (Tkinter): libs usadas pelo app/ desktop
        # (app/core.py, app/mt5_robot.py, app/tabs/*, app/theme/*).
        'tkinter', 'MetaTrader5', 'PIL', 'PIL.Image', 'PIL.ImageDraw',
    ] + collect_submodules('tkinter'),  # filedialog/ttk/messagebox/etc.
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # WEB retirada do build GUI-only (dashboard web ja nao se usa)
        'streamlit', 'altair', 'uvicorn', 'openai', 'litellm', 'fastapi',
        # ML executa so no pipeline externo (no embutir libs gigantes)
        'xgboost', 'lightgbm', 'catboost', 'tensorflow', 'torch', 'torchvision',
        'transformers', 'yfinance',
        # Web/DB/UI alternativa nao usadas pela GUI nativa
        'boto3', 'botocore', 'duckdb', 'dask', 'distributed', 'pyarrow',
        'sqlalchemy', 'polars',
        'PyQt5', 'PySide2', 'PySide6',
        # matplotlib nao se usa na GUI (graficos via Pillow/tk Canvas)
        'matplotlib',
    ],
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
    icon=_ICON,
)
