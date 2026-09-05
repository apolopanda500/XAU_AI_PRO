# -*- mode: python ; coding: utf-8 -*-
"""
Spec ENXUTA do EXE CLI (launcher) do XAU_AI_PRO v1.3.2+.

Entry point: Python/launcher.py (status/notify/release/versao/predict/train/help/dashboard/menu).

Estrategia de tamanho:
  1) SEM datas do projeto: o launcher carrega os modulos do projeto do DISCO
     (XAU_AI_PRO_ROOT), entao NAO embutimos Python/models/ (2,7 GB) nem MQL5/.
  2) Apenas libs de runtime realmente usadas pelo CLI:
     numpy, pandas, sklearn, joblib, sentry_sdk (+ certifi/urllib3 via hooks).
  3) Dashboard web: streamlit/altair/openai (+ uvicorn, exigido pelo streamlit
     em runtime via find_spec) incluidas com frontend estatico
     (collect_data_files) e metadata de versao (copy_metadata).
  4) Excludes defensivos das libs pesadas nao usadas.

console=False evita uma janela de terminal ao abrir a interface nativa.
"""
from PyInstaller.building.build_main import Analysis, PYZ, EXE
from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

import os

# Frontend estatico do Streamlit (UI web) + metadata de versao dos pacotes
# Obs: '.agents/**' (diretorio OCULTO com os skills embutidos do streamlit,
# ex.: 'streamlit skills') precisa ser incluido explicitamente - sem ele o
# EXE falha com "Bundled skills were not found in your Streamlit installation".
_STREAMLIT_DATAS = collect_data_files(
    'streamlit',
    includes=['static/**', 'web/**', 'components/**', '.agents/**'],)
_METADATA = copy_metadata('streamlit') + copy_metadata('altair') + copy_metadata('openai')

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
    datas=_STREAMLIT_DATAS + _METADATA + _APP_DATAS,  # streamlit + libs + app/ (GUI)
    hiddenimports=[
        # libs de runtime do CLI (numpy/pandas/sklearn/joblib/sentry_sdk)
        'numpy', 'pandas', 'sklearn', 'joblib', 'sentry_sdk',
        # dashboard web (streamlit + altair + openai p/ chat)
        'streamlit', 'altair', 'openai',
        # uvicorn: o Streamlit faz import lazy via importlib.util.find_spec(),
        # que a analise estatica do PyInstaller NAO detecta. Sem isso o
        # comando 'dashboard' falha no EXE com "uvicorn is not installed".
        'uvicorn',
        # INTERFACE NATIVA (Tkinter): libs usadas pelo app/ desktop
        # (app/core.py, app/mt5_robot.py, app/tabs/*, app/theme/*).
        'tkinter', 'MetaTrader5', 'PIL', 'PIL.Image', 'PIL.ImageDraw',
    ] + (collect_submodules('tkinter')  # filedialog/ttk/messagebox/etc.
         + collect_submodules('streamlit') + collect_submodules('altair')
         + collect_submodules('openai') + collect_submodules('uvicorn')),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # pesadas e NAO usadas pelo caminho CLI/dashboard
        # (scipy fica de fora: sklearn importa scipy.sparse internamente)
        'xgboost', 'yfinance',
        # uvicorn e obrigatorio p/ o Streamlit>=1.40 servir o dashboard
        'fastapi', 'boto3', 'botocore', 'litellm',
        'duckdb', 'dask', 'distributed', 'pyarrow',
        'sqlalchemy', 'tensorflow', 'torch', 'torchvision',
        'PyQt5', 'PySide2', 'PySide6',
        # matplotlib nao e usado pela GUI nativa (graficos via PIL/canvas)
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
