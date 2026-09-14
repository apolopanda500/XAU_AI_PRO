#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pre-flight check e build do EXE do XAU_AI_PRO."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

print("=== Pre-flight Build Check ===")

# Verifica PyInstaller
try:
    import PyInstaller
    print(f"  PyInstaller: {PyInstaller.__version__}")
except ImportError:
    print("  PyInstaller: NAO INSTALADO")
    sys.exit(1)

# Verifica arquivos essenciais
essential = ['launcher.spec', 'Python/launcher.py', 'app/main.py', 'app/core.py']
for f in essential:
    p = Path(f)
    print(f"  {f}: {'OK' if p.exists() else 'FALTANDO'}")

# Verifica dependencies do projeto
print("\n=== Verificacao de Dependencias ===")
deps = ['tkinter', 'pandas', 'numpy', 'PIL']
for dep in deps:
    try:
        __import__(dep)
        print(f"  {dep}: OK")
    except ImportError as e:
        print(f"  {dep}: FALTA ({e})")

print("\n=== Build sera iniciado em seguinte passo ===")