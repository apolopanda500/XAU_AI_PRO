# -*- coding: utf-8 -*-
"""Cliente da API Backend (ETAPA 16.4) para o Dashboard (16.5).

Consome a API do backend Node.js. Por padrao usa o backend local
(porta 3001, que le o forward_test_events.csv real do EA). Se a config
do app definir 'api.backend_url', usa o backend remoto (Vercel) com
autenticacao via 'api.backend_api_key' (header Authorization Bearer).
Se o backend estiver OFF, retorna None (dashboard mostra indisponivel).
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
    "financial": "/api/financial",
    "integrations": "/api/integrations",
}


# ---------------------------------------------------------------------------
# Configuracao remota (Vercel): URL + API key vindas da config do app.
# Fallback para o backend local (127.0.0.1:3001) quando nao configurado.
# ---------------------------------------------------------------------------

def _base_url() -> str:
    """URL base do backend: config 'api.backend_url' ou local (3001)."""
    try:
        from app.config_manager import get_config  # noqa: PLC0415
        url = (get_config().get("api", "backend_url", default="") or "").strip()
        if url:
            return url.rstrip("/")
    except Exception:  # noqa: BLE001
        pass
    return f"http://{BACKEND_HOST}:{BACKEND_PORT}"


def _api_key() -> str:
    """API key do backend remoto (config 'api.backend_api_key')."""
    try:
        from app.config_manager import get_config  # noqa: PLC0415
        return (get_config().get("api", "backend_api_key", default="") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _auth_headers() -> dict[str, str]:
    key = _api_key()
    if key:
        return {"Authorization": "Bearer " + key}
    return {}


def backend_online() -> bool:
    """Checa se o backend responde (health local ou remoto)."""
    url = _base_url() + "/api/health"
    try:
        req = urllib.request.Request(url, headers=_auth_headers())
        with urllib.request.urlopen(req, timeout=2.0) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        try:
            with socket.create_connection((BACKEND_HOST, BACKEND_PORT), timeout=0.5):
                return True
        except OSError:
            return False


def api_get(endpoint: str, timeout: float = 3.0) -> dict[str, Any] | None:
    url = _base_url() + ENDPOINTS.get(endpoint, endpoint)
    try:
        req = urllib.request.Request(url, headers=_auth_headers())
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
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

    fin = data.get("financial") or {}
    lines.append(("Win Rate", str(fin.get("win_rate_pct", 0)) + "%",
                  "ok" if (fin.get("win_rate_pct") or 0) >= 50 else "warn"))
    lines.append(("P/L Total", str(fin.get("pnl_total", 0)),
                  "ok" if (fin.get("pnl_total") or 0) >= 0 else "bad"))
    lines.append(("Trades", str(fin.get("total_trades", 0)), "ok"))

    alerts = data.get("alerts") or {}
    lines.append(("Alertas", str(alerts.get("total", 0)),
                  "warn" if alerts.get("total") else "ok"))
    return lines