"""Contratos universais do gateway.

Este módulo valida formato e limites antes do roteamento. Não executa ordens,
não manipula chaves e não permite operações de saque.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Literal
import math

Broker = Literal["mt5", "mexc", "binance"]
Market = Literal["spot", "futures", "forex", "indices", "metals"]
CryptoMarket = Literal["crypto-spot", "crypto-futures"]
Side = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "stop", "stop_limit"]


def normalize_market(market: str) -> str:
    """Normaliza o mercado vindo do app (aceita crypto-spot/crypto-futures)."""
    value = str(market or "").strip().lower()
    aliases = {"crypto-spot": "spot", "crypto-futures": "futures", "cripto-spot": "spot"}
    return aliases.get(value, value)


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
        if broker not in {"mt5", "mexc", "binance"} or market not in {"spot", "futures", "forex", "indices", "metals"}:
            raise ValueError("broker ou market inválido")
        if side not in {"buy", "sell"} or order_type not in {"market", "limit", "stop", "stop_limit"}:
            raise ValueError("side ou order_type inválido")
        symbol = str(payload.get("symbol", "")).strip().upper()
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
        stop_loss = payload.get("stop_loss")
        take_profit = payload.get("take_profit")
        for name, value in (("stop_loss", stop_loss), ("take_profit", take_profit)):
            if value is not None and (not math.isfinite(float(value)) or float(value) <= 0):
                raise ValueError(f"{name} inválido")
        return cls(broker, market, symbol, side, order_type, quantity, None if price is None else float(price), stop_loss, take_profit, payload.get("account_id"), payload.get("client_order_id"), request_id, payload.get("confirm") is True)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_read_scope(broker: str, market: str, symbol: str = "") -> dict[str, str]:
    if broker.lower() not in {"mt5", "mexc", "binance"}:
        raise ValueError("corretora não suportada")
    market = normalize_market(market)
    if market not in {"spot", "futures", "forex", "indices", "metals", "other"}:
        raise ValueError("mercado não suportado")
    return {"broker": broker.lower(), "market": market, "symbol": symbol.strip().upper()}


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
    filled_quantity: float = 0.0
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
