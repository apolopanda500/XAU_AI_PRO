# -*- coding: utf-8 -*-
"""
launcher.py  Entry point do EXE do XAU_AI_PRO.

Responsavel por:
  * Resolver a raiz do projeto em qualquer cenario de execucao
    (EXE empacotado, instalacao, fonte, ambiente XAU_AI_PRO_ROOT).
  * Abrir por padrao a INTERFACE NATIVA (Tkinter, app/core.py) quando
    XAU_AI_PRO_USE_GUI=1 (default)  o dashboard web vira comando explicito.
  * Comando 'dashboard': sobe o Streamlit com flags que corrigem
    - server.port ignorado em developmentMode (PyInstaller onefile);
    - botao "Deploy" (client.toolbarMode=viewer);
    - telemetria (gatherUsageStats=false);
    e abre o navegador APENAS quando /_stcore/health responder 200 ok.
  * Single-instance: se ja existe um painel saudavel na porta 8501/8502,
    reutiliza (abre o navegador e encerra) em vez de duplicar o servidor.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
import ctypes
from pathlib import Path

# Forca UTF-8 no stdout/stderr para evitar UnicodeEncodeError em consoles
# com encoding cp1252 (padrao no Windows).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

VERSION = "1.2.0"
APP_NAME = "XAU_AI_PRO"

# Portas padrao do dashboard web (Streamlit)
DEFAULT_PORT = 8501
FALLBACK_PORT = 8502

# Comandos que abrem a interface nativa (Tkinter)
_GUI_COMMANDS = {"gui", "desktop", "app"}


def _log(msg: str) -> None:
    """Log padrao no terminal (o EXE e console=True)."""
    print(f"[{APP_NAME}] {msg}", flush=True)


def _resolve_project_root() -> Path:
    """
    Localiza a raiz do projeto nos cenarios possiveis:

      1. Variavel de ambiente XAU_AI_PRO_ROOT (usada pelo instalador);
      2. Diretorio do executavel (EXE onefile -> pasta de instalacao);
      3. Diretorio pai do executavel (EXE dentro de subpasta);
      4. Diretorio de trabalho atual (execucao a partir do fonte).
    """
    candidates: list[Path] = []

    env_root = os.environ.get("XAU_AI_PRO_ROOT", "").strip()
    if env_root:
        candidates.append(Path(env_root))

        # sys.executable: python.exe (fonte) ou XAU_AI_PRO.exe (empacotado)
    exe_dir = Path(sys.executable).resolve().parent
    candidates.append(exe_dir)
    candidates.append(exe_dir.parent)
    candidates.append(Path.cwd())
    # IMPORTANTE: quando rodado de Python/ via source (venv), o cwd e` Python/
    # e o root e` o diretorio pai. Sem isso o app/ nunca e encontrado.
    candidates.append(Path.cwd().parent)
    # No modo EXE onefile, o root e` o diretorio onde o executavel foi extraido
    # (sys._MEIPASS). Adiciona como candidato de ultimo recurso.
    mei = os.environ.get("_MEIPASS", "")
    if mei:
        candidates.append(Path(mei))

    seen = set()
    for cand in candidates:
        key = str(cand).lower()
        if key in seen:
            continue
        seen.add(key)
        if (cand / "Python").is_dir() and (cand / "app").is_dir():
            return cand

    # Fallback: primeiro candidato existente
    for cand in candidates:
        if cand.exists():
            return cand
    return Path.cwd()


# ---------------------------------------------------------------------------
# Dashboard web (Streamlit)
# ---------------------------------------------------------------------------

def _port_healthy(port: int) -> bool:
    """True se o endpoint de saude do Streamlit responder 200 'ok'."""
    url = f"http://127.0.0.1:{port}/_stcore/health"
    try:
        with urllib.request.urlopen(url, timeout=1.0) as resp:
            return resp.status == 200 and resp.read().decode("utf-8", "ignore").strip() == "ok"
    except Exception:
        return False


def _port_in_use(port: int) -> bool:
    """True se a porta ja estiver ocupada (qualquer servico)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _open_browser_when_ready(url: str, port: int, max_wait: int = 90) -> None:
    """
    Abre o navegador apenas quando o servidor estiver pronto.
    Evita o erro "Connection error / Streamlit server is not responding"
    causado por abrir o browser antes do bind/startup do servidor.
    """

    def _wait_and_open() -> None:
        waited = 0
        while waited < max_wait:
            if _port_healthy(port):
                webbrowser.open(url)
                _log(f"Dashboard pronto: {url}")
                return
            time.sleep(1)
            waited += 1
        _log(f"[AVISO] Dashboard nao respondeu em {max_wait}s: {url}")

    threading.Thread(target=_wait_and_open, daemon=True).start()


def _run_streamlit_cli(root: Path, port: int) -> int:
    """Sobe o Streamlit com as flags corretivas (deploy/developmentMode/telemetria)."""
    app_path = root / "Python" / "dashboard" / "app.py"
    if not app_path.exists():
        _log(f"[ERRO] dashboard/app.py nao encontrado: {app_path}")
        return 2

    flags = [
        f"--server.port={port}",
        "--server.headless=true",
        "--global.developmentMode=false",
        "--client.toolbarMode=viewer",
        "--browser.gatherUsageStats=false",
    ]
    sys.argv = ["streamlit", "run", str(app_path), *flags]

    try:
        from streamlit.web import cli as stcli  # import tardio (so no comando dashboard)
        return stcli.main()
    except Exception as exc:  # noqa: BLE001
        _log(f"[ERRO] Falha ao iniciar o Streamlit: {exc}")
        return 1


def _run_dashboard(root: Path) -> int:
    """Single-instance: reutiliza painel saudavel ou sobe em porta livre."""
    url_8501 = f"http://127.0.0.1:{DEFAULT_PORT}"
    url_8502 = f"http://127.0.0.1:{FALLBACK_PORT}"

    # Servidor ja em execucao e saudavel -> apenas reutiliza
    if _port_healthy(DEFAULT_PORT):
        _log(f"Painel {APP_NAME} ja esta em execucao em {url_8501}")
        webbrowser.open(url_8501)
        return 0
    if _port_healthy(FALLBACK_PORT):
        _log(f"Painel {APP_NAME} ja esta em execucao em {url_8502}")
        webbrowser.open(url_8502)
        return 0

    # Nenhum saudavel: escolhe porta livre
    port = DEFAULT_PORT if not _port_in_use(DEFAULT_PORT) else FALLBACK_PORT
    url = f"http://127.0.0.1:{port}"
    _log(f"Iniciando dashboard em {url} (aguardando servidor pronto...)")

    _open_browser_when_ready(url, port)
    return _run_streamlit_cli(root, port)


# ---------------------------------------------------------------------------
# Interface nativa / skills / menu
# ---------------------------------------------------------------------------

def _run_gui(root: Path) -> int:
    """Abre a interface nativa (Tkinter) do XAU_AI_PRO - app/core.py."""
    # Impede duas janelas quando o atalho é clicado novamente ou quando um
    # processo antigo ainda está inicializando.
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\XAU_AI_PRO_GUI_SINGLE_INSTANCE")
    if ctypes.windll.kernel32.GetLastError() == 183:
        _log("GUI já está em execução; nova instância ignorada.")
        return 0
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    try:
        import app.core  # noqa: PLC0415
        return app.core.main()
    except Exception as exc:  # noqa: BLE001
        _log(f"[ERRO] Falha ao abrir a interface nativa: {exc}")
        # Preserve o traceback no log para diagnostico, sem esconder a causa.
        import traceback
        _log(traceback.format_exc())
        return 1


def _run_skills(root: Path) -> int:
    """Exibe os skills embutidos do Streamlit empacotados no EXE."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.find_spec("streamlit")
    base = Path(spec.origin).parent if spec and spec.origin else None
    agents = base / ".agents" if base else None

    _log(f"Streamlit: {base}")
    if agents and agents.is_dir():
        items = sorted(p.name for p in agents.iterdir())
        _log(f"Skills embutidos ({len(items)}): {', '.join(items) or 'vazio'}")
    else:
        _log("[AVISO] Diretorio .agents nao encontrado no pacote streamlit.")
    return 0


def _run_cpu(root: Path, extra: list[str]) -> int:
    """Diagnostico e opcoes de CPU: prioridade, afinidade, uso do sistema."""
    from app.cpu import (affinity_mask, cpu_usage, current_priority,
                         logical_cores, parse_affinity, set_affinity,
                         set_priority)
    for arg in extra:
        if "=" not in arg:
            continue
        key, _, value = arg.partition("=")
        key = key.strip().lower()
        value = value.strip()
        if key in ("priority", "prioridade"):
            set_priority(value)
            _log(f"Prioridade -> {value}")
        elif key in ("affinity", "afinidade", "nucleos"):
            mask = parse_affinity(value)
            if mask and set_affinity(mask):
                _log(f"Afinidade -> 0x{mask:X} ({value})")
            else:
                _log(f"[AVISO] Afinidade invalida: {value}")
        else:
            _log(f"[AVISO] Opcao desconhecida: {key}")
    _log(f"Nucleos logicos: {logical_cores()}")
    _log(f"Prioridade atual: {current_priority()}")
    _log(f"Mascara de afinidade: {affinity_mask():#x}")
    _log(f"Uso de CPU do sistema: {cpu_usage():.1f}%")
    _log("Uso: XAU_AI_PRO.exe cpu [prioridade=baixa|normal|alta] "
         "[afinidade=todos|metade|quarto|um|0,2-3]")
    return 0


def _show_menu() -> int:
    _log(f"{APP_NAME} v{VERSION} - comandos:")
    _log("  (sem argumento)  abre a interface nativa (padrao)")
    _log("  gui|desktop|app  abre a interface nativa (Tkinter)")
    _log("  dashboard        abre o painel web (Streamlit)")
    _log("  skills           lista os skills embutidos do Streamlit")
    _log("  cpu [prioridade=x] [afinidade=y]  diagnostico e opcoes de CPU")
    _log("  versao|version   mostra a versao")
    _log("  menu|help        mostra esta ajuda")
    _log("Dica: XAU_AI_PRO_USE_GUI=0 faz o padrao virar o dashboard.")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _default_action(root: Path) -> int:
    """
    Acao padrao ao executar sem argumentos.

    Por padrao abre a INTERFACE NATIVA (Tkinter) exclusivamente.
    O dashboard web (Streamlit) so e aberto via comando explicito 'dashboard'.
    Variavel XAU_AI_PRO_USE_GUI=0 ainda força o dashboard para compatibilidade.
    """
    use_gui = os.environ.get("XAU_AI_PRO_USE_GUI", "1").strip() == "1"
    if use_gui:
        _log("Abrindo interface nativa do XAU AI PRO (Tkinter)...")
        return _run_gui(root)
    _log("XAU_AI_PRO_USE_GUI=0  abrindo dashboard web...")
    return _run_dashboard(root)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = _resolve_project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # Variaveis de reforco do Streamlit (config.toml tem precedencia maxima;
    # flags de CLI vem em segundo lugar; env serve para opcoes sensiveis).
    os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")
    os.environ.setdefault("STREAMLIT_SERVER_ADDRESS", "127.0.0.1")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_FILE_WATCHER_TYPE", "none")
    os.environ.setdefault("STREAMLIT_CLIENT_TOOLBAR_MODE", "viewer")

    # Opcoes de CPU via ambiente (antes de abrir GUI/dashboard):
    #   XAU_AI_PRO_CPU_PRIORITY=baixa|normal|alta
    #   XAU_AI_PRO_CPU_AFFINITY=todos|metade|quarto|um|0,2-3
    try:
        env_priority = os.environ.get("XAU_AI_PRO_CPU_PRIORITY", "").strip()
        env_affinity = os.environ.get("XAU_AI_PRO_CPU_AFFINITY", "").strip()
        if env_priority or env_affinity:
            from app.cpu import describe, parse_affinity, set_affinity, set_priority
            if env_priority:
                set_priority(env_priority)
            if env_affinity:
                mask = parse_affinity(env_affinity)
                if mask:
                    set_affinity(mask)
            _log("CPU (env): " + describe(env_priority, env_affinity))
    except Exception:
        pass

    cmd = argv[0].lower() if argv else ""

    if not cmd:
        return _default_action(root)
    if cmd in _GUI_COMMANDS:
        return _run_gui(root)
    if cmd == "dashboard":
        return _run_dashboard(root)
    if cmd == "skills":
        return _run_skills(root)
    if cmd == "cpu":
        return _run_cpu(root, argv[1:])
    if cmd in ("versao", "version", "-v", "--version"):
        _log(f"{APP_NAME} v{VERSION}")
        return 0
    if cmd in ("menu", "help", "-h", "--help"):
        return _show_menu()
    _log(f"[ERRO] Comando desconhecido: {cmd}")
    _show_menu()
    return 2


if __name__ == "__main__":
    sys.exit(main())