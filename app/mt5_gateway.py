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


def start_gateway(force: bool = False) -> bool:
    """Inicia o MT5 Gateway em background. Retorna True se estiver online.

    Se ja estiver rodando, apenas retorna True (sem duplicar).
    """
    script = _gateway_script()
    if not script.exists():
        return gateway_online()
    if not force and gateway_online():
        return True
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
    """Encerra apenas o gateway local (porta 9001)."""
    if not gateway_online():
        return
    try:
        if os.name == "nt":
            out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
            for line in (out.stdout or "").splitlines():
                if (":9001" in line) and "LISTENING" in line:
                    pid = line.split()[-1].strip()
                    if pid.isdigit():
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
