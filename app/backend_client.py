# -*- coding: utf-8 -*-
"""Cliente da API Backend (ETAPA 16.4) para o Dashboard (16.5).

Consome a API unica do backend Node.js (porta 3001) que le o
forward_test_events.csv real do EA. Se o backend estiver OFF,
retorna None (dashboard mostra indisponivel - sem quebrar).
"""
from __future__ import annotations

import json
import socket
import urllib.request
from typing import Any

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 3001
BASE = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

ENDPOINTS = {
    "health": "/api/health",
    "events": "/api/events?limit=20",
    "latest": "/api/events/latest",
    "system": "/api/system",
    "trading": "/api/trading",
    "positions": "/api/positions",
    "ai": "/api/ai",
    "risk": "/api/risk",
    "execution": "/api/execution",
    "telemetry": "/api/telemetry",
    "alerts": "/api/alerts",
}


def backend_online() -> bool:
    try:
        with socket.create_connection((BACKEND_HOST, BACKEND_PORT), timeout=1.5):
            return True
    except OSError:
        return False


def api_get(endpoint: str, timeout: float = 3.0) -> dict[str, Any] | None:
    url = BASE + ENDPOINTS.get(endpoint, endpoint)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def fetch_all() -> dict[str, Any]:
    """Busca todos os endpoints; retorna dict endpoint->dados (None se falhou)."""
    out: dict[str, Any] = {"online": backend_online()}
    for name in ENDPOINTS:
        out[name] = api_get(name) if out["online"] else None
    return out


def status_lines(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Converte o fetch_all em linhas (nome, valor, cor) para o dashboard."""
    if not data.get("online"):
        return [("Backend API", "OFFLINE", "bad")]

    lines: list[tuple[str, str, str]] = []
    sys_ = data.get("system") or {}
    estado = str(sys_.get("estado", "?"))
    cor = {"HEALTHY": "ok", "TRADING": "ok", "WARNING": "warn", "SAFE": "warn",
           "RECOVERY": "warn", "ERROR": "bad", "FAILURE": "bad"}.get(estado, "warn")
    lines.append(("Estado Sistema", estado, cor))
    lines.append(("Eventos Total", str(sys_.get("total_eventos", 0)), "ok"))

    ai = data.get("ai") or {}
    lines.append(("IA Preducoes", str(ai.get("predictions", 0)),
                  "ok" if not ai.get("errors") else "bad"))
    if ai.get("errors"):
        lines.append(("IA Erros", str(ai["errors"]), "bad"))

    risk = data.get("risk") or {}
    lines.append(("Risk Blocks", str(risk.get("risk_blocks", 0)),
                  "warn" if risk.get("risk_blocks") else "ok"))
    lines.append(("Recoveries", str(risk.get("recoveries", 0)), "ok"))

    tr = data.get("trading") or {}
    lines.append(("Trades Open", str(tr.get("trades_abertos", 0)), "ok"))
    lines.append(("Trades Close", str(tr.get("trades_fechados", 0)), "ok"))

    exec_ = data.get("execution") or {}
    if exec_.get("taxa_aprovacao") is not None:
        lines.append(("Taxa Aprovacao", f'{exec_["taxa_aprovacao"]}%', "ok"))

    alerts = data.get("alerts") or {}
    lines.append(("Alertas", str(alerts.get("total", 0)),
                  "warn" if alerts.get("total") else "ok"))
    return lines