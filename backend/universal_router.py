"""Roteamento universal de comandos por corretora e mercado.

Camada de contrato בלבד: não faz fallback entre corretoras e não transforma
uma prévia em execução. Cada adaptador precisa devolver ticket e reconciliação.
"""
from __future__ import annotations
from dataclasses import asdict
from typing import Any
from backend.mexc_execution import MexcExecutionAdapter, MexcExecutionError
from backend.binance_execution import BinanceExecutionAdapter
from backend.mt5_execution import MT5ExecutionAdapter
from backend.universal_contracts import UniversalOrderRequest, command_contract

class UniversalRouterError(RuntimeError): pass

class UniversalRouter:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def prepare_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = UniversalOrderRequest.from_payload(payload)
        if request.request_id in self._seen:
            raise UniversalRouterError("request_id já utilizado")
        self._seen.add(request.request_id)
        contract = command_contract("order")
        contract.update({"request_id": request.request_id, "broker": request.broker, "market": request.market, "symbol": request.symbol, "side": request.side, "quantity": request.quantity, "price": request.price, "status": "pending_manual_review"})
        if request.broker == "mexc":
            adapter = MexcExecutionAdapter("futures" if request.market in {"futures", "crypto-futures"} else "spot")
            contract["adapter_payload"] = adapter.prepare(symbol=request.symbol, side=request.side, order_type=request.order_type, quantity=request.quantity, price=request.price, request_id=request.request_id, confirm=request.confirm)
        elif request.broker in {"binance", "mt5"}:
            adapter = BinanceExecutionAdapter("futures" if request.market in {"futures", "crypto-futures"} else "spot") if request.broker == "binance" else MT5ExecutionAdapter()
            contract["adapter_payload"] = adapter.prepare(symbol=request.symbol, side=request.side, order_type=request.order_type, quantity=request.quantity, price=request.price, request_id=request.request_id, confirm=request.confirm)
            contract["status"] = "pending_manual_review"
        return contract

    def execute_mexc(self, payload: dict[str, Any], *, explicit_authorization: bool) -> dict[str, Any]:
        request = UniversalOrderRequest.from_payload(payload)
        if request.broker != "mexc": raise UniversalRouterError("roteamento incompatível com MEXC")
        adapter = MexcExecutionAdapter("futures" if request.market in {"futures", "crypto-futures"} else "spot")
        order = adapter.prepare(symbol=request.symbol, side=request.side, order_type=request.order_type, quantity=request.quantity, price=request.price, request_id=request.request_id, confirm=request.confirm)
        return adapter.execute(order, explicit_authorization=explicit_authorization)

    def execute(self, payload: dict[str, Any], *, explicit_authorization: bool) -> dict[str, Any]:
        """Despacha para exatamente um adaptador, sem fallback entre corretoras."""
        request = UniversalOrderRequest.from_payload(payload)
        if request.broker == "mexc":
            adapter = MexcExecutionAdapter("futures" if request.market in {"futures", "crypto-futures"} else "spot")
        elif request.broker == "binance":
            adapter = BinanceExecutionAdapter("futures" if request.market in {"futures", "crypto-futures"} else "spot")
        else:
            adapter = MT5ExecutionAdapter()
        order = adapter.prepare(symbol=request.symbol, side=request.side, order_type=request.order_type, quantity=request.quantity, price=request.price, request_id=request.request_id, confirm=request.confirm)
        return adapter.execute(order, explicit_authorization=explicit_authorization)
