"""Contratos universais do gateway.

Este módulo valida formato e limites antes do roteamento. Não executa ordens,
não manipula chaves e não permite operações de saque.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Literal
import math
import numbers
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from backend.broker_registry import normalize_market as normalize_registry_market
from backend.broker_registry import normalize_read_scope

Broker = Literal["mt5", "mexc", "binance", "bybit", "okx"]
Market = Literal["crypto-spot", "crypto-futures", "forex", "indices", "metals", "stocks", "commodities", "bonds", "other"]
CryptoMarket = Literal["crypto-spot", "crypto-futures"]
Side = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "stop", "stop_limit"]


def normalize_market(market: str) -> str:
    return normalize_registry_market(market)


_EXCHANGE_HOSTS = {
    "binance": {"api.binance.com", "fapi.binance.com", "spot-testnet.binance.vision", "testnet.binancefuture.com"},
    "mexc": {"api.mexc.com", "contract.mexc.com"},
    "bybit": {"api.bybit.com", "api-testnet.bybit.com"},
    "okx": {"www.okx.com"},
}


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, _req: Request, _fp: Any, _code: int, _msg: str, _headers: Any, _newurl: str) -> Request | None:
        return None


def validate_exchange_base_url(value: str, broker: str) -> str:
    normalized = str(value or "").strip().rstrip("/")
    parsed = urlsplit(normalized)
    host = str(parsed.hostname or "").lower().rstrip(".")
    allowed = _EXCHANGE_HOSTS.get(str(broker or "").lower(), set())
    if any(ord(character) < 33 for character in normalized):
        raise ValueError("URL base contem caracteres de controle")
    if parsed.scheme.lower() != "https" or host not in allowed:
        raise ValueError(f"URL base nao permitida para {broker}")
    if parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("URL base contiene credenciais ou porta nao permitida")
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("URL base deve conter somente origem HTTPS")
    return normalized


def open_exchange_request(request: Request, timeout: float = 10.0) -> Any:
    opener = build_opener(ProxyHandler({}), _NoRedirectHandler())
    return opener.open(request, timeout=timeout)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def optional_number(value: Any, *, allow_negative: bool = True, integer: bool = False) -> float | int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or (not allow_negative and number < 0):
        return None
    if integer:
        return int(number)
    return number


def first_value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            value = data[key]
            if value is not None and value != "":
                return value
    return None


def timestamp_iso(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return current.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if isinstance(value, bool):
        return None
    if isinstance(value, numbers.Real) or (isinstance(value, str) and value.strip().replace(".", "", 1).isdigit()):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number):
            return None
        absolute = abs(number)
        if absolute >= 1e17:
            number /= 1e9
        elif absolute >= 1e14:
            number /= 1e6
        elif absolute >= 1e11:
            number /= 1e3
        try:
            return datetime.fromtimestamp(number, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical_provenance(*, broker: str, market: str, source: str, endpoint: str | None = None,
                         status: str = "ok", timestamp: Any = None,
                         received_at: str | None = None) -> dict[str, Any]:
    return {
        "broker": str(broker or "").lower(),
        "market": normalize_market(market),
        "source": str(source or ""),
        "endpoint": endpoint,
        "provider_timestamp": timestamp_iso(timestamp),
        "received_at": received_at or utc_now(),
        "status": status,
    }


def canonical_market_response(*, broker: str, market: str, source: str,
                               endpoint: str | None = None, status: str = "ok",
                               timestamp: Any = None, received_at: str | None = None,
                               error: str | None = None, **fields: Any) -> dict[str, Any]:
    normalized_status = str(status or "ok").lower()
    normalized_received = received_at or utc_now()
    body: dict[str, Any] = {
        "ok": normalized_status in {"ok", "partial"},
        "status": normalized_status,
        "broker": str(broker or "").lower(),
        "market": normalize_market(market),
        "source": str(source or ""),
        "timestamp": timestamp_iso(timestamp),
        "received_at": normalized_received,
        "provenance": canonical_provenance(
            broker=broker, market=market, source=source, endpoint=endpoint,
            status=normalized_status, timestamp=timestamp, received_at=normalized_received,
        ),
    }
    body.update(fields)
    if error is not None:
        body["error"] = error
    return body


def canonical_unavailable(*, broker: str, market: str, source: str,
                          endpoint: str | None = None, reason: str,
                          status: str = "unavailable", **fields: Any) -> dict[str, Any]:
    return canonical_market_response(
        broker=broker, market=market, source=source, endpoint=endpoint,
        status=status, error=reason, **fields,
    )


@dataclass(frozen=True)
class UniversalOrderRequest:
    broker: Broker
    market: Market
    symbol: str
    side: Side
    order_type: OrderType
    quantity: float
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    account_id: str | None = None
    client_order_id: str | None = None
    request_id: str | None = None
    confirm: bool = False

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "UniversalOrderRequest":
        broker = str(payload.get("broker", "")).lower()
        market = normalize_market(payload.get("market", ""))
        side = str(payload.get("side", "")).lower()
        order_type = str(payload.get("order_type", "market")).lower()
        try:
            scope = normalize_read_scope(broker, market, payload.get("symbol", ""))
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        broker = scope["broker"]
        market = scope["market"]
        if side not in {"buy", "sell"} or order_type not in {"market", "limit", "stop", "stop_limit"}:
            raise ValueError("side ou order_type inválido")
        symbol = scope["symbol"]
        quantity = float(payload.get("quantity", 0))
        if not symbol or len(symbol) > 40 or not math.isfinite(quantity) or quantity <= 0:
            raise ValueError("symbol e quantity são obrigatórios")
        price = payload.get("price")
        if price is not None and (not math.isfinite(float(price)) or float(price) <= 0):
            raise ValueError("price inválido")
        if order_type in {"limit", "stop_limit"} and price is None:
            raise ValueError("price é obrigatório para ordem limitada")
        request_id = str(payload.get("request_id", "")).strip()
        if not request_id or len(request_id) > 100:
            raise ValueError("request_id único é obrigatório")
        account_id = str(payload.get("account_id", "")).strip()
        if not account_id or len(account_id) > 160:
            raise ValueError("account_id é obrigatório")
        stop_loss = payload.get("stop_loss")
        take_profit = payload.get("take_profit")
        for name, value in (("stop_loss", stop_loss), ("take_profit", take_profit)):
            if value is not None and (not math.isfinite(float(value)) or float(value) <= 0):
                raise ValueError(f"{name} inválido")
        return cls(broker, market, symbol, side, order_type, quantity, None if price is None else float(price), stop_loss, take_profit, account_id, payload.get("client_order_id"), request_id, payload.get("confirm") is True)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_read_scope(broker: str, market: str, symbol: str = "") -> dict[str, str]:
    return normalize_read_scope(broker, market, symbol)


def execution_policy() -> dict[str, bool]:
    return {"read_enabled": True, "order_enabled": False, "withdrawals_enabled": False, "manual_confirmation_required": True}


@dataclass(frozen=True)
class AccountSnapshot:
    broker: str
    market: str
    account_id: str
    currency: str
    balance: float | None = None
    equity: float | None = None
    available: float | None = None
    margin_used: float | None = None
    withdrawals_enabled: bool = False


@dataclass(frozen=True)
class PositionSnapshot:
    broker: str
    market: str
    account_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float | None = None
    mark_price: float | None = None
    unrealized_pnl: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    ticket: str | None = None


@dataclass(frozen=True)
class OrderSnapshot:
    broker: str
    market: str
    account_id: str
    symbol: str
    status: str
    side: str
    order_type: str
    quantity: float
    filled_quantity: float | None = None
    price: float | None = None
    average_price: float | None = None
    ticket: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class HistoryRecord:
    broker: str
    market: str
    account_id: str
    symbol: str
    side: str
    quantity: float
    price: float | None
    realized_pnl: float | None
    executed_at: str
    order_id: str | None = None
    deal_id: str | None = None


@dataclass(frozen=True)
class GatewayEvent:
    source: str
    kind: str
    message: str
    occurred_at: str
    correlation_id: str | None = None
    account_id: str | None = None


def error_response(code: str, message: str, *, correlation_id: str | None = None) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message, "correlation_id": correlation_id}}


def command_contract(command: str, *, requires_confirmation: bool = True) -> dict[str, Any]:
    return {"command": command, "accepted": False, "requires_confirmation": requires_confirmation, "audit_required": True, "withdrawals_allowed": False, "ticket_required": True, "reconciliation_required": True}


def validate_execution_preconditions(*, confirmed: bool, available: float | None, quantity: float, expected_price: float | None = None, requested_price: float | None = None) -> None:
    if not confirmed:
        raise PermissionError("confirmação manual obrigatória")
    if quantity <= 0:
        raise ValueError("quantidade deve ser positiva")
    if available is not None and quantity > available:
        raise ValueError("saldo disponível insuficiente")
    if expected_price is not None and requested_price is not None and abs(requested_price - expected_price) > max(expected_price * 0.001, 1e-8):
        raise ValueError("preço fora da tolerância confirmada")
