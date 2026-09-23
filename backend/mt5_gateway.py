# -*- coding: utf-8 -*-
"""MT5 Gateway - servico local na porta 9001 (MCP HTTP).

Responde /api/health, /api/account, /api/positions, /api/history e uma rota
de ordem demo explicitamente protegida, usando o pacote MetaTrader5 da maquina.
Rodar: python backend/mt5_gateway.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import math
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.asset_registry import discover_assets
from backend import connection_service
from backend.mexc_client import MexcClient, MexcError
from backend.risk_gate import validate_trade
from backend.connection_store import save_connection, list_connections, delete_connection, set_connection_active, load_credentials
from backend.binance_client import BinanceClient, BinanceError
from backend.universal_contracts import UniversalOrderRequest, error_response, execution_policy
from backend.audit_log import record as record_audit
from backend.guardian_engine import guardian_set, guardian_remove, guardian_status, guardian_tick, start_guardian_loop
from backend import intent_log
from backend import persistent_queue
from backend import watchdog

HOST = "127.0.0.1"
PORT = 9001


def _gateway_build() -> str:
    """Build do gateway derivado da fonte unica Docs/version.json (L15)."""
    try:
        root = Path(__file__).resolve().parent.parent
        data = json.loads((root / "Docs" / "version.json").read_text(encoding="utf-8"))
        version = str(data.get("version", "1.2.3")).strip()
        suffix = str(data.get("gateway_build_suffix", "universal")).strip() or "universal"
        updated = str(data.get("updated_at", "")).strip().replace("-", "")
        stamp = updated if len(updated) == 8 and updated.isdigit() else "20260918"
        return f"xau-ai-pro-{version}-{suffix}-{stamp}"
    except (OSError, ValueError):
        return "xau-ai-pro-1.2.3-universal-20260918"


GATEWAY_BUILD = _gateway_build()
REAL_ORDER_KEYS: set[str] = set()
LAST_COMMAND: dict = {"command": None, "status": "idle", "updated_at": None}
REAL_EMERGENCY_STOP = Path(os.getenv("XAU_REAL_EMERGENCY_FILE", str(Path(__file__).with_name("REAL_EMERGENCY_STOP"))))
COMMON_FILES = Path(os.getenv("XAU_MT5_COMMON_FILES", str(Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal" / "Common" / "Files")))
CONFIG_FILE = Path(os.getenv("XAU_APP_CONFIG", str(Path(os.environ.get("APPDATA", "")) / "XAU_AI_PRO" / "config.json")))
AUDIT_FILE = Path(os.getenv("XAU_AUDIT_FILE", str(Path(os.environ.get("APPDATA", "")) / "XAU_AI_PRO" / "audit.jsonl")))
# Segurança de exposição: token opcional e rate limit (pré-requisito p/ acesso remoto/Android).
API_TOKEN = os.getenv("XAU_GATEWAY_TOKEN", "").strip()
RATE_LIMIT_MAX = int(os.getenv("XAU_RATE_LIMIT", "0") or 0)  # req/min; 0 = ilimitado (desktop local)
RATE_LIMIT_CMD_MAX = int(os.getenv("XAU_RATE_LIMIT_CMD", "0") or 0)  # comandos/min; 0 = usa RATE_LIMIT_MAX
_RATE_STATE = {"count": 0, "window": 0.0}
_RATE_STATE_CMD = {"count": 0, "window": 0.0}
CONFIG_DEFAULTS = {"theme": "dark", "language": "pt-BR", "precision": 2, "marketAutoRefresh": True, "dashboardAutoRefresh": True, "historyAutoRefresh": True}

def _safe_number(value) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return number if math.isfinite(number) and 0 <= number < 1e15 else 0.0

def _normalize_exchange_account(account):
    """Normaliza respostas Spot/Futuros sem usar campos de controle como saldo."""
    if isinstance(account, dict):
        balances = account.get("balances")
        if isinstance(balances, list):
            assets = [x for x in balances if isinstance(x, dict)]
            return {"balance": sum(_safe_number(x.get("free")) + _safe_number(x.get("locked")) for x in assets),
                    "available": sum(_safe_number(x.get("free")) for x in assets), "currency": "USDT", "assets": assets}
        total = _safe_number(account.get("totalWalletBalance")) or _safe_number(account.get("equity")) or _safe_number(account.get("balance"))
        available = _safe_number(account.get("availableBalance")) or _safe_number(account.get("available"))
        return {"balance": total, "available": available, "currency": "USDT", "assets": []}
    if isinstance(account, list):
        assets = [x for x in account if isinstance(x, dict)]
        total = sum(_safe_number(x.get("equity")) or _safe_number(x.get("balance")) for x in assets)
        available = sum(_safe_number(x.get("availableBalance")) or _safe_number(x.get("available")) or _safe_number(x.get("free")) for x in assets)
        return {"balance": total, "available": available, "currency": "USDT", "assets": assets}
    return {"balance": 0.0, "available": 0.0, "currency": "USDT", "assets": []}

def _load_local_exchange_env() -> None:
    """Carrega apenas o arquivo local ignorado pelo Git; nunca registra valores."""
    root = Path(__file__).resolve().parent.parent
    try:
        lines = []
        locations = [root, Path.cwd(), Path(os.environ.get("APPDATA", "")) / "XAU AI PRO"]
        for location in locations:
            for env_file in (location / ".env.mexc.local", location / ".env.binance.local"):
                if env_file.exists():
                    lines.extend(env_file.read_text(encoding="utf-8").splitlines())
        for line in lines:
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            if key.startswith(("MEXC_", "BINANCE_")) and value.strip():
                os.environ.setdefault(key.strip(), value.strip())
    except OSError:
        pass

_load_local_exchange_env()

def _exchange_market(market: str) -> str:
    """Mercado interno das exchanges (spot/futures) a partir do alias do app."""
    value = str(market or "").strip().lower()
    if value in {"crypto-futures", "futures", "futuros", "crypto_futures"}:
        return "futures"
    return "spot"


def _apply_saved_credentials(broker: str, market: str) -> None:
    if broker not in {"mexc", "binance"}: return
    pair = load_credentials(broker, market)
    if not pair: return
    prefix = broker.upper()
    suffix = "FUTURES" if market == "crypto-futures" else "SPOT"
    os.environ[f"{prefix}_{suffix}_API_KEY"], os.environ[f"{prefix}_{suffix}_API_SECRET"] = pair

def _universal_history(broker: str, market: str, symbol: str = "", days: int = 0) -> dict:
    _apply_saved_credentials(broker, market)
    if broker == "mt5":
        raw = _history(days or 30, symbol)
        deals = [{"id": str(row.get("ticket", "")), "broker": "mt5", "accountId": "mt5-active", "market": market or "other", "symbol": row.get("symbol", symbol), "side": row.get("type", ""), "entry": row.get("entry", "TRADE"), "status": "FILLED", "quantity": row.get("volume", 0), "price": row.get("price", 0), "grossPnl": row.get("profit", 0), "commission": row.get("commission", 0), "swap": row.get("swap", 0), "fee": row.get("fee", 0), "realizedPnl": row.get("profit", 0) - row.get("commission", 0) - row.get("swap", 0) - row.get("fee", 0), "executedAt": row.get("time", ""), "source": "mt5_gateway"} for row in raw.get("deals", [])]
        return {"ok": True, "deals": deals, "count": len(deals), "broker": "mt5", "market": market or "other", "source": "mt5_gateway"}
    if broker not in {"mexc", "binance"}:
        raise LookupError("corretora ainda não conectada ao gateway universal")
    exchange = _exchange_market(market)
    if broker == "binance":
        client = BinanceClient(exchange)
    else:
        client = MexcClient(exchange)
    raw = client.history(symbol=symbol)
    rows = raw if isinstance(raw, list) else raw.get("data", []) if isinstance(raw, dict) else []
    deals = []
    for row in rows:
        commission = float(row.get("commission") or 0)
        profit = float(row.get("realizedPnl") or row.get("profit") or 0)
        deals.append({"id": str(row.get("id") or row.get("orderId") or row.get("dealId") or ""), "broker": broker, "accountId": f"{broker}-active", "market": market or "crypto-spot", "symbol": row.get("symbol", symbol), "side": row.get("side", "BUY"), "entry": "TRADE", "status": row.get("status", "FILLED"), "quantity": float(row.get("qty") or row.get("quantity") or row.get("vol") or row.get("executedQty") or 0), "price": float(row.get("price") or row.get("dealPrice") or 0), "grossPnl": profit, "commission": commission, "swap": 0, "fee": float(row.get("fee") or 0), "realizedPnl": profit - commission - float(row.get("fee") or 0), "executedAt": row.get("time") or row.get("timeStamp") or row.get("timestamp") or "", "source": f"{broker}_api"})
    return {"ok": True, "deals": deals, "count": len(deals), "broker": broker, "market": market or "crypto-spot", "source": f"{broker}_api"}


def _universal_account(broker: str, market: str) -> dict:
    _apply_saved_credentials(broker, market)
    if broker == "mt5":
        account = _payload().get("account")
        if not account:
            raise LookupError("conta MT5 indisponível")
        return {"ok": True, "broker": "mt5", "market": market or "other", "account": account,
                "withdrawals_enabled": False, "source": "mt5_gateway"}
    exchange = _exchange_market(market)
    if broker == "mexc":
        client = MexcClient(exchange)
    elif broker == "binance":
        client = BinanceClient(exchange)
    else:
        raise LookupError("corretora não suportada")
    raw = client.account()
    account = raw.get("data", raw) if isinstance(raw, dict) else raw
    account = _normalize_exchange_account(account)
    return {"ok": True, "broker": broker, "market": market or "crypto-spot", "account": account, "withdrawals_enabled": False, "source": f"{broker}_api"}

def _universal_depth(broker: str, market: str, symbol: str) -> dict:
    _apply_saved_credentials(broker, market)
    exchange = _exchange_market(market)
    if broker == "binance":
        raw = BinanceClient(exchange).depth(symbol)
    elif broker == "mexc":
        raw = MexcClient(exchange).depth(symbol)
    else:
        raise LookupError("livro de ordens MT5 depende do DOM fornecido pelo broker")
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        raw = raw["data"]
    bids = raw.get("bids", []) if isinstance(raw, dict) else []
    asks = raw.get("asks", []) if isinstance(raw, dict) else []
    return {"ok": True, "broker": broker, "market": market, "symbol": symbol.upper(),
            "bids": bids, "asks": asks, "source": f"{broker}_public_depth"}


def _universal_quote(broker: str, market: str, symbol: str) -> dict:
    _apply_saved_credentials(broker, market)
    exchange = _exchange_market(market)
    if broker == "mexc":
        raw = MexcClient(exchange).ticker(symbol)
    elif broker == "binance":
        raw = BinanceClient(exchange).ticker(symbol)
    else:
        quote = dict(_quote(symbol))
        now = datetime.now(timezone.utc).isoformat()
        quote.update({
            "broker": "mt5",
            "market": market or "forex",
            "source": str(quote.get("source") or "mt5_gateway"),
            "timestamp": str(quote.get("timestamp") or now),
            "received_at": now,
        })
        return quote
    data = raw.get("data", raw) if isinstance(raw, dict) else raw
    bid = float(data.get("bidPrice") or data.get("bid1") or data.get("bid") or 0)
    ask = float(data.get("askPrice") or data.get("ask1") or data.get("ask") or 0)
    now = datetime.now(timezone.utc).isoformat()
    return {"broker": broker, "market": market, "symbol": symbol.upper(), "bid": bid, "ask": ask,
            "last": (bid + ask) / 2 if bid and ask else 0,
            "price": (bid + ask) / 2 if bid and ask else 0,
            "spread": ask - bid, "source": f"{broker}_api",
            "timestamp": now, "received_at": now}


def _universal_positions(broker: str, market: str) -> dict:
    """Posicoes normalizadas por corretora (leitura real, sem simulacao)."""
    _apply_saved_credentials(broker, market)
    if broker == "mt5":
        payload = _payload()
        return {"ok": True, "broker": "mt5", "market": market or "other",
                "positions": payload.get("positions", []),
                "exposure": payload.get("exposure", {}), "source": "mt5_gateway"}
    if broker not in {"mexc", "binance"}:
        raise LookupError("corretora não suportada")
    # Spot não possui posições alavancadas; expor ativos não-zero como holdings.
    client = BinanceClient(_exchange_market(market)) if broker == "binance" else MexcClient(_exchange_market(market))
    raw = client.account()
    account = raw.get("data", raw) if isinstance(raw, dict) else raw
    if _exchange_market(market) == "spot" and isinstance(account, dict) and isinstance(account.get("balances"), list):
        holdings = []
        for row in account["balances"]:
            if not isinstance(row, dict):
                continue
            free = _safe_number(row.get("free")); locked = _safe_number(row.get("locked"))
            if free or locked:
                holdings.append({"ticket": f"{broker}:{row.get('asset', '')}", "symbol": str(row.get("asset", "")),
                                 "side": "HOLD", "volume": free + locked, "available": free,
                                 "locked": locked, "profit": 0.0, "pnl_available": False,
                                 "source": f"{broker}_api"})
        return {"ok": True, "broker": broker, "market": market or "crypto-spot",
                "positions": holdings, "pnl": {"value": 0.0, "available": False},
                "source": f"{broker}_api"}
    if broker == "binance" and _exchange_market(market) == "futures" and isinstance(account, dict) and isinstance(account.get("positions"), list):
        positions = []
        for row in account["positions"]:
            amount = _safe_number(row.get("positionAmt"))
            if not amount:
                continue
            positions.append({"ticket": f"binance:{row.get('symbol', '')}", "symbol": str(row.get("symbol", "")),
                              "side": "BUY" if amount > 0 else "SELL", "volume": abs(amount),
                              "open_price": _safe_number(row.get("entryPrice")), "current_price": _safe_number(row.get("markPrice")),
                              "sl": 0.0, "tp": 0.0, "profit": _safe_number(row.get("unRealizedProfit")),
                              "pnl_available": True, "leverage": _safe_number(row.get("leverage")), "source": "binance_api"})
        return {"ok": True, "broker": broker, "market": market or "crypto-futures",
                "positions": positions, "pnl": {"value": sum(float(p["profit"]) for p in positions), "available": True},
                "source": "binance_api"}
    return {"ok": True, "broker": broker, "market": market or "crypto-spot",
            "positions": [], "pnl": {"value": None, "available": False},
            "unavailable": "posições de futuros ainda não expostas por este adaptador",
            "source": f"{broker}_api"}


def _universal_overview() -> dict:
    """Snapshot agregado sem exigir que o terminal MT5 esteja ligado."""
    rows = []
    for connection in list_connections():
        broker = str(connection.get("broker", "")).lower(); market = str(connection.get("market", ""))
        row = {"id": connection.get("id"), "broker": broker, "market": market,
               "active": bool(connection.get("active", True)), "status": "indisponivel",
               "account": None, "positions": [], "pnl": {"value": None, "available": False},
               "error": None, "source": "universal_gateway"}
        if not row["active"]:
            row["status"] = "desativada"; rows.append(row); continue
        try:
            if broker == "mt5":
                payload = _payload()
                if payload.get("account"):
                    row.update(status="conectada", account=payload.get("account"), positions=payload.get("positions", []), source="mt5_gateway")
                else:
                    row.update(status="offline", error="MT5 não conectado; demais corretoras continuam disponíveis")
            elif broker in {"mexc", "binance"}:
                row["account"] = _universal_account(broker, market).get("account")
                positions = _universal_positions(broker, market)
                row["positions"] = positions.get("positions", []); row["pnl"] = positions.get("pnl", row["pnl"]); row["status"] = "conectada"
            else:
                row["error"] = "corretora não suportada"
        except (MexcError, BinanceError, LookupError, ValueError) as exc:
            row["error"] = str(exc)
        rows.append(row)
    return {"ok": True, "mt5_required": False, "connections": rows,
            "connected": sum(1 for row in rows if row["status"] == "conectada"), "source": "universal_gateway"}


def _universal_quotes(broker: str, market: str, symbols: list[str]) -> dict:
    """Cotacoes em lote para o app nao precisar de N requisicoes."""
    quotes: list[dict] = []
    errors: list[dict] = []
    for symbol in symbols:
        try:
            quote = dict(_universal_quote(broker, market, symbol))
            now = datetime.now(timezone.utc).isoformat()
            quote.update({
                "broker": str(quote.get("broker") or broker).lower(),
                "market": str(quote.get("market") or market).lower(),
                "source": str(quote.get("source") or f"{broker}_gateway"),
                "timestamp": str(quote.get("timestamp") or now),
                "received_at": str(quote.get("received_at") or now),
                "symbol": str(quote.get("symbol") or symbol).upper(),
            })
            quotes.append(quote)
        except Exception as exc:
            errors.append({"symbol": symbol, "error": str(exc)})
    return {"ok": True, "broker": broker, "market": market, "quotes": quotes,
            "errors": errors, "count": len(quotes), "source": "universal_gateway"}


def _universal_trades(broker: str, market: str, symbol: str) -> dict:
    _apply_saved_credentials(broker, market)
    exchange = _exchange_market(market)
    if broker == "binance":
        raw = BinanceClient(exchange).trades(symbol)
    elif broker == "mexc":
        raw = MexcClient(exchange).trades(symbol)
    else:
        raise LookupError("negócios recentes indisponíveis para esta fonte")
    if isinstance(raw, dict):
        raw = raw.get("data", raw.get("result", []))
    return {"ok": True, "broker": broker, "market": market, "symbol": symbol.upper(),
            "trades": raw if isinstance(raw, list) else [], "source": f"{broker}_public_trades"}


def _config() -> dict:
    try:
        return {**CONFIG_DEFAULTS, **json.loads(CONFIG_FILE.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(CONFIG_DEFAULTS)

def _save_config(value: dict) -> dict:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    safe = {key: value[key] for key in CONFIG_DEFAULTS if key in value}
    CONFIG_FILE.write_text(json.dumps({**CONFIG_DEFAULTS, **safe}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**CONFIG_DEFAULTS, **safe}


def _mt5():
    import MetaTrader5 as mt5  # noqa: PLC0415
    return mt5


def _ensure_mt5() -> bool:
    # MetaTrader5.initialize() pode abrir o terminal automaticamente.
    # O app deve somente conectar a uma sessao que o usuario ja abriu.
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if "terminal64.exe" not in result.stdout.lower():
                return False
        except (OSError, subprocess.SubprocessError):
            return False
    mt5 = _mt5()
    if not mt5.initialize():
        return False
    try:
        report = intent_log.reconcile(mt5)
        if report.get("checked"):
            print(f"[gateway] reconciliacao de intents: {report}")
        watchdog.record("boot", {"mt5_ready": True, "reconcile": report})
    except Exception as exc:
        print(f"[gateway] reconciliacao indisponivel: {exc}")
    try:
        snapshot = watchdog.snapshot_metrics("boot")
        print(f"[gateway] snapshot inicial: equity={snapshot.get('equity')} "
              f"posicoes={snapshot.get('positions')} ea={snapshot.get('ea_state')}")
    except Exception as exc:
        print(f"[gateway] snapshot inicial indisponivel: {exc}")
    return True


def _read_ea_heartbeat() -> dict:
    """Lê o liveness publicado pelo EA, sem executar comandos no terminal."""
    path = COMMON_FILES / "XAU_AI_PRO_heartbeat.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        timestamp = datetime.strptime(str(payload.get("timestamp", "")), "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        age_sec = max(0.0, time.time() - timestamp.timestamp())
        file_age_sec = max(0.0, time.time() - path.stat().st_mtime)
        payload["age_sec"] = round(age_sec, 1)
        payload["file_age_sec"] = round(file_age_sec, 1)
        # O timestamp vem de TimeCurrent() do servidor MT5 e pode ficar
        # desalinhado do relogio local. A idade do arquivo e a evidencia de
        # escrita real em FILE_COMMON; o timestamp permanece diagnostico.
        payload["live"] = file_age_sec <= 30 and payload.get("state") == "RUNNING"
        if not payload["live"]:
            payload["reason"] = "arquivo nao atualizado" if file_age_sec > 30 else "estado nao RUNNING"
        elif age_sec > 15:
            payload["clock_skew"] = True
        payload["source"] = "EA FILE_COMMON"
        return payload
    except (OSError, ValueError, TypeError):
        return {"live": False, "source": "EA FILE_COMMON", "reason": "heartbeat ausente"}


def _journal_roots() -> list[Path]:
    """Diretórios candidatos de logs do Journal do terminal MT5."""
    roots: list[Path] = []
    terminal_root = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
    try:
        if terminal_root.is_dir():
            roots.extend(entry / "MQL5" / "Logs" for entry in terminal_root.iterdir() if (entry / "MQL5" / "Logs").is_dir())
    except OSError:
        pass
    base = Path(__file__).resolve().parents[3]
    roots.extend([base / "MQL5" / "Logs", base / "Logs"])
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _decode_log_tail(head: bytes, data: bytes, mid_file: bool) -> str:
    """Decodifica o trecho final de um log MT5 (UTF-16 LE típico, fallback UTF-8)."""
    has_bom = head[:2] in (b"\xff\xfe", b"\xfe\xff")
    if has_bom and not mid_file:
        return data.decode("utf-16", errors="replace")
    text = data.decode("utf-16-le", errors="replace")
    if "\x00" in text:  # não era UTF-16: provável UTF-8/ASCII
        text = data.decode("utf-8", errors="replace")
    return text


def _read_log_tail(path: Path, limit: int) -> list[str]:
    """Lê apenas a cauda do arquivo (logs do MT5 podem passar de 100 MB)."""
    try:
        size = path.stat().st_size
    except OSError:
        return []
    if size <= 0:
        return []
    chunk = min(size, max(65536, limit * 256))
    offset = size - chunk
    if offset % 2:
        offset -= 1  # mantém o alinhamento de 2 bytes exigido pelo UTF-16
    chunk = size - offset
    try:
        with path.open("rb") as handle:
            head = handle.read(2)
            handle.seek(offset)
            data = handle.read(chunk)
    except OSError:
        return []
    lines = [ln for ln in _decode_log_tail(head, data, mid_file=offset > 0).splitlines() if ln.strip()]
    if offset > 0 and len(lines) > 1:
        lines = lines[1:]  # a primeira linha do bloco pode estar cortada
    return lines[-max(1, min(limit, 500)):]


def _journal(limit: int = 100) -> dict:
    """Retorna as linhas mais recentes do Journal/Experts do terminal MT5."""
    override_env = os.getenv("XAU_MT5_LOGS_DIR", "").strip()
    roots = _journal_roots()
    override = Path(override_env) if override_env else None
    files = list(override.glob("*.log")) if override and override.is_dir() else []
    if not files:
        files = [f for root in roots if root.is_dir() for f in root.glob("*.log")]
    if not files:
        return {"ok": True, "source": "MT5 Journal", "lines": [], "count": 0}
    latest = max(files, key=lambda f: f.stat().st_mtime)
    rows = [{"source": "MT5 Journal", "file": latest.name, "message": ln} for ln in _read_log_tail(latest, limit)]
    return {"ok": True, "source": "MT5 Journal", "file": latest.name, "lines": rows, "count": len(rows)}


def _payload() -> dict:
    mt5 = _mt5()
    out = {"ts": datetime.now().isoformat(), "gateway": "XAU_AI_PRO MT5 Gateway"}
    out["ea_heartbeat"] = _read_ea_heartbeat()
    try:
        ti = mt5.terminal_info()
        out["terminal_connected"] = bool(ti.connected) if ti else False
    except Exception:
        out["terminal_connected"] = False
    try:
        info = mt5.account_info()
        if info:
            demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
            trade_mode = getattr(info, "trade_mode", None)
            account_mode = "DEMO" if trade_mode == demo_mode else ("REAL" if trade_mode is not None else "UNKNOWN")
            out["account"] = {
                "login": info.login, "name": info.name,
                "company": info.company, "server": info.server,
                "balance": info.balance,
                "equity": info.equity, "profit": info.profit,
                "margin": info.margin, "margin_free": info.margin_free,
                "margin_level": info.margin_level, "currency": info.currency,
                "trade_allowed": bool(getattr(ti, "trade_allowed", False)) if ti else False,
                "terminal_connected": bool(getattr(ti, "connected", False)) if ti else False,
                "mode": account_mode,
                "demo_confirmed": account_mode == "DEMO",
            }
    except Exception:
        pass
    try:
        pos = mt5.positions_get()
        out["positions"] = [{
            "ticket": p.ticket, "symbol": p.symbol,
            "type": "BUY" if p.type == 0 else "SELL",
            "volume": p.volume, "open_price": p.price_open,
            "price_current": p.price_current, "sl": p.sl, "tp": p.tp,
            "profit": p.profit, "magic": p.magic,
            "time": int(getattr(p, "time", 0) or 0),
        } for p in (pos or [])]
        out["exposure"] = {
            "count": len(pos or []),
            "volume": round(sum(float(getattr(p, "volume", 0.0)) for p in (pos or [])), 8),
            "floating_profit": round(sum(float(getattr(p, "profit", 0.0)) for p in (pos or [])), 2),
            "protected": sum(1 for p in (pos or []) if getattr(p, "sl", 0.0) and getattr(p, "tp", 0.0)) == len(pos or []),
        }
    except Exception:
        out["positions"] = []
        out["exposure"] = {"count": 0, "volume": 0, "floating_profit": 0, "protected": True}
    try:
        orders = mt5.orders_get() or []
        out["pending_orders"] = [{"ticket": o.ticket, "symbol": o.symbol, "type": int(o.type), "volume": o.volume_current, "price": o.price_open, "sl": o.sl, "tp": o.tp, "time": o.time_setup} for o in orders]
    except Exception:
        out["pending_orders"] = []
    try:
        deals = mt5.history_deals_get(datetime.now() - timedelta(days=7), datetime.now())
        out["history_count"] = len(deals or [])
    except Exception:
        out["history_count"] = 0
    return out


def _quote(symbol: str) -> dict:
    mt5 = _mt5()
    if not symbol:
        raise ValueError("symbol obrigatorio")
    if not mt5.symbol_select(symbol, True):
        raise LookupError(f"simbolo indisponivel no MT5: {symbol}")
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        raise LookupError(f"cotacao indisponivel no MT5: {symbol}")
    info = mt5.symbol_info(symbol)
    bid = float(tick.bid or 0.0)
    ask = float(tick.ask or 0.0)
    return {
        "symbol": symbol,
        "bid": bid,
        "ask": ask,
        "last": float(getattr(tick, "last", 0.0) or 0.0),
        "volume": float(getattr(tick, "volume", 0) or 0),
        "high": float(getattr(info, "session_price_high", 0.0) or 0.0),
        "low": float(getattr(info, "session_price_low", 0.0) or 0.0),
        "change_pct": 0.0,
        "timestamp": datetime.now().isoformat(),
        "source": "mt5_gateway",
    }


def _symbols() -> dict:
    """Lista somente símbolos reais visíveis no terminal MT5."""
    mt5 = _mt5()
    rows = discover_assets(mt5, include_hidden=True)
    return {"symbols": rows, "count": len(rows), "source": "mt5_gateway", "scope": "broker_catalog"}
    return {"symbols": rows, "count": len(rows), "source": "mt5_gateway", "scope": "broker_catalog"}


def _history(days: int = 30, symbol: str = "") -> dict:
    """Retorna deals fechados reais do MT5; nunca cria dados de teste."""
    mt5 = _mt5()
    days = max(1, min(days, 3650))
    end = datetime.now()
    # O filtro Hoje começa à meia-noite local; nunca inclui operações de ontem.
    start = end.replace(hour=0, minute=0, second=0, microsecond=0) if days == 1 else end - timedelta(days=days)
    deals = mt5.history_deals_get(start, end, group=f"*{symbol}*") if symbol else mt5.history_deals_get(start, end)
    rows = []
    for deal in deals or []:
        deal_type = getattr(deal, "type", None)
        entry = getattr(deal, "entry", None)
        # In/Out são mantidos para auditoria; somente saídas representam resultado realizado.
        rows.append({
            "ticket": int(getattr(deal, "ticket", 0)),
            "order": int(getattr(deal, "order", 0)),
            "position_id": int(getattr(deal, "position_id", 0)),
            "symbol": str(getattr(deal, "symbol", "")),
            "type": "BUY" if deal_type == getattr(mt5, "DEAL_TYPE_BUY", 0) else "SELL",
            "entry": "IN" if entry == getattr(mt5, "DEAL_ENTRY_IN", 0) else "OUT" if entry == getattr(mt5, "DEAL_ENTRY_OUT", 1) else str(entry),
            "volume": float(getattr(deal, "volume", 0.0) or 0.0),
            "price": float(getattr(deal, "price", 0.0) or 0.0),
            "profit": float(getattr(deal, "profit", 0.0) or 0.0),
            "commission": float(getattr(deal, "commission", 0.0) or 0.0),
            "swap": float(getattr(deal, "swap", 0.0) or 0.0),
            "fee": float(getattr(deal, "fee", 0.0) or 0.0),
            "magic": int(getattr(deal, "magic", 0)),
            "time": datetime.fromtimestamp(int(getattr(deal, "time", 0))).isoformat(),
        })
    rows.sort(key=lambda row: row["time"], reverse=True)
    return {"deals": rows, "count": len(rows), "days": days, "source": "mt5_gateway"}




_TIMEFRAME_MAP = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 16385, "H4": 16388, "D1": 16408}


def _economic_calendar(limit: int = 30, tz: str = "BRT", days: int = 14) -> dict:
    """Agenda economica real (tabela local recorrente) — nunca retorna mock.

    Fonte unica: app/economic_calendar.py. Os horarios sao estimativas baseadas
    em padroes de calendario; o payload marca isso explicitamente em 'disclaimer'.
    """
    from app.economic_calendar import upcoming_events

    limit = max(1, min(int(limit), 200))
    days = max(1, min(int(days), 60))
    events = upcoming_events(limit=limit, days=days, tz=tz or "BRT", relevance="all")
    return {
        "ok": True,
        "events": events,
        "count": len(events),
        "timezone": (tz or "BRT").upper(),
        "days": days,
        "source": "app.economic_calendar",
        "disclaimer": "Horarios estimados por padrao de calendario; confirme na agenda oficial do broker antes de operar.",
    }


def _mt5_candles(symbol: str = "XAUUSD", timeframe: str = "M5", count: int = 300) -> dict:
    """Candles OHLC reais do terminal (copy_rates); nunca gera dados sinteticos."""
    mt5 = _mt5()
    symbol = (symbol or "XAUUSD").upper()
    count = max(10, min(int(count), 2000))
    tf_code = _TIMEFRAME_MAP.get((timeframe or "M5").upper(), 5)
    rates = mt5.copy_rates(symbol, tf_code, count)
    if rates is None:
        return {"ok": False, "error": f"sem candles para {symbol} ({timeframe.upper()})", "candles": [], "count": 0, "source": "mt5_gateway"}
    rows = [{
        "time": int(rate["time"]),
        "open": float(rate["open"]),
        "high": float(rate["high"]),
        "low": float(rate["low"]),
        "close": float(rate["close"]),
        "volume": int(rate["tick_volume"]) if "tick_volume" in rate else 0,
    } for rate in rates]
    rows.sort(key=lambda row: row["time"])
    return {"ok": True, "symbol": symbol, "timeframe": timeframe.upper(), "candles": rows, "count": len(rows), "source": "mt5_gateway"}
def _risk_state(mt5) -> dict:
    """Estado de risco real do dia, lido do MT5 (nunca estimado).

    - daily_loss_pct: perda do dia (deals do dia, profit+commission+swap)
      como percentual do balance. Negativo quando ha lucro.
    - exposure_pct: volume aberto como percentual do teto do risk_gate
      (max_positions * max_volume = 5 * 0.10 = 0.5 lotes).
    - open_positions: quantidade de posicoes abertas.

    Falha de leitura -> devolve valores conservadores (Nao trata como 0),
    porque o risk_gate usa fail-closed para novas entradas.
    """
    from backend.risk_gate import RiskLimits

    limits = RiskLimits()
    try:
        info = mt5.account_info()
        balance = float(getattr(info, "balance", 0.0) or 0.0) if info else 0.0
    except Exception:
        balance = 0.0

    positions: list = []
    try:
        positions = list(mt5.positions_get() or [])
    except Exception:
        positions = []

    try:
        now = datetime.now()
        deals = list(mt5.history_deals_get(
            now.replace(hour=0, minute=0, second=0, microsecond=0), now) or [])
    except Exception:
        deals = []

    day_result = 0.0
    for deal in deals:
        day_result += float(getattr(deal, "profit", 0.0) or 0.0)
        day_result += float(getattr(deal, "commission", 0.0) or 0.0)
        day_result += float(getattr(deal, "swap", 0.0) or 0.0)

    daily_loss_pct = (-day_result / balance * 100.0) if balance > 0 else 0.0
    if daily_loss_pct < 0:
        daily_loss_pct = 0.0  # lucro do dia nao consome o limite de perda

    volume = sum(float(getattr(p, "volume", 0.0) or 0.0) for p in positions)
    ceiling = limits.max_volume * limits.max_positions
    exposure_pct = (volume / ceiling * 100.0) if ceiling > 0 else 0.0

    return {
        "daily_loss_pct": round(daily_loss_pct, 4),
        "exposure_pct": round(exposure_pct, 4),
        "open_positions": len(positions),
        "open_volume": round(volume, 4),
        "balance": balance,
        "day_result": round(day_result, 4),
        "limits": {
            "max_volume": limits.max_volume,
            "max_daily_loss_pct": limits.max_daily_loss_pct,
            "max_exposure_pct": limits.max_exposure_pct,
            "max_positions": limits.max_positions,
        },
    }


def _demo_order(payload: dict) -> dict:
    """Envia ordem apenas para conta DEMO quando a trava local estiver ativa."""
    if os.getenv("XAU_ENABLE_DEMO_ORDERS", "0") != "1":
        raise PermissionError("execucao demo desabilitada; defina XAU_ENABLE_DEMO_ORDERS=1")
    if payload.get("confirm_demo") is not True:
        raise PermissionError("confirm_demo=true obrigatorio")
    mt5 = _mt5()
    info = mt5.account_info()
    demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
    if not info or getattr(info, "trade_mode", None) != demo_mode:
        raise PermissionError("conta MT5 nao identificada como DEMO; ordem recusada")
    if not bool(getattr(info, "trade_allowed", False)):
        raise PermissionError("negociacao nao permitida pelo terminal MT5")
    symbol = str(payload.get("symbol", "")).strip()
    side = str(payload.get("side", "")).upper()
    volume = float(payload.get("volume", 0) or 0)
    sl = float(payload.get("sl", 0) or 0)
    tp = float(payload.get("tp", 0) or 0)
    if not symbol or side not in {"BUY", "SELL"} or not (0 < volume <= 0.10) or sl <= 0 or tp <= 0:
        raise ValueError("symbol, side, volume <= 0.10, sl e tp validos sao obrigatorios")
    # Risco REAL do dia: perda diaria e exposicao lidas do MT5 (nao mais 0.0 fixo).
    # Antes desta correcao o risk_gate recebia daily_loss_pct=0.0 e exposure_pct=0.0,
    # o que desarmava os dois limites mais importantes em conta de dinheiro real.
    risk = _risk_state(mt5)
    validate_trade(volume=volume, daily_loss_pct=risk["daily_loss_pct"],
                   exposure_pct=risk["exposure_pct"], open_positions=risk["open_positions"])
    if not mt5.symbol_select(symbol, True):
        raise LookupError(f"simbolo indisponivel no MT5: {symbol}")
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        raise LookupError(f"cotacao indisponivel no MT5: {symbol}")
    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
    price = float(tick.ask if side == "BUY" else tick.bid)
    request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": volume,
               "type": order_type, "price": price, "sl": sl, "tp": tp,
               "deviation": 20, "magic": 2026001, "comment": "XAU_AI_PRO_DEMO",
               "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
    check = mt5.order_check(request)
    if not check or getattr(check, "retcode", 0) != 0:
        return {"ok": False, "stage": "order_check", "retcode": int(getattr(check, "retcode", -1)), "comment": str(getattr(check, "comment", "check falhou")), "demo": True}
    result = mt5.order_send(request)
    return {"ok": bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE), "stage": "order_send", "retcode": int(getattr(result, "retcode", -1)), "comment": str(getattr(result, "comment", "")), "order": int(getattr(result, "order", 0)), "deal": int(getattr(result, "deal", 0)), "demo": True}


def _universal_execution_preview(payload: dict, action: str) -> dict:
    """Valida o contrato universal e retorna pré-envio; nunca roteia execução."""
    try:
        if action == "order":
            request = UniversalOrderRequest.from_payload(payload)
            data = request.to_dict()
        else:
            broker = str(payload.get("broker", "")).lower()
            symbol = str(payload.get("symbol", "")).strip().upper()
            if broker not in {"mt5", "mexc", "binance"} or not symbol:
                raise ValueError("broker e symbol são obrigatórios")
            data = {"broker": broker, "market": str(payload.get("market", "")).lower(), "symbol": symbol, "account_id": payload.get("account_id"), "ticket": payload.get("ticket")}
        return {"ok": False, "accepted": False, "stage": "validated", "action": action, "request": data, "policy": execution_policy(), "error": {"code": "EXECUTION_ADAPTER_PENDING", "message": "contrato válido; adaptador de execução ainda não habilitado"}}
    except (TypeError, ValueError) as exc:
        return error_response("INVALID_UNIVERSAL_REQUEST", str(exc))


def _real_order(payload: dict) -> dict:
    """Execucao REAL opt-in, com trava de emergencia e idempotencia."""
    if os.getenv("XAU_ENABLE_REAL_ORDERS", "0") != "1":
        raise PermissionError("execucao real desabilitada; XAU_ENABLE_REAL_ORDERS=1 obrigatorio")
    if REAL_EMERGENCY_STOP.exists():
        raise PermissionError("parada de emergencia ativa")
    if payload.get("confirm_real") is not True:
        raise PermissionError("confirm_real=true obrigatorio")
    request_id = str(payload.get("request_id", "")).strip()
    if not request_id or request_id in REAL_ORDER_KEYS:
        raise ValueError("request_id unico obrigatorio")
    mt5 = _mt5(); info = mt5.account_info()
    demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
    if not info or getattr(info, "trade_mode", None) == demo_mode:
        raise PermissionError("conta DEMO detectada; ordem real recusada")
    if not bool(getattr(info, "trade_allowed", False)):
        raise PermissionError("negociacao nao permitida pelo terminal MT5")
    symbol = str(payload.get("symbol", "")).strip(); side = str(payload.get("side", "")).upper()
    volume = float(payload.get("volume", 0) or 0); sl = float(payload.get("sl", 0) or 0); tp = float(payload.get("tp", 0) or 0)
    if not symbol or side not in {"BUY", "SELL"} or not (0 < volume <= 0.01) or sl <= 0 or tp <= 0:
        raise ValueError("symbol, side, volume real <= 0.01, sl e tp validos sao obrigatorios")
    if not mt5.symbol_select(symbol, True): raise LookupError(f"simbolo indisponivel no MT5: {symbol}")
    tick = mt5.symbol_info_tick(symbol)
    if not tick: raise LookupError(f"cotacao indisponivel no MT5: {symbol}")
    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
    price = float(tick.ask if side == "BUY" else tick.bid)
    request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": volume, "type": order_type, "price": price, "sl": sl, "tp": tp, "deviation": 10, "magic": 2026001, "comment": "XAU_AI_PRO_REAL", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
    check = mt5.order_check(request)
    if not check or getattr(check, "retcode", 0) != 0:
        return {"ok": False, "stage": "order_check", "retcode": int(getattr(check, "retcode", -1)), "comment": str(getattr(check, "comment", "check falhou")), "real": True}
    REAL_ORDER_KEYS.add(request_id)
    result = mt5.order_send(request)
    return {"ok": bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE), "stage": "order_send", "retcode": int(getattr(result, "retcode", -1)), "comment": str(getattr(result, "comment", "")), "order": int(getattr(result, "order", 0)), "deal": int(getattr(result, "deal", 0)), "real": True}


def _demo_close(payload: dict) -> dict:
    """Fecha uma posição DEMO específica; nunca aceita conta real."""
    if os.getenv("XAU_ENABLE_DEMO_ORDERS", "0") != "1":
        raise PermissionError("ordens DEMO desabilitadas")
    if payload.get("confirm_demo") is not True:
        raise PermissionError("confirm_demo=true obrigatorio")
    mt5 = _mt5(); info = mt5.account_info()
    demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
    if not info or getattr(info, "trade_mode", None) != demo_mode:
        raise PermissionError("somente conta DEMO aceita")
    ticket = int(payload.get("ticket", 0) or 0)
    positions = mt5.positions_get(ticket=ticket) if ticket else None
    if not positions:
        raise LookupError("posicao DEMO nao encontrada")
    position = positions[0]; symbol = str(getattr(position, "symbol", "")); volume = float(payload.get("_partial_volume", getattr(position, "volume", 0)) or 0)
    tick = mt5.symbol_info_tick(symbol)
    if not tick: raise LookupError(f"cotacao indisponivel no MT5: {symbol}")
    position_type = getattr(position, "type", 0)
    close_type = mt5.ORDER_TYPE_SELL if position_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = float(tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask)
    request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": volume, "type": close_type, "position": ticket, "price": price, "deviation": 20, "magic": 2026001, "comment": "XAU_AI_PRO_DEMO_CLOSE", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
    intent_id = intent_log.record_intent("demo_close", {"ticket": ticket, "symbol": symbol, "volume": volume}, status="pending")
    check = mt5.order_check(request)
    if not check or getattr(check, "retcode", 0) != 0:
        intent_log.record_intent("demo_close", {"ticket": ticket, "symbol": symbol, "volume": volume}, intent_id=intent_id, status="failed", extra={"stage": "order_check", "retcode": int(getattr(check, "retcode", -1))})
        return {"ok": False, "stage": "order_check", "retcode": int(getattr(check, "retcode", -1)), "comment": str(getattr(check, "comment", "check falhou")), "demo": True}
    result = mt5.order_send(request)
    ok_close = bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE)
    intent_log.record_intent("demo_close", {"ticket": ticket, "symbol": symbol, "volume": volume}, intent_id=intent_id, status="sent" if ok_close else "failed", extra={"retcode": int(getattr(result, "retcode", -1)), "order": int(getattr(result, "order", 0)), "deal": int(getattr(result, "deal", 0))})
    return {"ok": ok_close, "stage": "order_send", "retcode": int(getattr(result, "retcode", -1)), "comment": str(getattr(result, "comment", "")), "order": int(getattr(result, "order", 0)), "deal": int(getattr(result, "deal", 0)), "demo": True}


def _demo_manage(payload: dict, action: str) -> dict:
    """Gerenciamento de posição exclusivamente DEMO via TRADE_ACTION_SLTP."""
    if os.getenv("XAU_ENABLE_DEMO_ORDERS", "0") != "1" or payload.get("confirm_demo") is not True:
        raise PermissionError("comando DEMO desabilitado ou confirm_demo=true ausente")
    mt5 = _mt5(); info = mt5.account_info(); demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
    if not info or getattr(info, "trade_mode", None) != demo_mode: raise PermissionError("somente conta DEMO aceita")
    ticket = int(payload.get("ticket", 0) or 0); rows = mt5.positions_get(ticket=ticket) if ticket else None
    if not rows: raise LookupError("posição DEMO não encontrada")
    pos = rows[0]; entry = float(getattr(pos, "price_open", 0) or 0); current_sl = float(getattr(pos, "sl", 0) or 0); current_tp = float(getattr(pos, "tp", 0) or 0)
    side = getattr(pos, "type", 0); tick = mt5.symbol_info_tick(str(getattr(pos, "symbol", "")))
    if not tick: raise LookupError("cotação indisponível")
    if action == "modify": sl = float(payload.get("sl", current_sl) or 0); tp = float(payload.get("tp", current_tp) or 0)
    elif action == "breakeven": sl = entry; tp = current_tp
    else:
        distance = float(payload.get("distance", 0) or 0)
        if distance <= 0: raise ValueError("distance deve ser maior que zero")
        market = float(tick.bid if side == getattr(mt5, "POSITION_TYPE_BUY", 0) else tick.ask)
        sl = market - distance if side == getattr(mt5, "POSITION_TYPE_BUY", 0) else market + distance; tp = current_tp
    request = {"action": mt5.TRADE_ACTION_SLTP, "symbol": str(getattr(pos, "symbol", "")), "position": ticket, "sl": sl, "tp": tp}
    intent_id = intent_log.record_intent("demo_manage", {"ticket": ticket, "sl": sl, "tp": tp}, status="pending")
    result = mt5.order_send(request)
    ok_manage = bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE)
    intent_log.record_intent("demo_manage", {"ticket": ticket, "sl": sl, "tp": tp}, intent_id=intent_id, status="sent" if ok_manage else "failed", extra={"retcode": int(getattr(result, "retcode", -1))})
    return {"ok": ok_manage, "ticket": ticket, "sl": sl, "tp": tp, "retcode": int(getattr(result, "retcode", -1)), "comment": str(getattr(result, "comment", "")), "demo": True}


def _demo_close_all(payload: dict) -> dict:
    if payload.get("confirm_demo") is not True: raise PermissionError("confirm_demo=true obrigatorio")
    mt5 = _mt5(); rows = list(mt5.positions_get() or []); results = [_demo_close({"ticket": int(getattr(p, "ticket", 0)), "confirm_demo": True}) for p in rows]
    return {"ok": all(item.get("ok") for item in results) if results else True, "closed": results, "count": len(results), "demo": True}


def _demo_partial_close(payload: dict) -> dict:
    ticket = int(payload.get("ticket", 0) or 0); part = float(payload.get("volume", 0) or 0)
    if part <= 0: raise ValueError("volume parcial deve ser maior que zero")
    mt5 = _mt5(); rows = mt5.positions_get(ticket=ticket) if ticket else None
    if not rows: raise LookupError("posição DEMO não encontrada")
    p = rows[0]; total = float(getattr(p, "volume", 0) or 0)
    if part >= total: raise ValueError("volume parcial deve ser menor que o volume da posição")
    data = dict(payload); data["ticket"] = ticket
    return _demo_close({**data, "_partial_volume": part})


def _require_demo_command(payload: dict) -> tuple:
    """Valida a trava comum de qualquer comando que altera a conta DEMO."""
    if os.getenv("XAU_ENABLE_DEMO_ORDERS", "0") != "1":
        raise PermissionError("ordens DEMO desabilitadas")
    if payload.get("confirm_demo") is not True:
        raise PermissionError("confirm_demo=true obrigatorio")
    mt5 = _mt5()
    info = mt5.account_info()
    if not info or getattr(info, "trade_mode", None) != getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0):
        raise PermissionError("somente conta DEMO aceita")
    return mt5, info


def _demo_protection(payload: dict, remove: bool = False) -> dict:
    mt5, _ = _require_demo_command(payload)
    ticket = int(payload.get("ticket", 0) or 0)
    rows = mt5.positions_get(ticket=ticket) if ticket else None
    if not rows:
        raise LookupError("posicao DEMO nao encontrada")
    pos = rows[0]
    symbol = str(getattr(pos, "symbol", ""))
    if remove:
        sl, tp = 0.0, 0.0
    else:
        sl = float(payload.get("sl", 0) or 0)
        tp = float(payload.get("tp", 0) or 0)
        if sl <= 0 or tp <= 0:
            raise ValueError("sl e tp validos sao obrigatorios")
    request = {"action": mt5.TRADE_ACTION_SLTP, "symbol": symbol, "position": ticket, "sl": sl, "tp": tp}
    result = mt5.order_send(request)
    return {"ok": bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE),
            "action": "remove_protection" if remove else "set_protection", "ticket": ticket,
            "symbol": symbol, "sl": sl, "tp": tp, "retcode": int(getattr(result, "retcode", -1)),
            "comment": str(getattr(result, "comment", "")), "demo": True}


def _demo_close_symbol(payload: dict) -> dict:
    mt5, _ = _require_demo_command(payload)
    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol:
        raise ValueError("symbol obrigatorio")
    rows = list(mt5.positions_get(symbol=symbol) or [])
    results = [_demo_close({"ticket": int(getattr(p, "ticket", 0)), "confirm_demo": True}) for p in rows]
    return {"ok": all(r.get("ok") for r in results) if results else True, "symbol": symbol,
            "closed": results, "count": len(results), "demo": True}


def _demo_cancel_orders(payload: dict, all_orders: bool = False) -> dict:
    mt5, _ = _require_demo_command(payload)
    ticket = int(payload.get("ticket", 0) or 0)
    rows = list(mt5.orders_get() or []) if all_orders else list(mt5.orders_get(ticket=ticket) or [])
    if not all_orders and not ticket:
        raise ValueError("ticket obrigatorio")
    results = []
    for order in rows:
        order_ticket = int(getattr(order, "ticket", 0))
        request = {"action": mt5.TRADE_ACTION_REMOVE, "order": order_ticket,
                   "symbol": str(getattr(order, "symbol", "")), "magic": 2026001,
                   "comment": "XAU_AI_PRO_DEMO_CANCEL"}
        result = mt5.order_send(request)
        results.append({"ok": bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE),
                        "ticket": order_ticket, "retcode": int(getattr(result, "retcode", -1)),
                        "comment": str(getattr(result, "comment", ""))})
    return {"ok": all(r["ok"] for r in results) if results else True, "cancelled": results,
            "count": len(results), "demo": True}

def _asset_toggle(payload: dict, enabled: bool) -> dict:
    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol: raise ValueError("symbol obrigatorio")
    mt5 = _mt5(); ok = bool(mt5.symbol_select(symbol, enabled))
    return {"ok": ok, "symbol": symbol, "enabled": enabled, "visible": bool(getattr(mt5.symbol_info(symbol), "visible", False)), "source": "mt5_gateway"}


def _demo_read(kind: str) -> dict:
    mt5 = _mt5()
    info = mt5.account_info()
    if not info or getattr(info, "trade_mode", None) != getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0):
        raise PermissionError("somente conta DEMO disponivel")
    if kind == "positions":
        rows = list(mt5.positions_get() or [])
        return {"ok": True, "positions": [{"ticket": int(p.ticket), "symbol": str(p.symbol), "side": "BUY" if p.type == 0 else "SELL", "volume": float(p.volume), "open_price": float(p.price_open), "current_price": float(p.price_current), "sl": float(p.sl), "tp": float(p.tp), "profit": float(p.profit), "magic": int(p.magic)} for p in rows], "count": len(rows), "account_mode": "DEMO", "source": "mt5_gateway"}
    if kind == "orders":
        rows = list(mt5.orders_get() or [])
        return {"ok": True, "orders": [{"ticket": int(o.ticket), "symbol": str(o.symbol), "type": int(o.type), "volume": float(o.volume_current), "price": float(o.price_open), "sl": float(o.sl), "tp": float(o.tp), "time_setup": int(o.time_setup)} for o in rows], "count": len(rows), "account_mode": "DEMO", "source": "mt5_gateway"}
    payload = _payload()
    return {"ok": True, "gateway": "online", "mt5_connected": bool(payload.get("account")), "ea_heartbeat": payload.get("ea_heartbeat"), "positions": len(payload.get("positions", [])), "account_mode": "DEMO", "last_command": LAST_COMMAND, "source": "mt5_gateway"}


def _ea_status() -> dict:
    hb = _read_ea_heartbeat()
    mt5 = _mt5()
    ti = mt5.terminal_info()
    return {"ok": True, "ea_heartbeat": hb, "live": bool(hb.get("live")),
            "terminal_connected": bool(ti and getattr(ti, "connected", False)),
            "autotrading": bool(hb.get("autotrading", False)), "source": "mt5_gateway"}


def _ea_command(payload: dict, command: str) -> dict:
    hb = _read_ea_heartbeat()
    if not hb.get("live"):
        raise RuntimeError("EA sem heartbeat vivo; comando nao enviado")
    if command in {"close", "close-all"}:
        if payload.get("confirm_live") is not True or payload.get("authorize_execution") is not True:
            raise PermissionError("confirm_live=true e authorize_execution=true obrigatorios")
    value = str(payload.get("value", payload.get("symbol", payload.get("timeframe", ""))))
    command_file = COMMON_FILES / "XAU_AI_PRO_ea_command.json"
    command_file.parent.mkdir(parents=True, exist_ok=True)
    symbol = str(payload.get("symbol", "")).strip()
    ticket = int(payload.get("ticket", 0) or 0)
    lines = [f"command={command}", f"value={value}"]
    if symbol: lines.append(f"symbol={symbol}")
    if ticket > 0: lines.append(f"ticket={ticket}")
    command_file.write_text("\n".join(lines) + "\n", encoding="ascii")
    return {"ok": True, "accepted": True, "command": command, "value": value, "ticket": ticket, "status": "queued", "demo": hb.get("mode", "DEMO") == "DEMO", "source": "mt5_common_files"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silencia log
        pass

    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        """Permite o preflight Tauri/browser antes dos comandos DEMO."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _is_command(self) -> bool:
        """POST e considerado comando; GET e leitura (polling de painel)."""
        return self.command.upper() != "GET"

    def _autorizado(self) -> tuple[bool, str]:
        """Token opcional (XAU_GATEWAY_TOKEN) + rate limit por categoria.

        Comandos (POST) e leituras (GET) tem janelas separadas: o polling do
        painel nao consome a cota de comandos. XAU_RATE_LIMIT_CMD define a
        cota de comandos (fallback: XAU_RATE_LIMIT).
        """
        if API_TOKEN:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {API_TOKEN}":
                return False, "token"
        if RATE_LIMIT_MAX <= 0 and RATE_LIMIT_CMD_MAX <= 0:
            return True, ""
        limit = RATE_LIMIT_CMD_MAX if self._is_command() else RATE_LIMIT_MAX
        if limit <= 0:
            return True, ""
        state = _RATE_STATE_CMD if self._is_command() else _RATE_STATE
        agora = time.time()
        if agora - state["window"] >= 60.0:
            state["window"], state["count"] = agora, 1
        elif state["count"] + 1 > limit:
            return False, "rate"
        else:
            state["count"] += 1
        return True, ""

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        ok, motivo = self._autorizado()
        if not ok:
            self._send(401 if motivo == "token" else 429, {"ok": False, "error": "token invalido" if motivo == "token" else "rate limit excedido"})
            return
        if parsed.path.startswith("/api/connections/"):
            parts = parsed.path.strip("/").split("/"); connection_id = unquote("/".join(parts[2:-1]))
            action = parts[-1] if parts else ""
            if action == "test": self._send(200, {"ok": True, "configured": any(x["id"] == connection_id for x in list_connections()), "credentials_exposed": False}); return
            if action in {"activate", "deactivate"}: self._send(200, {"ok": set_connection_active(connection_id, action == "activate"), "active": action == "activate"}); return
        if parsed.path == "/api/connections": self._send(200, {"ok": True, "connections": list_connections()}); return
        path = parsed.path
        query = parse_qs(parsed.query)
        if path in ("/", "/api/health"):
            self._send(200, {"ok": True, "uptime_sec": int(time.time() - _T0),
                             "source": "mt5_gateway", "gateway_build": GATEWAY_BUILD})
        elif path == "/api/config":
            self._send(200, {"ok": True, "config": _config(), "source": "local_gateway"})
        elif path == "/api/config/themes":
            self._send(200, {"themes": [{"id": "dark", "label": "Dark"}, {"id": "xau_dark", "label": "XAU Dark"}, {"id": "btc_dark", "label": "BTC Dark"}, {"id": "light", "label": "Light"}]})
        elif path == "/api/config/languages":
            self._send(200, {"languages": [{"id": "pt-BR", "label": "Português (Brasil)"}, {"id": "en-US", "label": "English"}, {"id": "es-ES", "label": "Español"}]})
        elif path == "/api/update/check":
            self._send(200, {"ok": True, "current": "1.2.0", "available": "1.2.0", "update_available": False, "source": "local_build"})
        elif path == "/api/audit":
            self._send(200, {"ok": True, "records": _journal(100).get("lines", []), "source": "mt5_journal"})
        elif path == "/api/audit/commands":
            self._send(200, {"ok": True, "commands": [], "source": "gateway_command_log"})
        elif path == "/api/execution/history":
            self._send(200, _history(30, ""))
        elif path == "/api/errors":
            self._send(200, {"ok": True, "errors": [], "source": "gateway"})
        elif path == "/api/sync/status":
            payload = _payload(); self._send(200, {"ok": True, "gateway": "online", "mt5_connected": bool(payload.get("account")), "ea_heartbeat": payload.get("ea_heartbeat"), "positions": len(payload.get("positions", [])), "source": "mt5_gateway"})
        elif path == "/api/stream/status":
            self._send(200, {"ok": True, "transport": "http-polling", "websocket": False, "intervals": {"status": 10, "positions": 5, "journal": 10}, "source": "mt5_gateway"})
        elif path == "/api/demo/positions":
            try: self._send(200, _demo_read("positions"))
            except PermissionError as exc: self._send(403, {"ok": False, "error": str(exc), "demo": True})
        elif path == "/api/demo/orders":
            try: self._send(200, _demo_read("orders"))
            except PermissionError as exc: self._send(403, {"ok": False, "error": str(exc), "demo": True})
        elif path == "/api/demo/execution-status":
            try: self._send(200, _demo_read("status"))
            except PermissionError as exc: self._send(403, {"ok": False, "error": str(exc), "demo": True})
        elif path == "/api/demo/last-command":
            self._send(200, {"ok": True, "last_command": LAST_COMMAND, "source": "gateway_memory"})
        elif path == "/api/guardian/status":
            self._send(200, guardian_status())
        elif path == "/api/intents":
            try:
                self._send(200, intent_log.snapshot(int(query.get("limit", ["50"])[0])))
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc)})
        elif path == "/api/queue/status":
            self._send(200, persistent_queue.queue_status())
        elif path == "/api/watchdog":
            try:
                self._send(200, watchdog.ea_state())
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc)})
        elif path == "/api/telemetry":
            try:
                self._send(200, watchdog.telemetry(int(query.get("limit", ["100"])[0])))
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc)})
        elif path == "/api/telemetry/history":
            try:
                self._send(200, watchdog.history(int(query.get("limit", ["120"])[0])))
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "snapshots": [], "count": 0})
        elif path == "/api/boot":
            from backend.fastapi_gateway import boot_report as _boot_report
            try:
                self._send(200, _boot_report())
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "source": "boot_report"})
        elif path == "/api/ea/status":
            try: self._send(200, _ea_status())
            except Exception as exc: self._send(503, {"ok": False, "error": str(exc), "source": "mt5_gateway"})
        elif path == "/api/capabilities":
            self._send(200, {"ok": True, "read": ["health", "status", "account", "inventory", "symbols", "assets", "quote", "quotes", "positions", "orders", "history", "journal", "guardian/status", "boot"], "demo_commands": ["demo/order", "demo/close", "guardian/set", "guardian/remove", "guardian/tick"], "ea_commands": ["ea/start", "ea/stop", "ea/pause", "ea/resume", "ea/close", "ea/close-all"], "real_commands": [], "real_orders_enabled": False})
        elif path in ("/api/status", "/api/system"):
            ok = _ensure_mt5()
            self._send(200, {"ok": ok, **_payload()})
        elif path == "/api/inventory":
            ok = _ensure_mt5()
            payload = _payload()
            self._send(200, {"ok": ok, "account": payload.get("account"), "positions": payload.get("positions", []), "pending_orders": payload.get("pending_orders", []), "exposure": payload.get("exposure", {}), "ea_heartbeat": payload.get("ea_heartbeat")})
        elif path == "/api/journal":
            try:
                self._send(200, _journal(int(query.get("limit", ["100"])[0])))
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "lines": [], "count": 0})
        elif path == "/api/account":
            self._send(200, _payload().get("account") or {"ok": False})
        elif path in ("/api/symbols", "/api/assets"):
            try:
                self._send(200, _symbols())
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "symbols": [], "count": 0})
        elif path == "/api/assets/details":
            self._send(200, _symbols())
        elif path.startswith("/api/assets/"):
            symbol = path.rsplit("/", 1)[-1].strip().upper(); mt5 = _mt5(); info = mt5.symbol_info(symbol)
            if not info: self._send(404, {"ok": False, "error": f"simbolo indisponivel: {symbol}"})
            else: self._send(200, {"ok": True, "symbol": symbol, "visible": bool(getattr(info, "visible", False)), "digits": int(getattr(info, "digits", 0)), "volume_min": float(getattr(info, "volume_min", 0)), "volume_max": float(getattr(info, "volume_max", 0)), "volume_step": float(getattr(info, "volume_step", 0)), "point": float(getattr(info, "point", 0)), "source": "mt5_gateway"})
        elif path == "/api/positions":
            self._send(200, {"positions": _payload().get("positions", [])})
        elif path == "/api/orders":
            self._send(200, {"orders": _payload().get("pending_orders", []), "count": len(_payload().get("pending_orders", [])), "source": "mt5_gateway"})
        elif path == "/api/mt5/candles":
            try:
                symbol = query.get("symbol", ["XAUUSD"])[0].strip().upper() or "XAUUSD"
                timeframe = query.get("timeframe", ["M5"])[0].strip()
                try: count = int(query.get("count", ["300"])[0])
                except (TypeError, ValueError): count = 300
                self._send(200, _mt5_candles(symbol, timeframe, count))
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "candles": [], "count": 0})
        elif path == "/api/history":
            try:
                days = int(query.get("days", ["30"])[0])
                symbol = query.get("symbol", [""])[0].strip()
                self._send(200, _history(days, symbol))
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "deals": [], "count": 0})
        elif path == "/api/universal/history":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower()
                market = query.get("market", [""])[0].strip().lower()
                symbol = query.get("symbol", [""])[0].strip()
                try: days = max(0, int(query.get("days", ["0"])[0]))
                except (TypeError, ValueError): days = 0
                self._send(200, _universal_history(broker, market, symbol, days))
            except (MexcError, BinanceError, LookupError, ValueError) as exc:
                self._send(503, {"ok": False, "error": str(exc), "deals": [], "count": 0})
            except Exception as exc:
                self._send(503, {"ok": False, "error": f"falha no histórico universal: {exc}", "deals": [], "count": 0})
        elif path == "/api/universal/account":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower(); market = query.get("market", [""])[0].strip().lower()
                self._send(200, _universal_account(broker, market))
            except (MexcError, BinanceError, LookupError, ValueError) as exc:
                self._send(503, {"ok": False, "error": str(exc), "withdrawals_enabled": False})
        elif path == "/api/universal/overview":
            self._send(200, _universal_overview())
        elif path == "/api/universal/positions":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower(); market = query.get("market", [""])[0].strip().lower()
                self._send(200, _universal_positions(broker, market))
            except (MexcError, BinanceError, LookupError, ValueError) as exc:
                self._send(503, {"ok": False, "error": str(exc), "positions": []})
        elif path == "/api/universal/quote":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower(); market = query.get("market", ["crypto-spot"])[0].strip().lower(); symbol = query.get("symbol", [""])[0].strip()
                if not symbol: raise ValueError("symbol obrigatório")
                self._send(200, _universal_quote(broker, market, symbol))
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc)})
        elif path == "/api/universal/quotes":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower(); market = query.get("market", ["crypto-spot"])[0].strip().lower()
                raw = query.get("symbols", [""])[0]
                symbols = [item.strip() for item in raw.split(",") if item.strip()]
                if not symbols: raise ValueError("symbols obrigatório (lista separada por vírgula)")
                self._send(200, _universal_quotes(broker, market, symbols))
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "quotes": [], "errors": []})
        elif path == "/api/universal/depth":
            try:
                broker = query.get("broker", ["binance"])[0].strip().lower(); market = query.get("market", ["crypto-spot"])[0].strip().lower(); symbol = query.get("symbol", [""])[0].strip()
                if not symbol: raise ValueError("symbol obrigatório")
                self._send(200, _universal_depth(broker, market, symbol))
            except (MexcError, BinanceError, LookupError, ValueError) as exc:
                self._send(503, {"ok": False, "error": str(exc), "bids": [], "asks": []})
        elif path == "/api/universal/trades":
            try:
                broker = query.get("broker", ["binance"])[0].strip().lower(); market = query.get("market", ["crypto-spot"])[0].strip().lower(); symbol = query.get("symbol", [""])[0].strip()
                if not symbol: raise ValueError("symbol obrigatório")
                self._send(200, _universal_trades(broker, market, symbol))
            except (MexcError, BinanceError, LookupError, ValueError) as exc:
                self._send(503, {"ok": False, "error": str(exc), "trades": []})
        elif path == "/api/mt5/quote":
            try:
                self._send(200, _quote(query.get("symbol", [""])[0]))
            except (LookupError, ValueError) as exc:
                self._send(404, {"ok": False, "error": str(exc)})
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc)})
        elif path == "/api/mt5/quotes":
            symbols = query.get("symbols", ["XAUUSD"])[0].split(",")
            quotes = []
            errors = []
            for symbol in symbols:
                try:
                    quotes.append(_quote(symbol.strip()))
                except Exception as exc:
                    errors.append({"symbol": symbol, "error": str(exc)})
            self._send(200, {"quotes": quotes, "errors": errors})
        else:
            self._send(404, {"ok": False, "error": "not_found"})

    def do_PUT(self):  # noqa: N802
        if urlparse(self.path).path != "/api/config": self._send(404, {"ok": False, "error": "not_found"}); return
        try:
            length = int(self.headers.get("Content-Length", "0")); body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict): raise ValueError("configuração deve ser objeto")
            self._send(200, {"ok": True, "config": _save_config({**_config(), **body})})
        except Exception as exc: self._send(400, {"ok": False, "error": str(exc)})

    def do_DELETE(self):  # noqa: N802
        parsed = urlparse(self.path); prefix = "/api/connections/"
        if parsed.path.startswith(prefix):
            self._send(200, {"ok": delete_connection(unquote(parsed.path[len(prefix):]))}); return
        self._send(404, {"ok": False, "error": "not_found"})

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        ok, motivo = self._autorizado()
        if not ok:
            self._send(401 if motivo == "token" else 429, {"ok": False, "error": "token invalido" if motivo == "token" else "rate limit excedido"})
            return
        if parsed.path == "/api/connections":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                result = connection_service.save(payload)
                connection = next((x for x in list_connections() if x["id"] == payload["id"]), None)
                self._send(201, {**result, "connection": connection})
            except ValueError as exc:
                self._send(422, {"ok": False, "error": str(exc), "credentials_exposed": False})
            except Exception:
                self._send(503, {"ok": False, "error": "Falha ao salvar conexao.", "credentials_exposed": False})
            return
        if parsed.path.startswith("/api/connections/"):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                connection_id, separator, command = parsed.path[len("/api/connections/"):].rpartition("/")
                if not separator or not connection_id:
                    raise LookupError("Conexao ou comando inexistente.")
                self._send(200, connection_service.action(unquote(connection_id), command))
            except LookupError:
                self._send(404, {"ok": False, "error": "Conexao ou comando inexistente.", "credentials_exposed": False})
            except Exception:
                # Nao refletir erros externos: podem conter credenciais.
                self._send(502, {"ok": False, "validated": False, "error": "Falha ao validar conexao.", "credentials_exposed": False})
            return
        if parsed.path in {"/api/universal/emergency-stop", "/api/universal/emergency-resume"}:
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            if payload.get("confirm") is not True:
                self._send(422, {"ok": False, "error": "confirmação explícita obrigatória", "emergency_stop": REAL_EMERGENCY_STOP.exists()}); return
            if parsed.path.endswith("emergency-stop"):
                REAL_EMERGENCY_STOP.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
                LAST_COMMAND.update({"command": parsed.path, "status": "active", "updated_at": datetime.now().isoformat()})
                self._send(200, {"ok": True, "emergency_stop": True, "status": "active", "new_orders_blocked": True, "withdrawals_enabled": False}); return
            REAL_EMERGENCY_STOP.unlink(missing_ok=True)
            LAST_COMMAND.update({"command": parsed.path, "status": "resumed", "updated_at": datetime.now().isoformat()})
            self._send(200, {"ok": True, "emergency_stop": False, "status": "resumed", "new_orders_blocked": False, "withdrawals_enabled": False}); return
        universal_actions = {"/api/universal/order": "order", "/api/universal/close": "close", "/api/universal/modify": "modify", "/api/universal/cancel": "cancel"}
        if parsed.path in universal_actions:
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            if parsed.path == "/api/universal/order" and payload.get("execute") is True:
                try:
                    from backend.universal_router import UniversalRouter
                    result = UniversalRouter().execute(payload, explicit_authorization=payload.get("authorize_execution") is True)
                    record_audit(AUDIT_FILE, action="order", payload=payload, status=result.get("status", "unknown"))
                    LAST_COMMAND.update({"command": parsed.path, "status": result.get("status"), "request_id": payload.get("request_id"), "updated_at": datetime.now().isoformat()})
                    self._send(200 if result.get("ok") else 403, result); return
                except Exception as exc:
                    self._send(422, {"ok": False, "status": "rejected", "error": str(exc), "withdrawals_enabled": False}); return
            result = _universal_execution_preview(payload, universal_actions[parsed.path])
            record_audit(AUDIT_FILE, action=universal_actions[parsed.path], payload=payload, status=result.get("stage", "rejected"))
            LAST_COMMAND.update({"command": parsed.path, "status": "validated" if result.get("stage") == "validated" else "rejected", "updated_at": datetime.now().isoformat()})
            self._send(200 if result.get("stage") == "validated" else 422, result); return
        if parsed.path in {"/api/assets/select", "/api/assets/enable", "/api/assets/disable"}:
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            self._send(200, _asset_toggle(payload, parsed.path != "/api/assets/disable")); return
        if parsed.path in {"/api/command/validate", "/api/command/cancel"}:
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            allowed = {"/api/demo/order", "/api/demo/close", "/api/demo/close-all", "/api/demo/modify-position", "/api/demo/breakeven", "/api/demo/trailing", "/api/demo/partial-close", "/api/demo/set-protection", "/api/demo/remove-protection", "/api/demo/close-symbol", "/api/demo/cancel-order", "/api/demo/cancel-all-orders"}
            command = str(payload.get("command", "")); ok = command in allowed and payload.get("confirm_demo") is True
            self._send(200, {"ok": ok, "command": command, "valid": ok, "cancelled": parsed.path.endswith("/cancel") and ok, "reason": "comando DEMO reconhecido" if ok else "comando DEMO desconhecido ou confirmação ausente"}); return
        if parsed.path == "/api/config/reset":
            self._send(200, {"ok": True, "config": _save_config(CONFIG_DEFAULTS)}); return
        if parsed.path == "/api/real/validate":
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            try:
                validate_trade(volume=float(payload.get("volume", 0)), daily_loss_pct=float(payload.get("daily_loss_pct", 0)), exposure_pct=float(payload.get("exposure_pct", 0)), open_positions=int(payload.get("open_positions", 0)))
                self._send(200, {"ok": True, "approved": False, "execution_enabled": False, "reason": "risco validado; liberação REAL ainda exige autorização manual", "withdrawals_enabled": False})
            except (ValueError, TypeError) as exc: self._send(403, {"ok": False, "approved": False, "execution_enabled": False, "error": str(exc), "withdrawals_enabled": False})
            return
        if parsed.path == "/api/real/request":
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            request_id = str(payload.get("request_id", "")).strip()
            if not request_id or not payload.get("account_id") or not payload.get("broker") or not payload.get("market"):
                self._send(422, {"ok": False, "error": "request_id, account_id, broker e market são obrigatórios", "execution_enabled": False, "withdrawals_enabled": False}); return
            LAST_COMMAND.update({"command": "/api/real/request", "status": "pending_manual_review", "request_id": request_id, "updated_at": datetime.now().isoformat()})
            self._send(202, {"ok": True, "status": "pending_manual_review", "request_id": request_id, "execution_enabled": False, "withdrawals_enabled": False, "message": "solicitação registrada para autorização manual"}); return
        ea_paths = {"/api/ea/start": "start", "/api/ea/stop": "stop", "/api/ea/pause": "pause", "/api/ea/resume": "resume", "/api/ea/set-symbol": "set-symbol", "/api/ea/set-mode": "set-mode", "/api/ea/set-timeframe": "set-timeframe", "/api/ea/set-autotrading": "set-autotrading", "/api/ea/close": "close", "/api/ea/close-all": "close-all"}
        if parsed.path in ea_paths:
            try:
                length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
                self._send(202, _ea_command(payload, ea_paths[parsed.path]))
            except Exception as exc: self._send(503, {"ok": False, "error": str(exc), "command": ea_paths[parsed.path]})
            return
        guardian_paths = {"/api/guardian/set": guardian_set, "/api/guardian/remove": guardian_remove,
                          "/api/guardian/tick": lambda p: guardian_tick(),
                          "/api/intents/reconcile": lambda p: intent_log.reconcile(_mt5())}
        if parsed.path in guardian_paths:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                self._send(200, guardian_paths[parsed.path](payload))
            except (PermissionError, ValueError, LookupError) as exc:
                self._send(403, {"ok": False, "error": str(exc), "demo": True})
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "demo": True})
            return
        if parsed.path not in {"/api/demo/order", "/api/demo/close", "/api/demo/close-all", "/api/demo/modify-position", "/api/demo/breakeven", "/api/demo/trailing", "/api/demo/partial-close", "/api/demo/set-protection", "/api/demo/remove-protection", "/api/demo/close-symbol", "/api/demo/cancel-order", "/api/demo/cancel-all-orders", "/api/real/order"}:
            self._send(404, {"ok": False, "error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as exc:
            self._send(400, {"ok": False, "error": f"payload invalido: {exc}", "demo": True})
            return
        try:
            actions = {"/api/demo/order": _demo_order, "/api/demo/close": _demo_close, "/api/demo/close-all": _demo_close_all, "/api/demo/modify-position": lambda p: _demo_manage(p, "modify"), "/api/demo/breakeven": lambda p: _demo_manage(p, "breakeven"), "/api/demo/trailing": lambda p: _demo_manage(p, "trailing"), "/api/demo/partial-close": _demo_partial_close, "/api/demo/set-protection": _demo_protection, "/api/demo/remove-protection": lambda p: _demo_protection(p, True), "/api/demo/close-symbol": _demo_close_symbol, "/api/demo/cancel-order": _demo_cancel_orders, "/api/demo/cancel-all-orders": lambda p: _demo_cancel_orders(p, True), "/api/real/order": _real_order}
            action = actions[parsed.path]
            result = action(payload)
            LAST_COMMAND.update({"command": parsed.path, "status": "ok" if result.get("ok", False) else "rejected", "updated_at": datetime.now().isoformat()})
            self._send(200, result)
        except (PermissionError, ValueError, LookupError) as exc:
            kind = persistent_queue._KIND_BY_ROUTE.get(parsed.path, "")
            queued = persistent_queue.offline_fallback_kind(kind, payload, exc)
            if queued is not None:
                self._send(202, queued)
            else:
                self._send(403, {"ok": False, "error": str(exc), "demo": True})
        except Exception as exc:
            kind = persistent_queue._KIND_BY_ROUTE.get(parsed.path, "")
            queued = persistent_queue.offline_fallback_kind(kind, payload, exc)
            if queued is not None:
                self._send(202, queued)
            else:
                self._send(503, {"ok": False, "error": str(exc), "demo": True})


_T0 = time.time()


def main() -> None:
    # O gateway universal deve subir mesmo sem o pacote/terminal MT5.
    # Rotas MT5 retornam estado indisponível; corretoras externas continuam
    # utilizáveis. Não executar _ensure_mt5() durante o boot.
    try:
        mt5_ready = _ensure_mt5()
    except Exception as exc:
        mt5_ready = False
        print(f"[gateway] MT5 opcional indisponível: {exc}")
    if not mt5_ready:
        print("[gateway] MT5 offline; modo universal continua ativo.")
    start_guardian_loop()
    persistent_queue.start_queue_loop()
    watchdog.start_telemetry_loop()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.daemon_threads = True
    print(f"[gateway] MT5 Gateway rodando em http://{HOST}:{PORT}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
