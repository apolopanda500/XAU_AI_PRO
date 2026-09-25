"""Binance execution adapter with explicit opt-in and no withdrawal APIs."""
from __future__ import annotations
import hashlib, hmac, json, os, time

class BinanceExecutionError(RuntimeError):
    pass

class BinanceExecutionAdapter:
    def __init__(self, market: str = "spot") -> None:
        if market not in {"spot", "futures"}: raise ValueError("market invalido")
        self.market = market

    def prepare(self, *, symbol, side, order_type, quantity, price=None, request_id, confirm, available=None):
        if not request_id or not confirm: raise BinanceExecutionError("request_id e confirmacao manual sao obrigatorios")
        if not symbol or side.lower() not in {"buy", "sell"} or quantity <= 0: raise BinanceExecutionError("simbolo, lado ou quantidade invalidos")
        if available is not None and quantity > available: raise BinanceExecutionError("saldo insuficiente")
        if order_type.lower() == "limit" and (price is None or price <= 0): raise BinanceExecutionError("preco obrigatorio")
        if order_type.lower() not in {"market", "limit"}: raise BinanceExecutionError("tipo Binance nao suportado")
        return {"symbol": symbol.upper(), "side": side.upper(), "type": order_type.upper(), "quantity": quantity, "price": price, "newClientOrderId": request_id}

    def execute(self, order, *, explicit_authorization):
        if not explicit_authorization:
            raise BinanceExecutionError("autorizacao explicita ausente")
        return {"ok": False, "status": "blocked", "reason": "execução Binance bloqueada", "order": order, "withdrawals_enabled": False, "live_execution": False}
