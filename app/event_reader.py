# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""Leitor do Event Stream (ETAPA 15.6.2/15.6.4).

Contrato: Docs/contracts/ea_python_app_contract.md (Contrato C - Eventos).
Arquivo: <Terminal MT5>\\MQL5\\Files\\Data\\forward_test_events.csv
(generado pelo Monitoring/EventEmitter.mqh — append-only UTF-16 LE + BOM).

Fornece o stream de eventos para o App/Dashboard:
  - read_events(limit=10)  -> ultimos eventos (list[dict])
  - event_summary(limit)   -> dicionario com estado derivado (15.6.5)
  - event_status_lines()   -> linhas (nome, valor, cor) para o dashboard
"""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path
from typing import Any

EVENT_CSV = "forward_test_events.csv"

# Estados (15.6.5)
HEALTHY = "HEALTHY"
WARNING = "WARNING"
ERROR = "ERROR"
SAFE = "SAFE"
RECOVERY = "RECOVERY"
UNAVAILABLE = "UNAVAILABLE"
ONLINE = "ONLINE"
OFFLINE = "OFFLINE"

# Nomes padronizados (15.6.1)
EV_SYSTEM_START = "SYSTEM_START"
EV_SYSTEM_STOP = "SYSTEM_STOP"
EV_FWD_START = "FORWARD_TEST_START"
EV_HEALTH_UPDATE = "HEALTH_UPDATE"
EV_AI_PREDICTION = "AI_PREDICTION"
EV_AI_ERROR = "AI_ERROR"
EV_AI_BLOCK = "AI_BLOCK"
EV_SIGNAL_GENERATED = "SIGNAL_GENERATED"
EV_TRADE_APPROVED = "TRADE_APPROVED"
EV_TRADE_REJECTED = "TRADE_REJECTED"
EV_TRADE_OPEN = "TRADE_OPEN"
EV_TRADE_CLOSE = "TRADE_CLOSE"
EV_RISK_BLOCK = "RISK_BLOCK"
EV_NEWS_BLOCK = "NEWS_BLOCK"
EV_CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
EV_SAFE_MODE = "SAFE_MODE"
EV_RECOVERY = "RECOVERY"
EV_BROKER_ERROR = "BROKER_ERROR"
EV_PYTHON_ERROR = "PYTHON_ERROR"
EV_DATABASE_ERROR = "DATABASE_ERROR"
EV_SYSTEM_ERROR = "SYSTEM_ERROR"
EV_HEALTH_WARNING = "HEALTH_WARNING"
EV_HEALTH_FAILURE = "HEALTH_FAILURE"


def _candidate_paths() -> list[Path]:
    paths: list[Path] = []

    # 1. Terminal MT5 real (espelho preferido)
    try:
        py_root = Path(__file__).resolve().parent.parent / "Python"
        if str(py_root) not in sys.path:
            sys.path.insert(0, str(py_root))
        from mt5_bridge import get_mt5_files_path  # type: ignore
        paths.append(Path(get_mt5_files_path()) / "Data" / EVENT_CSV)
    except Exception:
        pass

    # 2. Espelho local do projeto (fallback)
    try:
        from app.utils.paths import get_mql_data_path
        paths.append(get_mql_data_path() / EVENT_CSV)
    except Exception:
        pass

    return paths


def _events_file() -> Path | None:
    """Retorna o arquivo de eventos mais recente entre os candidatos."""
    best: tuple[float, Path] | None = None
    for p in _candidate_paths():
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, p)
    return best[1] if best else None


_EVENT_COLS = ["Time", "Event", "Symbol", "TF", "Ticket", "Severity",
               "Module", "Message", "Value", "Status"]


def read_events(limit: int = 10) -> list[dict[str, Any]]:
    """Le os ultimos `limit` eventos (colunas padronizadas 15.6.2).

    Tolerante a separador: usa ',' (contrato) e tambem '	' (fallback
    p/ arquivos antigos gerados sem delimiter explicito no FileOpen).
    """
    p = _events_file()
    if p is None:
        return []

    rows: list[dict[str, Any]] = []
    try:
        with p.open("r", encoding="utf-16", errors="replace") as f:
            raw = f.read()
    except Exception:
        return []

    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return []

    header = lines[0]
    delim = "	" if "	" in header and "," not in header else ","
    cols = [h.strip() for h in header.split(delim)]
    if len(cols) < 2:
        # fallback: usar colunas padrao
        cols = list(_EVENT_COLS)
        delim = "	" if "	" in header else ","

    for ln in lines[1:]:
        parts = [x.strip() for x in ln.split(delim)]
        row: dict[str, Any] = {}
        for i, col in enumerate(cols):
            row[col] = parts[i] if i < len(parts) else ""
        rows.append(row)

    return rows[-limit:]


def event_summary(limit: int = 20) -> dict[str, Any]:
    """Resumo/estado do sistema a partir do event stream (15.6.4/15.6.5)."""
    events = read_events(limit)
    summary: dict[str, Any] = {
        "online": False,
        "uptime_sec": 0,
        "trades_total": 0,
        "ai_state": UNAVAILABLE,
        "estado": UNAVAILABLE,
        "ultimo_evento": None,
        "contagem_por_tipo": {},
        "fonte": None,
    }

    if not events:
        return summary

    p = _events_file()
    summary["fonte"] = str(p) if p else None
    summary["ultimo_evento"] = events[-1]
    summary["online"] = True

    # Uptime (a partir do SYSTEM_START mais antigo na janela)
    for ev in events:
        if ev.get("Event") == EV_SYSTEM_START:
            try:
                t0 = time.mktime(time.strptime(ev.get("Time", ""), "%Y.%m.%d %H:%M:%S"))
                summary["uptime_sec"] = max(0, int(time.time() - t0))
            except Exception:
                pass
            break

    # Contagem por tipo
    tipo_counts: dict[str, int] = {}
    for ev in events:
        evt = ev.get("Event", "")
        tipo_counts[evt] = tipo_counts.get(evt, 0) + 1
    summary["contagem_por_tipo"] = tipo_counts

    # Estado derivado (15.6.5) — prioridade decrescente
    if tipo_counts.get(EV_HEALTH_FAILURE, 0) > 0:
        summary["estado"] = "FAILURE"
    elif tipo_counts.get(EV_CIRCUIT_BREAKER, 0) > 0 or tipo_counts.get(EV_SAFE_MODE, 0) > 0:
        summary["estado"] = SAFE
    elif (tipo_counts.get(EV_SYSTEM_ERROR, 0) + tipo_counts.get(EV_BROKER_ERROR, 0)
          + tipo_counts.get(EV_PYTHON_ERROR, 0) + tipo_counts.get(EV_DATABASE_ERROR, 0)) > 0:
        summary["estado"] = ERROR
    elif tipo_counts.get(EV_RECOVERY, 0) > 0:
        summary["estado"] = RECOVERY
    elif (tipo_counts.get(EV_HEALTH_WARNING, 0) + tipo_counts.get(EV_RISK_BLOCK, 0)
          + tipo_counts.get(EV_NEWS_BLOCK, 0) + tipo_counts.get(EV_AI_BLOCK, 0)) > 0:
        summary["estado"] = WARNING
    elif tipo_counts.get(EV_TRADE_OPEN, 0) > 0:
        summary["estado"] = "TRADING"
    else:
        summary["estado"] = HEALTHY

    # IA (UNAVAILABLE/ERROR/READY)
    if tipo_counts.get(EV_AI_BLOCK, 0) > 0 or tipo_counts.get(EV_AI_ERROR, 0) > 0:
        summary["ai_state"] = UNAVAILABLE if tipo_counts.get(EV_AI_BLOCK, 0) > 0 else ERROR
    elif tipo_counts.get(EV_AI_PREDICTION, 0) > 0:
        summary["ai_state"] = "READY"
    else:
        summary["ai_state"] = UNAVAILABLE

    # Trades na janela
    summary["trades_total"] = tipo_counts.get(EV_TRADE_OPEN, 0) + tipo_counts.get(EV_TRADE_CLOSE, 0)

    return summary


def event_status_lines(limit: int = 8) -> list[tuple[str, str, str]]:
    """Linhas (nome, valor, cor) para o dashboard — cor: ''/ok/warn/bad."""
    try:
        s = event_summary(limit)
    except Exception:
        return [("Eventos", "ERRO DE LEITURA", "bad")]

    if s.get("fonte") is None:
        return [("Eventos", "SEM STREAM", "warn")]

    lines: list[tuple[str, str, str]] = []
    estado = str(s.get("estado", UNAVAILABLE))
    cor_estado = {
        HEALTHY: "ok",
        "TRADING": "ok",
        ONLINE: "ok",
        WARNING: "warn",
        RECOVERY: "warn",
        SAFE: "warn",
        "FAILURE": "bad",
        ERROR: "bad",
        UNAVAILABLE: "warn",
        OFFLINE: "bad",
    }.get(estado, "warn")
    lines.append(("Estado Sistema", estado, cor_estado))

    ai = str(s.get("ai_state", UNAVAILABLE))
    lines.append(("IA", ai, "ok" if ai == "READY" else ("warn" if ai == UNAVAILABLE else "bad")))

    last = s.get("ultimo_evento") or {}
    last_evt = str(last.get("Event", ""))
    last_time = str(last.get("Time", ""))
    lines.append(("Ultimo Evento", f"{last_evt} @ {last_time}",
                  "warn" if any(b in last_evt for b in ("BLOCK", "ERROR", "FAILURE", "SAFE", "RECOVERY")) else "ok"))

    if s.get("uptime_sec"):
        lines.append(("Uptime (janela)", f"{int(s['uptime_sec']) // 60}min", "ok"))
    if s.get("trades_total"):
        lines.append(("Trades (janela)", str(s["trades_total"]), "ok"))

    counts = s.get("contagem_por_tipo") or {}
    if counts:
        top = max(counts, key=lambda k: counts[k])
        lines.append(("Top Evento", f"{top} x{counts[top]}",
                      "warn" if any(b in top for b in ("BLOCK", "ERROR", "FAILURE")) else "ok"))

    return lines


if __name__ == "__main__":
    import pprint
    pprint.pprint(event_summary(10))