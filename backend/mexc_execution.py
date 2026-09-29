# -*- coding: utf-8 -*-
"""Adaptador MEXC de execucao real com gate, idempotencia e nocional.

Padrao desbloqueado (XAU_ENABLE_MEXC_EXECUTION=1). Definir ``=0`` volta a
bloquear sem alterar codigo. Só existe ordem de compra/venda aqui: nenhuma
rota deste adaptador alcanca saque ou transferencia.
"""
from __future__ import annotations

from backend.exchange_execution import execute_order, gate_blocked, no_credentials, reference_price
from backend.mexc_client import MexcClient

GATE = "XAU_ENABLE_MEXC_EXECUTION"


class MexcExecutionError(RuntimeError):
    pass


class MexcExecutionAdapter:
    def __init__(self, market: str = "spot") -> None:
        if market not in {"spot", "futures"}:
            raise ValueError("market inválido")
        self.market = market
        self.spot = market == "spot"

    @property
    def client(self) -> MexcClient:
        return MexcClient(self.market)

    def prepare(self, *, symbol: str, side: str, order_type: str, quantity: float,
                price: float | None = None, request_id: str, confirm: bool,
                available: float | None = None) -> dict:
        if not request_id or not confirm:
            raise MexcExecutionError("request_id e confirmação manual são obrigatórios")
        if not symbol.strip() or side.lower() not in {"buy", "sell"}:
            raise MexcExecutionError("símbolo ou lado inválido")
        if quantity <= 0 or (available is not None and quantity > available):
            raise MexcExecutionError("quantidade excede saldo disponível")
        if order_type.lower() not in {"market", "limit"}:
            raise MexcExecutionError("tipo MEXC não suportado")
        if order_type.lower() == "limit" and (price is None or price <= 0):
            raise MexcExecutionError("tipo/preço inválido")
        return {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
            **({"price": price} if price is not None else {}),
            "newClientOrderId": request_id,
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
            raise MexcExecutionError("autorizacao explicita ausente")
        blocked = gate_blocked(GATE, "mexc")
        if blocked is not None:
            return {**blocked, "order": order}

        client = self.client
        if not client.configured:
            return no_credentials("mexc", order)
        price = self._reference_price(order)

        def _send(client_order_id: str) -> dict:
            return client.create_order(
                symbol=str(order.get("symbol", "")),
                side=str(order.get("side", "buy")),
                order_type=str(order.get("type", "market")),
                quantity=float(order.get("quantity", 0) or 0),
                price=order.get("price"),
                request_id=client_order_id,
            )

        return execute_order(
            broker="mexc",
            gate=GATE,
            order=order,
            request_id=str(order.get("newClientOrderId") or order.get("request_id") or ""),
            price=price,
            send=_send,
        )
