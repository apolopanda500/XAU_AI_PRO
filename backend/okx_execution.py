from __future__ import annotations


class OkxExecutionError(RuntimeError):
    pass


class OkxExecutionAdapter:
    def __init__(self, market: str = "spot") -> None:
        if market not in {"spot", "futures"}:
            raise ValueError("mercado OKX inválido")
        self.market = market

    def prepare(self, *, symbol: str, side: str, order_type: str, quantity: float, price: float | None = None, request_id: str, confirm: bool, available: float | None = None) -> dict:
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
        return {"instId": symbol.upper().replace("/", "-"), "side": side.lower(), "ordType": order_type.lower(), "sz": str(quantity), "px": str(price) if price is not None else None, "clOrdId": request_id, "tdMode": "cash" if self.market == "spot" else "cross", "market": self.market}

    def execute(self, order: dict, *, explicit_authorization: bool) -> dict:
        if not explicit_authorization:
            raise OkxExecutionError("autorização explícita ausente")
        return {"ok": False, "status": "blocked", "reason": "execução OKX não habilitada neste ciclo", "order": order, "withdrawals_enabled": False, "live_execution": False}
