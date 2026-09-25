"""Adaptador MEXC de execução com trava explícita e reconciliação posterior.

O envio permanece desligado por padrão. Ative apenas em ambiente controlado
com XAU_ENABLE_MEXC_EXECUTION=1 e confirmação manual no contrato.
"""
from __future__ import annotations
import hashlib, hmac, json, os, time
from urllib.parse import urlencode
from urllib.request import Request

from backend.universal_contracts import open_exchange_request, validate_exchange_base_url

class MexcExecutionError(RuntimeError): pass

class MexcExecutionAdapter:
    def __init__(self, market: str = "spot") -> None:
        if market not in {"spot", "futures"}: raise ValueError("market inválido")
        self.market=market; self.spot=market=="spot"
        self.base=validate_exchange_base_url(os.getenv("MEXC_SPOT_BASE_URL" if self.spot else "MEXC_FUTURES_BASE_URL", "https://api.mexc.com" if self.spot else "https://contract.mexc.com"), "mexc")
        self.key=os.getenv(f"MEXC_{market.upper()}_API_KEY", "").strip(); self.secret=os.getenv(f"MEXC_{market.upper()}_API_SECRET", "").strip()
    def _signed(self, method: str, path: str, params: dict[str, object]) -> dict:
        if not self.key or not self.secret: raise MexcExecutionError("credenciais MEXC não configuradas")
        query=dict(params); query["timestamp"]=int(time.time()*1000); encoded=urlencode(query); query["signature"]=hmac.new(self.secret.encode(),encoded.encode(),hashlib.sha256).hexdigest()
        base=validate_exchange_base_url(self.base,"mexc")
        req=Request(base+path, data=urlencode(query).encode() if method=="POST" else None, headers={"X-MEXC-APIKEY":self.key,"Content-Type":"application/x-www-form-urlencoded"}, method=method)
        if method=="GET": req.full_url=base+path+"?"+urlencode(query)
        with open_exchange_request(req, timeout=10) as response: data=json.loads(response.read().decode())
        if isinstance(data,dict) and data.get("code") not in (None,0,200): raise MexcExecutionError(str(data))
        return data if isinstance(data,dict) else {"data":data}
    def prepare(self, *, symbol: str, side: str, order_type: str, quantity: float, price: float|None=None, request_id: str, confirm: bool, available: float|None=None) -> dict:
        if not request_id or not confirm: raise MexcExecutionError("request_id e confirmação manual são obrigatórios")
        if not symbol.strip() or side.lower() not in {"buy","sell"}: raise MexcExecutionError("símbolo ou lado inválido")
        if quantity<=0 or (available is not None and quantity>available): raise MexcExecutionError("quantidade excede saldo disponível")
        if order_type.lower() not in {"market","limit"} or (order_type.lower()=="limit" and (price is None or price<=0)): raise MexcExecutionError("tipo/preço inválido")
        return {"symbol":symbol.upper(),"side":side.upper(),"type":order_type.upper(),"quantity":quantity,**({"price":price} if price is not None else {}),"newClientOrderId":request_id}
    def execute(self, order: dict, *, explicit_authorization: bool) -> dict:
        if not explicit_authorization:
            raise MexcExecutionError("autorização explícita ausente")
        return {"ok": False, "status": "blocked", "reason": "execução MEXC bloqueada", "withdrawals_enabled": False, "live_execution": False, "order": order}
