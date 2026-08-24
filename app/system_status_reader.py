"""Leitor do snapshot system_status.json gerado pelo EA (ETAPA 15.6).

Contrato: Docs/contracts/ea_python_app_contract.md (schema v1.0).
Arquivo: <Terminal MT5>\\MQL5\\Files\\Data\\system_status.json
(ASCII, gravado a cada ~30s pelo Monitoring/SystemStatus.mqh com
throttle interno de 15s).

Estrategia de caminhos (ordem):
1. Terminal MT5 real via Python/mt5_bridge.get_mt5_files_path()
2. Espelho local do projeto (get_mql_data_path)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from app.utils.paths import get_mql_data_path

HEARTBEAT_MAX_AGE_SEC = 120  # EA grava a cada ~30s; 120s = tolerancia


def _candidate_paths() -> list[Path]:
    paths: list[Path] = []

    # 1. Terminal MT5 real (resolucao dinamica do mt5_bridge)
    try:
        py_root = Path(__file__).resolve().parent.parent / "Python"
        if str(py_root) not in sys.path:
            sys.path.insert(0, str(py_root))
        from mt5_bridge import get_mt5_files_path  # type: ignore

        paths.append(Path(get_mt5_files_path()) / "Data" / "system_status.json")
    except Exception:
        pass

    # 2. Espelho local do projeto (fallback)
    try:
        paths.append(get_mql_data_path() / "system_status.json")
    except Exception:
        pass

    return paths


def system_status_file() -> Path | None:
    """Retorna o snapshot mais recente entre os candidatos."""
    best: tuple[float, Path] | None = None
    for p in _candidate_paths():
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, p)
    return best[1] if best else None


def read_system_status() -> dict[str, Any] | None:
    """Le o snapshot e devolve dict enriquecido ou None se indisponivel.

    Campos adicionais inseridos:
        heartbeat_age_sec : int   - idade do arquivo em segundos (-1 se ausente)
        ea_online         : bool  - heartbeat dentro da tolerancia
        source            : str   - caminho de origem
    """
    p = system_status_file()
    if p is None:
        return None

    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        age = int(time.time() - p.stat().st_mtime)
    except Exception:
        return None

    data["heartbeat_age_sec"] = age
    data["ea_online"] = 0 <= age <= HEARTBEAT_MAX_AGE_SEC
    data["source"] = str(p)
    return data


def summarize(status: dict[str, Any] | None) -> list[tuple[str, str, str]]:
    """Traduz o snapshot para linhas (nome, valor, cor) do dashboard.

    Cor: '' (neutro) | 'ok' | 'warn' | 'bad'
    """
    if not status:
        return [("EA Snapshot", "INDISPONIVEL", "bad")]

    lines: list[tuple[str, str, str]] = []

    online = bool(status.get("ea_online"))
    lines.append((
        "EA Heartbeat",
        f"ONLINE ({status.get('heartbeat_age_sec', -1)}s)" if online
        else f"STALE ({status.get('heartbeat_age_sec', -1)}s)",
        "ok" if online else "bad",
    ))

    health = status.get("health", {})
    conn = bool(health.get("terminal_connected"))
    algo = bool(health.get("algo_trading_enabled"))
    lines.append(("Conexao MT5", "OK" if conn else "OFF", "ok" if conn else "bad"))
    if not algo:
        lines.append(("AutoTrading", "DESATIVADO", "warn"))

    tr = status.get("trading", {})
    pos = str(tr.get("position", "NONE"))
    pl = float(tr.get("floating_pl", 0.0))
    color_pl = "" if pos == "NONE" else ("ok" if pl >= 0 else "bad")
    lines.append(("Posicao", pos, color_pl))
    if pos != "NONE":
        lines.append(("P/L Flutuante", f"{pl:,.2f}", color_pl))

    risk = status.get("risk", {})
    rstatus = str(risk.get("status", "?"))
    dd = float(risk.get("drawdown_pct", 0.0))
    reason = str(risk.get("reason", "") or "")
    label = rstatus + (f" ({reason})" if reason else "")
    lines.append(("Risco", label, "ok" if rstatus == "OPEN" else "bad"))
    lines.append(("Drawdown Dia", f"{dd:.2f}%",
                  "ok" if dd < 5 else ("warn" if dd < 10 else "bad")))

    ai = status.get("ai", {})
    avail = bool(ai.get("available"))
    signal = str(ai.get("signal", "UNAVAILABLE"))
    conf = float(ai.get("confidence", 0.0))
    stale = bool(ai.get("stale"))
    mv = str(ai.get("model_version", ""))
    lines.append((
        "IA",
        f"{signal} {conf:.1f}% v{mv}" if avail and signal != "UNAVAILABLE"
        else "UNAVAILABLE",
        "ok" if (avail and signal != "UNAVAILABLE" and not stale)
        else ("warn" if avail or signal == "UNAVAILABLE" else "bad"),
    ))

    news = status.get("news", {})
    blocked = bool(news.get("blocked"))
    lines.append(("News Filter",
                  "BLOQUEADO" if blocked else "LIVRE",
                  "bad" if blocked else "ok"))

    py = status.get("python", {})
    pavail = bool(py.get("predictions_available"))
    pages = int(py.get("prediction_age_sec", -1))
    lines.append(("Python Engine",
                  f"OK ({pages}s)" if pavail else f"STALE ({pages}s)",
                  "ok" if pavail else "bad"))

    db = status.get("database", {})
    dexists = bool(db.get("dataset_exists"))
    dbytes = int(db.get("dataset_bytes", 0))
    lines.append(("Dataset",
                  f"{dbytes / (1024 * 1024):.1f} MB" if dexists else "AUSENTE",
                  "ok" if dexists else "bad"))

    return lines