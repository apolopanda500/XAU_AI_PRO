# -*- coding: utf-8 -*-
"""Envio real de ordem nas corretoras de cripto.

Compartilhado por mexc/binance/bybit/okx. Regras que valem para as quatro:

1. Gate `XAU_ENABLE_<BROKER>_EXECUTION`. Padrao ``1`` (app desbloqueado);
   definir ``=0`` volta a bloquear sem mexer em codigo.
2. ``request_id`` obrigatorio e usado como idempotencia: o mesmo pedido nunca
   e enviado duas vezes.
3. O nocional e calculado ANTES do envio, com o preco do limite ou com o
   ultimo negocio publico da propria corretora. Sem preco nao ha envio:
   ``RiskLimits.max_notional`` nao pode ser pulado.
4. Aqui so existe envio de ordem. Nenhum caminho deste modulo conhece
   endpoint de saque ou transferencia.
"""
from __future__ import annotations

import math
import os
from typing import Any

from backend.execution_receipts import client_order_id, recall, remember
from backend.risk_gate import RiskLimits

_PRICE_KEYS = ("last", "lastPrice", "price", "close", "bidPrice", "bid", "askPrice", "ask")


def gate_blocked(gate: str, broker: str) -> dict[str, Any] | None:
    """Retorna o bloqueio quando a gate esta desligada; None quando liberada."""
    if os.getenv(gate, "1") != "1":
        return {
            "ok": False,
            "status": "blocked",
            "code": "EXECUTION_GATE_OFF",
            "reason": f"{gate}=0; envio real para {broker} desativado pelo operador",
            "order": {},
            "withdrawals_enabled": False,
            "transfers": False,
            "live_execution": False,
        }
    return None


def reference_price(raw: Any) -> float | None:
    """Preco de referencia de um payload de ticker, sem inventar valor."""
    if isinstance(raw, dict):
        for key in _PRICE_KEYS:
            value = raw.get(key)
            price = _to_float(value)
            if price is not None and price > 0:
                return price
        for nested in ("data", "ticker", "result", "bookTicker"):
            price = reference_price(raw.get(nested))
            if price is not None:
                return price
        bid = _to_float(raw.get("bidPrice") or raw.get("bid"))
        ask = _to_float(raw.get("askPrice") or raw.get("ask"))
        if bid and ask and bid > 0 and ask > 0:
            return round((bid + ask) / 2, 8)
    if isinstance(raw, list):
        for item in raw:
            price = reference_price(item)
            if price is not None:
                return price
    return None


def _to_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def guard_notional(broker: str, quantity: Any, price: Any, limits: RiskLimits | None = None) -> float:
    """Confere volume e nocional antes de qualquer requisicao a corretora.

    Somete o que da para medir de verdade numa corretora de cripto: quantidade
    e nocional. As metricas de conta MT5 (perda diaria, exposicao, drawdown)
    nao existem aqui e por isso nao sao alegadas.
    """
    limits = limits or RiskLimits()
    amount = _to_float(quantity)
    if amount is None or amount <= 0:
        raise ValueError("quantidade invalida: envio recusado")
    value = _to_float(price)
    if value is None or value <= 0:
        raise ValueError("preco de referencia ausente: nocional nao calculado, envio recusado")
    notional = amount * value
    if not math.isfinite(notional) or notional > limits.max_notional:
        raise ValueError(f"nocional {notional:.2f} acima do limite {limits.max_notional:.2f} para {broker}")
    return notional


def no_credentials(broker: str, order: dict[str, Any] | None = None) -> dict[str, Any]:
    """Sem chave da corretora nao ha envio possivel, e isso e dito antes da rede."""
    return {
        "ok": False,
        "status": "blocked",
        "code": "EXECUTION_NO_CREDENTIALS",
        "reason": f"credenciais {broker} nao configuradas; nada foi enviado a corretora",
        "broker": broker,
        "order": dict(order or {}),
        "withdrawals_enabled": False,
        "transfers": False,
        "live_execution": False,
    }


def execute_order(
    *,
    broker: str,
    gate: str,
    order: dict[str, Any],
    request_id: str,
    price: Any,
    send,
    configured: bool = True,
) -> dict[str, Any]:
    """Executa o envio com gate, credencial, idempotencia e nocional.

    ``send`` recebe o client order id ja formatado e devolve o payload da
    corretora (dict) ou lanca a excecao do adaptador.
    """
    blocked = gate_blocked(gate, broker)
    if blocked is not None:
        blocked["order"] = dict(order)
        return blocked

    if not configured:
        return no_credentials(broker, order)

    key = str(request_id or "").strip()
    if not key:
        raise ValueError("request_id obrigatorio para envio real")
    previous = recall(key)
    if previous is not None:
        return {**previous, "duplicate": True, "order": dict(order)}

    notional = guard_notional(broker, order.get("quantity", order.get("qty", order.get("sz", 0))), price)
    external_id = client_order_id(key)

    try:
        raw = send(external_id)
    except Exception as exc:
        receipt = {
            "ok": False,
            "status": "rejected",
            "code": "EXECUTION_REJECTED",
            "reason": str(exc),
            "broker": broker,
            "request_id": key,
            "notional": notional,
            "withdrawals_enabled": False,
            "transfers": False,
            "live_execution": False,
        }
        remember(key, receipt)
        return receipt

    payload = raw if isinstance(raw, dict) else {"raw": raw}
    ticket = str(payload.get("orderId") or payload.get("order_id") or payload.get("id")
                 or payload.get("orderLinkId") or payload.get("clOrdId") or "")
    receipt = {
        "ok": True,
        "status": "executed",
        "code": "EXECUTED",
        "broker": broker,
        "request_id": key,
        "client_order_id": external_id,
        "ticket": ticket,
        "notional": notional,
        "order": dict(order),
        "exchange": payload,
        "withdrawals_enabled": False,
        "transfers": False,
        "live_execution": True,
        "reconciled": False,
    }
    remember(key, receipt)
    return receipt
