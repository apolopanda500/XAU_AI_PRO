"""Binance execution adapter with explicit opt-in and no withdrawal APIs."""
from __future__ import annotations
import hashlib, hmac, json, os, time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
        if not explicit_authorization: raise BinanceExecutionError("autorizacao explicita ausente")
        if os.getenv("XAU_ENABLE_BINANCE_EXECUTION", "0") != "1": return {"ok": False, "status": "blocked", "reason": "execucao Binance desativada por padrao", "order": order, "withdrawals_enabled": False}
        key = os.getenv(f"BINANCE_{self.market.upper()}_API_KEY", "").strip(); secret = os.getenv(f"BINANCE_{self.market.upper()}_API_SECRET", "").strip()
        if not key or not secret: raise BinanceExecutionError(f"credenciais Binance {self.market} nao configuradas")
        base = os.getenv(f"BINANCE_{self.market.upper()}_BASE_URL", "https://api.binance.com" if self.market == "spot" else "https://fapi.binance.com").rstrip("/")
        path = "/api/v3/order" if self.market == "spot" else "/fapi/v1/order"
        payload = {"symbol": order["symbol"], "side": order["side"], "type": order["type"], "quantity": order["quantity"], "newClientOrderId": order["newClientOrderId"], "timestamp": int(time.time() * 1000)}
        if order.get("price") is not None: payload.update({"price": order["price"], "timeInForce": "GTC"})
        encoded = urlencode(payload); payload["signature"] = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        request = Request(base + path, data=urlencode(payload).encode(), headers={"X-MBX-APIKEY": key, "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        try:
            with urlopen(request, timeout=10) as response: result = json.loads(response.read().decode())
        except Exception as exc: raise BinanceExecutionError(f"Binance {self.market} indisponivel: {exc}") from exc
        if isinstance(result, dict) and int(result.get("code", 0) or 0) < 0: raise BinanceExecutionError(str(result))
        return {"ok": True, "status": "submitted", "ticket": result.get("orderId"), "broker": "binance", "market": self.market, "response": result, "withdrawals_enabled": False}
