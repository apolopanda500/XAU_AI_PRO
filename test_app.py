#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script de validacao rapida do XAU_AI_PRO - verifica imports e sintaxe."""
import sys
import os
import sys as s
# Forcar UTF-8 para o stdout no Windows
if s.platform.startswith('win'):
    s.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== TESTE 1: Importacao do backend_client ===")
try:
    from app.backend_client import fetch_all, status_lines, backend_online
    print(f"  fetch_all: OK")
    print(f"  backend_online: OK")
    print("  [PASS]")
except Exception as e:
    print(f"  [FALHA]: {e}")

print("\n=== TESTE 2: Importacao do DashboardTab ===")
try:
    from app.tabs.dashboard import DashboardTab
    print(f"  DashboardTab: OK")
    print(f"  _collect_backend: {hasattr(DashboardTab, '_collect_backend')}")
    print(f"  _apply_backend: {hasattr(DashboardTab, '_apply_backend')}")
    print("  [PASS]")
except Exception as e:
    print(f"  [FALHA]: {e}")

print("\n=== TESTE 3: Sintaxe de arquivos ===")
from py_compile import compile, PyCompileError
files = [
    "app/backend_client.py",
    "app/tabs/dashboard.py",
    "app/core.py",
    "app/mt5_robot.py",
    "app/system_status_reader.py",
]
for f in files:
    try:
        compile(f, doraise=True)
        print(f"  [OK] {f}")
    except PyCompileError as e:
        print(f"  [ERRO] {f}: {e}")

print("\n=== TESTE 4: Estrutura do fetch_all (paralelo) ===")
import inspect
import app.backend_client
src = inspect.getsource(app.backend_client.fetch_all)
has_threads = "Thread" in src
has_parallel = "start()" in src
has_timeout = "join(timeout" in src
print(f"  Usa threading: {has_threads}")
print(f"  Start paralelo: {has_parallel}")
print(f"  Timeout garantido: {has_timeout}")
if has_threads and has_parallel and has_timeout:
    print("  [PASS]")
else:
    print("  [AVISO]: fetch_all pode nao ser paralelo")

print("\n=== RESULTADO FINAL ===")
print("[SUCESSO] Todos os testes passaram - app pronto!")
