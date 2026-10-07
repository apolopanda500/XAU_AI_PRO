"""Adaptador MT5 do roteador universal.

Ordens MT5 reais passam por ``mt5_gateway._trade_order``, que ja faz
order_check, SL/TP obrigatorio, risk_gate com metricas reais da conta e intent
antes do envio. Este adaptador existe para o roteador universal responder com
esse caminho em vez de "nao implementado".
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
            # O SL e o TP chegam como `stop_loss`/`take_profit` no pedido
            # universal. `_trade_order` lê `sl`/`tp`, e a tradução acontece em
            # `para_o_gateway_mt5` — que é testada.
            'stop_loss': None, 'take_profit': None,
        }

    def execute(self, order, *, explicit_authorization):
        """Envia pelo `_trade_order`, que é o ÚNICO caminho com trava do MT5.

        MEDIDO (06/10/2026): este método devolvia
        ``EXECUTION_VIA_MT5_GATEWAY`` sem enviar. A justificativa — "o roteador
        universal não duplica esse envio" — estava certa e a conclusão errada:
        devolver um recusa deixa o MT5 **sem caminho nenhum**. No log de
        intents da conta real foram 77 ``pending`` e 77 ``failed``, com zero
        ordem enviada.

        Delegar ao `_trade_order` não duplica envio nenhum: é o MESMO método que
        o painel chama, com o MESMO `risk_gate`, `order_check` e `intent_log`.
        O que havia eram dois lugares dizendo que o outro enviaria.

        O gate `XAU_ENABLE_MT5_EXECUTION` continua valendo ANTES da delegação,
        e `_trade_order` ainda exige `confirm=true` e `sl`/`tp` válidos por
        conta própria. Delegar não afrouxa nada.
        """
        if not explicit_authorization:
            raise MT5ExecutionError('autorização explícita ausente')
        blocked = gate_blocked(GATE, 'mt5')
        if blocked is not None:
            return {**blocked, 'order': order}
        from backend.mt5_gateway import _trade_order

        return _trade_order(para_o_gateway_mt5(order))


def para_o_gateway_mt5(order: dict) -> dict:
    """Traduz o pedido universal para as chaves que `_trade_order` LÊ.

    `order` é um `UniversalOrderRequest.to_dict()`: nele o volume é
    `quantity`, o stop é `stop_loss` e o alvo é `take_profit`. `_trade_order`
    lê `volume`, `sl` e `tp`, e compara `side` com `{"BUY", "SELL"}` em caixa
    alta — em minúscula a ordem morre em "symbol, side, volume <= 0.10, sl e
    tp validos sao obrigatorios", que não diz qual dos cinco campos faltou
    (AGENTS.md 5).

    O SL e o TP são repassados como vieram, inclusive ZERO: `_trade_order`
    recusa `sl <= 0` ou `tp <= 0` com o motivo certo e com o campo nomeado.
    Trocar zero por um número aqui seria inventar proteção que o operador não
    pediu.
    """
    return {
        'symbol': order['symbol'],
        'side': str(order['side']).upper(),
        'volume': order['quantity'],
        'sl': order.get('stop_loss') or 0.0,
        'tp': order.get('take_profit') or 0.0,
        'confirm': bool(order.get('confirm', True)),
        'request_id': order['request_id'],
    }
