"""Adaptador MT5 do roteador universal.

Ordens MT5 reais nao sao enviadas por aqui: elas passam por
``mt5_gateway._trade_order``, que ja faz order_check, SL/TP obrigatorio,
risk_gate com metricas reais da conta e intent antes do envio. Este
adaptador existe para o roteador universal responder com esse caminho em vez
de "nao implementado".
"""
from __future__ import annotations

from backend.exchange_execution import gate_blocked

GATE = "XAU_ENABLE_MT5_EXECUTION"


class MT5ExecutionError(RuntimeError):
    pass


class MT5ExecutionAdapter:
    def prepare(self, *, symbol, side, order_type, quantity, price=None, request_id, confirm, available=None):
        if not request_id or not confirm:
            raise MT5ExecutionError('request_id e confirmação manual são obrigatórios')
        if not symbol or side.lower() not in {'buy', 'sell'} or quantity <= 0:
            raise MT5ExecutionError('símbolo, lado ou quantidade inválidos')
        if available is not None and quantity > available:
            raise MT5ExecutionError('volume excede disponibilidade')
        return {
            'symbol': symbol.upper(), 'side': side.lower(), 'order_type': order_type.lower(),
            'volume': quantity, 'price': price, 'request_id': request_id,
        }

    def execute(self, order, *, explicit_authorization):
        if not explicit_authorization:
            raise MT5ExecutionError('autorização explícita ausente')
        blocked = gate_blocked(GATE, 'mt5')
        if blocked is not None:
            return {**blocked, 'order': order}
        return {
            'ok': False,
            'status': 'routed',
            'code': 'EXECUTION_VIA_MT5_GATEWAY',
            'reason': 'ordem MT5 e enviada por /api/trade/order (gateway MT5, com risk_gate e order_check); '
                      'o roteador universal nao duplica esse envio',
            'order': order,
            'route': '/api/trade/order',
            'withdrawals_enabled': False,
            'transfers': False,
            'live_execution': False,
        }
