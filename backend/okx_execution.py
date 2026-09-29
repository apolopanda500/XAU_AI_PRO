# -*- coding: utf-8 -*-
"""Adaptador OKX de execucao real com gate, idempotencia e nocional.

Padrao desbloqueado (XAU_ENABLE_OKX_EXECUTION=1). Definir ``=0`` volta a
bloquear sem alterar codigo. Só existe ordem de compra/venda aqui: nenhuma
rota deste adaptador alcanca saque ou transferencia.
"""
from __future__ import annotations

from backend.exchange_execution import execute_order, gate_blocked, no_credentials, reference_price
from backend.okx_client import OkxClient

GATE = "XAU_ENABLE_OKX_EXECUTION"


class OkxExecutionError(RuntimeError):
    pass


class OkxExecutionAdapter:
    def __init__(self, market: str = "spot") -> None:
        if market not in {"spot", "futures"}:
            raise ValueError("mercado OKX inválido")
        self.market = market

    @property
    def client(self) -> OkxClient:
        return OkxClient(self.market)

    def prepare(self, *, symbol: str, side: str, order_type: str, quantity: float,
                price: float | None = None, request_id: str, confirm: bool,
                available: float | None = None) -> dict:
        if not request_id or not confirm:
            raise OkxExecutionError("request_id e confirmação manual são obrigatórios")
        if not symbol or side.lower() not in {"buy", "sell"} or quantity <= 0:
            raise OkxExecutionError("símbolo, lado ou quantidade inválidos")
        if order_type.lower() not in {"market", "limit"}:
            raise OkxExecutionError("tipo OKX não suportado")
        if order_type.lower() == "limit" and (price is None or price <= 0):
            raise OkxExecutionError("preço é obrigatório para limite")
        if available is not None and quantity > available:
            raise OkxExecutionError("saldo insuficiente")
        return {
            "instId": symbol.upper().replace("/", "-"),
            "side": side.lower(),
            "ordType": order_type.lower(),
            "sz": str(quantity),
            "px": str(price) if price is not None else None,
            "clOrdId": request_id,
            "tdMode": "cash" if self.market == "spot" else "cross",
            "market": self.market,
        }

    def _reference_price(self, order: dict) -> float | None:
        limit = order.get("px")
        try:
            if limit is not None and float(limit) > 0:
                return float(limit)
        except (TypeError, ValueError):
            pass
        try:
            return reference_price(self.client.ticker(str(order.get("instId", ""))))
        except Exception:
            return None

    def execute(self, order: dict, *, explicit_authorization: bool) -> dict:
        if not explicit_authorization:
            raise OkxExecutionError("autorizacao explicita ausente")
        blocked = gate_blocked(GATE, "okx")
        if blocked is not None:
            return {**blocked, "order": order}

        client = self.client
        if not client.configured:
            return no_credentials("okx", order)
        price = self._reference_price(order)

        def _send(client_order_id: str) -> dict:
            return client.create_order(
                symbol=str(order.get("instId", "")),
                side=str(order.get("side", "buy")),
                order_type=str(order.get("ordType", "market")),
                quantity=float(order.get("sz", 0) or 0),
                price=order.get("px"),
                request_id=client_order_id,
            )

        return execute_order(
            broker="okx",
            gate=GATE,
            order=order,
            request_id=str(order.get("clOrdId") or order.get("request_id") or ""),
            price=price,
            send=_send,
        )
