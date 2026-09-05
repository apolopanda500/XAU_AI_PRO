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
import os
import sqlite3
import subprocess
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
    """TradingView real: cotacao via endpoint /symbol (preco em tempo real).

    Exemplos de tickers: XAUUSD, EURUSD, FOREXCOM:XAUUSD, TVC:GOLD,
    BINANCE:BTCUSDT, NASDAQ:AAPL. Busca o primeiro que retornar dados.
    """
    symbol = (kw.get("symbol") or "XAUUSD").upper().replace("/", "")
    if action in ("symbols", "screener", "assets", "list"):
        symbols = kw.get("symbols") or ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "BTCUSD", "ETHUSD"]
        results = []
        for item in symbols:
            r = _act_tradingview("quote", symbol=str(item))
            if r.get("ok"):
                results.append(r["result"])
        return _res(bool(results), {"items": results}, "TradingView: nenhum ativo retornou dados" if not results else "")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/",
    }
    # Lista de prefixos para tentar (do mais generico ao mais especifico)
    candidates = [symbol]
    if symbol in ("XAUUSD", "XAGUSD", "GOLD", "SILVER"):
        candidates += ["FOREXCOM:" + symbol, "OANDA:" + symbol, "FX:" + symbol, "TVC:GOLD"]
    elif len(symbol) == 6 and symbol.isalpha():
        candidates += ["FX:" + symbol, "FOREXCOM:" + symbol, "OANDA:" + symbol]
    elif symbol in ("BTC", "ETH", "BNB", "SOL", "XRP") or symbol.endswith("USD") and symbol[:3] in ("BTC", "ETH", "BNB", "SOL", "XRP"):
        base_crypto = symbol[:3]
        candidates += ["BINANCE:" + base_crypto + "USDT", "COINBASE:" + base_crypto + "USD"]
    last_err = ""
    for ticker in candidates:
        url = ("https://scanner.tradingview.com/symbol"
               f"?symbol={ticker}&fields=close,change,change_abs,volume,description")
        try:
            data = _http_json(url, timeout=10, headers=headers)
            if isinstance(data, dict) and data.get("close"):
                return _res(True, {
                    "symbol": ticker,
                    "price": data.get("close"),
                    "change_pct": data.get("change"),
                    "change_abs": data.get("change_abs"),
                    "volume": data.get("volume"),
                })
            last_err = f"sem dados para {ticker}"
        except Exception as e:  # noqa: BLE001
            last_err = f"{ticker}: {e}"
    return _res(False, error=f"TradingView: {last_err}")


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
    """QuantConnect API v2 real: autentica com hash SHA256 + timestamp.

    O token pode vir do parametro api_key, da config salva ou da variavel
    de ambiente QUANTCONNECT_TOKEN (preferencia nessa ordem).
    Documentacao: https://www.quantconnect.com/docs/v2/cloud-platform/api-reference/authentication
    """
    import base64
    import hashlib
    import time as _time

    s = _server("quantconnect")
    token = (kw.get("api_key") or os.environ.get("QUANTCONNECT_TOKEN") or s.get("api_key") or "").strip()
    uid = str(kw.get("user_id") or os.environ.get("QUANTCONNECT_USER_ID") or s.get("user_id") or "").strip()
    if not token:
        return _res(False, error="QuantConnect: token nao configurado (Integracoes > MCP Servers ou env QUANTCONNECT_TOKEN)")
    if not uid:
        return _res(False, error="QuantConnect: user_id nao configurado (env QUANTCONNECT_USER_ID)")

    base = (kw.get("endpoint") or s.get("endpoint") or "https://www.quantconnect.com/api/v2").rstrip("/")
    timestamp = str(int(_time.time()))
    time_stamped_token = f"{token}:{timestamp}"
    hash_token = hashlib.sha256(time_stamped_token.encode("utf-8")).hexdigest()
    auth = base64.b64encode(f"{uid}:{hash_token}".encode("utf-8")).decode("ascii")
    hdrs = {
        "Authorization": f"Basic {auth}",
        "Timestamp": timestamp,
    }

    endpoint_map = {
        "health": "/authenticate",
        "ping": "/authenticate",
        "projects": "/projects",
        "backtests": "/backtests",
    }
    url = base + endpoint_map.get(action, "/authenticate")

    try:
        data = _http_json(url, timeout=15, headers=hdrs, method="POST", body={})
        if isinstance(data, dict):
            if data.get("success") is True:
                return _res(True, data)
            if data.get("success") is False or data.get("errors"):
                return _res(False, error="QuantConnect: " + str(data.get("errors") or data.get("message"))[:200])
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


def _act_cline(action: str, **kw: Any) -> dict[str, Any]:
    """Cline / OpenAI-compatible: chat ou health-check via API REST.

    O token pode vir do parametro api_key, da config salva ou da variavel
    de ambiente CLINE_API_KEY. O endpoint padrao e OpenAI-compatible.
    """
    s = _server("cline")
    key = (kw.get("api_key") or os.environ.get("CLINE_API_KEY") or os.environ.get("OPENAI_API_KEY") or s.get("api_key") or "").strip()
    base = (kw.get("endpoint") or os.environ.get("CLINE_BASE_URL") or s.get("endpoint") or "https://api.openai.com/v1").rstrip("/")
    model = (kw.get("model") or os.environ.get("CLINE_MODEL") or s.get("model") or "gpt-4o-mini").strip()
    if not key:
        return _res(False, error="Cline: API key nao configurada (env CLINE_API_KEY)")

    hdrs = {"Authorization": f"Bearer {key}"}

    if action in ("health", "ping"):
        try:
            data = _http_json(base + "/models", timeout=15, headers=hdrs)
            if isinstance(data, dict) and "data" in data:
                return _res(True, {"models": len(data["data"]), "first_model": data["data"][0].get("id") if data["data"] else None})
            return _res(True, data)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:200]
            except Exception:
                pass
            return _res(False, error=f"Cline: HTTP {e.code} {body}")
        except Exception as e:  # noqa: BLE001
            return _res(False, error=f"Cline: {e}")

    if action == "chat":
        prompt = kw.get("prompt", kw.get("message", "Ola, voce e o agente Cline integrado ao XAU_AI_PRO."))
        messages = [{"role": "user", "content": prompt}]
        try:
            data = _http_json(
                base + "/chat/completions",
                timeout=30,
                headers={**hdrs, "Content-Type": "application/json"},
                method="POST",
                body={"model": model, "messages": messages, "max_tokens": 512},
            )
            if isinstance(data, dict) and data.get("choices"):
                content = data["choices"][0].get("message", {}).get("content", "")
                return _res(True, {"reply": content, "model": model, "usage": data.get("usage")})
            if isinstance(data, dict) and (data.get("error") or data.get("message")):
                return _res(False, error="Cline: " + str(data.get("error") or data.get("message"))[:200])
            return _res(True, data)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:200]
            except Exception:
                pass
            return _res(False, error=f"Cline: HTTP {e.code} {body}")
        except Exception as e:  # noqa: BLE001
            return _res(False, error=f"Cline: {e}")

    return _res(False, error=f"Cline: acao '{action}' nao suportada (use health, ping, chat)")


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


def _act_stdio(action: str, **kw: Any) -> dict[str, Any]:
    """Handler generico para MCPs stdio (npx/node/python/uvx).

    Verifica se o comando base esta disponivel no PATH — o teste real
    de "instalacao" desses MCPs (redis, mongodb, github, etc).
    """
    endpoint = kw.get("_endpoint", "")
    name = kw.get("_name", "stdio")
    if not endpoint:
        return _res(False, f"{name}: endpoint vazio")
    import shlex

    cmd = shlex.split(endpoint, posix=False)
    base = cmd[0]
    if action in ("health", "ping", "tools", "list_tools", "call"):
        try:
            from app.mcp_stdio import stdio_from_endpoint
            client = stdio_from_endpoint(endpoint, kw.get("_env"))
            try:
                init = client.start()
                if not init.get("ok"):
                    return _res(False, error=f"{name}: {init.get('error', 'initialize falhou')}")
                tools = init.get("tools", [])
                if action in ("tools", "list_tools"):
                    return _res(True, {"tools": tools, "count": len(tools)})
                if action == "call":
                    tool_name = kw.get("tool") or kw.get("name")
                    if not tool_name:
                        return _res(False, error=f"{name}: informe tool")
                    result = client.call_tool(str(tool_name), kw.get("arguments") or {})
                    return result if result.get("ok") else _res(False, error=str(result.get("error", "tools/call falhou")))
                return _res(True, {"initialized": True, "tools": tools, "count": len(tools)})
            finally:
                client.close()
        except Exception as exc:
            return _res(False, error=f"{name}: handshake MCP falhou: {exc}")
    if base.lower().startswith(("npx", "node", "python", "uvx")):
        try:
            from app.mcp_stdio import stdio_from_endpoint
            client = stdio_from_endpoint(endpoint, kw.get("_env"))
            init = client.start()
            client.close()
            if init.get("ok"):
                return _res(True, f"{name}: handshake MCP concluído ({len(init.get('tools', []))} ferramentas)")
            return _res(False, f"{name}: handshake MCP falhou: {init.get('error', '')}")
        except Exception as e:
            return _res(False, f"{name}: erro no handshake: {e}")
    return _res(True, f"{name}: configurado")


# ---------------------------------------------------------------------------
# Dispatcher (servidores com logica especifica + fallback stdio generico)
# ---------------------------------------------------------------------------

_ACTIONS_SPECIFIC = {
    "alpha_vantage": _act_alpha_vantage,
    "alpaca": _act_alpaca,
    "tradingview": _act_tradingview,
    "mt5_gateway": _act_mt5_gateway,
    "quantconnect": _act_quantconnect,
    "cline": _act_cline,
    "postgres_sqlite": _act_postgres_sqlite,
}

# Todos os demais servidores (redis, mongodb, github, brave, etc) usam stdio
_ALL_SERVER_IDS: set[str] = set()


def _get_all_server_ids() -> set[str]:
    """Descobre dinamicamente todos os ids de servidores instalados."""
    global _ALL_SERVER_IDS
    if _ALL_SERVER_IDS:
        return _ALL_SERVER_IDS
    base = Path(__file__).resolve().parent.parent / "mcp" / "servers"
    if base.is_dir():
        for f in base.glob("*.json"):
            if f.name != "registry.json":
                _ALL_SERVER_IDS.add(f.stem)
    return _ALL_SERVER_IDS


def call_tool(server_id: str, action: str = "quote", **params: Any) -> dict[str, Any]:
    """Chama uma ferramenta MCP real. Retorna {"ok", "result"/"error"}.

    Servidores com logica especifica (alpha_vantage, mt5_gateway, etc) usam
    handlers dedicados. Os demais (redis, mongodb, github, brave, etc) sao
    tratados como stdio genericos — verifica disponibilidade do comando.
    """
    try:
        fn = _ACTIONS_SPECIFIC.get(server_id)
        if fn:
            return fn(action, **params)
        # fallback: qualquer outro servidor instalado -> stdio generico
        if server_id in _get_all_server_ids():
            s = _server(server_id)
            params.setdefault("_endpoint", s.get("endpoint") or s.get("default_endpoint", ""))
            if server_id == "filesystem" and params["_endpoint"].strip().endswith("server-filesystem"):
                params["_endpoint"] += " ."
            params.setdefault("_name", s.get("name", server_id))
            key = str(s.get("api_key") or "").strip()
            if server_id == "github_mcp":
                token = key or os.environ.get("GITHUB_MCP_TOKEN", "")
                if token:
                    params.setdefault("_env", {"GITHUB_PERSONAL_ACCESS_TOKEN": token})
            elif server_id == "brave":
                token = key or os.environ.get("BRAVE_API_KEY", "")
                if token:
                    params.setdefault("_env", {"BRAVE_API_KEY": token})
            return _act_stdio(action, **params)
        return _res(False, error=f"Server MCP desconhecido: {server_id}")
    except Exception as e:  # noqa: BLE001
        return _res(False, error=str(e))


def _availability(sid: str, server: dict[str, Any]) -> tuple[bool, str]:
    if not server.get("enabled", False):
        return False, "desativado pelo usuario"
    key = str(server.get("api_key") or "").strip()
    required_keys = {
        "alpaca": ("APCA_API_KEY_ID", "chave Alpaca ausente"),
        "alpha_vantage": ("ALPHA_VANTAGE_API_KEY", "chave Alpha Vantage ausente"),
        "brave": ("BRAVE_API_KEY", "chave Brave Search ausente"),
        "github_mcp": ("GITHUB_MCP_TOKEN", "token GitHub ausente"),
        "quantconnect": ("QUANTCONNECT_TOKEN", "token QuantConnect ausente"),
    }
    requirement = required_keys.get(sid)
    if requirement and not (key or os.environ.get(requirement[0])):
        return False, requirement[1]
    return True, "configurado"


def tool_status() -> list[dict[str, Any]]:
    """Status de cada MCP server (ativado? testavel? ultima resposta?)."""
    servers = load_mcp_servers()
    out = []
    for sid, s in servers.items():
        available, reason = _availability(sid, s)
        out.append({
            "id": sid,
            "name": s.get("name", sid),
            "configured": bool(s.get("enabled", False)),
            "enabled": available,
            "reason": reason,
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
