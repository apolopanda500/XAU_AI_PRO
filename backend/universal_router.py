"""Roteamento universal de comandos por corretora e mercado.

Camada de contrato apenas: nao faz fallback entre corretoras. Cada adaptador
devolve o proprio ticket e o proprio motivo de recusa. O envio real passa por
intent_log (pendente -> enviado/falhou) para nunca existir ordem sem rastro.
"""
from __future__ import annotations
from typing import Any
from backend.broker_registry import EXECUTION_GATES
from backend import intent_log
from backend.mexc_execution import MexcExecutionAdapter, MexcExecutionError
from backend.binance_execution import BinanceExecutionAdapter
from backend.bybit_execution import BybitExecutionAdapter
from backend.okx_execution import OkxExecutionAdapter
from backend.mt5_execution import MT5ExecutionAdapter
from backend.universal_contracts import UniversalOrderRequest, command_contract

class UniversalRouterError(RuntimeError): pass


class UniversalRouter:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def adapter_for(self, request: Any) -> Any | None:
        """Adaptador da corretora do pedido. None quando nao existe."""
        market = "futures" if getattr(request, "market", "") in {"futures", "crypto-futures"} else "spot"
        broker = str(getattr(request, "broker", "")).lower()
        if broker == "mexc":
            return MexcExecutionAdapter(market)
        if broker == "binance":
            return BinanceExecutionAdapter(market)
        if broker == "bybit":
            return BybitExecutionAdapter(market)
        if broker == "okx":
            return OkxExecutionAdapter(market)
        if broker == "mt5":
            return MT5ExecutionAdapter()
        return None

    def prepare_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = UniversalOrderRequest.from_payload(payload)
        if request.request_id in self._seen:
            raise UniversalRouterError("request_id já utilizado")
        self._seen.add(request.request_id)
        contract = command_contract("order")
        contract.update({"request_id": request.request_id, "account_id": request.account_id, "broker": request.broker, "market": request.market, "symbol": request.symbol, "side": request.side, "quantity": request.quantity, "price": request.price, "status": "pending_manual_review"})
        if request.broker == "mexc":
            adapter = MexcExecutionAdapter("futures" if request.market in {"futures", "crypto-futures"} else "spot")
            contract["adapter_payload"] = adapter.prepare(symbol=request.symbol, side=request.side, order_type=request.order_type, quantity=request.quantity, price=request.price, request_id=request.request_id, confirm=request.confirm)
        elif request.broker in {"binance", "bybit", "okx", "mt5"}:
            if request.broker == "binance":
                adapter = BinanceExecutionAdapter("futures" if request.market in {"futures", "crypto-futures"} else "spot")
            elif request.broker == "bybit":
                adapter = BybitExecutionAdapter("futures" if request.market in {"futures", "crypto-futures"} else "spot")
            elif request.broker == "okx":
                adapter = OkxExecutionAdapter("futures" if request.market in {"futures", "crypto-futures"} else "spot")
            else:
                adapter = MT5ExecutionAdapter()
            contract["adapter_payload"] = adapter.prepare(symbol=request.symbol, side=request.side, order_type=request.order_type, quantity=request.quantity, price=request.price, request_id=request.request_id, confirm=request.confirm)
            contract["status"] = "pending_manual_review"
        return contract

    def execute_mexc(self, payload: dict[str, Any], *, explicit_authorization: bool) -> dict[str, Any]:
        if explicit_authorization is not True:
            raise UniversalRouterError("autorização explícita obrigatória")
        request = UniversalOrderRequest.from_payload(payload)
        if request.broker != "mexc":
            raise UniversalRouterError("roteamento incompatível com MEXC")
        return self.execute(payload, explicit_authorization=True)

    def execute(self, payload: dict[str, Any], *, explicit_authorization: bool) -> dict[str, Any]:
        """Executa a ordem pelo adaptador da propria corretora.

        Nao ha fallback entre corretoras. Quem responde e o adaptador: ele
        aplica a trava XAU_ENABLE_<BROKER>_EXECUTION e devolve o proprio
        motivo. Esta funcao nao olha o rotulo da conta em lugar nenhum.

        Todo envio fica no intent_log antes e depois do envio: resposta
        perdida da corretora vira `unknown` e nunca vira reenvio automatico.
        """
        if explicit_authorization is not True:
            raise UniversalRouterError("autorização explícita obrigatória")
        request = UniversalOrderRequest.from_payload(payload)
        adapter = self.adapter_for(request)
        if adapter is None:
            raise UniversalRouterError(f"sem adaptador de execucao para {request.broker}")
        contract = self.prepare_order(payload)
        order = contract.get("adapter_payload", {})

        intent_id = intent_log.record_intent(
            "exchange_order",
            {"broker": request.broker, "market": request.market, "symbol": request.symbol,
             "side": request.side, "quantity": request.quantity, "order_type": request.order_type,
             "request_id": request.request_id, "account_id": request.account_id},
            intent_id=str(request.request_id),
            status="pending",
        )
        try:
            result = adapter.execute(order, explicit_authorization=True)
        except Exception as exc:
            intent_log.record_intent(
                "exchange_order",
                {"broker": request.broker, "symbol": request.symbol, "request_id": request.request_id},
                intent_id=intent_id, status="failed", extra={"error": str(exc)[:300]},
            )
            raise

        if isinstance(result, dict):
            if result.get("ok") is True:
                status = "sent"
            elif result.get("status") == "blocked":
                status = "failed"
            else:
                status = "failed"
            intent_log.record_intent(
                "exchange_order",
                {"broker": request.broker, "symbol": request.symbol, "request_id": request.request_id},
                intent_id=intent_id, status=status,
                extra={"code": result.get("code"), "ticket": result.get("ticket"),
                       "reason": str(result.get("reason", ""))[:300]},
            )
            return {**contract, **result, "intent_id": intent_id}
        return result
