#!/usr/bin/env python3
"""
XAU AI PRO - Launcher (modo console + serviços)
Alternativa ao run_app.py (GUI).

- Inicia Backend FastAPI (8000) e Dashboard Streamlit (8501) em background.
- Abre o navegador automaticamente no dashboard.
- O proxy LiteLLM (IA) é opcional: se falhar, o sistema continua funcionando.
- Logs são gravados em Logs/ para diagnóstico (erros não ficam invisíveis).

Para a interface desktop com login e mercado em tempo real, prefira:
    python Ultimate/run_app.py
"""

import os
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# CAMINHOS
# ============================================================
if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).parent.parent
else:
    BASE = Path(__file__).resolve().parent.parent

LOG_DIR = BASE / "Logs"
API_PATH = BASE / "Python" / "backend" / "api.py"
APP_PATH = BASE / "Python" / "dashboard" / "app.py"


def _py() -> str:
    return sys.executable or "python"


def _ensure_logs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def _is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", int(port))) == 0


def _start(cmd: list[str], name: str) -> subprocess.Popen | None:
    logfile = LOG_DIR / f"{name}.log"
    logfile.parent.mkdir(parents=True, exist_ok=True)
    f = open(logfile, "a", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=f,
            stderr=f,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        _log(f"[OK] {name} iniciado (pid={proc.pid}). Log: {logfile.name}")
        return proc
    except Exception as e:
        _log(f"[ERRO] Não foi possível iniciar {name}: {e}")
        return None


def main() -> None:
    _ensure_logs()
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 56)
    print("   XAU AI PRO — LAUNCHER")
    print("   (use 'python Ultimate/run_app.py' para a GUI desktop)")
    print("=" * 56)

    procs: list[subprocess.Popen] = []

    backend_port = 8000
    if _is_open(backend_port):
        _log(f"Backend já está na porta {backend_port}. Pulando.")
    elif API_PATH.exists():
        proc = _start([_py(), str(API_PATH)], "backend")
        if proc:
            procs.append(proc)
    else:
        _log("[ERRO] backend/api.py não encontrado.")

    dash_port = 8501
    if _is_open(dash_port):
        _log(f"Dashboard já está na porta {dash_port}. Pulando.")
    elif APP_PATH.exists():
        proc = _start(
            [_py(), "-m", "streamlit", "run", str(APP_PATH),
             "--server.port", str(dash_port), "--server.headless", "true",
             "--browser.gatherUsageStats", "false"],
            "dashboard",
        )
        if proc:
            procs.append(proc)
    else:
        _log("[ERRO] dashboard/app.py não encontrado.")

    time.sleep(4)
    try:
        import webbrowser

        webbrowser.open(f"http://127.0.0.1:{dash_port}")
        _log(f"Abrindo dashboard em http://127.0.0.1:{dash_port}")
    except Exception as e:
        _log(f"Não foi possível abrir o navegador: {e}")

    _log("Serviços em execução. Pressione Ctrl+C para encerrar.")
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        _log("Encerrando...")
    finally:
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    main()