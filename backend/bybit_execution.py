from __future__ import annotations


class BybitExecutionError(RuntimeError):
    pass


class BybitExecutionAdapter:
    def __init__(self, market: str = "spot") -> None:
        if market not in {"spot", "futures"}:
            raise ValueError("mercado Bybit inválido")
        self.market = market

    def prepare(self, *, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None, request_id: str, confirm: bool, available: float | None = None) -> dict:
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
        return {"symbol": symbol.upper(), "side": side.lower(), "orderType": order_type.lower(), "qty": str(quantity), "price": str(price) if price is not None else None, "orderLinkId": request_id, "market": self.market}

    def execute(self, order: dict, *, explicit_authorization: bool) -> dict:
        if not explicit_authorization:
            raise BybitExecutionError("autorização explícita ausente")
        return {"ok": False, "status": "blocked", "reason": "execução Bybit não habilitada neste ciclo", "order": order, "withdrawals_enabled": False, "live_execution": False}
