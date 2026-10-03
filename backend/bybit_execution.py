# -*- coding: utf-8 -*-
"""Adaptador Bybit de execucao real com gate, idempotencia e nocional.

Padrao desbloqueado (XAU_ENABLE_BYBIT_EXECUTION=1). Definir ``=0`` volta a
bloquear sem alterar codigo. Só existe ordem de compra/venda aqui: nenhuma
rota deste adaptador alcanca saque ou transferencia.
"""
from __future__ import annotations

from backend.bybit_client import BybitClient
from backend.exchange_execution import execute_order, gate_blocked, no_credentials, reference_price

GATE = "XAU_ENABLE_BYBIT_EXECUTION"


class BybitExecutionError(RuntimeError):
    pass


class BybitExecutionAdapter:
    def __init__(self, market: str = "spot") -> None:
        if market not in {"spot", "futures"}:
            raise ValueError("mercado Bybit inválido")
        self.market = market

    @property
    def client(self) -> BybitClient:
        return BybitClient(self.market)

    def prepare(self, *, symbol: str, side: str, order_type: str, quantity: float,
                price: float | None = None, request_id: str, confirm: bool,
                available: float | None = None) -> dict:
        if not request_id or not confirm:
            raise BybitExecutionError("request_id e confirmação manual são obrigatórios")
        if not symbol or side.lower() not in {"buy", "sell"} or quantity <= 0:
            raise BybitExecutionError("símbolo, lado ou quantidade inválidos")
        if order_type.lower() not in {"market", "limit"}:
            raise BybitExecutionError("tipo Bybit não suportado")
        if order_type.lower() == "limit" and (price is None or price <= 0):
            raise BybitExecutionError("preço é obrigatório para limite")
        if available is not None and quantity > available:
            raise BybitExecutionError("saldo insuficiente")
        return {
            "symbol": symbol.upper(),
            "side": side.lower(),
            "orderType": order_type.lower(),
            "qty": str(quantity),
            "price": str(price) if price is not None else None,
            "orderLinkId": request_id,
            "market": self.market,
        }

    def _reference_price(self, order: dict) -> float | None:
        limit = order.get("price")
        try:
            if limit is not None and float(limit) > 0:
                return float(limit)
        except (TypeError, ValueError):
            pass
        try:
            return reference_price(self.client.ticker(str(order.get("symbol", ""))))
        except Exception:
            return None

    def execute(self, order: dict, *, explicit_authorization: bool) -> dict:
        if not explicit_authorization:
            raise BybitExecutionError("autorizacao explicita ausente")
        blocked = gate_blocked(GATE, "bybit")
        if blocked is not None:
            return {**blocked, "order": order}

        client = self.client
        if not client.configured:
            return no_credentials("bybit", order)
        price = self._reference_price(order)

        def _send(client_order_id: str) -> dict:
            return client.create_order(
                symbol=str(order.get("symbol", "")),
                side=str(order.get("side", "buy")),
                order_type=str(order.get("orderType", "market")),
                quantity=float(order.get("qty", 0) or 0),
                price=order.get("price"),
                request_id=client_order_id,
            )

        return execute_order(
            broker="bybit",
            gate=GATE,
            order=order,
            request_id=str(order.get("orderLinkId") or order.get("request_id") or ""),
            price=price,
            send=_send,
        )
