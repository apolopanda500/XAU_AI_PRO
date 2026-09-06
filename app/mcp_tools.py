# -*- coding: utf-8 -*-
"""Conectores MCP operacionais: TradingView e MT5 Gateway."""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from app.integrations_client import load_mcp_servers

_UA = {"User-Agent": "XAU_AI_PRO/1.3.2"}


def _server(server_id: str) -> dict[str, Any]:
    server = load_mcp_servers().get(server_id)
    if not server:
        raise ValueError(f"MCP server '{server_id}' nao encontrado")
    return server


def _http_json(url: str, timeout: float, headers: dict[str, str] | None = None) -> Any:
    request_headers = dict(_UA)
    request_headers.update(headers or {})
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _result(ok: bool, result: Any = None, error: str = "") -> dict[str, Any]:
    return {"ok": ok, "result": result, "error": error}


def _act_tradingview(action: str, **params: Any) -> dict[str, Any]:
    symbol = str(params.get("symbol") or "XAUUSD").upper().replace("/", "")
    if action in {"symbols", "screener", "assets", "list"}:
        symbols = params.get("symbols") or ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"]
        items = []
        for item in symbols:
            quote = _act_tradingview("quote", symbol=str(item))
            if quote.get("ok"):
                items.append(quote["result"])
        return _result(bool(items), {"items": items}, "TradingView: nenhum ativo retornou dados" if not items else "")

    candidates = [symbol]
    if symbol in {"XAUUSD", "XAGUSD", "GOLD", "SILVER"}:
        candidates += [f"FOREXCOM:{symbol}", f"OANDA:{symbol}", "TVC:GOLD"]
    elif len(symbol) == 6 and symbol.isalpha():
        candidates += [f"FX:{symbol}", f"FOREXCOM:{symbol}", f"OANDA:{symbol}"]
    headers = {"Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"}
    last_error = ""
    for ticker in candidates:
        url = f"https://scanner.tradingview.com/symbol?symbol={ticker}&fields=close,change,change_abs,volume"
        try:
            data = _http_json(url, timeout=10, headers=headers)
            if isinstance(data, dict) and data.get("close") is not None:
                return _result(True, {"symbol": ticker, "price": data.get("close"),
                                      "change_pct": data.get("change"), "change_abs": data.get("change_abs"),
                                      "volume": data.get("volume")})
            last_error = f"sem dados para {ticker}"
        except Exception as error:  # noqa: BLE001
            last_error = f"{ticker}: {error}"
    return _result(False, error=f"TradingView: {last_error}")


def _act_mt5_gateway(action: str, **params: Any) -> dict[str, Any]:
    server = _server("mt5_gateway")
    base = str(params.get("endpoint") or server.get("endpoint") or "http://127.0.0.1:9001").rstrip("/")
    paths = {"health": "/api/health", "status": "/api/status", "system": "/api/status",
             "positions": "/api/positions", "account": "/api/account", "history": "/api/history"}
    try:
        return _result(True, _http_json(base + paths.get(action, "/api/health"), timeout=4))
    except Exception as error:  # noqa: BLE001
        return _result(False, error=f"MT5 Gateway: {error}")


_ACTIONS_SPECIFIC = {"tradingview": _act_tradingview, "mt5_gateway": _act_mt5_gateway}


def call_tool(server_id: str, action: str = "quote", **params: Any) -> dict[str, Any]:
    """Executa somente conectores aprovados, sem fallback genérico."""
    try:
        handler = _ACTIONS_SPECIFIC.get(server_id)
        if handler is None:
            return _result(False, error=f"Server MCP nao aprovado: {server_id}")
        return handler(action, **params)
    except Exception as error:  # noqa: BLE001
        return _result(False, error=str(error))


def _availability(server_id: str, server: dict[str, Any]) -> tuple[bool, str]:
    if server_id not in _ACTIONS_SPECIFIC:
        return False, "conector nao aprovado"
    if not server.get("enabled", False):
        return False, "desativado pelo usuario"
    return True, "configurado"


def tool_status() -> list[dict[str, Any]]:
    status = []
    for server_id, server in load_mcp_servers().items():
        available, reason = _availability(server_id, server)
        status.append({"id": server_id, "name": server.get("name", server_id),
                       "configured": bool(server.get("enabled", False)), "enabled": available,
                       "reason": reason, "type": server.get("type", "http"),
                       "endpoint": server.get("endpoint", "")})
    return status


def enabled_tools() -> list[str]:
    return [server["id"] for server in tool_status() if server["enabled"]]
