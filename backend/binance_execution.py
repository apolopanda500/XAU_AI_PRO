"""Binance execution adapter: envio real de ordem com gate e idempotencia.

Padrao desbloqueado (XAU_ENABLE_BINANCE_EXECUTION=1). Definir ``=0`` volta a
bloquear sem alterar codigo. Só existe ordem de compra/venda aqui: nenhuma
rota deste adaptador alcanca saque ou transferencia.
"""
from __future__ import annotations

from backend.binance_client import BinanceClient
from backend.exchange_execution import execute_order, gate_blocked, no_credentials, reference_price


class BinanceExecutionError(RuntimeError):
    pass


GATE = "XAU_ENABLE_BINANCE_EXECUTION"


class BinanceExecutionAdapter:
    def __init__(self, market: str = "spot") -> None:
        if market not in {"spot", "futures"}:
            raise ValueError("market invalido")
        self.market = market

    @property
    def client(self) -> BinanceClient:
        return BinanceClient(self.market)

    def prepare(self, *, symbol, side, order_type, quantity, price=None, request_id, confirm, available=None):
        if not request_id or not confirm:
            raise BinanceExecutionError("request_id e confirmacao manual sao obrigatorios")
        if not symbol or side.lower() not in {"buy", "sell"} or quantity <= 0:
            raise BinanceExecutionError("simbolo, lado ou quantidade invalidos")
        if available is not None and quantity > available:
            raise BinanceExecutionError("saldo insuficiente")
        if order_type.lower() not in {"market", "limit"}:
            raise BinanceExecutionError("tipo Binance nao suportado")
        if order_type.lower() == "limit" and (price is None or price <= 0):
            raise BinanceExecutionError("preco obrigatorio")
        return {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
            "price": price,
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

    def execute(self, order, *, explicit_authorization):
        if not explicit_authorization:
            raise BinanceExecutionError("autorizacao explicita ausente")
        blocked = gate_blocked(GATE, "binance")
        if blocked is not None:
            return {**blocked, "order": order}

        client = self.client
        if not client.configured:
            return no_credentials("binance", order)
        price = self._reference_price(order)

        def _send(client_order_id: str) -> dict:
            params = dict(order)
            params.pop("market", None)
            return client.create_order(
                symbol=str(params.get("symbol", "")),
                side=str(params.get("side", "buy")),
                order_type=str(params.get("type", "market")),
                quantity=float(params.get("quantity", 0) or 0),
                price=params.get("price"),
                request_id=client_order_id,
            )

        return execute_order(
            broker="binance",
            gate=GATE,
            order=order,
            request_id=str(order.get("newClientOrderId") or order.get("request_id") or ""),
            price=price,
            send=_send,
        )


__all__ = ["BinanceExecutionAdapter", "BinanceExecutionError", "GATE"]
