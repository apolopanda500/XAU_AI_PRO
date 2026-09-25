# -*- mode: python ; coding: utf-8 -*-
"""
Spec ENXUTA GUI-ONLY do EXE do XAU_AI_PRO v1.3.2+ (build 2026).

Entry point: Python/launcher.py (GUI nativa Tkinter + comandos CLI simples).

--------------------------------------------------------------------------
REQUISITO DE SEGURANCA: VALIDAR O ARTEFATO ANTES DE DISTRIBUIR
--------------------------------------------------------------------------
Este spec nao garante ausencia de deteccoes nem autoriza operar capital real.
Validar cada artefato em ambiente limpo antes de distribuir. Diretrizes:

  1) upx=False            -> evitar compactacao adicional; nao garante
                              resultado de antivirus.
  2) console=False        -> manter (GUI), mas exige assinatura de codigo.
  3) codesign_identity    -> esta opcao e de assinatura macOS; assinatura
                              Authenticode Windows ocorre apos o build.
  4) Preferir onedir      -> evita autoextracao onefile; nao impede alertas.

Historico: houve deteccao do executavel instalado em fluxo Tauri/NSIS
(21/09/2026). A causa nao foi comprovada; nao atribuir a UPX ou PyInstaller.
--------------------------------------------------------------------------

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
from pathlib import Path

# Raiz do projeto = pasta onde este .spec esta (portavel: local e CI).
# SPECPATH e fornecido pelo PyInstaller apontando para o diretorio do spec.
_ROOT = SPECPATH
_ICON = os.path.join(_ROOT, 'app', 'assets', 'icon.ico')

_EXCLUDED_DIRS = {'__pycache__', 'node_modules', '.output', '.swc', '.vercel', '.claude', '.agents'}


def _source_datas(directory, suffixes):
    rows = []
    for base, dirs, files in os.walk(directory):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED_DIRS and not name.startswith('.')]
        for name in files:
            if Path(name).suffix.lower() not in suffixes:
                continue
            source = os.path.join(base, name)
            relative = os.path.relpath(source, _ROOT).replace(os.sep, '/')
            rows.append((source, os.path.dirname(relative) or '.'))
    return rows


_APP_DATAS = _source_datas(os.path.join(_ROOT, 'app'), {'.py', '.png', '.ico', '.jpg', '.jpeg', '.svg'})
_BACKEND_DATAS = _source_datas(os.path.join(_ROOT, 'backend'), {'.py'})

a = Analysis(
    [os.path.join(_ROOT, 'Python', 'launcher.py')],
    pathex=[_ROOT, os.path.join(_ROOT, 'Python')],
    binaries=[],
    datas=_APP_DATAS + _BACKEND_DATAS,
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
        'matplotlib', 'pycparser.lextab', 'pycparser.yacctab', 'scipy.special._cdflib',
    ],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='XAU_AI_PRO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # ------------------------------------------------------------------
    # ANTI-FALSO-POSITIVO (auditoria 2026-09-22 + ciclo onedir 2026-09-23)
    # ------------------------------------------------------------------
    # Nao usar UPX neste build; validar cada artefato com antivirus.
    # A deteccao anterior ocorreu em um fluxo Tauri/NSIS; sua causa
    # nao foi comprovada e nao pode ser atribuida a este spec.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_ICON,
)
# ----------------------------------------------------------------------
# MODO ONEDIR (ciclo 2026-09-23): elimina a auto-extracao em %TEMP%\_MEI*
# associado a onefile; onedir nao garante ausencia de deteccoes.
# O EXE acima exclui binarios (exclude_binaries=True); o COLLECT abaixo
# monta a pasta dist\XAU_AI_PRO\ com EXE + DLLs lado a lado.
# Ver mt5-gateway.spec (mesmo padrao, nunca detectado).
# ----------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='XAU_AI_PRO',
)
