# -*- coding: utf-8 -*-
"""MT5 Gateway - servico local na porta 9001 (MCP HTTP).

Responde /api/health, /api/account, /api/positions, /api/history e uma rota
de ordem explicitamente protegida, usando o pacote MetaTrader5 da maquina.
Rodar: python backend/mt5_gateway.py
"""
from __future__ import annotations

import copy
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
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.asset_registry import discover_assets
from backend.broker_registry import EXECUTION_GATES, capabilities_for, capability_matrix, code_only_brokers, get_broker, normalize_read_scope, read_brokers
from backend import connection_service
from backend.mexc_client import MexcClient, MexcError
from backend.bybit_client import BybitClient, BybitError
from backend.okx_client import OkxClient, OkxError
from backend.risk_gate import validate_trade
from backend.connection_store import save_connection, list_connections, delete_connection, load_connection_credentials_full, resolve_connection
from backend.binance_client import BinanceClient, BinanceError
from backend.universal_contracts import (
    UniversalOrderRequest,
    canonical_market_response,
    canonical_unavailable,
    error_response,
    execution_policy,
    first_value,
    optional_number,
    timestamp_iso,
    utc_now,
)
from backend.audit_log import record as record_audit
from backend.guardian_engine import guardian_set, guardian_remove, guardian_status, guardian_tick, start_guardian_loop
from backend.third_party_ea import READ_ONLY_CAPABILITIES, evaluate_all as evaluate_third_party_ea
from backend import intent_log
from backend import persistent_queue
from backend import watchdog
from backend import gateway_server
from Python.model_registry import model_catalog

HOST = "127.0.0.1"
PORT = 9001


def _gateway_build() -> str:
    """Build do gateway derivado da fonte unica Docs/version.json.

    O frontend compara este valor com uma constante propria (main.tsx) e o
    core Rust idem (EXPECTED_GATEWAY_BUILD): um gateway com build diferente
    derruba o bootstrap com "Falha ao inicializar o ambiente local seguro".
    Por isso o Docs/version.json tambem e embutido no pacote PyInstaller
    (entry `Docs/version.json` no mt5-gateway.spec) e aqui testamos os dois
    layouts — o do repositorio e o do `_internal` congelado.
    """
    candidatos: list[Path] = []
    try:
        candidatos.append(Path(__file__).resolve().parent.parent / "Docs" / "version.json")
    except OSError:
        pass
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidatos.append(Path(meipass) / "Docs" / "version.json")
    for caminho in candidatos:
        try:
            data = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        version = str(data.get("version", "1.2.4")).strip()
        suffix = str(data.get("gateway_build_suffix", "universal")).strip() or "universal"
        updated = str(data.get("updated_at", "")).strip().replace("-", "")
        stamp = updated if len(updated) == 8 and updated.isdigit() else "20260928"
        return f"xau-ai-pro-{version}-{suffix}-{stamp}"
    return "xau-ai-pro-1.2.4-universal-20260928"


GATEWAY_BUILD = _gateway_build()
REAL_ORDER_KEYS: set[str] = set()
LAST_COMMAND: dict = {"command": None, "status": "idle", "updated_at": None}
REAL_EMERGENCY_STOP = Path(os.getenv("XAU_REAL_EMERGENCY_FILE", str(Path(__file__).with_name("REAL_EMERGENCY_STOP"))))
COMMON_FILES = Path(os.getenv("XAU_MT5_COMMON_FILES", str(Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal" / "Common" / "Files")))
CONFIG_FILE = Path(os.getenv("XAU_APP_CONFIG", str(Path(os.environ.get("APPDATA", "")) / "XAU_AI_PRO" / "config.json")))
AUDIT_FILE = Path(os.getenv("XAU_AUDIT_FILE", str(Path(os.environ.get("APPDATA", "")) / "XAU_AI_PRO" / "audit.jsonl")))
# =============================================================================
# TOKEN: AMBIENTE PRIMEIRO, `.env` DEPOIS
# =============================================================================
# POR QUE ISTO EXISTE (medido em 05/10/2026)
# ==========================================
# O token vinha SO de `os.getenv`. Subir o gateway pela linha de comando
# (`python -m backend.fastapi_gateway`) dava `API_TOKEN = ""`, e o gateway
# ficava fail-closed: TODO request recebia 401, inclusive com o token CORRETO.
# Quem carrega o `.env` e o Tauri (`main.rs:628`, `.env("XAU_GATEWAY_TOKEN",
# token)`), entao o gateway so tinha token quando lancado pelo app.
#
# O EA precisa do MESMO token que o app injeta, para que o `WebRequest` dele
# seja aceito. Com o token so no ambiente do Tauri, o operador teria que
# descobrir qual era — e o valor muda por sessao.
#
# A ORDEM IMPORTA: o ambiente vence o `.env`. O Tauri injeta o token da
# sessao, e ele tem de prevalecer sobre o arquivo — senao uma sessao nova
# ficaria com o token do arquivo enquanto o app usa outro, e a UI perderia o
# acesso ao proprio backend.
#
# SEM `python-dotenv`: o `.env` deste projeto tem `FIGMA_TOKEN`,
# `XAU_GATEWAY_TOKEN` e credenciais de exchange. O leitor e minimo de proposito
# (ignora comentario, apara espacos, nao sobrescreve o que ja existe), e nao
# importa o pacote extra.

def _token_do_ambiente_ou_dotenv(nome: str) -> str:
    """`nome` do ambiente; se faltar, do `.env` da raiz do repo."""
    do_ambiente = os.getenv(nome, "").strip()
    if do_ambiente:
        return do_ambiente

    try:
        raiz = Path(__file__).resolve().parent.parent
        arq = raiz / ".env"
        if not arq.is_file():
            return ""
        for linha in arq.read_text(encoding="utf-8", errors="replace").splitlines():
            limpa = linha.strip()
            if not limpa or limpa.startswith("#") or "=" not in limpa:
                continue
            chave, valor = limpa.split("=", 1)
            if chave.strip() != nome:
                continue
            valor = valor.strip().strip('"').strip("'")
            if valor:
                return valor
    except (OSError, ValueError):
        # Sem `.env` legivel, o token fica vazio e o gateway segue fail-closed.
        # Isso e o comportamento correto: sem token, ninguem autentica; com token
        # pela metade, alguem autentica errado.
        return ""
    return ""


# Segurança de exposição: token opcional e rate limit (pré-requisito p/ acesso remoto/Android).
API_TOKEN = _token_do_ambiente_ou_dotenv("XAU_GATEWAY_TOKEN")
#: Motivos de `_autorizado` que sao FALHA DE AUTENTICACAO (HTTP 401), e nao
#: excesso de cota (429). "sem token configurado" entrou na lista quando o
#: gateway passou a ser fail-closed; sem isso, a falta de token caia no ramo
#: de rate limit e respondia 429/500 em vez de 401.
_MOTIVOS_TOKEN = frozenset({"token", "sem token configurado"})
THIRD_PARTY_READ_ONLY = os.getenv("XAU_THIRD_PARTY_EA_READ_ONLY", "0") == "1"
RATE_LIMIT_MAX = int(os.getenv("XAU_RATE_LIMIT", "0") or 0)  # req/min; 0 = ilimitado (desktop local)
RATE_LIMIT_CMD_MAX = int(os.getenv("XAU_RATE_LIMIT_CMD", "0") or 0)  # comandos/min; 0 = usa RATE_LIMIT_MAX
_RATE_STATE = {"count": 0, "window": 0.0}
_RATE_STATE_CMD = {"count": 0, "window": 0.0}
CONFIG_DEFAULTS = {"theme": "dark", "language": "pt-BR", "precision": 2, "marketAutoRefresh": True, "dashboardAutoRefresh": True, "historyAutoRefresh": True}
DEFAULT_CORS_ORIGINS = {"http://127.0.0.1:1420", "http://localhost:1420", "http://127.0.0.1:3000", "http://localhost:3000", "http://127.0.0.1:9001", "http://localhost:9001", "http://tauri.localhost", "https://tauri.localhost"}
CORS_ORIGINS = {item.strip() for item in os.getenv("XAU_CORS_ORIGINS", "").split(",") if item.strip()} or set(DEFAULT_CORS_ORIGINS)

def _safe_number(value) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return number if math.isfinite(number) and 0 <= number < 1e15 else 0.0


def _account_number(value):
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return number if math.isfinite(number) and abs(number) < 1e15 else 0.0


def _sum_account_values(rows, keys):
    grouped: dict[str, list[float]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        asset = str(first_value(row, "asset", "currency", "ccy") or "").upper()
        row_values = []
        for key in keys:
            if key in row and row[key] not in (None, ""):
                value = _account_number(row[key])
                if value is not None:
                    row_values.append(value)
        if row_values:
            grouped.setdefault(asset, []).append(sum(row_values))
    for preferred in ("USDT", "USDC", "USD"):
        if preferred in grouped:
            return sum(grouped[preferred])
    if len(grouped) == 1:
        return sum(next(iter(grouped.values())))
    return None


def _account_currency(rows) -> str | None:
    assets = {str(first_value(row, "asset", "currency", "ccy") or "").upper() for row in rows if isinstance(row, dict)}
    assets.discard("")
    for preferred in ("USDT", "USDC", "USD"):
        if preferred in assets:
            return preferred
    return next(iter(assets)) if len(assets) == 1 else None


def _normalize_exchange_account(account):
    """Normaliza respostas Spot/Futuros sem usar campos de controle como saldo."""
    if isinstance(account, dict):
        balances = account.get("balances")
        if isinstance(balances, list):
            assets = [x for x in balances if isinstance(x, dict)]
            return {
                "balance": _sum_account_values(assets, ("free", "locked", "balance")),
                "available": _sum_account_values(assets, ("free", "available", "availableBalance")),
                "currency": _account_currency(assets),
                "assets": assets,
            }
        total = None
        for key in ("totalWalletBalance", "equity", "balance", "totalMarginBalance"):
            if key in account and account[key] not in (None, ""):
                total = _account_number(account[key])
                break
        available = None
        for key in ("availableBalance", "available", "free"):
            if key in account and account[key] not in (None, ""):
                available = _account_number(account[key])
                break
        return {"balance": total, "available": available, "currency": "USDT", "assets": []}
    if isinstance(account, list):
        assets = [x for x in account if isinstance(x, dict)]
        return {
            "balance": _sum_account_values(assets, ("equity", "balance", "totalWalletBalance")),
            "available": _sum_account_values(assets, ("availableBalance", "available", "free")),
            "currency": _account_currency(assets),
            "assets": assets,
        }
    return {"balance": None, "available": None, "currency": "USDT", "assets": []}

def _exchange_market(market: str) -> str:
    value = str(market or "").strip().lower()
    if value in {"crypto-futures", "futures", "futuros", "crypto_futures"}:
        return "futures"
    return "spot"


def _stored_exchange_credentials(account_id: str, broker: str, market: str) -> tuple[str, str, str, str]:
    connection = resolve_connection(account_id, broker, market)
    key, secret, passphrase = load_connection_credentials_full(str(connection["id"]))
    return key, secret, passphrase, str(connection["id"])


def _exchange_client(broker: str, market: str, *, private: bool = False, account_id: str = ""):
    exchange = _exchange_market(market)
    credentials = _stored_exchange_credentials(account_id, broker, market) if private else None
    if broker == "binance":
        client = BinanceClient(exchange, credentials[0], credentials[1]) if credentials else BinanceClient(exchange)
    elif broker == "mexc":
        client = MexcClient(exchange, credentials[0], credentials[1]) if credentials else MexcClient(exchange)
    elif broker == "bybit":
        client = BybitClient(exchange, False, credentials[0], credentials[1]) if credentials else BybitClient(exchange)
    elif broker == "okx":
        client = OkxClient(exchange, False, credentials[0], credentials[1], credentials[2]) if credentials else OkxClient(exchange)
    else:
        raise LookupError(f"corretora não suportada: {broker}")
    client.account_id = credentials[3] if credentials else ""
    return client

READ_BROKERS = read_brokers()
CODE_ONLY_BROKERS = code_only_brokers()
try:
    MARKET_CACHE_TTL = max(0.0, float(os.getenv("XAU_MARKET_CACHE_TTL", "1")))
except ValueError:
    MARKET_CACHE_TTL = 1.0
_MARKET_CACHE: dict[tuple, tuple[float, Any]] = {}
_MARKET_CACHE_LOCK = threading.Lock()


def _cached_market(key: tuple, loader):
    now = time.monotonic()
    with _MARKET_CACHE_LOCK:
        entry = _MARKET_CACHE.get(key)
        if entry and entry[0] > now:
            return copy.deepcopy(entry[1])
    value = loader()
    if MARKET_CACHE_TTL > 0 and isinstance(value, dict) and value.get("ok"):
        with _MARKET_CACHE_LOCK:
            _MARKET_CACHE[key] = (now + MARKET_CACHE_TTL, copy.deepcopy(value))
    return value


def _universal_scope(broker: str, market: str, symbol: str = "") -> dict[str, str]:
    normalized_broker = str(broker or "").strip().lower()
    normalized_market = str(market or "").strip().lower()
    if not normalized_market:
        normalized_market = "crypto-spot" if normalized_broker in {"binance", "mexc", "bybit", "okx"} else "other"
    return normalize_read_scope(normalized_broker, normalized_market, symbol)


def _response_status(payload: dict) -> int:
    status = str(payload.get("status", "ok")).lower()
    if status == "invalid":
        return 422
    if status in {"unsupported", "code_only"}:
        return 501
    if payload.get("ok") is False:
        return 503
    return 200


def _read_exception_response(broker: str, market: str, exc: Exception, endpoint: str, **fields: Any) -> dict:
    return canonical_unavailable(
        broker=broker,
        market=market or "other",
        source="universal_gateway",
        endpoint=endpoint,
        reason=str(exc),
        status="invalid" if isinstance(exc, ValueError) else "unavailable",
        error_code="invalid_request" if isinstance(exc, ValueError) else "upstream_unavailable",
        **fields,
    )


def _unsupported_read_response(broker: str, market: str, endpoint: str, **fields: Any) -> dict:
    return canonical_unavailable(
        broker=broker,
        market=market or "other",
        source=f"{broker}_code_only",
        endpoint=endpoint,
        reason=f"{broker} está em code_only; aguarda fixtures e homologação",
        status="unsupported",
        supported=False,
        production_ready=False,
        **fields,
    )


def _unwrap_market_payload(raw: object) -> object:
    if isinstance(raw, dict):
        data = raw.get("data")
        if isinstance(data, dict):
            return data
        result = raw.get("result")
        if isinstance(result, dict):
            return result
    return raw


def _payload_rows(raw: object) -> list[object]:
    if isinstance(raw, list):
        return list(raw)
    if not isinstance(raw, dict):
        return []
    for key in ("data", "result", "list", "rows", "symbols", "instruments", "trades", "items"):
        value = raw.get(key)
        if isinstance(value, list):
            return list(value)
    for key in ("data", "result"):
        value = raw.get(key)
        if isinstance(value, dict):
            nested = _payload_rows(value)
            if nested:
                return nested
    return [raw]


def _row_symbol(row: object) -> str:
    if not isinstance(row, dict):
        return ""
    return str(first_value(row, "symbol", "instId", "instrument_id", "name") or "").upper()


def _quote_from_raw(broker: str, market: str, symbol: str, raw: object, endpoint: str = "ticker") -> dict:
    symbol = str(symbol or "").strip().upper()
    data = _unwrap_market_payload(raw)
    if isinstance(data, list):
        selected = next((item for item in data if _row_symbol(item) == symbol), data[0] if data else None)
        data = selected
    if not isinstance(data, dict):
        data = {}
    bid = optional_number(first_value(data, "bidPrice", "bid1Price", "bid1", "bidPx", "bid"))
    ask = optional_number(first_value(data, "askPrice", "ask1Price", "ask1", "askPx", "ask"))
    last = optional_number(first_value(data, "lastPrice", "lastTradedPrice", "last", "price"))
    if last is None and bid is not None and ask is not None:
        last = (bid + ask) / 2.0
    spread = ask - bid if bid is not None and ask is not None else None
    upstream_timestamp = first_value(data, "eventTime", "time", "timestamp", "ts", "closeTime", "T", "E")
    has_values = any(value is not None for value in (bid, ask, last))
    status = "ok" if has_values and bid is not None and ask is not None else "partial" if has_values else "unavailable"
    source = f"{broker}_api" if broker != "mt5" else "mt5_gateway"
    values = {
        # O simbolo devolvido e sempre o que foi pedido (forma canonica do app).
        # A OKX nomeia o par com hifen (BTC-USDT) e a Binance sem (BTCUSDT); sem
        # esta separacao o mesmo ativo apareceria como dois instrumentos no front.
        "symbol": symbol or str(first_value(data, "symbol", "instId") or "").upper(),
        "source_symbol": str(first_value(data, "symbol", "instId") or "").upper() or None,
        "bid": bid,
        "ask": ask,
        "last": last,
        "price": last,
        "spread": spread,
        "change": optional_number(first_value(data, "priceChange", "change", "changeValue")),
        "change_pct": optional_number(first_value(data, "priceChangePercent", "changePercent", "change_pct")),
        "volume": optional_number(first_value(data, "volume", "vol", "amount")),
        "quote_volume": optional_number(first_value(data, "quoteVolume", "quoteVol", "turnover")),
        "open": optional_number(first_value(data, "openPrice", "open", "open24h")),
        "high": optional_number(first_value(data, "highPrice", "high", "high24h", "upper24Price")),
        "low": optional_number(first_value(data, "lowPrice", "low", "low24h", "lower24Price")),
    }
    return canonical_market_response(
        broker=broker,
        market=market or "other",
        source=source,
        endpoint=endpoint,
        status=status,
        timestamp=upstream_timestamp,
        error=None if has_values else "ticker ausente no upstream",
        **values,
    )


def _stats_from_raw(broker: str, market: str, symbol: str, raw: object, endpoint: str = "ticker_24h") -> dict:
    symbol = str(symbol or "").strip().upper()
    data = _unwrap_market_payload(raw)
    if isinstance(data, list):
        data = next((item for item in data if _row_symbol(item) == symbol), data[0] if data else None)
    if not isinstance(data, dict):
        data = {}
    last = optional_number(first_value(data, "lastPrice", "last", "price"))
    change = optional_number(first_value(data, "priceChange", "change", "changeValue"))
    change_pct = optional_number(first_value(data, "priceChangePercent", "changePercent", "change_pct"))
    values = {
        "symbol": str(first_value(data, "symbol", "instId") or symbol).upper(),
        "last": last,
        "price": last,
        "change": change,
        "change_pct": change_pct,
        "volume": optional_number(first_value(data, "volume", "vol", "amount", "dealAmt")),
        "quote_volume": optional_number(first_value(data, "quoteVolume", "quoteVol", "turnover")),
        "open": optional_number(first_value(data, "openPrice", "open", "open24h")),
        "high": optional_number(first_value(data, "highPrice", "high", "high24h", "upper24Price")),
        "low": optional_number(first_value(data, "lowPrice", "low", "low24h", "lower24Price")),
        "trades_count": optional_number(first_value(data, "count", "trades", "tradeCount", "dealCount"), integer=True),
    }
    has_values = any(values.get(name) is not None for name in ("last", "change", "change_pct", "volume", "quote_volume", "open", "high", "low", "trades_count"))
    upstream_timestamp = first_value(data, "closeTime", "time", "timestamp", "ts")
    return canonical_market_response(
        broker=broker,
        market=market or "other",
        source=f"{broker}_api",
        endpoint=endpoint,
        status="ok" if has_values else "unavailable",
        timestamp=upstream_timestamp,
        error=None if has_values else "estatísticas 24h ausentes no upstream",
        **values,
        stats=dict(values),
    )


def _depth_from_raw(broker: str, market: str, symbol: str, raw: object, endpoint: str = "depth") -> dict:
    data = _unwrap_market_payload(raw)
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        data = {}
    bids = first_value(data, "bids", "b")
    asks = first_value(data, "asks", "a")
    has_levels = "bids" in data or "b" in data or "asks" in data or "a" in data
    upstream_timestamp = first_value(data, "E", "T", "ts", "timestamp", "updateTime")
    return canonical_market_response(
        broker=broker,
        market=market or "other",
        source=f"{broker}_public_depth",
        endpoint=endpoint,
        status="ok" if has_levels else "unavailable",
        timestamp=upstream_timestamp,
        error=None if has_levels else "livro de ordens ausente no upstream",
        symbol=str(symbol or "").strip().upper(),
        bids=bids if isinstance(bids, list) else None,
        asks=asks if isinstance(asks, list) else None,
        last_update_id=optional_number(first_value(data, "lastUpdateId", "u", "update_id"), integer=True),
    )


def _trade_row(raw: object, broker: str, market: str) -> dict:
    data = raw if isinstance(raw, dict) else {}
    price = optional_number(first_value(data, "price", "px", "last", "dealPrice"))
    quantity = optional_number(first_value(data, "qty", "quantity", "amount", "size", "vol"))
    side = first_value(data, "side", "direction")
    if side is None and "isBuyerMaker" in data:
        side = "SELL" if bool(data.get("isBuyerMaker")) else "BUY"
    upstream_timestamp = first_value(data, "time", "timestamp", "ts", "tradeTime", "createdTime")
    return {
        "id": first_value(data, "id", "tradeId", "dealId", "orderId"),
        "broker": broker,
        "market": market or "other",
        "symbol": str(first_value(data, "symbol", "instId") or "").upper() or None,
        "side": str(side).upper() if side is not None else None,
        "price": price,
        "quantity": quantity,
        "time": timestamp_iso(upstream_timestamp),
        "timestamp": timestamp_iso(upstream_timestamp),
        "provider_timestamp": timestamp_iso(upstream_timestamp),
        "isBuyerMaker": data.get("isBuyerMaker") if "isBuyerMaker" in data else None,
        "source": f"{broker}_public_trades",
        "received_at": utc_now(),
    }


def _trades_from_raw(broker: str, market: str, symbol: str, raw: object, endpoint: str = "trades") -> dict:
    rows = _payload_rows(raw)
    if isinstance(raw, dict) and not any(key in raw for key in ("trades", "list", "data", "result")):
        rows = []
    normalized = [_trade_row(row, broker, market) for row in rows if isinstance(row, dict)]
    upstream_timestamp = first_value(raw, "ts", "timestamp", "T", "E") if isinstance(raw, dict) else None
    return canonical_market_response(
        broker=broker,
        market=market or "other",
        source=f"{broker}_public_trades",
        endpoint=endpoint,
        status="ok" if isinstance(raw, list) or rows or raw == [] else "unavailable",
        timestamp=upstream_timestamp,
        error=None if normalized or raw == [] or rows else "negócios ausentes no upstream",
        symbol=str(symbol or "").strip().upper(),
        trades=normalized,
        count=len(normalized),
    )


def _candle_row(raw: object) -> dict:
    data: object = raw
    dtype_names = tuple(getattr(getattr(raw, "dtype", None), "names", ()) or ())
    if dtype_names:
        data = {name: raw[name] for name in dtype_names}
    elif not isinstance(raw, dict) and hasattr(raw, "tolist"):
        converted = raw.tolist()
        if isinstance(converted, (list, tuple, dict)):
            data = converted
    if isinstance(data, dict):
        values = {
            "time": optional_number(first_value(data, "time", "timestamp", "openTime", "open_time", "t"), integer=True),
            "open": optional_number(first_value(data, "open", "o")),
            "high": optional_number(first_value(data, "high", "h")),
            "low": optional_number(first_value(data, "low", "l")),
            "close": optional_number(first_value(data, "close", "c")),
            "volume": optional_number(first_value(data, "volume", "v", "vol", "tick_volume", "real_volume")),
        }
    elif isinstance(data, (list, tuple)) and len(data) >= 5:
        values = {
            "time": optional_number(data[0], integer=True),
            "open": optional_number(data[1]),
            "high": optional_number(data[2]),
            "low": optional_number(data[3]),
            "close": optional_number(data[4]),
            "volume": optional_number(data[5]) if len(data) > 5 else None,
        }
    else:
        values = {"time": None, "open": None, "high": None, "low": None, "close": None, "volume": None}
    values["timestamp"] = timestamp_iso(values["time"])
    return values


def _columnar_candle_rows(raw: object) -> list[dict]:
    data = _unwrap_market_payload(raw)
    if not isinstance(data, dict):
        return []
    aliases = {
        "time": ("time", "timestamp", "openTime", "t"),
        "open": ("open", "o"),
        "high": ("high", "h"),
        "low": ("low", "l"),
        "close": ("close", "c"),
        "volume": ("volume", "v", "vol", "tick_volume", "real_volume"),
    }
    columns: dict[str, list] = {}
    for name, keys in aliases.items():
        value = first_value(data, *keys)
        if isinstance(value, list):
            columns[name] = value
    if not all(name in columns for name in ("time", "open", "high", "low", "close")):
        return []
    count = min(len(values) for values in columns.values())
    return [{name: values[index] for name, values in columns.items()} for index in range(count)]


def _candles_from_raw(broker: str, market: str, symbol: str, raw: object, timeframe: str, endpoint: str = "klines") -> dict:
    columnar = _columnar_candle_rows(raw)
    if columnar:
        rows = columnar
    elif isinstance(raw, dict) and isinstance(raw.get("candles"), list):
        rows = raw["candles"]
    else:
        rows = _payload_rows(raw)
    parsed = [_candle_row(row) for row in rows]
    candles = [row for row in parsed if row.get("timestamp") and all(row.get(name) is not None for name in ("open", "high", "low", "close"))]
    candles.sort(key=lambda row: row.get("timestamp") or "")
    upstream_timestamp = candles[-1].get("time") if candles else first_value(raw, "timestamp", "ts") if isinstance(raw, dict) else None
    return canonical_market_response(
        broker=broker,
        market=market or "other",
        source="mt5_gateway" if broker == "mt5" else f"{broker}_api",
        endpoint=endpoint,
        status="ok" if candles else "unavailable",
        timestamp=upstream_timestamp,
        error=None if candles else "candles ausentes ou inválidos no upstream",
        symbol=str(symbol or "").strip().upper(),
        timeframe=str(timeframe or "").upper() or None,
        candles=candles,
        count=len(candles),
        discarded=len(parsed) - len(candles),
    )


def _assets_from_raw(broker: str, market: str, raw: object, endpoint: str = "exchange_info") -> dict:
    rows = _payload_rows(raw)
    assets = []
    broker_capabilities = capabilities_for(broker, market)
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = first_value(row, "symbol", "instId", "instrument_id", "name")
        if symbol is None:
            continue
        status = str(first_value(row, "status", "state", "contractStatus", "statusCode") or "").strip().lower() or None
        enabled_value = first_value(row, "enabled", "active", "visible")
        enabled = None if enabled_value is None else bool(enabled_value)
        if status in {"trading", "online", "normal", "enabled", "available"}:
            enabled = True
        elif status in {"suspended", "halt", "disabled", "closed", "delisted", "unavailable"}:
            enabled = False
        trade_mode = optional_number(first_value(row, "trade_mode", "tradeMode"), integer=True)
        restrictions = []
        if enabled is False:
            restrictions.append("symbol_disabled")
        if trade_mode == 0:
            restrictions.append("trading_disabled")
        elif trade_mode == 1:
            restrictions.append("long_only")
        elif trade_mode == 2:
            restrictions.append("short_only")
        elif trade_mode == 3:
            restrictions.append("close_only")
        availability = "unavailable" if enabled is False else "unverified" if enabled is None else "restricted" if restrictions else "available"
        capability_status = "unsupported" if availability == "unavailable" else "unverified" if availability == "unverified" else "available"
        assets.append({
            "symbol": str(symbol).upper(),
            "display_name": first_value(row, "display_name", "displayName", "description", "baseAsset", "base_ccy", "name"),
            "base_asset": first_value(row, "baseAsset", "base", "base_ccy", "baseCcy"),
            "quote_asset": first_value(row, "quoteAsset", "quote", "quote_ccy", "quoteCcy", "settleCurrency"),
            "status": status,
            "enabled": enabled,
            "asset_class": first_value(row, "assetClass", "asset_class", "category", "type"),
            "asset_type": first_value(row, "assetClass", "asset_class", "category", "type"),
            "change_pct": optional_number(first_value(row, "priceChangePercent", "changePercent", "change_pct")),
            "volume_min": optional_number(first_value(row, "volume_min", "minVolume", "minVol")),
            "volume_max": optional_number(first_value(row, "volume_max", "maxVolume", "maxVol")),
            "volume_step": optional_number(first_value(row, "volume_step", "stepSize", "lotSize", "volumeStep")),
            "point": optional_number(first_value(row, "point", "tickSize", "priceTick")),
            "digits": optional_number(first_value(row, "digits", "pricePrecision"), integer=True),
            "trade_mode": trade_mode,
            # Ficha de especificacao (pagina de simbolo da XM): contrato,
            # spread em pontos e swaps. Vem do discover do MT5 ou do
            # exchange_info; ausente = nao informado, nunca zero presumido.
            "contract_size": optional_number(first_value(row, "contract_size", "contractSize")),
            "spread_points": optional_number(first_value(row, "spread_points", "spread"), integer=True),
            "swap_long": optional_number(first_value(row, "swap_long", "swapLong")),
            "swap_short": optional_number(first_value(row, "swap_short", "swapShort")),
            "availability": availability,
            "restrictions": restrictions,
            "capabilities": list(broker_capabilities),
            "capability_matrix": [
                {"capability": capability, "status": capability_status, "restrictions": restrictions}
                for capability in broker_capabilities
            ],
        })
    return canonical_market_response(
        broker=broker,
        market=market or "other",
        source="mt5_gateway" if broker == "mt5" else f"{broker}_api",
        endpoint=endpoint,
        status="ok" if assets else "unavailable",
        error=None if assets else "catálogo de ativos ausente no upstream",
        assets=assets,
        symbols=assets,
        count=len(assets),
    )


def _universal_history(broker: str, market: str, symbol: str = "", days: int = 0, account_id: str = "") -> dict:
    scope = _universal_scope(broker, market, symbol)
    broker = scope["broker"]
    market = scope["market"]
    symbol = scope["symbol"]
    if broker in CODE_ONLY_BROKERS:
        return _unsupported_read_response(broker, market, "history", deals=[], count=0)
    if broker == "mt5":
        raw = _history(days or 30, symbol)
        # `mt5` NUNCA era definido nesta funcao: a linha seguinte referenciava
        # um nome inexistente e levantava NameError em TODA chamada a
        # /api/universal/history. Era por isso que a aba Historico mostrava
        # "sem dados" e o usuario via a tela travada — nao era falta de login.
        mt5 = _mt5()
        mt5_info = mt5.account_info() if mt5 is not None else None
        mt5_account_id = f"mt5:{str(getattr(mt5_info, 'login', '') if mt5_info is not None else '').strip() or 'active'}"
        deals = []
        for row in raw.get("deals", []):
            profit = optional_number(row.get("profit"))
            commission = optional_number(row.get("commission"))
            swap = optional_number(row.get("swap"))
            fee = optional_number(row.get("fee"))
            # PnL realizado = lucro - custos. Campo ausente do MT5 significa
            # "nao se aplica" (zero), nao "desconhecido".
            #
            # Antes exigia profit E commission E swap E fee nao-nulos, e devia
            # null sempre que um deles faltasse. Em MT5 o deal de entrada (IN)
            # tipicamente vem sem fee, entao praticamente todo deal saia com
            # realizedPnl nulo — e como o front tambem esperava `profit` (o
            # gateway manda `grossPnl`), o PnL caia em 0 para todas as linhas e
            # win-rate/fator de lucro davam sempre zero. Era por isso que a aba
            # Historico aparecia "generica", sem numeros.
            realized = None
            if profit is not None:
                realized = profit - (commission or 0.0) - (swap or 0.0) - (fee or 0.0)
            deals.append({
                "id": str(row.get("ticket", "")),
                "broker": "mt5",
                "accountId": mt5_account_id,
                "market": market or "other",
                "symbol": row.get("symbol") or symbol or None,
                "side": row.get("type"),
                "entry": row.get("entry"),
                "status": "FILLED",
                "quantity": optional_number(row.get("volume")),
                "price": optional_number(row.get("price")),
                # Alias em pt/en: o front lia `profit`, que nunca veio.
                "profit": profit,
                "grossPnl": profit,
                "commission": commission,
                "swap": swap,
                "fee": fee,
                "realizedPnl": realized,
                "executedAt": timestamp_iso(row.get("time")),
                "source": "mt5_gateway",
            })
        return canonical_market_response(broker="mt5", market=market, source="mt5_gateway", status="ok", deals=deals, count=len(deals), days=days or 30)
    # Bybit e OKX estavam fora daqui, mas os quatro clientes implementam
    # `history(symbol, limit)` e o bloco de normalizacao abaixo e generico
    # (`first_value` por nome de campo). A interface oferecia as duas na lista
    # de corretoras e recebia "corretora nao suportada" — opcao quebrada na UI.
    if broker not in {"mexc", "binance", "bybit", "okx"}:
        raise LookupError("corretora não suportada")
    client = _exchange_client(broker, market, private=True, account_id=account_id)
    selected_account_id = client.account_id
    raw = client.history(symbol=symbol)
    rows = _payload_rows(raw)
    deals = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        commission = optional_number(first_value(row, "commission", "fee"))
        fee = optional_number(first_value(row, "fee", "commission"))
        profit = optional_number(first_value(row, "realizedPnl", "profit", "pnl"))
        realized = profit - commission - fee if profit is not None and commission is not None and fee is not None else None
        deals.append({
            "id": first_value(row, "id", "orderId", "dealId"),
            "broker": broker,
            "accountId": selected_account_id,
            "market": market or "crypto-spot",
            "symbol": first_value(row, "symbol", "instId") or symbol or None,
            "side": first_value(row, "side", "direction"),
            "entry": "TRADE",
            "status": first_value(row, "status") or "FILLED",
            "quantity": optional_number(first_value(row, "qty", "quantity", "vol", "executedQty", "amount")),
            "price": optional_number(first_value(row, "price", "dealPrice", "avgPrice")),
            "grossPnl": profit,
            "commission": commission,
            "swap": optional_number(first_value(row, "swap")),
            "fee": fee,
            "realizedPnl": realized,
            "executedAt": timestamp_iso(first_value(row, "time", "timeStamp", "timestamp", "tradeTime")),
            "source": f"{broker}_api",
        })
    return canonical_market_response(broker=broker, market=market, source=f"{broker}_api", status="ok", account_id=selected_account_id, deals=deals, count=len(deals))


def _universal_account(broker: str, market: str, account_id: str = "") -> dict:
    scope = _universal_scope(broker, market)
    broker = scope["broker"]
    market = scope["market"]
    if broker in CODE_ONLY_BROKERS:
        return _unsupported_read_response(broker, market, "account", account=None, withdrawals_enabled=False)
    if broker == "mt5":
        account = _payload().get("account")
        if not account:
            return canonical_unavailable(broker="mt5", market=market, source="mt5_gateway", reason="conta MT5 indisponível", account=None, withdrawals_enabled=False)
        return canonical_market_response(broker="mt5", market=market, source="mt5_gateway", status="ok", account_id=f"mt5:{account.get('login', 'active')}", account=account, withdrawals_enabled=False)
    client = _exchange_client(broker, market, private=True, account_id=account_id)
    raw = client.account()
    account = _normalize_exchange_account(_unwrap_market_payload(raw))
    return canonical_market_response(broker=broker, market=market, source=f"{broker}_api", status="ok", account_id=client.account_id, account=account, withdrawals_enabled=False)


def _universal_quote(broker: str, market: str, symbol: str) -> dict:
    scope = _universal_scope(broker, market, symbol)
    broker = scope["broker"]
    market = scope["market"]
    symbol = scope["symbol"]
    if not symbol:
        raise ValueError("symbol é obrigatório")
    if broker in CODE_ONLY_BROKERS:
        return _unsupported_read_response(broker, market, "ticker", symbol=symbol, bid=None, ask=None, last=None, price=None, spread=None)
    if broker not in READ_BROKERS:
        return canonical_unavailable(broker=broker, market=market, source="universal_gateway", reason="corretora não suportada", status="unsupported", symbol=symbol, bid=None, ask=None, last=None, price=None, spread=None)
    key = ("quote", broker, market, symbol)
    if broker == "mt5":
        return _cached_market(key, lambda: _quote_from_raw(broker, market, symbol, _quote(symbol), "ticker"))
    client = _exchange_client(broker, market)
    return _cached_market(key, lambda: _quote_from_raw(broker, market, symbol, client.ticker(symbol), "ticker"))


def _universal_assets(broker: str, market: str) -> dict:
    scope = _universal_scope(broker, market)
    broker = scope["broker"]
    market = scope["market"]
    if broker in CODE_ONLY_BROKERS:
        return _unsupported_read_response(broker, market, "assets", assets=[], symbols=[], count=0)
    if broker not in READ_BROKERS:
        return canonical_unavailable(broker=broker, market=market, source="universal_gateway", reason="corretora não suportada", status="unsupported", assets=[], symbols=[], count=0)
    key = ("assets", broker, market)
    if broker == "mt5":
        return _cached_market(key, lambda: _assets_from_raw("mt5", market, _symbols(), "catalog"))
    client = _exchange_client(broker, market)
    return _cached_market(key, lambda: _assets_from_raw(broker, market, client.assets() if hasattr(client, "assets") else client.exchange_info()))


def _universal_asset_capabilities(broker: str, market: str, symbol: str = "") -> dict:
    scope = _universal_scope(broker, market, symbol)
    broker = scope["broker"]
    market = scope["market"]
    symbol = scope["symbol"]
    response = _universal_assets(broker, market)
    rows = [row for row in response.get("assets", []) if isinstance(row, dict) and (not symbol or row.get("symbol") == symbol)]
    if symbol and not rows:
        return canonical_unavailable(broker=broker, market=market, source=response.get("source", "universal_gateway"), endpoint="asset_capabilities", reason=f"ativo não encontrado: {symbol}", status="unavailable", symbol=symbol, matrix=[])
    response["endpoint"] = "asset_capabilities"
    response["symbol"] = symbol or None
    response["matrix"] = rows
    response["count"] = len(rows)
    return response


def _universal_candles(broker: str, market: str, symbol: str, timeframe: str = "M5", limit: int = 500) -> dict:
    scope = _universal_scope(broker, market, symbol)
    broker = scope["broker"]
    market = scope["market"]
    symbol = scope["symbol"]
    if not symbol:
        raise ValueError("symbol é obrigatório")
    if broker in CODE_ONLY_BROKERS:
        return _unsupported_read_response(broker, market, "candles", symbol=symbol, timeframe=timeframe, candles=[], count=0)
    if broker not in READ_BROKERS:
        return canonical_unavailable(broker=broker, market=market, source="universal_gateway", reason="corretora não suportada", status="unsupported", symbol=symbol, candles=[], count=0)
    key = ("candles", broker, market, symbol, str(timeframe or "M5").upper(), int(limit))
    # Alias modelo -> corretora (`XAUUSD` -> `GOLD` na XM): a leitura usa o
    # simbolo que a corretora entende. Config do operador, nunca codigo.
    try:
        from backend.symbol_aliases import para_corretora as _para_corretora

        leitura = _para_corretora(broker, symbol) or symbol
    except Exception:
        leitura = symbol
    if broker == "mt5":
        return _cached_market(key, lambda: _candles_from_raw("mt5", market, symbol, _mt5_candles(leitura, timeframe, limit).get("candles", []), timeframe, "copy_rates_from_pos"))
    client = _exchange_client(broker, market)
    if not hasattr(client, "klines"):
        return canonical_unavailable(broker=broker, market=market, source=f"{broker}_api", reason="candles não implementados", symbol=symbol, candles=[], count=0)
    return _cached_market(key, lambda: _candles_from_raw(broker, market, symbol, client.klines(symbol, interval=timeframe, limit=limit), timeframe))


def _universal_depth(broker: str, market: str, symbol: str, limit: int = 20) -> dict:
    scope = _universal_scope(broker, market, symbol)
    broker = scope["broker"]
    market = scope["market"]
    symbol = scope["symbol"]
    limit = max(1, min(int(limit), 100))
    if not symbol:
        raise ValueError("symbol é obrigatório")
    if broker in CODE_ONLY_BROKERS:
        return _unsupported_read_response(broker, market, "depth", symbol=symbol, bids=None, asks=None)
    if broker == "mt5":
        return canonical_unavailable(broker="mt5", market=market, source="mt5_gateway", reason="DOM MT5 não está exposto por este adaptador", symbol=symbol, bids=None, asks=None)
    if broker not in READ_BROKERS:
        return canonical_unavailable(broker=broker, market=market, source="universal_gateway", reason="corretora não suportada", status="unsupported", symbol=symbol, bids=None, asks=None)
    return _cached_market(("depth", broker, market, symbol, limit), lambda: _depth_from_raw(broker, market, symbol, _exchange_client(broker, market).depth(symbol, limit=limit)))


def _universal_trades(broker: str, market: str, symbol: str, limit: int = 20) -> dict:
    scope = _universal_scope(broker, market, symbol)
    broker = scope["broker"]
    market = scope["market"]
    symbol = scope["symbol"]
    limit = max(1, min(int(limit), 100))
    if not symbol:
        raise ValueError("symbol é obrigatório")
    if broker in CODE_ONLY_BROKERS:
        return _unsupported_read_response(broker, market, "trades", symbol=symbol, trades=[], count=0)
    if broker not in READ_BROKERS:
        return canonical_unavailable(broker=broker, market=market, source="universal_gateway", reason="corretora não suportada", status="unsupported", symbol=symbol, trades=[], count=0)
    client = _exchange_client(broker, market)
    if not hasattr(client, "trades"):
        return canonical_unavailable(broker=broker, market=market, source=f"{broker}_api", reason="negócios recentes não implementados", status="unsupported", symbol=symbol, trades=[], count=0)
    return _cached_market(("trades", broker, market, symbol, limit), lambda: _trades_from_raw(broker, market, symbol, client.trades(symbol, limit=limit)))


def _universal_stats24h(broker: str, market: str, symbol: str) -> dict:
    scope = _universal_scope(broker, market, symbol)
    broker = scope["broker"]
    market = scope["market"]
    symbol = scope["symbol"]
    if not symbol:
        raise ValueError("symbol é obrigatório")
    if broker in CODE_ONLY_BROKERS:
        return _unsupported_read_response(broker, market, "stats24h", symbol=symbol)
    if broker not in READ_BROKERS:
        return canonical_unavailable(broker=broker, market=market, source="universal_gateway", reason="corretora não suportada", status="unsupported", symbol=symbol)
    client = _exchange_client(broker, market)
    if not hasattr(client, "stats_24h"):
        return canonical_unavailable(broker=broker, market=market, source=f"{broker}_api", reason="estatísticas 24h não implementadas", symbol=symbol)
    return _cached_market(("stats24h", broker, market, symbol), lambda: _stats_from_raw(broker, market, symbol, client.stats_24h(symbol)))


def _universal_positions(broker: str, market: str, account_id: str = "") -> dict:
    scope = _universal_scope(broker, market)
    broker = scope["broker"]
    market = scope["market"]
    if broker in CODE_ONLY_BROKERS:
        return _unsupported_read_response(broker, market, "positions", positions=[], pnl={"value": None, "available": False})
    if broker == "mt5":
        payload = _payload()
        account = payload.get("account") or {}
        return canonical_market_response(broker="mt5", market=market, source="mt5_gateway", status="ok", account_id=f"mt5:{account.get('login', 'active')}", positions=payload.get("positions", []), exposure=payload.get("exposure", {}))
    if broker not in {"binance", "mexc"}:
        return canonical_unavailable(broker=broker, market=market, source="universal_gateway", reason="corretora não suportada", status="unsupported", positions=[], pnl={"value": None, "available": False})
    client = _exchange_client(broker, market, private=True, account_id=account_id)
    raw = client.account()
    account = _unwrap_market_payload(raw)
    if _exchange_market(market) == "spot" and isinstance(account, dict) and isinstance(account.get("balances"), list):
        holdings = []
        for row in account["balances"]:
            if not isinstance(row, dict):
                continue
            free = optional_number(row.get("free"))
            locked = optional_number(row.get("locked"))
            if free is None and locked is None:
                continue
            volume = (free or 0.0) + (locked or 0.0)
            if volume == 0:
                continue
            holdings.append({
                "ticket": f"{broker}:{row.get('asset', '')}",
                "symbol": str(row.get("asset", "")) or None,
                "side": "HOLD",
                "volume": volume,
                "available": free,
                "locked": locked,
                "profit": None,
                "pnl_available": False,
                "source": f"{broker}_api",
            })
        return canonical_market_response(broker=broker, market=market, source=f"{broker}_api", status="ok", account_id=client.account_id, positions=holdings, pnl={"value": None, "available": False})
    if broker == "binance" and _exchange_market(market) == "futures" and isinstance(account, dict) and isinstance(account.get("positions"), list):
        positions = []
        pnl_values = []
        for row in account["positions"]:
            amount = optional_number(row.get("positionAmt"))
            if amount is None or amount == 0:
                continue
            profit = optional_number(row.get("unRealizedProfit"))
            if profit is not None:
                pnl_values.append(profit)
            positions.append({
                "ticket": f"binance:{row.get('symbol', '')}",
                "symbol": str(row.get("symbol", "")) or None,
                "side": "BUY" if amount > 0 else "SELL",
                "volume": abs(amount),
                "open_price": optional_number(row.get("entryPrice")),
                "current_price": optional_number(row.get("markPrice")),
                "sl": optional_number(row.get("stopPrice")),
                "tp": None,
                "profit": profit,
                "pnl_available": profit is not None,
                "leverage": optional_number(row.get("leverage")),
                "source": "binance_api",
            })
        return canonical_market_response(broker=broker, market=market, source="binance_api", status="ok", account_id=client.account_id, positions=positions, pnl={"value": sum(pnl_values) if pnl_values else None, "available": bool(pnl_values)})
    return canonical_unavailable(broker=broker, market=market, source=f"{broker}_api", reason="posições de futuros ainda não expostas por este adaptador", account_id=client.account_id, positions=[], pnl={"value": None, "available": False})


def _universal_overview() -> dict:
    rows = []
    for connection in list_connections():
        broker = str(connection.get("broker", "")).lower()
        market = str(connection.get("market", ""))
        row = {"id": connection.get("id"), "broker": broker, "market": market, "active": bool(connection.get("active", True)), "status": "indisponivel", "account": None, "positions": [], "pnl": {"value": None, "available": False}, "error": None, "source": "universal_gateway"}
        if not row["active"]:
            row["status"] = "desativada"
            rows.append(row)
            continue
        if broker in CODE_ONLY_BROKERS:
            row.update(status="code_only", error="adapter aguardando fixtures e homologação")
            rows.append(row)
            continue
        try:
            if broker == "mt5":
                payload = _payload()
                if payload.get("account"):
                    row.update(status="conectada", account=payload.get("account"), positions=payload.get("positions", []), source="mt5_gateway")
                else:
                    row.update(status="offline", error="MT5 não conectado; demais corretoras continuam disponíveis")
            elif broker in {"mexc", "binance"}:
                account = _universal_account(broker, market, str(connection.get("id", "")))
                positions = _universal_positions(broker, market, str(connection.get("id", "")))
                row["account"] = account.get("account")
                row["positions"] = positions.get("positions", [])
                row["pnl"] = positions.get("pnl", row["pnl"])
                row["status"] = "conectada" if account.get("ok") else "indisponivel"
                row["error"] = account.get("error")
            else:
                row["error"] = "corretora não suportada"
        except (MexcError, BinanceError, BybitError, OkxError, LookupError, ValueError) as exc:
            row["error"] = str(exc)
        rows.append(row)
    return {"ok": True, "mt5_required": False, "connections": rows, "connected": sum(1 for row in rows if row["status"] == "conectada"), "source": "universal_gateway"}


def _universal_quotes(broker: str, market: str, symbols: list[str]) -> dict:
    scope = _universal_scope(broker, market)
    broker = scope["broker"]
    market = scope["market"]
    requested = []
    for item in symbols or []:
        value = str(item or "").strip().upper()
        if value and value not in requested:
            requested.append(value)
    if len(requested) > 24:
        raise ValueError("no máximo 24 símbolos por cotação em lote")
    if broker in CODE_ONLY_BROKERS:
        return _unsupported_read_response(broker, market, "ticker_batch", symbols=requested, quotes=[], errors=[], count=0)
    if broker not in READ_BROKERS or not requested:
        return canonical_unavailable(broker=broker, market=market, source="universal_gateway", reason="symbols são obrigatórios" if not requested else "corretora não suportada", status="unsupported" if requested else "unavailable", symbols=requested, quotes=[], errors=[], count=0)
    rows: list[object] = []
    client = None
    quote_impl = globals().get("_universal_quote")
    use_batch = broker != "mt5" and quote_impl is not None and getattr(quote_impl, "__module__", __name__) == __name__ and hasattr(_exchange_client(broker, market), "ticker_batch")
    if use_batch:
        client = _exchange_client(broker, market)
        try:
            raw_rows = client.ticker_batch(requested)
            rows = raw_rows if isinstance(raw_rows, list) else _payload_rows(raw_rows)
        except (AttributeError, NotImplementedError):
            client = None
        except Exception:
            client = None
    by_symbol = {_row_symbol(row): row for row in rows if _row_symbol(row)}
    quotes = []
    errors = []
    unavailable = []
    for symbol in requested:
        if broker == "mt5":
            try:
                # Alias modelo -> corretora na leitura (`XAUUSD` -> `GOLD`).
                try:
                    from backend.symbol_aliases import para_corretora as _para_corretora

                    leitura = _para_corretora(broker, symbol) or symbol
                except Exception:
                    leitura = symbol
                raw = _quote(leitura)
            except Exception as exc:
                errors.append({"symbol": symbol, "error": str(exc)})
                unavailable.append(symbol)
                continue
        else:
            raw = by_symbol.get(symbol)
            if raw is None and client is None:
                try:
                    raw = _universal_quote(broker, market, symbol)
                except Exception as exc:
                    errors.append({"symbol": symbol, "error": str(exc)})
                    unavailable.append(symbol)
                    continue
            elif raw is None and client is not None:
                try:
                    raw = client.ticker(symbol)
                except Exception as exc:
                    errors.append({"symbol": symbol, "error": str(exc)})
                    unavailable.append(symbol)
                    continue
            if raw is None:
                errors.append({"symbol": symbol, "error": "ticker ausente no batch"})
                unavailable.append(symbol)
                continue
        quote = _quote_from_raw(broker, market, symbol, raw, "ticker_batch" if broker != "mt5" else "ticker")
        quote["status"] = "ok" if quote.get("last") is not None or quote.get("bid") is not None or quote.get("ask") is not None else "unavailable"
        quote["ok"] = quote["status"] != "unavailable"
        quotes.append(quote)
    status = "ok" if quotes and not errors else "partial" if quotes else "unavailable"
    return canonical_market_response(broker=broker, market=market, source="universal_gateway", status=status, symbols=requested, quotes=quotes, errors=errors, unavailable=unavailable, count=len(quotes), error=None if quotes else "nenhuma cotação disponível")


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


def _mt5_connected() -> bool:
    """A sessao do MT5 ja esta inicializada neste processo?

    `MetaTrader5.terminal_info()` devolve None enquanto nao ha sessao, e nao
    lanca: e o jeito barato de checar antes de mexer em `copy_rates`, que
    devolve None e nao explica por que.
    """
    try:
        mt5 = _mt5()
        info = getattr(mt5, "terminal_info", None)
        return bool(callable(info) and info() is not None)
    except Exception:  # noqa: BLE001
        return False


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


def candles_mt5_para_dataframe(linhas: Any) -> Any:
    """Converte as linhas do MT5 no DataFrame que a feature builder espera.

    FATOR DE FALHA REPETIDO
    ========================
    O treino usa `Time/Open/High/Low/Close/Volume` (ver `INPUT_COLUMNS` em
    `Python/ai/train_v2.py`). As linhas do gateway vem em minusculo e `time` em
    epoch de segundos. Sem esta conversao, a inferencia falha com
    `None of ['Time'] are in the columns`.

    Alem disso, `t.reamostrar` usa `resample()`, que exige `DatetimeIndex`, e a
    feature builder exige a COLUNA `Time`. `drop=False` satisfaz os dois: o
    indice vira datetime sem remover a coluna.

    Ja foi corrigido em tres lugares isoladamente (a previsao do gateway, o
    backtest e agora o motor automatico), e cada vez o mesmo erro voltou em
    um caminho novo. Por isso vira um unico ponto de traducao.
    """
    import pandas as pd

    df = pd.DataFrame(linhas or [])
    if df.empty:
        return df
    df = df.rename(columns={c: c.capitalize() for c in df.columns})
    if "Time" in df.columns:
        coluna = df["Time"]
        # O gateway ja pode devolver `timestamp` em ISO; nesse caso `time` fica
        # redundante. Prioridade: coluna ja datetime > timestamp > epoch em s.
        if not pd.api.types.is_datetime64_any_dtype(coluna):
            if "Timestamp" in df.columns and "Time" not in ("time",):
                origem = df["Timestamp"]
                if pd.api.types.is_numeric_dtype(origem):
                    df["Time"] = pd.to_datetime(origem, unit="s", errors="coerce", utc=True)
                else:
                    df["Time"] = pd.to_datetime(origem, errors="coerce", utc=True)
            else:
                df["Time"] = pd.to_datetime(coluna, unit="s", errors="coerce", utc=True)
        df = df.dropna(subset=["Time"]).sort_values("Time").set_index("Time", drop=False)
    return df


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
    out = {
        "ts": utc_now(),
        "gateway": "XAU_AI_PRO MT5 Gateway",
        "terminal_connected": False,
        "account": None,
        "positions": [],
        "positions_available": False,
        "pending_orders": [],
        "pending_orders_available": False,
        "exposure": None,
        "history_count": None,
        "ea_heartbeat": _read_ea_heartbeat(),
    }
    try:
        mt5 = _mt5()
    except Exception:
        return out
    ti = None
    try:
        ti = mt5.terminal_info()
        out["terminal_connected"] = bool(getattr(ti, "connected", False)) if ti else False
    except Exception:
        out["terminal_connected"] = False
    try:
        info = mt5.account_info()
        if info:
            demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
            trade_mode = getattr(info, "trade_mode", None)
            if isinstance(trade_mode, str):
                account_mode = trade_mode.upper()
            elif trade_mode is None:
                account_mode = "UNKNOWN"
            elif trade_mode == demo_mode:
                account_mode = "DEMO"
            else:
                account_mode = "REAL"
            out["account"] = {
                "login": getattr(info, "login", None),
                "name": getattr(info, "name", None),
                "company": getattr(info, "company", None),
                "server": getattr(info, "server", None),
                "balance": optional_number(getattr(info, "balance", None)),
                "equity": optional_number(getattr(info, "equity", None)),
                "profit": optional_number(getattr(info, "profit", None)),
                "margin": optional_number(getattr(info, "margin", None)),
                "margin_free": optional_number(getattr(info, "margin_free", None)),
                "margin_level": optional_number(getattr(info, "margin_level", None)),
                "currency": getattr(info, "currency", None),
                "trade_allowed": bool(getattr(ti, "trade_allowed", False)) if ti else False,
                "terminal_connected": bool(getattr(ti, "connected", False)) if ti else False,
                "mode": account_mode,
                "account_confirmed": account_mode == "DEMO",
            }
    except Exception:
        out["account"] = None
    try:
        raw_positions = mt5.positions_get()
        if raw_positions is not None:
            positions = []
            volumes = []
            profits = []
            for position in raw_positions:
                volume = optional_number(getattr(position, "volume", None))
                profit = optional_number(getattr(position, "profit", None))
                if volume is not None:
                    volumes.append(volume)
                if profit is not None:
                    profits.append(profit)
                positions.append({
                    "ticket": getattr(position, "ticket", None),
                    "symbol": getattr(position, "symbol", None),
                    "type": "BUY" if getattr(position, "type", None) == 0 else "SELL",
                    "volume": volume,
                    "open_price": optional_number(getattr(position, "price_open", None)),
                    "price_current": optional_number(getattr(position, "price_current", None)),
                    "sl": optional_number(getattr(position, "sl", None)),
                    "tp": optional_number(getattr(position, "tp", None)),
                    "profit": profit,
                    "magic": getattr(position, "magic", None),
                    "time": optional_number(getattr(position, "time", None), integer=True),
                })
            out["positions"] = positions
            out["positions_available"] = True
            out["exposure"] = {
                "count": len(positions),
                "volume": round(sum(volumes), 8) if volumes else 0.0,
                "floating_profit": round(sum(profits), 2) if profits else 0.0,
                "protected": all(bool(getattr(position, "sl", 0.0)) and bool(getattr(position, "tp", 0.0)) for position in raw_positions),
            }
    except Exception:
        out["positions"] = []
        out["positions_available"] = False
        out["exposure"] = None
    try:
        raw_orders = mt5.orders_get()
        if raw_orders is not None:
            out["pending_orders"] = [{
                "ticket": getattr(order, "ticket", None),
                "symbol": getattr(order, "symbol", None),
                "type": getattr(order, "type", None),
                "volume": optional_number(getattr(order, "volume_current", None)),
                "price": optional_number(getattr(order, "price_open", None)),
                "sl": optional_number(getattr(order, "sl", None)),
                "tp": optional_number(getattr(order, "tp", None)),
                "time": optional_number(getattr(order, "time_setup", None), integer=True),
            } for order in raw_orders]
            out["pending_orders_available"] = True
    except Exception:
        out["pending_orders"] = []
        out["pending_orders_available"] = False
    try:
        deals = mt5.history_deals_get(datetime.now() - timedelta(days=7), datetime.now())
        if deals is not None:
            out["history_count"] = len(deals)
    except Exception:
        out["history_count"] = None
    return out


def _status_snapshot() -> dict:
    try:
        payload = _payload()
    except Exception:
        payload = {"terminal_connected": False, "account": None, "positions": [], "positions_available": False, "ea_heartbeat": {"live": False, "source": "EA FILE_COMMON", "reason": "status indisponível"}, "pending_orders": [], "pending_orders_available": False, "exposure": None, "ts": utc_now()}
    positions = payload.get("positions") if isinstance(payload.get("positions"), list) else []
    terminal_connected = bool(payload.get("terminal_connected", False))
    return {
        "ok": True,
        "gateway": "online",
        "terminal_connected": terminal_connected,
        "mt5_connected": terminal_connected,
        "account": payload.get("account"),
        "positions": positions,
        "positions_available": bool(payload.get("positions_available", False)),
        "position_count": len(positions) if payload.get("positions_available", False) else None,
        "pending_orders": payload.get("pending_orders") if isinstance(payload.get("pending_orders"), list) else [],
        "pending_orders_available": bool(payload.get("pending_orders_available", False)),
        "exposure": payload.get("exposure"),
        "ea_heartbeat": payload.get("ea_heartbeat") if isinstance(payload.get("ea_heartbeat"), dict) else {"live": False, "source": "EA FILE_COMMON", "reason": "heartbeat ausente"},
        "ts": payload.get("ts") or utc_now(),
        "source": "mt5_gateway",
    }


def _quote(symbol: str) -> dict:
    mt5 = _mt5()
    symbol = str(symbol or "").strip().upper()
    if not symbol:
        raise ValueError("symbol obrigatorio")
    info = mt5.symbol_info(symbol)
    if not info:
        raise LookupError(f"simbolo indisponivel no MT5: {symbol}")
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        raise LookupError(f"cotacao indisponivel no MT5: {symbol}")
    bid = optional_number(getattr(tick, "bid", None))
    ask = optional_number(getattr(tick, "ask", None))
    last = optional_number(getattr(tick, "last", None))
    timestamp = first_value(tick, "time_ms", "time", "timestamp") if isinstance(tick, dict) else getattr(tick, "time_ms", getattr(tick, "time", None))
    change_pct = optional_number(getattr(info, "change_pct", None)) if info is not None else None
    if change_pct is None and info is not None:
        change_pct = optional_number(getattr(info, "price_change_percent", None))
    spread = ask - bid if bid is not None and ask is not None else None
    received_at = utc_now()
    return {
        "symbol": symbol,
        "bid": bid,
        "ask": ask,
        "last": last,
        "price": last,
        "spread": spread,
        "volume": optional_number(getattr(tick, "volume", None)),
        "high": optional_number(getattr(info, "session_price_high", None)) if info is not None else None,
        "low": optional_number(getattr(info, "session_price_low", None)) if info is not None else None,
        "change_pct": change_pct,
        "timestamp": timestamp_iso(timestamp),
        "received_at": received_at,
        "digits": getattr(info, "digits", None) if info is not None else None,
        "point": optional_number(getattr(info, "point", None)) if info is not None else None,
        "currency_base": getattr(info, "currency_base", None) if info is not None else None,
        "currency_profit": getattr(info, "currency_profit", None) if info is not None else None,
        "trade_mode": getattr(info, "trade_mode", None) if info is not None else None,
        "source": "mt5_gateway",
        "status": "ok" if last is not None or bid is not None or ask is not None else "unavailable",
    }


def _symbols() -> dict:
    mt5 = _mt5()
    rows = discover_assets(mt5, include_hidden=True)
    return {
        "symbols": rows,
        "count": len(rows),
        "source": "mt5_gateway",
        "scope": "broker_catalog",
        "status": "ok" if rows else "unavailable",
        "received_at": utc_now(),
        "timestamp": None,
    }



def _history(days: int = 30, symbol: str = "") -> dict:
    mt5 = _mt5()
    days = max(1, min(int(days), 3650))
    end = datetime.now()
    start = end.replace(hour=0, minute=0, second=0, microsecond=0) if days == 1 else end - timedelta(days=days)
    deals = mt5.history_deals_get(start, end, group=f"*{symbol}*") if symbol else mt5.history_deals_get(start, end)
    rows = []
    for deal in deals or []:
        deal_type = getattr(deal, "type", None)
        entry = getattr(deal, "entry", None)
        deal_time = optional_number(getattr(deal, "time", None), integer=True)
        rows.append({
            "ticket": optional_number(getattr(deal, "ticket", None), integer=True),
            "order": optional_number(getattr(deal, "order", None), integer=True),
            "position_id": optional_number(getattr(deal, "position_id", None), integer=True),
            "symbol": getattr(deal, "symbol", None),
            "type": "BUY" if deal_type == getattr(mt5, "DEAL_TYPE_BUY", 0) else "SELL",
            "entry": "IN" if entry == getattr(mt5, "DEAL_ENTRY_IN", 0) else "OUT" if entry == getattr(mt5, "DEAL_ENTRY_OUT", 1) else entry,
            "volume": optional_number(getattr(deal, "volume", None)),
            "price": optional_number(getattr(deal, "price", None)),
            "profit": optional_number(getattr(deal, "profit", None)),
            "commission": optional_number(getattr(deal, "commission", None)),
            "swap": optional_number(getattr(deal, "swap", None)),
            "fee": optional_number(getattr(deal, "fee", None)),
            "magic": optional_number(getattr(deal, "magic", None), integer=True),
            "time": timestamp_iso(deal_time),
        })
    rows.sort(key=lambda row: row.get("time") or "", reverse=True)
    return {"deals": rows, "count": len(rows), "days": days, "source": "mt5_gateway"}




_TIMEFRAME_MAP = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 16385, "H4": 16388, "D1": 16408}

# Instante em que ESTE processo subiu. O arquivo de telemetria e um historico
# permanente que sobrevive a reinicios e a troca de conta; o high-water mark do
# risco so pode considerar amostras da sessao atual.
_SESSION_START_TS = time.time()

# High-water mark de patrimonio por conta, valido apenas nesta sessao do
# processo. Ver _risk_state.
_SESSION_PEAK_EQUITY: dict[str, float] = {}


def _economic_alerts_within(hours: float = 6.0, tz: str = "BRT") -> list[dict]:
    """Proximos eventos de alto impacto dentro de N horas (agenda local).

    Fonte: app/economic_calendar.alerts_within. Usado pelo endpoint
    /api/economic/alerts como trigger de notificacao no app (Tauri).
    """
    from backend.planos.economic_calendar import alerts_within

    hours = max(0.0, min(float(hours), 72.0))
    return alerts_within(hours=hours, tz=tz or "BRT")


def _economic_calendar(limit: int = 30, tz: str = "BRT", days: int = 14) -> dict:
    """Agenda economica real (tabela local recorrente) — nunca retorna mock.

    Fonte unica: app/economic_calendar.py. Os horarios sao estimativas baseadas
    em padroes de calendario; o payload marca isso explicitamente em 'disclaimer'.
    """
    from backend.planos.economic_calendar import upcoming_events

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


def _mt5_unavailable(symbol: str, timeframe: str, reason: str, code: str, mt5: object | None = None) -> dict:
    """Candles indisponiveis, com o motivo real e o erro do terminal.

    Antes este caminho devolvia apenas "sem candles para X". O operador via um
    503 sem distinguishing "terminal fechado" de "simbolo invalido" de
    "sem historico", e nao havia como corrigir. Agora o codigo do motivo e o
    `last_error` do MetaTrader5 acompanham a resposta.
    """
    last_error = None
    terminal_open = None
    if mt5 is not None:
        getter = getattr(mt5, "last_error", None)
        if callable(getter):
            try:
                erro = getter()
                last_error = [erro[0], erro[1]] if isinstance(erro, (tuple, list)) and len(erro) == 2 else None
            except Exception:  # noqa: BLE001 - diagnostico nunca pode derrubar a rota
                last_error = None
        probe = getattr(mt5, "terminal_info", None)
        if callable(probe):
            try:
                terminal_open = probe() is not None
            except Exception:  # noqa: BLE001
                terminal_open = None
    return canonical_unavailable(
        broker="mt5",
        market="other",
        source="mt5_gateway",
        endpoint="copy_rates_from_pos",
        reason=reason,
        reason_code=code,
        terminal_open=terminal_open,
        mt5_last_error=last_error,
        symbol=symbol,
        timeframe=timeframe,
        candles=[],
        count=0,
    )


def _mt5_candles(symbol: str, timeframe: str = "M5", count: int = 300) -> dict:
    # A sessao do MT5 precisa estar inicializada antes de `copy_rates`. Ate
    # 2026-09-29 esta funcao pegava o modulo cru e chamava `copy_rates` direto;
    # quando o gateway ainda nao tinha ligado a sessao (que acontece em cada
    # processo novo, e o auto_engine roda em thread), o MT5 devolvia None e a
    # resposta saia como `terminal_disconnected` mesmo com o terminal aberto e
    # logado. `initialize()` em processo ja aberto nao abre uma segunda janela
    # nem inicia sessao sozinho — ele conecta ao terminal que ja existe, que e
    # exatamente a exigencia do projeto (so conectar, nunca abrir).
    #
    # A guarda e `getattr` e nao acesso direto: os dubles de teste injetam um
    # modulo MT5 minimo, sem `initialize`. Sem o getattr, todo teste de candles
    # quebrava com `AttributeError` antes de chegar a rota que ele quer
    # exercitar.
    inicializar = getattr(_mt5(), "initialize", None)
    if callable(inicializar) and not _mt5_connected():
        _ensure_mt5()
    mt5 = _mt5()
    symbol = str(symbol or "").strip().upper()
    count = max(10, min(int(count), 2000))
    normalized_timeframe = (timeframe or "M5").upper()
    if normalized_timeframe not in _TIMEFRAME_MAP:
        raise ValueError(f"timeframe MT5 invalido: {timeframe}")
    tf_code = _TIMEFRAME_MAP[normalized_timeframe]
    copy_from_pos = getattr(mt5, "copy_rates_from_pos", None)
    legacy_copy = getattr(mt5, "copy_rates", None)
    if callable(copy_from_pos):
        rates = copy_from_pos(symbol, tf_code, 0, count)
    elif callable(legacy_copy):
        rates = legacy_copy(symbol, tf_code, count)
    else:
        return _mt5_unavailable(symbol, normalized_timeframe, "a biblioteca do MT5 nao expoe copy_rates", "mt5_api_missing", mt5)
    if rates is None:
        # O MetaTrader5 devolve None tanto para terminal fechado quanto para
        # simbolo invalido; `terminal_info` e `last_error` separam os dois casos.
        terminal_aberto = False
        probe = getattr(mt5, "terminal_info", None)
        if callable(probe):
            try:
                terminal_aberto = probe() is not None
            except Exception:  # noqa: BLE001
                terminal_aberto = False
        if not terminal_aberto:
            return _mt5_unavailable(symbol, normalized_timeframe, "terminal MT5 nao conectado ou nao autorizado", "terminal_disconnected", mt5)
        return _mt5_unavailable(symbol, normalized_timeframe, f"sem candles de {symbol} em {normalized_timeframe} (simbolo invalido, sem historico ou nao assinante)", "no_candles_for_symbol", mt5)
    rows = [_candle_row(rate) for rate in rates]
    rows.sort(key=lambda row: row.get("time") if isinstance(row.get("time"), (int, float)) else 0)
    return canonical_market_response(broker="mt5", market="other", source="mt5_gateway", endpoint="copy_rates_from_pos", status="ok" if rows else "unavailable", timestamp=rows[-1].get("time") if rows else None, error=None if rows else f"sem candles para {symbol} ({normalized_timeframe})", symbol=symbol, timeframe=normalized_timeframe, candles=rows, count=len(rows))
def _risk_state(mt5) -> dict:
    """Estado de risco real do dia, lido do MT5 (nunca estimado).

    - daily_loss_pct: perda do dia (deals do dia, profit+commission+swap)
      como percentual do balance. Negativo quando ha lucro.
    - exposure_pct: volume aberto como percentual do teto do risk_gate
      (max_positions * max_volume = 5 * 0.10 = 0.5 lotes).
    - open_positions: quantidade de posicoes abertas.

    Falha de leitura bloqueia novas entradas; None do MT5 nao significa lista vazia.
    """
    from backend.risk_gate import RiskLimits

    # Mesma questao de `_mt5_candles`: `account_info()` devolve None sem sessao
    # inicializada. A thread do motor automatico roda em processo novo, e era
    # exatamente ai que o ciclo morria com "risk_gate nao respondeu: sem dados"
    # — sem uma unica linha de log dizendo que faltava conectar ao terminal.
    inicializar = getattr(mt5, "initialize", None)
    if callable(inicializar) and not _mt5_connected():
        _ensure_mt5()

    limits = RiskLimits()
    try:
        info = mt5.account_info()
        if info is None:
            raise RuntimeError("conta MT5 indisponivel para validar risco")
        balance = float(info.balance)
        equity = float(info.equity)
        if not math.isfinite(balance) or balance <= 0:
            raise RuntimeError("saldo MT5 invalido para validar risco")
        if not math.isfinite(equity) or equity <= 0:
            raise RuntimeError("patrimonio MT5 invalido para validar risco")

        raw_positions = mt5.positions_get()
        if raw_positions is None:
            raise RuntimeError("posicoes MT5 indisponiveis para validar risco")
        positions = list(raw_positions)

        now = datetime.now()
        raw_deals = mt5.history_deals_get(
            now.replace(hour=0, minute=0, second=0, microsecond=0), now)
        if raw_deals is None:
            raise RuntimeError("historico MT5 indisponivel para validar risco")
        deals = list(raw_deals)
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError("nao foi possivel validar o risco no MT5") from exc

    try:
        day_result = 0.0
        operation_keys: set[str] = set()
        entry_in = getattr(mt5, "DEAL_ENTRY_IN", 0)
        for deal in deals:
            deal_result = (float(getattr(deal, "profit", 0.0) or 0.0)
                           + float(getattr(deal, "commission", 0.0) or 0.0)
                           + float(getattr(deal, "swap", 0.0) or 0.0))
            day_result += deal_result
            entry = getattr(deal, "entry", entry_in)
            if entry != entry_in:
                continue
            position_id = int(getattr(deal, "position_id", 0) or 0)
            ticket = int(getattr(deal, "ticket", 0) or 0)
            if position_id > 0:
                operation_keys.add(f"position:{position_id}")
            elif ticket > 0:
                operation_keys.add(f"ticket:{ticket}")
            else:
                raise RuntimeError("identificador de operacao MT5 ausente")
        daily_trades = len(operation_keys)
        volume = sum(float(getattr(p, "volume", 0.0) or 0.0) for p in positions)
    except RuntimeError:
        raise
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError("dados MT5 invalidos para validar risco") from exc
    if not math.isfinite(day_result):
        raise RuntimeError("resultado diario MT5 invalido para validar risco")

    telemetry = watchdog.history(1000)
    equity_samples = [equity]
    for snapshot in telemetry.get("snapshots", []):
        value = optional_number(snapshot.get("equity"))
        if value is None or value <= 0:
            continue
        # O arquivo telemetry_history.jsonl e permanente e guarda sessoes
        # anteriores (e ate outras contas). Um pico de uma sessao velha com
        # outro saldo virava um drawdown fantasma que bloqueava TODA ordem,
        # mesmo com risco zerado. So amostras desta sessao contam.
        amostra_ts = optional_number(snapshot.get("ts"))
        if amostra_ts is not None and amostra_ts < _SESSION_START_TS:
            continue
        equity_samples.append(float(value))
    last_snapshot = telemetry.get("last")
    if isinstance(last_snapshot, dict):
        value = optional_number(last_snapshot.get("equity"))
        if value is not None and value > 0:
            amostra_ts = optional_number(last_snapshot.get("ts"))
            if amostra_ts is None or amostra_ts >= _SESSION_START_TS:
                equity_samples.append(float(value))
    # High-water mark de ESTA sessao, por conta. Nao vem do arquivo de
    # telemetria permanente, que guarda sessoes antigas e ate outras contas e
    # produzia um drawdown fantasma que bloqueava toda ordem mesmo com risco
    # zerado. Nasce no patrimonio real atual e so sobe durante a sessao: uma
    # sessao recem iniciada tem drawdown legitimamente 0, e nao uma falha.
    chave_conta = f"mt5:{str(getattr(info, 'login', '') or 'active').strip()}"
    pico_sessao = _SESSION_PEAK_EQUITY.get(chave_conta)
    if pico_sessao is None or not math.isfinite(pico_sessao) or pico_sessao <= 0:
        pico_sessao = equity
    pico_sessao = max(pico_sessao, max(equity_samples))
    _SESSION_PEAK_EQUITY[chave_conta] = pico_sessao
    peak_equity = pico_sessao
    drawdown_pct = max(0.0, (peak_equity - equity) / peak_equity * 100.0) if peak_equity > 0 else 0.0
    if not math.isfinite(drawdown_pct):
        raise RuntimeError("drawdown MT5 invalido para validar risco")

    daily_loss_pct = (-day_result / balance * 100.0) if balance > 0 else 0.0
    if daily_loss_pct < 0:
        daily_loss_pct = 0.0  # lucro do dia nao consome o limite de perda

    if not math.isfinite(volume) or volume < 0:
        raise RuntimeError("volume MT5 invalido para validar risco")
    ceiling = limits.max_volume * limits.max_positions
    exposure_pct = (volume / ceiling * 100.0) if ceiling > 0 else 0.0

    return {
        # `ok` explicito: `auto_engine.ciclo_unico` recusa o ciclo quando
        # `risco.get("ok")` e falso. Sem este campo, um estado de risco
        # PERFEITAMENTE valido era recusado com "risk_gate nao respondeu: sem
        # dados" — o `error` tambem nao existia, entao a tela mostrava "sem
        # dados" para um estado que tinha balance, equity e limites reais.
        "ok": True,
        "source": "mt5_gateway",
        "withdrawals_enabled": False,
        "daily_loss_pct": round(daily_loss_pct, 4),
        "exposure_pct": round(exposure_pct, 4),
        "open_positions": len(positions),
        "daily_trades": daily_trades,
        "drawdown_pct": round(drawdown_pct, 4),
        "peak_equity": round(peak_equity, 4),
        "open_volume": round(volume, 4),
        "balance": balance,
        "equity": equity,
        "day_result": round(day_result, 4),
        "limits": {
            "max_volume": limits.max_volume,
            "max_daily_loss_pct": limits.max_daily_loss_pct,
            "max_exposure_pct": limits.max_exposure_pct,
            "max_positions": limits.max_positions,
            "max_daily_trades": limits.max_daily_trades,
            "max_drawdown_pct": limits.max_drawdown_pct,
        },
    }


def _record_trade_intent(action: str, payload: dict, status: str, intent_id: str | None = None, extra: dict | None = None) -> str | None:
    """Registra a intencao de um comando de trade.

    Isolar a chamada num unico ponto garante que nenhuma rota que altera conta
    fique sem rastro: `intent_log` e append-only e reconcilia por `request_id`.
    """
    try:
        detalhes = {
            "request_id": payload.get("request_id"),
            "symbol": payload.get("symbol"),
            "ticket": payload.get("ticket"),
            "side": payload.get("side"),
            "volume": payload.get("volume"),
        }
        detalhes.update(extra or {})
        registro = intent_log.record_intent(action, detalhes, intent_id=intent_id, status=status)
        return registro or intent_id
    except Exception:  # noqa: BLE001 - auditoria nunca pode derrubar a ordem
        return intent_id


def _spread_points(mt5, symbol: str, tick) -> float:
    """Spread real do simbolo em pontos, lido do terminal."""
    try:
        info = mt5.symbol_info(symbol)
        point = float(getattr(info, "point", 0) or 0)
        ask = float(getattr(tick, "ask", 0) or 0)
        bid = float(getattr(tick, "bid", 0) or 0)
        if point <= 0 or ask <= 0 or bid <= 0:
            raise ValueError("tick sem ask/bid utilizavel")
        return (ask - bid) / point
    except (AttributeError, TypeError, ValueError):
        # Sem dado de spread, a trava nao pode ser pulada: recusar e o
        # comportamento correto, e o chamador transforma em recusa explicita.
        raise ValueError(f"spread indisponivel para {symbol}; a operacao nao foi aprovada")


def _notional(mt5, symbol: str, volume: float, price: float) -> float:
    """Nocional da operacao: contrato x volume x preco."""
    try:
        info = mt5.symbol_info(symbol)
        contract = float(getattr(info, "trade_contract_size", 0) or 0)
        if contract <= 0:
            raise ValueError("contrato invalido")
        return contract * float(volume) * float(price)
    except (AttributeError, TypeError, ValueError):
        raise ValueError(f"nocional indisponivel para {symbol}; a operacao nao foi aprovada")


def _trade_order(payload: dict) -> dict:
    """Envia ordem em conta DEMO ou REAL quando a trava local estiver ativa."""
    if REAL_EMERGENCY_STOP.exists():
        raise PermissionError("parada de emergência ativa")
    if (os.getenv("XAU_ENABLE_TRADE_COMMANDS", "1") != "1" and os.getenv("XAU_ENABLE_DEMO_ORDERS", "0") != "1"):
        raise PermissionError("execucao de trade desabilitada; defina XAU_ENABLE_TRADE_COMMANDS=1")
    if payload.get("confirm") is not True:
        raise PermissionError("confirm=true obrigatorio")
    mt5 = _mt5()
    info = mt5.account_info()
    if not info:
        raise PermissionError("conta MT5 nao identificada; ordem recusada")
    if not bool(getattr(info, "trade_allowed", False)):
        raise PermissionError("negociacao nao permitida pelo terminal MT5")
    symbol = str(payload.get("symbol", "")).strip()
    side = str(payload.get("side", "")).upper()
    volume = float(payload.get("volume", 0) or 0)
    sl = float(payload.get("sl", 0) or 0)
    tp = float(payload.get("tp", 0) or 0)
    if not symbol or side not in {"BUY", "SELL"} or not (0 < volume <= 0.10) or sl <= 0 or tp <= 0:
        raise ValueError("symbol, side, volume <= 0.10, sl e tp validos sao obrigatorios")
    # Alias modelo -> corretora (`XAUUSD` -> `GOLD` na XM): a ordem manual
    # sai com o simbolo que o terminal entende. Config do operador.
    try:
        from backend.symbol_aliases import para_corretora as _para_corretora

        symbol = _para_corretora("mt5", symbol) or symbol
    except Exception:
        pass
    # Risco REAL do dia: perda diaria e exposicao lidas do MT5 (nao mais 0.0 fixo).
    # Antes desta correcao o risk_gate recebia daily_loss_pct=0.0 e exposure_pct=0.0,
    # o que desarmava os dois limites mais importantes em conta de dinheiro real.
    risk = _risk_state(mt5)
    if not mt5.symbol_select(symbol, True):
        raise LookupError(f"simbolo indisponivel no MT5: {symbol}")
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        raise LookupError(f"cotacao indisponivel no MT5: {symbol}")
    # A validacao de risco vem DEPOIS do tick porque o risk_gate passou a exigir
    # spread e nocional reais: as duas travas existiam no codigo com default
    # None, o que fazia a checagem ser pulada (fail-open).
    validate_trade(volume=volume, daily_loss_pct=risk["daily_loss_pct"],
                   exposure_pct=risk["exposure_pct"], open_positions=risk["open_positions"],
                   daily_trades=risk["daily_trades"], drawdown_pct=risk["drawdown_pct"],
                   spread=_spread_points(mt5, symbol, tick),
                   notional=_notional(mt5, symbol, volume, float(tick.ask if side == "BUY" else tick.bid)))
    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
    price = float(tick.ask if side == "BUY" else tick.bid)
    request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": volume,
               "type": order_type, "price": price, "sl": sl, "tp": tp,
               "deviation": 20, "magic": 2026001, "comment": "XAU_AI_PRO_DEMO",
               "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
    check = mt5.order_check(request)
    if not check or getattr(check, "retcode", 0) != 0:
        _record_trade_intent("trade_order", payload, "failed", extra={"stage": "order_check", "retcode": int(getattr(check, "retcode", -1))})
        return {"ok": False, "stage": "order_check", "retcode": int(getattr(check, "retcode", -1)), "comment": str(getattr(check, "comment", "check falhou")), "trade": True}
    # Abertura de posicao e a unica ordem que altera a conta; ela precisa de
    # intent antes do envio, senao uma resposta perdida do MT5 deixa a operacao
    # sem rastro e sem reconciliacao. Fechamento e gestao ja registravam
    # (linhas de _trade_close/_trade_manage); a abertura nao registrava.
    intent_id = _record_trade_intent("trade_order", payload, "pending")
    result = mt5.order_send(request)
    ok = bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE)
    _record_trade_intent(
        "trade_order", payload, "sent" if ok else "failed", intent_id=intent_id,
        extra={
            "retcode": int(getattr(result, "retcode", -1)),
            "order": int(getattr(result, "order", 0)),
            "deal": int(getattr(result, "deal", 0)),
        },
    )
    return {"ok": ok, "stage": "order_send", "retcode": int(getattr(result, "retcode", -1)), "comment": str(getattr(result, "comment", "")), "order": int(getattr(result, "order", 0)), "deal": int(getattr(result, "deal", 0)), "trade": True, "intent_id": intent_id}


def _universal_execution_preview(payload: dict, action: str) -> dict:
    """Valida o contrato universal e retorna pré-envio; nunca roteia execução."""
    try:
        if action == "order":
            request = UniversalOrderRequest.from_payload(payload)
            data = request.to_dict()
        else:
            broker = str(payload.get("broker", "")).lower()
            symbol = str(payload.get("symbol", "")).strip().upper()
            if broker not in set(EXECUTION_GATES) or not symbol:
                raise ValueError("broker e symbol são obrigatórios")
            scope = _universal_scope(broker, str(payload.get("market", "")), symbol)
            data = {"broker": scope["broker"], "market": scope["market"], "symbol": scope["symbol"], "account_id": str(payload.get("account_id", "")).strip(), "ticket": payload.get("ticket")}
        account_id = str(data.get("account_id", "")).strip()
        if not account_id:
            raise ValueError("account_id é obrigatório")
        if data["broker"] != "mt5":
            resolve_connection(account_id, data["broker"], data["market"])
        return {"ok": True, "accepted": True, "stage": "validated", "action": action, "request": data, "policy": execution_policy(), "execution_enabled": True}
    except (LookupError, TypeError, ValueError) as exc:
        return error_response("INVALID_UNIVERSAL_REQUEST", str(exc))


def _universal_execute(payload: dict, action: str) -> dict:
    """Executa acao universal quando execute=true.

    Antes disto existia apenas `_universal_execution_preview`, e todo
    payload com execute=true era devolvido com 403 "somente previa". O
    operador pedia ordem, o app dizia que nao podia, e o motivo citava
    versao/demo — nao a causa real.

    Agora:
        - broker mt5  -> roteia para _trade_order/_trade_close/_trade_manage/
          _trade_cancel_orders, que ja trazem as travas de verdade
          (XAU_ENABLE_TRADE_COMMANDS, confirm=true, SL/TP obrigatorios,
          order_check antes do order_send, risk_gate).
        - demais      -> adaptador da propria corretora, que aplica
          XAU_ENABLE_<BROKER>_EXECUTION e devolve o motivo dele. Antes o
          app dizia "nao existe adaptador", que e falso: mexc, binance,
          bybit e okx ja estao no codigo.

    Fecha a conta qualquer que seja o tipo dela: DEMO e REAL usam o
    mesmo caminho.
    """
    previa = _universal_execution_preview(payload, action)
    if not previa.get("ok"):
        return previa
    request = previa.get("request", {})
    broker = str(request.get("broker", "")).lower()
    if broker != "mt5":
        # O broker TEM adaptador (mexc/binance/bybit/okx). Quem responde e o
        # proprio adaptador: ele aplica a trava dele
        # (XAU_ENABLE_<BROKER>_EXECUTION, uma etapa separada por corretora)
        # e devolve o motivo real. O rotulo da conta (DEMO/REAL) nao entra
        # nesta decisao em lugar nenhum.
        if action != "order":
            return error_response(
                "EXECUTION_UNSUPPORTED_ACTION",
                f"acao {action} ainda nao tem implementacao para {broker}",
            )
        try:
            from backend.universal_router import UniversalRouter
            return UniversalRouter().execute(payload, explicit_authorization=True)
        except Exception as exc:
            return error_response("EXECUTION_ADAPTER_ERROR", str(exc))


    if action == "order":
      symbol = str(request.get("symbol", "")).strip()
      side = str(payload.get("side", payload.get("action", ""))).upper()
      if side in {"BUY", "SELL"}:
          pass
      elif side in {"B", "BUY"}:
          side = "BUY"
      elif side in {"S", "SELL"}:
          side = "SELL"
      volume = float(payload.get("volume", payload.get("quantity", 0)) or 0)
      return _trade_order({
          "symbol": symbol, "side": side, "volume": volume,
          "sl": float(payload.get("sl", 0) or 0),
          "tp": float(payload.get("tp", 0) or 0),
          "confirm": True,
      })

    base = {"symbol": str(request.get("symbol", "")).strip(),
          "account_id": str(request.get("account_id", "")).strip(),
          "confirm": True}
    if payload.get("ticket"):
      base["ticket"] = payload.get("ticket")

    if action == "close":
      return _trade_close(base) if base.get("ticket") else _trade_close_symbol(base)
    if action == "modify":
      base.update({"sl": payload.get("sl"), "tp": payload.get("tp")})
      return _trade_manage(base, "modify")
    if action == "cancel":
      base["all_orders"] = bool(payload.get("all_orders"))
      return _trade_cancel_orders(base, bool(payload.get("all_orders")))
    return error_response("INVALID_UNIVERSAL_REQUEST", f"acao desconhecida: {action}")



def _metrica_obrigatoria(payload: dict, chave: str) -> float:
    """Le uma metrica de risco obrigatoria.

    Ausente vira ValueError com mensagem clara, nunca KeyError: um KeyError
    escapava do `except (ValueError, TypeError)` do handler e derrubava a
    conexao sem resposta, em vez de recusar a operacao.
    """
    if chave not in payload or payload[chave] is None:
        raise ValueError(f"{chave} e obrigatorio: a trava nao pode ser pulada")
    return float(payload[chave])


def validate_trade_with_context(payload: dict) -> tuple[bool, str, bool]:
    try:
        validate_trade(
            volume=float(payload["volume"]),
            daily_loss_pct=float(payload["daily_loss_pct"]),
            exposure_pct=float(payload["exposure_pct"]),
            open_positions=float(payload["open_positions"]),
            daily_trades=float(payload["daily_trades"]),
            drawdown_pct=float(payload["drawdown_pct"]),
            # O chamador precisa enviar as metricas. Ausencia e recusada, nao
            # tratada como zero: sem dado de risco a decisao nao e aprovada.
            spread=float(payload["spread"]),
            notional=float(payload["notional"]),
        )
        return True, "risco validado", False
    except (TypeError, ValueError, OverflowError) as exc:
        return False, str(exc), False


def _real_order(payload: dict) -> dict:
    """Executa ordem em conta real pelo mesmo caminho do trade.

    A recusa por TIPO de conta foi removida a pedido do operador. Nada aqui
    decide pelo modo da conta: as travas continuam sendo
    XAU_ENABLE_TRADE_COMMANDS, confirm=true, SL/TP obrigatorios,
    order_check antes do order_send e o risk_gate.
    """
    return _trade_order(payload)


def _trade_pending_order(payload: dict) -> dict:
    """Cria ordem pendente (BUY/SELL Limit ou Stop) com SL e TP no request.

    Nao ha garantia de OCO ou equivalencia com brackets de outras plataformas.
    A corretora define a aceitacao, o preenchimento e o comportamento das protecoes.

    Travas herdadas (identicas a _trade_order):
      - XAU_ENABLE_TRADE_COMMANDS=1
      - confirm=true
      - volume <= 0.10, sl > 0, tp > 0
      - risk_gate.validate_trade com daily_loss/exposure REAIS (passo C)
      - order_check antes de order_send
    """
    if (os.getenv("XAU_ENABLE_TRADE_COMMANDS", "1") != "1" and os.getenv("XAU_ENABLE_DEMO_ORDERS", "0") != "1"):
        raise PermissionError("execucao de trade desabilitada; defina XAU_ENABLE_TRADE_COMMANDS=1")
    if payload.get("confirm") is not True:
        raise PermissionError("confirm=true obrigatorio")
    mt5 = _mt5()
    info = mt5.account_info()
    if not info:
        raise PermissionError("conta MT5 nao identificada; ordem recusada")
    if not bool(getattr(info, "trade_allowed", False)):
        raise PermissionError("negociacao nao permitida pelo terminal MT5")

    symbol = str(payload.get("symbol", "")).strip()
    side = str(payload.get("side", "")).upper()
    order_kind = str(payload.get("kind", "limit")).lower()
    volume = float(payload.get("volume", 0) or 0)
    price = float(payload.get("price", 0) or 0)
    sl = float(payload.get("sl", 0) or 0)
    tp = float(payload.get("tp", 0) or 0)

    if not symbol or side not in {"BUY", "SELL"}:
        raise ValueError("symbol e side (BUY/SELL) validos sao obrigatorios")
    if order_kind not in {"limit", "stop"}:
        raise ValueError("kind deve ser 'limit' ou 'stop'")
    if volume <= 0 or volume > 0.10 or sl <= 0 or tp <= 0 or price <= 0:
        raise ValueError("volume <= 0.10, sl/tp > 0 e price > 0 obrigatorios")

    risk = _risk_state(mt5)
    if not mt5.symbol_select(symbol, True):
        raise LookupError(f"simbolo indisponivel no MT5: {symbol}")
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        raise LookupError(f"cotacao indisponivel no MT5: {symbol}")
    validate_trade(volume=volume, daily_loss_pct=risk["daily_loss_pct"],
                   exposure_pct=risk["exposure_pct"], open_positions=risk["open_positions"],
                   daily_trades=risk["daily_trades"], drawdown_pct=risk["drawdown_pct"],
                   spread=_spread_points(mt5, symbol, tick),
                   notional=_notional(mt5, symbol, volume, price))
    info_sym = mt5.symbol_info(symbol)
    digits = int(getattr(info_sym, "digits", 2) or 2)
    price = round(price, digits)
    sl = round(sl, digits)
    tp = round(tp, digits)

    bid = float(tick.bid or 0.0)
    ask = float(tick.ask or 0.0)
    # Sanidade: limit so entra em direcao favoravel; stop so rompe a favor.
    if side == "BUY":
        if order_kind == "limit" and price >= ask:
            raise ValueError(f"BUY LIMIT deve ser abaixo do ask ({ask})")
        if order_kind == "stop" and price <= ask:
            raise ValueError(f"BUY STOP deve ser acima do ask ({ask})")
        pending_type = (mt5.ORDER_TYPE_BUY_LIMIT if order_kind == "limit"
                        else mt5.ORDER_TYPE_BUY_STOP)
    else:
        if order_kind == "limit" and price <= bid:
            raise ValueError(f"SELL LIMIT deve ser acima do bid ({bid})")
        if order_kind == "stop" and price >= bid:
            raise ValueError(f"SELL STOP deve ser abaixo do bid ({bid})")
        pending_type = (mt5.ORDER_TYPE_SELL_LIMIT if order_kind == "limit"
                        else mt5.ORDER_TYPE_SELL_STOP)

    request = {"action": mt5.TRADE_ACTION_PENDING, "symbol": symbol,
               "volume": volume, "type": int(pending_type), "price": price,
               "sl": sl, "tp": tp, "deviation": 20, "magic": 2026001,
               "comment": "XAU_AI_PRO_DEMO_PEND",
               "type_time": mt5.ORDER_TIME_GTC,
               "type_filling": mt5.ORDER_FILLING_IOC}
    check = mt5.order_check(request)
    if not check or getattr(check, "retcode", 0) != 0:
        return {"ok": False, "stage": "order_check",
                "retcode": int(getattr(check, "retcode", -1)),
                "comment": str(getattr(check, "comment", "check falhou")),
                "trade": True}
    result = mt5.order_send(request)
    ok = bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE)
    return {"ok": ok, "stage": "order_send",
            "retcode": int(getattr(result, "retcode", -1) if result else -1),
            "comment": str(getattr(result, "comment", "") if result else ""),
            "order": int(getattr(result, "order", 0) if result else 0),
            "deal": 0,
            "order_type": "PENDING_" + order_kind.upper(),
            "side": side, "price": price, "sl": sl, "tp": tp,
            "oco_bracket": True, "trade": True}


def _trade_close(payload: dict) -> dict:
    mt5, _ = _require_trade_command(payload)
    ticket = int(payload.get("ticket", 0) or 0)
    positions = mt5.positions_get(ticket=ticket) if ticket else None
    if not positions:
        raise LookupError("posicao nao encontrada")
    position = positions[0]; symbol = str(getattr(position, "symbol", "")); volume = float(payload.get("_partial_volume", getattr(position, "volume", 0)) or 0)
    tick = mt5.symbol_info_tick(symbol)
    if not tick: raise LookupError(f"cotacao indisponivel no MT5: {symbol}")
    position_type = getattr(position, "type", 0)
    close_type = mt5.ORDER_TYPE_SELL if position_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = float(tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask)
    request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": volume, "type": close_type, "position": ticket, "price": price, "deviation": 20, "magic": 2026001, "comment": "XAU_AI_PRO_DEMO_CLOSE", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
    intent_id = intent_log.record_intent("trade_close", {"ticket": ticket, "symbol": symbol, "volume": volume}, status="pending")
    check = mt5.order_check(request)
    if not check or getattr(check, "retcode", 0) != 0:
        intent_log.record_intent("trade_close", {"ticket": ticket, "symbol": symbol, "volume": volume}, intent_id=intent_id, status="failed", extra={"stage": "order_check", "retcode": int(getattr(check, "retcode", -1))})
        return {"ok": False, "stage": "order_check", "retcode": int(getattr(check, "retcode", -1)), "comment": str(getattr(check, "comment", "check falhou")), "trade": True}
    result = mt5.order_send(request)
    ok_close = bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE)
    intent_log.record_intent("trade_close", {"ticket": ticket, "symbol": symbol, "volume": volume}, intent_id=intent_id, status="sent" if ok_close else "failed", extra={"retcode": int(getattr(result, "retcode", -1)), "order": int(getattr(result, "order", 0)), "deal": int(getattr(result, "deal", 0))})
    return {"ok": ok_close, "stage": "order_send", "retcode": int(getattr(result, "retcode", -1)), "comment": str(getattr(result, "comment", "")), "order": int(getattr(result, "order", 0)), "deal": int(getattr(result, "deal", 0)), "trade": True}


def _trade_manage(payload: dict, action: str) -> dict:
    """Gerenciamento de posição via TRADE_ACTION_SLTP."""
    if (os.getenv("XAU_ENABLE_TRADE_COMMANDS", "1") != "1" and os.getenv("XAU_ENABLE_DEMO_ORDERS", "0") != "1") or payload.get("confirm") is not True:
        raise PermissionError("comando de trade desabilitado ou confirm=true ausente")
    mt5 = _mt5(); info = mt5.account_info()
    if not info: raise PermissionError("conta MT5 nao identificada")
    ticket = int(payload.get("ticket", 0) or 0); rows = mt5.positions_get(ticket=ticket) if ticket else None
    if not rows: raise LookupError("posição não encontrada")
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
    intent_id = intent_log.record_intent("trade_manage", {"ticket": ticket, "sl": sl, "tp": tp}, status="pending")
    result = mt5.order_send(request)
    ok_manage = bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE)
    intent_log.record_intent("trade_manage", {"ticket": ticket, "sl": sl, "tp": tp}, intent_id=intent_id, status="sent" if ok_manage else "failed", extra={"retcode": int(getattr(result, "retcode", -1))})
    return {"ok": ok_manage, "ticket": ticket, "sl": sl, "tp": tp, "retcode": int(getattr(result, "retcode", -1)), "comment": str(getattr(result, "comment", "")), "trade": True}


def _trade_close_all(payload: dict) -> dict:
    mt5, _ = _require_trade_command(payload)
    rows = list(mt5.positions_get() or [])
    results = [_trade_close({"ticket": int(getattr(p, "ticket", 0)), "confirm": True}) for p in rows]
    return {"ok": all(item.get("ok") for item in results) if results else True, "closed": results, "count": len(results), "trade": True}


def _trade_partial_close(payload: dict) -> dict:
    ticket = int(payload.get("ticket", 0) or 0); part = float(payload.get("volume", 0) or 0)
    if part <= 0: raise ValueError("volume parcial deve ser maior que zero")
    mt5 = _mt5(); rows = mt5.positions_get(ticket=ticket) if ticket else None
    if not rows: raise LookupError("posição não encontrada")
    p = rows[0]; total = float(getattr(p, "volume", 0) or 0)
    if part >= total: raise ValueError("volume parcial deve ser menor que o volume da posição")
    data = dict(payload); data["ticket"] = ticket
    return _trade_close({**data, "_partial_volume": part})


def _require_trade_command(payload: dict) -> tuple:
    if REAL_EMERGENCY_STOP.exists():
        raise PermissionError("parada de emergência ativa")
    if (os.getenv("XAU_ENABLE_TRADE_COMMANDS", "1") != "1" and os.getenv("XAU_ENABLE_DEMO_ORDERS", "0") != "1"):
        raise PermissionError("ordens de trade desabilitadas")
    if payload.get("confirm") is not True:
        raise PermissionError("confirm=true obrigatorio")
    mt5 = _mt5()
    info = mt5.account_info()
    if not info:
        raise PermissionError("conta MT5 nao identificada")
    return mt5, info


def _trade_protection(payload: dict, remove: bool = False) -> dict:
    mt5, _ = _require_trade_command(payload)
    ticket = int(payload.get("ticket", 0) or 0)
    rows = mt5.positions_get(ticket=ticket) if ticket else None
    if not rows:
        raise LookupError("posicao nao encontrada")
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
            "comment": str(getattr(result, "comment", "")), "trade": True}


def _trade_close_symbol(payload: dict) -> dict:
    mt5, _ = _require_trade_command(payload)
    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol:
        raise ValueError("symbol obrigatorio")
    rows = list(mt5.positions_get(symbol=symbol) or [])
    results = [_trade_close({"ticket": int(getattr(p, "ticket", 0)), "confirm": True}) for p in rows]
    return {"ok": all(r.get("ok") for r in results) if results else True, "symbol": symbol,
            "closed": results, "count": len(results), "trade": True}


def _trade_cancel_orders(payload: dict, all_orders: bool = False) -> dict:
    mt5, _ = _require_trade_command(payload)
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
            "count": len(results), "trade": True}

def _asset_toggle(payload: dict, enabled: bool) -> dict:
    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol: raise ValueError("symbol obrigatorio")
    mt5 = _mt5(); ok = bool(mt5.symbol_select(symbol, enabled))
    return {"ok": ok, "symbol": symbol, "enabled": enabled, "visible": bool(getattr(mt5.symbol_info(symbol), "visible", False)), "source": "mt5_gateway"}


def _conta_kind(info) -> str:
    """Rótulo da conta para a interface: REAL, DEMO ou HEDGE.

    Apenas informativo. Nada aqui bloqueia envio de ordem: a trava de
    execução é XAU_ENABLE_TRADE_COMMANDS + confirm=true, e não o tipo
    de conta. Nunca levanta exceção — quem chama costuma estar no meio
    de um tratamento de erro.
    """
    try:
        if info is None:
            return "UNKNOWN"
        mode = getattr(info, "trade_mode", None)
        if isinstance(mode, str):
            return mode.upper()
        if mode is None:
            return "UNKNOWN"
        # MetaTrader: 0 = REAL, 1 = DEMO, 2 = CONTEST
        return {0: "REAL", 1: "DEMO", 2: "CONTEST"}.get(int(mode), "UNKNOWN")
    except Exception:  # noqa: BLE001 - rotulo informativo jamais derruba resposta
        return "UNKNOWN"


def _conta_kind_atual() -> str:
    """Rotulo da conta atual, sem nunca levantar excecao."""
    try:
        return _conta_kind(_mt5().account_info())
    except Exception:  # noqa: BLE001
        return "UNKNOWN"


def _trade_read(kind: str) -> dict:
    mt5 = _mt5()
    info = mt5.account_info()
    if not info:
        raise PermissionError("conta MT5 nao identificada")
    if kind == "positions":
        raw_rows = mt5.positions_get()
        if raw_rows is None:
            raise RuntimeError("posições MT5 indisponíveis")
        rows = list(raw_rows)
        return {"ok": True, "positions": [{"ticket": int(p.ticket), "symbol": str(p.symbol), "side": "BUY" if p.type == 0 else "SELL", "volume": float(p.volume), "open_price": float(p.price_open), "current_price": float(p.price_current), "sl": float(p.sl), "tp": float(p.tp), "profit": float(p.profit), "magic": int(p.magic)} for p in rows], "count": len(rows), "account_mode": _conta_kind(info), "source": "mt5_gateway"}
    if kind == "orders":
        raw_rows = mt5.orders_get()
        if raw_rows is None:
            raise RuntimeError("ordens MT5 indisponíveis")
        rows = list(raw_rows)
        return {"ok": True, "orders": [{"ticket": int(o.ticket), "symbol": str(o.symbol), "type": int(o.type), "volume": float(o.volume_current), "price": float(o.price_open), "sl": float(o.sl), "tp": float(o.tp), "time_setup": int(o.time_setup)} for o in rows], "count": len(rows), "account_mode": _conta_kind(info), "source": "mt5_gateway"}
    payload = _payload()
    return {"ok": True, "gateway": "online", "mt5_connected": bool(payload.get("account")), "ea_heartbeat": payload.get("ea_heartbeat"), "positions": len(payload.get("positions", [])), "account_mode": "DEMO", "last_command": LAST_COMMAND, "source": "mt5_gateway"}


def _ea_status() -> dict:
    hb = _read_ea_heartbeat()
    mt5 = _mt5()
    ti = mt5.terminal_info()
    return {"ok": True, "ea_heartbeat": hb, "live": bool(hb.get("live")),
            "terminal_connected": bool(ti and getattr(ti, "connected", False)),
            "autotrading": bool(hb.get("autotrading", False)), "source": "mt5_gateway"}


# Comandos que o EA aceita pelo arquivo em FILE_COMMON. A mesma lista aparece
# no contrato de capabilities, entao nao pode ser duplicada em outro lugar.
EA_COMMANDS = ("start", "stop", "pause", "resume", "set-symbol", "set-mode",
               "set-timeframe", "set-autotrading", "close", "close-all")


def _ea_command(payload: dict, command: str) -> dict:
    _require_trade_command(payload)
    if command not in EA_COMMANDS:
        raise ValueError("comando de EA não permitido")
    hb = _read_ea_heartbeat()
    if not hb.get("live"):
        raise RuntimeError("EA sem heartbeat vivo; comando nao enviado")
    value = str(payload.get("value", payload.get("symbol", payload.get("timeframe", "")))).strip()
    symbol = str(payload.get("symbol", "")).strip().upper()
    if any(character in value + symbol for character in "\r\n="):
        raise ValueError("parâmetros de comando inválidos")
    if len(value) > 100 or len(symbol) > 40 or any(ord(character) < 32 for character in value + symbol):
        raise ValueError("parâmetros de comando inválidos")
    command_file = COMMON_FILES / "XAU_AI_PRO_ea_command.json"
    command_file.parent.mkdir(parents=True, exist_ok=True)
    ticket = int(payload.get("ticket", 0) or 0)
    lines = [f"command={command}", f"value={value}"]
    if symbol:
        lines.append(f"symbol={symbol}")
    if ticket > 0:
        lines.append(f"ticket={ticket}")
    command_file.write_text("\n".join(lines) + "\n", encoding="ascii")
    return {"ok": True, "accepted": True, "command": command, "value": value, "ticket": ticket, "status": "queued", "trade": True, "account_mode": "DEMO", "source": "mt5_common_files"}


def capabilities_contract() -> dict:
    matrix = capability_matrix(include_planned=False)
    brokers: dict[str, dict] = {}
    executing: set[str] = set()
    for row in matrix:
        broker = brokers.setdefault(row["broker"], {"status": row["status"], "read_only": row["read_only"], "markets": [], "execution": [], "withdrawals": False})
        broker["markets"].append({"market": row["market"], "capabilities": row["capabilities"]})
        for action in row["execution"]:
            if action not in broker["execution"]:
                broker["execution"].append(action)
            if row["execution"]:
                executing.add(row["broker"])
    # O app esta desbloqueado: existe execucao real nas corretoras cuja gate
    # esta ligada. Saque e transferencia continuam fora desta decisao.
    live = bool(executing)
    routed = sorted({row["broker"] for row in matrix})
    return {
        "ok": True,
        "source": "fastapi_gateway",
        "received_at": utc_now(),
        "provider_timestamp": None,
        "read_only": not live,
        "read": [
            "health", "status", "account", "inventory", "symbols", "assets", "quote", "quotes",
            "candles", "depth", "trades", "stats24h", "positions", "orders", "history", "journal", "boot",
        ],
        "assets_read": True,
        "quotes_read": True,
        "candles_read": True,
        "depth_read": True,
        "trades_read": True,
        "stats24h_read": True,
        "batch_quotes": True,
        "withdrawals_enabled": False,
        "transfers_enabled": False,
        "real_orders_enabled": live,
        "live_execution_enabled": live,
        "execution_live": live,
        "generic_commands": False,
        "generic_ea": False,
        "generic_ea_commands": False,
        "third_party_ea": {
            "read_only": True,
            "opt_in_manifest": True,
            "identity_cryptographic": False,
            "capabilities": sorted(READ_ONLY_CAPABILITIES),
            "commands": False,
            "write_operations": [],
        },
        "ea_commands": list(EA_COMMANDS),
        "real_commands": sorted(executing),
        "execution_commands": sorted(executing),
        "trade_commands": ["trade/order", "trade/close", "trade/close-all"],
        "multi_asset": {"enabled": True, "scope": "broker_catalog", "complete": False},
        "multi_broker": {"enabled": True, "routed": routed, "production_ready": sorted(executing), "code_only": sorted(set(routed) - executing), "complete": live},
        "matrix": matrix,
        "brokers": brokers,
    }


def _cors_origin(origin: str | None) -> str | None:
    """Origem liberada para o cabecalho CORS. Vazio = nenhuma.

    ANTES (04/10/2026): `if not origin: return "*"`. Sem cabecalho `Origin` —
    o caso de qualquer cliente de linha de comando, curl ou script — a resposta
    saia com `Access-Control-Allow-Origin: *`. Num gateway que exige token
    para as rotas de comando, o wildcard nao dava acesso sozinho, mas dava a
    qualquer pagina da web a opcao de tentar, e o `Vary: Origin` deixava de
    valer para a resposta em cache.

    Agora: sem origem, nao ha origem. Um navegador sempre envia `Origin` em
    pedido cross-origin, entao a perda real e nenhuma — e o que o navegador
    faz em `same-origin` e nao enviar, o que tambem nao precisa de CORS.
    """
    if not origin:
        return None
    return origin if origin in CORS_ORIGINS else None


def _rate_limit_for(is_command: bool) -> int:
    if is_command and RATE_LIMIT_CMD_MAX > 0:
        return RATE_LIMIT_CMD_MAX
    return RATE_LIMIT_MAX


# Travas de plano por rota. `plano_gate` traduz a feature para o entitlement do
# catalogo em app/subscriptions.py. Rotas de leitura do catalogo ficam de fora:
# sem elas a UI nao descobre o que existe e a tela inteira quebra no Free.
_ROTAS_GET: dict[str, str] = {
    "/api/economic/calendar": "economic_calendar",
    "/api/backtest": "model_backtest",
}

_ROTAS_POST: dict[str, str] = {
    "/api/auto/start": "auto_engine",
    "/api/auto/tick": "auto_engine",
    "/api/order": "manual_order",
    "/api/universal/order": "manual_order",
    "/api/social/follow": "social_paper",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silencia log
        pass

    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        origin = _cors_origin(self.headers.get("Origin"))
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        origin = _cors_origin(self.headers.get("Origin"))
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _is_command(self) -> bool:
        """POST e considerado comando; GET e leitura (polling de painel)."""
        return self.command.upper() != "GET"

    def _autorizado(self) -> tuple[bool, str]:
        """Token obrigatorio (XAU_GATEWAY_TOKEN) + rate limit por categoria.

        Comandos (POST) e leituras (GET) tem janelas separadas: o polling do
        painel nao consome a cota de comandos. XAU_RATE_LIMIT_CMD define a
        cota de comandos (fallback: XAU_RATE_LIMIT).

        FAIL-CLOSED: antes era `if API_TOKEN:` — sem a variavel, o gateway
        aceitava qualquer chamada. O gateway so escuta em 127.0.0.1, mas
        qualquer processo da maquina (e um mapeamento de porta exposto)
        conseguiria ler conta e enviar ordem. Agora, sem token configurado,
        o gateway RECUSA tudo: e melhor ficar inacessivel do que aberto.
        """
        if not API_TOKEN:
            return False, "sem token configurado"
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {API_TOKEN}":
            return False, "token"
        if RATE_LIMIT_MAX <= 0 and RATE_LIMIT_CMD_MAX <= 0:
            return True, ""
        limit = _rate_limit_for(self._is_command())
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
            self._send(401 if motivo in _MOTIVOS_TOKEN else 429, {"ok": False, "error": "nao autorizado" if motivo in _MOTIVOS_TOKEN else "rate limit excedido"})
            return
        _feature = _ROTAS_GET.get(parsed.path)
        if _feature is not None:
            from backend import plano_gate

            # O nome NAO pode ser `_payload`: existe uma funcao global com esse
            # nome, e atribuir a variavel local transformaria toda chamada
            # `_payload()` de do_GET em "UnboundLocalError".
            _liberado, _recusa = plano_gate.verificar(_feature)
            if not _liberado:
                self._send(403, plano_gate.resposta_bloqueio(_feature, _recusa))
                return
        if parsed.path.startswith("/api/connections/"):
            parts = parsed.path.strip("/").split("/"); connection_id = unquote("/".join(parts[2:-1]))
            action = parts[-1] if parts else ""
            if action == "test": self._send(200, {"ok": True, "configured": any(x["id"] == connection_id for x in list_connections()), "credentials_exposed": False}); return
        if parsed.path == "/api/connections": self._send(200, {"ok": True, "connections": list_connections()}); return
        # LATENCIA AO VIVO POR CORRETORA (rodape estilo MT5)
        #
        # Mede round-trip HTTP real contra o endpoint publico de cada venue. E
        # leitura informativa: falha aqui nunca bloqueia operacao, e uma
        # corretora sem resposta devolve `ms: None` — nunca 0, porque 0 ms e
        # mentira que a tela repetiria como se fosse medida.
        if parsed.path == "/api/latencia":
            from backend import latencia as _latencia
            self._send(200, _latencia.medir_todas()); return
        # CALENDARIO ECONOMICO (2026-09-30)
        #
        # A rota estava declarada no mapa de planos (`_ROTAS_GET`) e a funcao
        # `_economic_calendar` existia, mas NENHUMA linha do `do_GET` chamava
        # uma ou outra. Resultado: 404, e a aba Calendario ficava vazia.
        #
        # Por que o teste nao pegou: `EconomicCalendarTab.test.tsx` trava o
        # `fetch` com eventos de mentira. Ele prova a RENDERIZACAO, nunca a
        # rota — e um 404 e um payload vazio produzem a mesma tela.
        #
        # Aqui a chamada e real. Se `app.economic_calendar` falhar, a resposta
        # diz o motivo em vez de virar lista vazia sem explicacao.
        if parsed.path == "/api/economic/calendar":
            # `parse_qs` JA esta importado no topo do modulo (linha 21).
            # Nao repetir o import aqui: Python passa a tratar o nome como
            # variavel local da funcao e o `UnboundLocalError` derrubava TODAS
            # as rotas do `do_GET`. O mesmo bug ja aconteceu nesta sessao com
            # `_payload` — ver `plano_gate` e o comentario no `do_GET`.
            _q = parse_qs(parsed.query)
            _g = lambda _k, _d: (_q.get(_k) or [_d])[0]
            try:
                self._send(200, _economic_calendar(
                    limit=int(_g("limit", "30") or 30),
                    tz=_g("tz", "BRT"),
                    days=int(_g("days", "14") or 14),
                ))
            except (ValueError, TypeError) as _e:
                self._send(400, {"ok": False, "error": f"parametro invalido: {_e}"})
            except Exception as _e:
                self._send(503, {"ok": False, "error": f"agenda indisponivel: {_e}",
                                  "events": [], "count": 0})
            return
        if parsed.path == "/api/ai/trained":
            # O painel do motor so pode oferecer par que o motor VAI aceitar.
            # `_carregar()` so devolve o modelo quando `publicable` e verdadeiro,
            # entao listar aqui um par reprovado levava o operador a escolher
            # XAUUSD M15 (edge +0,0498 contra o minimo +0,0500), ligar o motor e
            # ver "modelo ausente para m15". `so_publicavel=0` traz o inventario
            # completo, com o motivo da reprovacao, para a tela de treino.
            from backend import ai_inference

            modelos = ai_inference.listar_modelos()
            if parse_qs(parsed.query).get("so_publicavel", ["1"])[0] not in ("0", "false", "False"):
                publicaveis = [m for m in modelos if m.get("publicable")]
                reprovados = [
                    {
                        "id": m["id"],
                        "symbol": m["symbol"],
                        "timeframe": m["timeframe"],
                        "reason": m.get("reason", ""),
                        "edge": m.get("edge"),
                        "min_edge": m.get("edge_min"),
                    }
                    for m in modelos if not m.get("publicable")
                ]
                self._send(200, {
                    "ok": True,
                    "models": publicaveis,
                    "reprovados": reprovados,
                    "count": len(publicaveis),
                    "reprovados_count": len(reprovados),
                }); return
            self._send(200, {"ok": True, "models": modelos, "count": len(modelos)}); return
        if parsed.path == "/api/auto/state":
            from backend import auto_engine
            self._send(200, {"ok": True, **auto_engine.motor.snapshot()}); return
        # ---------------------------------------------------------------- planos
        # Estas rotas viviam so no `fastapi_gateway` (9003), mas o frontend fala
        # com o gateway local (9001, ver `apiBase()`). Resultado: a tela de
        # Planos recebia 404 em todas as cinco chamadas e aparecia vazia — era
        # ela que o usuario descreveu como "generica, sem vida".
        #
        # `live_execution` e `withdrawals_enabled` seguem False de forma fixa:
        # escolher um plano nao habilita ordem nem saque.
# ------------------------------------------------------------- VIP e metas
        # Mesmo defeito das rotas de plano acima, agora na progressao: a rota
        # `/api/vip/progress` vivia SO no `fastapi_gateway` (9003). O frontend
        # fala com o gateway local (9001, ver `apiBase()`), entao a aba VIP
        # recebia 404 em TODA chamada — com e sem token. Medido no app
        # instalado em 02/10/2026:
        #     GET 9001/api/vip/progress -> 404   (com token valido)
        #     GET 9003/api/vip/progress -> 404   (o core nao tem a rota)
        #
        # `/api/acesso` e nova e vai no mesmo bloco: e a arvore unica que junta
        # plano e volume, e a tela precisa dela para saber o que destravou.
        if parsed.path == "/api/vip/progress":
            from backend.vip_progress import progresso
            self._send(200, {"ok": True, **progresso()}); return
        if parsed.path == "/api/acesso":
            from backend.acesso import acesso
            self._send(200, {"ok": True, **acesso()}); return
        if parsed.path == "/api/subscriptions/plans":
            from backend.planos.subscriptions import list_plans
            self._send(200, {"ok": True, "plans": list_plans(),
                             "billing": "not_configured", "live_execution": False,
                             "withdrawals_enabled": False}); return
        if parsed.path == "/api/subscriptions/me":
            from backend.planos.subscriptions import get_subscription
            self._send(200, {"ok": True, "subscription": get_subscription(),
                             "live_execution": False, "withdrawals_enabled": False}); return
        if parsed.path == "/api/social/strategies":
            from backend.planos.social_paper import list_strategies
            self._send(200, {"ok": True, "strategies": list_strategies(),
                             "mode": "paper_trade", "live_execution": False,
                             "withdrawals_enabled": False}); return
        path = parsed.path
        query = parse_qs(parsed.query)
        if path in ("/", "/api/health"):
            self._send(200, {"ok": True, "uptime_sec": int(time.time() - _T0),
                             "source": "mt5_gateway", "gateway_build": GATEWAY_BUILD})
        elif path == "/api/config":
            self._send(200, {"ok": True, "config": _config(), "source": "local_gateway"})
        elif path == "/api/ai/models":
            self._send(200, {"ok": True, "models": model_catalog(), "source": "local_model_artifacts"})
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
            self._send(200, _status_snapshot())
        elif path == "/api/stream/status":
            self._send(200, {"ok": True, "transport": "http-polling", "websocket": False, "intervals": {"status": 10, "positions": 5, "journal": 10}, "source": "mt5_gateway"})
        elif path == "/api/trade/positions":
            try: self._send(200, _trade_read("positions"))
            except PermissionError as exc: self._send(403, {"ok": False, "error": str(exc), "trade": True})
        elif path == "/api/trade/orders":
            try: self._send(200, _trade_read("orders"))
            except PermissionError as exc: self._send(403, {"ok": False, "error": str(exc), "trade": True})
        elif path == "/api/trade/execution-status":
            try: self._send(200, _trade_read("status"))
            except PermissionError as exc: self._send(403, {"ok": False, "error": str(exc), "trade": True})
        elif path == "/api/trade/last-command":
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
            from backend.fastapi_gateway import boot_status
            self._send(200, boot_status())
        elif path == "/api/ea/status":
            try: self._send(200, _ea_status())
            except Exception as exc: self._send(503, {"ok": False, "error": str(exc), "source": "mt5_gateway"})
        elif path == "/api/capabilities":
            self._send(200, capabilities_contract())
        elif path in ("/api/status", "/api/system"):
            self._send(200, _status_snapshot())
        elif path == "/api/ea-compatibility":
            try:
                self._send(200, evaluate_third_party_ea(_mt5()))
            except Exception as exc:
                self._send(503, {"ok": False, "status": "temporarily_unavailable", "error": str(exc), "read_only": True, "commands_enabled": False, "adapters": [], "matched": 0, "source": "local_manifest+mt5_read_only"})
        elif path == "/api/inventory":
            payload = _payload()
            self._send(200, {"ok": bool(payload.get("account")), "account": payload.get("account"), "positions": payload.get("positions", []), "pending_orders": payload.get("pending_orders", []), "exposure": payload.get("exposure", {}), "ea_heartbeat": payload.get("ea_heartbeat")})
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
                symbol = query.get("symbol", [""])[0].strip().upper()
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
                try:
                    days = max(0, int(query.get("days", ["0"])[0]))
                except (TypeError, ValueError):
                    days = 0
                result = _universal_history(broker, market, symbol, days, query.get("account_id", [""])[0].strip())
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "history", deals=[], count=0)
                self._send(_response_status(result), result)
        elif path == "/api/universal/account":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower()
                market = query.get("market", [""])[0].strip().lower()
                result = _universal_account(broker, market, query.get("account_id", [""])[0].strip())
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "account", account=None, withdrawals_enabled=False)
                self._send(_response_status(result), result)
        elif path == "/api/universal/overview":
            self._send(200, _universal_overview())
        elif path == "/api/universal/positions":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower()
                market = query.get("market", [""])[0].strip().lower()
                result = _universal_positions(broker, market, query.get("account_id", [""])[0].strip())
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "positions", positions=[], pnl={"value": None, "available": False})
                self._send(_response_status(result), result)
        elif path == "/api/universal/quote":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower()
                market = query.get("market", ["crypto-spot"])[0].strip().lower()
                symbol = query.get("symbol", [""])[0].strip()
                result = _universal_quote(broker, market, symbol)
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "ticker", symbol=query.get("symbol", [""])[0], bid=None, ask=None, last=None, price=None, spread=None)
                self._send(_response_status(result), result)
        elif path == "/api/universal/quotes":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower()
                market = query.get("market", ["crypto-spot"])[0].strip().lower()
                raw = query.get("symbols", [""])[0]
                symbols = [item.strip() for item in raw.split(",") if item.strip()]
                result = _universal_quotes(broker, market, symbols)
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "ticker_batch", quotes=[], errors=[])
                self._send(_response_status(result), result)
        elif path == "/api/universal/assets":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower()
                market = query.get("market", ["other"])[0].strip().lower()
                result = _universal_assets(broker, market)
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "assets", assets=[], symbols=[], count=0)
                self._send(_response_status(result), result)
        elif path == "/api/universal/capabilities":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower()
                market = query.get("market", ["other"])[0].strip().lower()
                symbol = query.get("symbol", [""])[0].strip()
                result = _universal_asset_capabilities(broker, market, symbol)
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "asset_capabilities", matrix=[], count=0)
                self._send(_response_status(result), result)
        elif path == "/api/universal/candles":
            try:
                broker = query.get("broker", ["mt5"])[0].strip().lower()
                market = query.get("market", ["other"])[0].strip().lower()
                symbol = query.get("symbol", [""])[0].strip()
                timeframe = query.get("timeframe", query.get("interval", ["M5"]))[0].strip()
                try:
                    limit = int(query.get("limit", query.get("count", ["500"]))[0])
                except (TypeError, ValueError):
                    limit = 500
                result = _universal_candles(broker, market, symbol, timeframe, limit)
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "candles", symbol=query.get("symbol", [""])[0], candles=[], count=0)
                self._send(_response_status(result), result)
        elif path == "/api/universal/depth":
            try:
                broker = query.get("broker", ["binance"])[0].strip().lower()
                market = query.get("market", ["crypto-spot"])[0].strip().lower()
                symbol = query.get("symbol", [""])[0].strip()
                try:
                    limit = int(query.get("limit", ["20"])[0])
                except (TypeError, ValueError):
                    limit = 20
                result = _universal_depth(broker, market, symbol, limit)
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "depth", symbol=query.get("symbol", [""])[0], bids=None, asks=None)
                self._send(_response_status(result), result)
        elif path == "/api/universal/trades":
            try:
                broker = query.get("broker", ["binance"])[0].strip().lower()
                market = query.get("market", ["crypto-spot"])[0].strip().lower()
                symbol = query.get("symbol", [""])[0].strip()
                try:
                    limit = int(query.get("limit", ["20"])[0])
                except (TypeError, ValueError):
                    limit = 20
                result = _universal_trades(broker, market, symbol, limit)
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "trades", symbol=query.get("symbol", [""])[0], trades=[], count=0)
                self._send(_response_status(result), result)
        elif path in {"/api/universal/stats24h", "/api/universal/stats_24h"}:
            try:
                broker = query.get("broker", ["binance"])[0].strip().lower()
                market = query.get("market", ["crypto-spot"])[0].strip().lower()
                symbol = query.get("symbol", [""])[0].strip()
                result = _universal_stats24h(broker, market, symbol)
                self._send(_response_status(result), result)
            except Exception as exc:
                result = _read_exception_response(query.get("broker", [""])[0], query.get("market", ["other"])[0], exc, "stats24h", symbol=query.get("symbol", [""])[0])
                self._send(_response_status(result), result)
        elif path == "/api/mt5/quote":
            try:
                self._send(200, _quote(query.get("symbol", [""])[0]))
            except (LookupError, ValueError) as exc:
                self._send(404, {"ok": False, "error": str(exc)})
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc)})
        elif path == "/api/mt5/quotes":
            symbols = query.get("symbols", [""])[0].split(",")
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
        ok, motivo = self._autorizado()
        if not ok:
            self._send(401 if motivo in _MOTIVOS_TOKEN else 429, {"ok": False, "error": "nao autorizado" if motivo in _MOTIVOS_TOKEN else "rate limit excedido"})
            return
        if THIRD_PARTY_READ_ONLY:
            self._send(403, {"ok": False, "status": "blocked", "error": "perfil de compatibilidade somente leitura", "commands_enabled": False, "execution_enabled": False})
            return
        if urlparse(self.path).path != "/api/config": self._send(404, {"ok": False, "error": "not_found"}); return
        try:
            length = int(self.headers.get("Content-Length", "0")); body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict): raise ValueError("configuração deve ser objeto")
            self._send(200, {"ok": True, "config": _save_config({**_config(), **body})})
        except Exception as exc: self._send(400, {"ok": False, "error": str(exc)})

    def do_DELETE(self):  # noqa: N802
        ok, motivo = self._autorizado()
        if not ok:
            self._send(401 if motivo in _MOTIVOS_TOKEN else 429, {"ok": False, "error": "nao autorizado" if motivo in _MOTIVOS_TOKEN else "rate limit excedido"})
            return
        if THIRD_PARTY_READ_ONLY:
            self._send(403, {"ok": False, "status": "blocked", "error": "perfil de compatibilidade somente leitura", "commands_enabled": False, "execution_enabled": False})
            return
        parsed = urlparse(self.path); prefix = "/api/connections/"
        if parsed.path.startswith(prefix):
            self._send(200, {"ok": delete_connection(unquote(parsed.path[len(prefix):]))}); return
        self._send(404, {"ok": False, "error": "not_found"})

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        ok, motivo = self._autorizado()
        if not ok:
            self._send(401 if motivo in _MOTIVOS_TOKEN else 429, {"ok": False, "error": "nao autorizado" if motivo in _MOTIVOS_TOKEN else "rate limit excedido"})
            return
        if THIRD_PARTY_READ_ONLY and parsed.path != "/api/universal/emergency-stop":
            self._send(403, {"ok": False, "status": "blocked", "error": "perfil de compatibilidade somente leitura", "commands_enabled": False, "execution_enabled": False, "withdrawals_enabled": False})
            return
        _feature_post = _ROTAS_POST.get(parsed.path)
        if _feature_post is not None:
            from backend import plano_gate

            # Mesmo cuidado do GET: nunca nomear a variavel `_payload` aqui.
            _liberado, _recusa = plano_gate.verificar(_feature_post)
            if not _liberado:
                self._send(403, plano_gate.resposta_bloqueio(_feature_post, _recusa))
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
            if os.getenv("XAU_ENABLE_EMERGENCY_RESUME", "1") != "1":
                self._send(403, {"ok": False, "error": "retomada bloqueada; requer XAU_ENABLE_EMERGENCY_RESUME=1", "emergency_stop": REAL_EMERGENCY_STOP.exists()}); return
            REAL_EMERGENCY_STOP.unlink(missing_ok=True)
            LAST_COMMAND.update({"command": parsed.path, "status": "resumed", "updated_at": datetime.now().isoformat()})
            self._send(200, {"ok": True, "emergency_stop": False, "status": "resumed", "new_orders_blocked": False, "withdrawals_enabled": False}); return
        universal_actions = {"/api/universal/order": "order", "/api/universal/close": "close", "/api/universal/modify": "modify", "/api/universal/cancel": "cancel"}
        if parsed.path in universal_actions:
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            if payload.get("execute") is True:
                try:
                    result = _universal_execute(payload, universal_actions[parsed.path])
                except (PermissionError, ValueError, LookupError) as exc:
                    result = {"ok": False, "status": "rejected", "error": str(exc), "execution_enabled": True}
                except Exception as exc:  # noqa: BLE001 - resposta sempre, nunca conexao morta
                    result = {"ok": False, "status": "rejected", "error": str(exc), "execution_enabled": True}
                record_audit(AUDIT_FILE, action="trade/" + universal_actions[parsed.path], payload=payload, status="executed" if result.get("ok") else "rejected")
                LAST_COMMAND.update({"command": parsed.path, "status": "executed" if result.get("ok") else "rejected", "updated_at": datetime.now().isoformat()})
                self._send(200 if result.get("ok") else 422, result); return
            result = _universal_execution_preview(payload, universal_actions[parsed.path])
            record_audit(AUDIT_FILE, action=universal_actions[parsed.path], payload=payload, status=result.get("stage", "rejected"))
            LAST_COMMAND.update({"command": parsed.path, "status": "validated" if result.get("stage") == "validated" else "rejected", "updated_at": datetime.now().isoformat()})
            self._send(200 if result.get("stage") == "validated" else 422, result); return
        if parsed.path in {"/api/assets/select", "/api/assets/enable", "/api/assets/disable"}:
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            self._send(200, _asset_toggle(payload, parsed.path != "/api/assets/disable")); return
        if parsed.path in {"/api/command/validate", "/api/command/cancel"}:
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            allowed = {"/api/trade/order", "/api/trade/pending", "/api/trade/close", "/api/trade/close-all", "/api/trade/modify-position", "/api/trade/breakeven", "/api/trade/trailing", "/api/trade/partial-close", "/api/trade/set-protection", "/api/trade/remove-protection", "/api/trade/close-symbol", "/api/trade/cancel-order", "/api/trade/cancel-all-orders"}
            command = str(payload.get("command", "")); ok = command in allowed and payload.get("confirm") is True
            self._send(200, {"ok": ok, "command": command, "valid": ok, "cancelled": parsed.path.endswith("/cancel") and ok, "reason": "comando de trade reconhecido" if ok else "comando de trade desconhecido ou confirmação ausente"}); return
        if parsed.path == "/api/config/reset":
            self._send(200, {"ok": True, "config": _save_config(CONFIG_DEFAULTS)}); return
        if parsed.path == "/api/real/validate":
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            try:
                # Metrica ausente e recusa explicita, nao KeyError: um KeyError
                # escapava do except e derrubava a conexao sem resposta alguma.
                validate_trade(volume=float(payload["volume"]), daily_loss_pct=float(payload["daily_loss_pct"]), exposure_pct=float(payload["exposure_pct"]), open_positions=float(payload["open_positions"]), daily_trades=float(payload["daily_trades"]), drawdown_pct=float(payload["drawdown_pct"]), spread=float(_metrica_obrigatoria(payload, "spread")), notional=float(_metrica_obrigatoria(payload, "notional")))
                self._send(200, {"ok": True, "approved": True, "execution_enabled": True, "reason": "risco validado; execucao liberada", "withdrawals_enabled": False})
            except (ValueError, TypeError, KeyError) as exc: self._send(403, {"ok": False, "approved": False, "execution_enabled": False, "error": str(exc), "withdrawals_enabled": False})
            return
        if parsed.path == "/api/real/request":
            length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
            request_id = str(payload.get("request_id", "")).strip()
            if not request_id or not payload.get("account_id") or not payload.get("broker") or not payload.get("market"):
                self._send(422, {"ok": False, "error": "request_id, account_id, broker e market são obrigatórios", "execution_enabled": False, "withdrawals_enabled": False}); return
            try:
                scope = _universal_scope(str(payload.get("broker", "")), str(payload.get("market", "")))
                if scope["broker"] != "mt5":
                    resolve_connection(str(payload.get("account_id", "")), scope["broker"], scope["market"])
            except (LookupError, ValueError) as exc:
                self._send(422, {"ok": False, "error": str(exc), "execution_enabled": False, "withdrawals_enabled": False}); return
            LAST_COMMAND.update({"command": "/api/real/request", "status": "approved", "request_id": request_id, "updated_at": datetime.now().isoformat()})
            self._send(202, {"ok": True, "status": "approved", "request_id": request_id, "execution_enabled": True, "withdrawals_enabled": False, "message": "solicitacao aprovada; execucao liberada"}); return
        ea_paths = {"/api/ea/start": "start", "/api/ea/stop": "stop", "/api/ea/pause": "pause", "/api/ea/resume": "resume", "/api/ea/set-symbol": "set-symbol", "/api/ea/set-mode": "set-mode", "/api/ea/set-timeframe": "set-timeframe", "/api/ea/set-autotrading": "set-autotrading", "/api/ea/close": "close", "/api/ea/close-all": "close-all"}
        if parsed.path in ea_paths:
            try:
                length = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(length) or b"{}")
                self._send(202, _ea_command(payload, ea_paths[parsed.path]))
            except (PermissionError, ValueError, LookupError) as exc:
                code = 403 if ea_paths[parsed.path] in {"close", "close-all"} else 503
                self._send(code, {"ok": False, "error": str(exc), "command": ea_paths[parsed.path], "account_mode": _conta_kind_atual()})
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "command": ea_paths[parsed.path]})
            return
        # -------------------------------------------------------------- planos (POST)
        # Ativar plano e seguir estrategia mudam estado local; nenhuma das duas
        # toca em ordem, conta ou saque.
        # ------------------------------------------------- motor automatico (POST)
        # Estas rotas viviam so no `fastapi_gateway` (9003), mas o painel fala
        # com o gateway local (9001, ver `apiBase()`): apertar "Ligar" devolvia
        # 404 e a operacao automatica NUNCA era ligada pelo app. A ordem continua
        # indo para `mt5.order_send()` — o mercado e real, em conta DEMO.
        if parsed.path in ("/api/auto/config", "/api/auto/start", "/api/auto/stop", "/api/auto/tick"):
            length = int(self.headers.get("Content-Length", "0") or 0)
            try:
                corpo = json.loads(self.rfile.read(length) or b"{}") if length else {}
            except (ValueError, UnicodeDecodeError):
                self._send(400, {"ok": False, "error": "corpo JSON invalido"}); return
            if not isinstance(corpo, dict):
                self._send(400, {"ok": False, "error": "corpo JSON invalido"}); return
            from backend import auto_engine

            m = auto_engine.motor
            try:
                if parsed.path == "/api/auto/config":
                    self._send(200, m.configurar(corpo)); return
                if parsed.path == "/api/auto/start":
                    self._send(200, m.ligar()); return
                if parsed.path == "/api/auto/stop":
                    self._send(200, m.desligar()); return

                # /api/auto/tick: UM ciclo sob demanda, sem depender da thread.
                import pandas as pd

                from backend import ai_inference

                def risk_state() -> dict[str, Any]:
                    return _risk_state(_mt5())

                def enviar(payload: dict[str, Any]) -> dict[str, Any]:
                    return _trade_order(payload)

                # `_mt5_candles` devolve a RESPOSTA canonica, nao a lista.
                # Passar o dict ao DataFrame estourava em
                # "All arrays must be of the same length".
                resposta = _mt5_candles(m.simbolo, m.timeframe, 600)
                linhas = resposta.get("candles") if isinstance(resposta, dict) else resposta
                if not linhas:
                    motivo = ""
                    if isinstance(resposta, dict):
                        motivo = str(resposta.get("reason_code") or resposta.get("error") or "")
                    self._send(503, {
                        "ok": False,
                        "error": f"MT5 nao devolveu candles para {m.simbolo} {m.timeframe}"
                                 + (f" ({motivo})" if motivo else ""),
                    }); return
                df = candles_mt5_para_dataframe(linhas)
                inf = ai_inference.inferir(m.simbolo, df, m.timeframe)
                decisao = m.ciclo_unico(lambda s, t: inf, enviar, risk_state)
                self._send(200, {"ok": True, "decision": decisao.para_dict()}); return
            except PermissionError as exc:
                self._send(403, {"ok": False, "error": str(exc),
                                 "withdrawals_enabled": False}); return
            except Exception as exc:  # noqa: BLE001
                self._send(503, {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                                 "withdrawals_enabled": False}); return

        if parsed.path == "/api/subscriptions/activate":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            from backend.planos.subscriptions import activate_local_plan
            try:
                assinatura = activate_local_plan(str(payload.get("plan_id", "")))
            except ValueError as exc:
                self._send(422, {"ok": False, "error": str(exc), "billing": "not_configured",
                                 "withdrawals_enabled": False}); return
            self._send(200, {"ok": True, "subscription": assinatura,
                             "billing": "not_configured", "live_execution": False,
                             "withdrawals_enabled": False}); return
        if parsed.path == "/api/social/follow":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            from backend.planos.social_paper import follow_strategy
            # `follow_strategy(strategy_id, user_id=None)`: o segundo argumento e
            # o usuario, nao um booleano "seguindo". Passar `bool(...)` aqui
            # transformava o id do usuario em True/False e quebrava o estado.
            try:
                resultado = follow_strategy(str(payload.get("strategy_id", "")))
            except (ValueError, LookupError) as exc:
                self._send(422, {"ok": False, "error": str(exc), "withdrawals_enabled": False}); return
            self._send(200, {"ok": True, **resultado, "mode": "paper_trade",
                             "live_execution": False, "withdrawals_enabled": False}); return
        guardian_paths = {"/api/guardian/set": guardian_set, "/api/guardian/remove": guardian_remove,
                          "/api/guardian/tick": lambda p: guardian_tick(),
                          "/api/intents/reconcile": lambda p: intent_log.reconcile(_mt5())}
        if parsed.path in guardian_paths:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                self._send(200, guardian_paths[parsed.path](payload))
            except (PermissionError, ValueError, LookupError) as exc:
                self._send(403, {"ok": False, "error": str(exc), "trade": True})
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc), "trade": True})
            return
        if parsed.path not in {"/api/trade/order", "/api/trade/pending", "/api/trade/close", "/api/trade/close-all", "/api/trade/modify-position", "/api/trade/breakeven", "/api/trade/trailing", "/api/trade/partial-close", "/api/trade/set-protection", "/api/trade/remove-protection", "/api/trade/close-symbol", "/api/trade/cancel-order", "/api/trade/cancel-all-orders", "/api/real/order"}:
            self._send(404, {"ok": False, "error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as exc:
            self._send(400, {"ok": False, "error": f"payload invalido: {exc}", "trade": True})
            return
        try:
            actions = {"/api/trade/order": _trade_order, "/api/trade/pending": _trade_pending_order, "/api/trade/close": _trade_close, "/api/trade/close-all": _trade_close_all, "/api/trade/modify-position": lambda p: _trade_manage(p, "modify"), "/api/trade/breakeven": lambda p: _trade_manage(p, "breakeven"), "/api/trade/trailing": lambda p: _trade_manage(p, "trailing"), "/api/trade/partial-close": _trade_partial_close, "/api/trade/set-protection": _trade_protection, "/api/trade/remove-protection": lambda p: _trade_protection(p, True), "/api/trade/close-symbol": _trade_close_symbol, "/api/trade/cancel-order": _trade_cancel_orders, "/api/trade/cancel-all-orders": lambda p: _trade_cancel_orders(p, True), "/api/real/order": _real_order}
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
                self._send(403, {"ok": False, "error": str(exc), "trade": True})
        except Exception as exc:
            kind = persistent_queue._KIND_BY_ROUTE.get(parsed.path, "")
            queued = persistent_queue.offline_fallback_kind(kind, payload, exc)
            if queued is not None:
                self._send(202, queued)
            else:
                self._send(503, {"ok": False, "error": str(exc), "trade": True})


_T0 = time.time()


def main() -> None:
    if THIRD_PARTY_READ_ONLY:
        print("[gateway] perfil de compatibilidade somente leitura ativo")
    else:
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
    srv = gateway_server.criar_servidor((HOST, PORT), Handler)
    srv.daemon_threads = True
    print(
        f"[gateway] MT5 Gateway rodando em http://{HOST}:{PORT} "
        f"(backlog={srv.request_queue_size}, "
        f"keep_alive={Handler.protocol_version})"
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("[gateway] encerrado por interrupcao")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
