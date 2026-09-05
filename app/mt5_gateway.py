# -*- coding: utf-8 -*-
"""Gestao do MT5 Gateway local (porta 9001).

Inicia o servico backend/mt5_gateway.py em background junto com o app
e garante que nao haja processo duplicado.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 9001


def _gateway_script() -> Path:
    root = Path(__file__).resolve().parent.parent
    return root / "backend" / "mt5_gateway.py"


def gateway_online() -> bool:
    """True se a porta do gateway esta aceitando conexoes."""
    try:
        with socket.create_connection((GATEWAY_HOST, GATEWAY_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _python_exe() -> str:
    # Se estiver num venv, usa o python do venv; senao, o python atual.
    if sys.executable:
        return sys.executable
    return "python"


# Indica que o gateway esta rodando in-process (thread interna do EXE).
# Nesse caso stop_gateway() NAO pode fazer taskkill (mataria o proprio app).
_INPROCESS = False


def _start_gateway_inprocess() -> bool:
    """Roda o gateway na propria process (thread daemon).

    Necessario quando o app roda empacotado (EXE PyInstaller): nao existe
    python externo garantido na maquina e sys.executable e o proprio EXE,
    que nao consegue executar o script backend/mt5_gateway.py. O bundle
    ja inclui MetaTrader5, entao o gateway roda perfeitamente in-process.
    """
    global _INPROCESS
    import importlib.util

    script = _gateway_script()
    if not script.exists():
        return gateway_online()
    try:
        spec = importlib.util.spec_from_file_location("mt5_gateway_srv", script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # apenas defs; nao bloqueia
        threading.Thread(target=mod.main, daemon=True, name="mt5-gateway").start()
        _INPROCESS = True
    except Exception:
        return False
    # aguarda a porta abrir (ate 8s)
    for _ in range(16):
        if gateway_online():
            return True
        time.sleep(0.5)
    return gateway_online()


def start_gateway(force: bool = False) -> bool:
    """Inicia o MT5 Gateway em background. Retorna True se estiver online.

    Se ja estiver rodando, apenas retorna True (sem duplicar).
    No EXE (frozen) roda in-process; no fonte, spawna um python separado.
    """
    if not force and gateway_online():
        return True
    # EXE: in-process (spawn com o proprio EXE nao funciona)
    if getattr(sys, "frozen", False):
        return _start_gateway_inprocess()
    script = _gateway_script()
    if not script.exists():
        return gateway_online()
    try:
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        subprocess.Popen(
            [_python_exe(), str(script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            creationflags=flags,
        )
    except Exception:
        pass
    # aguarda ate 8s pela porta
    for _ in range(16):
        if gateway_online():
            return True
        time.sleep(0.5)
    return gateway_online()


def stop_gateway() -> None:
    """Encerra apenas o gateway local (porta 9001).

    Se o gateway roda in-process (EXE), nao faz taskkill: a thread daemon
    morre junto com o app (matar o PID da porta encerraria o proprio app).
    """
    if not gateway_online():
        return
    if _INPROCESS:
        return
    try:
        if os.name == "nt":
            out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
            for line in (out.stdout or "").splitlines():
                if (":9001" in line) and "LISTENING" in line:
                    pid = line.split()[-1].strip()
                    if pid.isdigit() and pid != str(os.getpid()):
                        subprocess.run(["taskkill", "/PID", pid, "/F"],
                                       capture_output=True, text=True, timeout=5)
                        return
        else:
            subprocess.run(["pkill", "-f", "mt5_gateway.py"], capture_output=True, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    print("online:", gateway_online())
    print("start:", start_gateway())
