# -*- coding: utf-8 -*-
"""Motor MCP real do XAU_AI_PRO.

Executa acoes reais nos MCP servers configurados (nao apenas "enfeite"):
  - alpha_vantage   : cotacao e series historicas via API Alpha Vantage (chave)
  - alpaca          : cotacao de acoes/crypto (chave)
  - tradingview     : scanner de mercados (endpoint scanner.tradingview.com)
  - mt5_gateway     : gateway local MT5 (127.0.0.1:9001) - ping/status
  - postgres_sqlite : consulta SQL real (SQLite local ou PostgreSQL via DATABASE_URL)
  - sequential_thinking: encadeia etapas de raciocinio (motor local de passos)

call_tool(server_id, action, **params) -> {"ok": bool, "result": ...}
Nunca levanta: erros retornam ok=False com mensagem.
"""
from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.config_manager import get_config
from app.integrations_client import load_mcp_servers

_UA = {"User-Agent": "XAU_AI_PRO/1.3.2"}


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

def _server(sid: str) -> dict[str, Any]:
    servers = load_mcp_servers()
    s = servers.get(sid)
    if not s:
        raise ValueError(f"MCP server '{sid}' nao encontrado")
    return s


def _http_json(url: str, timeout: float = 12.0, headers: dict | None = None,
               method: str = "GET", body: dict | None = None) -> Any:
    hdrs = dict(_UA)
    hdrs.update(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return raw


def _res(ok: bool, result: Any = None, error: str = "") -> dict[str, Any]:
    return {"ok": ok, "result": result, "error": error}


# ---------------------------------------------------------------------------
# Acoes por server
# ---------------------------------------------------------------------------

def _act_alpha_vantage(action: str, **kw: Any) -> dict[str, Any]:
    s = _server("alpha_vantage")
    key = (kw.get("api_key") or s.get("api_key") or "").strip()
    if not key:
        return _res(False, error="Alpha Vantage: API key nao configurada (Integracoes > MCP Servers)")
    symbol = kw.get("symbol", "XAUUSD")
    fn = "GLOBAL_QUOTE" if action == "quote" else "TIME_SERIES_DAILY"
    url = ("https://www.alphavantage.co/query?function=%s&symbol=%s&apikey=%s"
           % (fn, symbol, key))
    data = _http_json(url, timeout=15)
    if isinstance(data, dict) and data.get("Global Quote"):
        gq = data["Global Quote"]
        return _res(True, {
            "symbol": gq.get("01. symbol", symbol),
            "price": gq.get("05. price"),
            "change_pct": gq.get("10. change percent"),
            "high": gq.get("03. high"), "low": gq.get("04. low"),
        })
    if isinstance(data, dict) and "Error Message" in data:
        return _res(False, error="Alpha Vantage: " + data["Error Message"][:120])
    return _res(False, error="Alpha Vantage: sem dados (limite de requisicoes?)")


def _act_alpaca(action: str, **kw: Any) -> dict[str, Any]:
    s = _server("alpaca")
    key = (kw.get("api_key") or s.get("api_key") or "").strip()
    secret = (kw.get("secret_key") or "").strip()
    if not key and not s.get("api_key"):
        return _res(False, error="Alpaca: API key nao configurada")
    symbol = kw.get("symbol", "XAUUSD")
    url = "https://data.alpaca.markets/v2/stocks/%s/latest" % symbol
    try:
        data = _http_json(url, timeout=12, headers={
            "APCA-API-KEY-ID": key or s.get("api_key", ""),
            "APCA-API-SECRET-KEY": secret,
        })
        if isinstance(data, dict) and data.get("price"):
            return _res(True, {"symbol": symbol, "price": data["price"]})
        return _res(False, error="Alpaca: sem dados para " + symbol)
    except urllib.error.HTTPError as e:
        return _res(False, error=f"Alpaca: HTTP {e.code}")
    except Exception as e:  # noqa: BLE001
        return _res(False, error=f"Alpaca: {e}")


def _act_tradingview(action: str, **kw: Any) -> dict[str, Any]:
    """Scanner TradingView real: busca simbolos por mercado/filtro."""
    market = kw.get("market", "crypto").lower()
    symbol = kw.get("symbol", "")
    # Prefixos conhecidos por mercado (tickers TradingView)
    if market in ("forex", "fx"):
        exchange = "OANDA"
        emarket = "forex"
    elif market == "crypto":
        exchange = "BINANCE"
        emarket = "crypto"
    else:
        exchange = "NASDAQ"
        emarket = "america"
    if symbol:
        tickers = ["%s:%sUSDT" % (exchange, symbol.upper()) if emarket == "crypto" else "%s:%s" % (exchange, symbol.upper())]
    else:
        tickers = [
            "%s:BTCUSDT" % exchange, "%s:ETHUSDT" % exchange,
            "%s:XAUUSD" % exchange, "%s:BTCUSD" % exchange,
        ] if emarket != "crypto" else [
            "BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:BNBUSDT",
            "BINANCE:SOLUSDT", "BINANCE:XRPUSDT",
        ]
    payload = {
        "symbols": {"tickers": tickers},
        "columns": ["name", "close", "change", "change_abs", "volume"],
    }
    try:
        data = _http_json("https://scanner.tradingview.com/%s/scan" % emarket,
                          timeout=12, method="POST", body=payload)
        if isinstance(data, dict) and data.get("totalCount", -1) >= 0:
            items = []
            for row in data.get("data", [])[:10]:
                d = row.get("d", [])
                items.append({
                    "symbol": str(d[0]) if len(d) > 0 else "",
                    "price": d[1] if len(d) > 1 else None,
                    "change_pct": d[2] if len(d) > 2 else None,
                    "change_abs": d[3] if len(d) > 3 else None,
                    "volume": d[4] if len(d) > 4 else None,
                })
            return _res(True, {"total": data.get("totalCount", 0), "items": items})
        return _res(False, error="TradingView: resposta inesperada")
    except Exception as e:  # noqa: BLE001
        return _res(False, error=f"TradingView: {e}")


def _act_mt5_gateway(action: str, **kw: Any) -> dict[str, Any]:
    s = _server("mt5_gateway")
    base = (kw.get("endpoint") or s.get("endpoint") or "http://127.0.0.1:9001").rstrip("/")
    endpoint = {
        "health": "/api/health",
        "status": "/api/status",
        "system": "/api/status",
        "positions": "/api/positions",
        "account": "/api/account",
        "history": "/api/history",
    }.get(action, "/api/health")
    try:
        data = _http_json(base + endpoint, timeout=4)
        return _res(True, data)
    except Exception as e:  # noqa: BLE001
        return _res(False, error=f"MT5 Gateway: {e}")


def _act_postgres_sqlite(action: str, **kw: Any) -> dict[str, Any]:
    """Consulta SQL real: SQLite local por padrao; PostgreSQL se DATABASE_URL."""
    s = _server("postgres_sqlite")
    db_url = (kw.get("database_url") or s.get("database_url") or "").strip()
    query = kw.get("query", "").strip()
    if not query:
        return _res(False, error="Postgres/SQLite: informe a consulta SQL (param 'query')")
    if db_url.startswith("postgres"):
        try:
            import psycopg2  # noqa: PLC0415
            conn = psycopg2.connect(db_url, connect_timeout=5)
            cur = conn.cursor()
            cur.execute(query)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            conn.close()
            return _res(True, {"columns": cols, "rows": [list(r) for r in rows[:50]]})
        except ImportError:
            return _res(False, error="Postgres: instale 'psycopg2' (pip install psycopg2-binary)")
        except Exception as e:  # noqa: BLE001
            return _res(False, error=f"Postgres: {e}")
    # SQLite local
    try:
        root = Path(__file__).resolve().parent.parent
        db = kw.get("db_path") or str(root / "database" / "trading.db")
        conn = sqlite3.connect(db, timeout=5)
        cur = conn.cursor()
        cur.execute(query)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        conn.close()
        return _res(True, {"columns": cols, "rows": [list(r) for r in rows[:50]]})
    except Exception as e:  # noqa: BLE001
        return _res(False, error=f"SQLite: {e}")




def _act_quantconnect(action: str, **kw: Any) -> dict[str, Any]:
    """QuantConnect API real: testa token e lista projetos.

    Autenticacao: header Authorization Bearer <token> + QuantConnect-UserId.
    """
    s = _server("quantconnect")
    token = (kw.get("api_key") or s.get("api_key") or "").strip()
    uid = str(kw.get("user_id") or s.get("user_id") or "").strip()
    if not token:
        return _res(False, error="QuantConnect: token nao configurado (Integracoes > MCP Servers)")
    base = (kw.get("endpoint") or s.get("endpoint") or "https://www.quantconnect.com/api/v2").rstrip("/")
    hdrs = {"Authorization": "Bearer " + token}
    if uid:
        hdrs["QuantConnect-UserId"] = uid
    try:
        if action in ("health", "projects", "ping"):
            data = _http_json(base + "/projects", timeout=15, headers=hdrs)
        elif action in ("backtests", "results"):
            data = _http_json(base + "/backtests", timeout=15, headers=hdrs)
        else:
            data = _http_json(base + "/projects", timeout=15, headers=hdrs)
        if isinstance(data, dict):
            if data.get("projects") is not None:
                projects = []
                for prj in data["projects"][:10]:
                    projects.append({
                        "id": prj.get("projectId"),
                        "nome": prj.get("name"),
                        "idioma": prj.get("language"),
                    })
                return _res(True, {"total": len(data["projects"]), "projects": projects})
            if data.get("backtests") is not None:
                return _res(True, {"total": len(data["backtests"])})
            if data.get("success") is not None:
                return _res(True, data)
            if "message" in data or "errors" in data:
                return _res(False, error="QuantConnect: " + str(data.get("message") or data.get("errors"))[:120])
        return _res(True, data)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        return _res(False, error=f"QuantConnect: HTTP {e.code} {body}")
    except Exception as e:  # noqa: BLE001
        return _res(False, error=f"QuantConnect: {e}")

def _act_sequential_thinking(action: str, **kw: Any) -> dict[str, Any]:
    """Encadeia etapas de raciocinio (motor local; nao precisa de npx)."""
    thought = kw.get("thought", "").strip()
    steps = kw.get("steps", 3)
    if not thought:
        return _res(False, error="Sequential Thinking: informe 'thought'")
    try:
        steps = max(1, min(10, int(steps)))
    except (TypeError, ValueError):
        steps = 3
    out = []
    for i in range(1, steps + 1):
        out.append({
            "step": i,
            "question": f"Passo {i}: o que sabemos/verificamos sobre '{thought[:80]}'?",
            "status": "pending",
        })
    return _res(True, {"thought": thought, "steps": out})


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_ACTIONS = {
    "alpha_vantage": _act_alpha_vantage,
    "alpaca": _act_alpaca,
    "tradingview": _act_tradingview,
    "mt5_gateway": _act_mt5_gateway,
    "quantconnect": _act_quantconnect,
    "postgres_sqlite": _act_postgres_sqlite,
    "sequential_thinking": _act_sequential_thinking,
}


def call_tool(server_id: str, action: str = "quote", **params: Any) -> dict[str, Any]:
    """Chama uma ferramenta MCP real. Retorna {"ok", "result"/"error"}."""
    try:
        fn = _ACTIONS.get(server_id)
        if not fn:
            return _res(False, error=f"Server MCP desconhecido: {server_id}")
        return fn(action, **params)
    except Exception as e:  # noqa: BLE001
        return _res(False, error=str(e))


def tool_status() -> list[dict[str, Any]]:
    """Status de cada MCP server (ativado? testavel? ultima resposta?)."""
    servers = load_mcp_servers()
    out = []
    for sid, s in servers.items():
        out.append({
            "id": sid,
            "name": s.get("name", sid),
            "enabled": bool(s.get("enabled", False)),
            "type": s.get("type", "http"),
            "endpoint": s.get("endpoint", ""),
        })
    return out


def enabled_tools() -> list[str]:
    return [s["id"] for s in tool_status() if s["enabled"]]


if __name__ == "__main__":
    import sys
    sid = sys.argv[1] if len(sys.argv) > 1 else "mt5_gateway"
    act = sys.argv[2] if len(sys.argv) > 2 else "quote"
    print(json.dumps(call_tool(sid, act), ensure_ascii=False, indent=2, default=str))