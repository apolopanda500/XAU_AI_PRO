"""
  O ADAPTADOR MT5 DO ROTEADOR (06/10/2026)
  ========================================

  MEDIDO no log de intents de PRODUCAO, conta 391773676: 158 intents, sendo 77
  `exchange_order` pending e 77 `exchange_order` **failed**, e **zero** intents
  com ticket de ordem. Toda tentativa morria com:

      EXECUTION_VIA_MT5_GATEWAY — "o roteador universal nao duplica esse envio"

  `MT5ExecutionAdapter.execute` devolvia essa recusa em vez de enviar. A
  justificativa ("nao duplica esse envio") estava certa e a conclusao errada:
  devolver recusa deixa o MT5 SEM CAMINHO NENHUM. Eram dois lugares dizendo
  que o outro enviaria, e nenhum enviava.

  Aqui a correcao e no ADAPTADOR, e nao no `_loop`: `TestRoteamentoPorCorretora`
  (AGENTS.md 3) proibe caminho exclusivo por corretora, e o `UniversalRouter`
  precisa continuar escolhendo o adaptador. Delegar ao `_trade_order` mantem a
  escolha por corretora e mata o beco sem saida na origem.
"""

from __future__ import annotations

import pytest

from backend import mt5_execution as mx


PEDIDO = {
    "symbol": "BTCUSD",
    "side": "buy",
    "order_type": "market",
    "quantity": 0.01,
    "price": None,
    "request_id": "auto-mt5:BTCUSD:H1:5971026",
    "confirm": True,
    "stop_loss": 85310.25,
    "take_profit": 85710.25,
}


class _TradeOrderEspiao:
    """O `mt5_gateway._trade_order`, observado. Nao chama MetaTrader.

    `recusa` e um interruptor em vez de reatribuir `__call__`: Python resolve
    `__call__` na CLASSE, entao trocar o atributo na instancia nao muda nada e o
    teste passaria medindo o caminho errado.
    """

    def __init__(self):
        self.recebido = None
        self.recusa = None

    def __call__(self, payload):
        self.recebido = payload
        if self.recusa is not None:
            return self.recusa
        return {"ok": True, "deal": 246012074, "order": 246012075, "trade": True}


@pytest.fixture()
def trade_order(monkeypatch):
    espiao = _TradeOrderEspiao()
    monkeypatch.setattr("backend.mt5_gateway._trade_order", espiao)
    return espiao


class TestTraducaoParaOTradeOrder:
    def test_usa_as_chaves_que_o_trade_order_le(self):
        """
        O pedido universal tem `quantity`/`stop_loss`/`take_profit`; o
        `_trade_order` le `volume`/`sl`/`tp`. Sem a traducao, `sl` e `tp` valem
        ZERO e a ordem morre em "symbol, side, volume <= 0.10, sl e tp validos
        sao obrigatorios" — o motivo que nao diz qual dos cinco faltou.
        """
        pedido = mx.para_o_gateway_mt5(PEDIDO)
        assert pedido["volume"] == 0.01
        assert pedido["sl"] == 85310.25
        assert pedido["tp"] == 85710.25

    def test_side_em_caixa_alta(self):
        # `_trade_order` compara com `side not in {"BUY", "SELL"}`.
        assert mx.para_o_gateway_mt5(PEDIDO)["side"] == "BUY"
        assert mx.para_o_gateway_mt5({**PEDIDO, "side": "sell"})["side"] == "SELL"

    def test_confirm_e_request_id_sobram(self):
        assert mx.para_o_gateway_mt5(PEDIDO)["confirm"] is True
        assert mx.para_o_gateway_mt5(PEDIDO)["request_id"] == PEDIDO["request_id"]

    def test_PROVA_NEGATIVA_zero_de_sl_vai_como_zero(self):
        """
        SL/TP zero chegam como recusados por `_trade_order`, com o campo
        nomeado. Substituir zero por um numero aqui seria INVENTAR protecao que
        o operador nao pediu — e o gateway aceitaria.
        """
        pedido = mx.para_o_gateway_mt5({**PEDIDO, "stop_loss": None, "take_profit": None})
        assert pedido["sl"] == 0.0
        assert pedido["tp"] == 0.0

    def test_PROVA_NEGATIVA_sem_request_id_levanta(self):
        """Sem `request_id` nao ha idempotencia, e `_trade_order` recusa."""
        with pytest.raises(KeyError):
            mx.para_o_gateway_mt5({k: v for k, v in PEDIDO.items() if k != "request_id"})


class TestExecuteDelega:
    def test_o_adaptador_CHAMA_o_trade_order(self, trade_order):
        """O beco sem saida: 77 pending + 77 failed, zero ordem enviada."""
        resultado = mx.MT5ExecutionAdapter().execute(PEDIDO, explicit_authorization=True)
        assert trade_order.recebido is not None, (
            "o adaptador MT5 precisa DELEGAR o envio; devolver recusa deixa o "
            "motor sem caminho e ele repete o ciclo para sempre"
        )
        assert resultado["ok"] is True
        assert trade_order.recebido["volume"] == 0.01

    def test_PROVA_NEGATIVA_o_adaptador_NAO_devolve_mais_a_recusa(self, trade_order):
        """
        `EXECUTION_VIA_MT5_GATEWAY` nao pode voltar. Ela era a forma do
        adaptador dizer "outro envia" — e ninguem enviava.
        """
        resultado = mx.MT5ExecutionAdapter().execute(PEDIDO, explicit_authorization=True)
        assert resultado.get("code") != "EXECUTION_VIA_MT5_GATEWAY"
        assert resultado.get("status") != "routed"

    def test_a_recusa_agora_tem_o_motivo_do_gateway(self, trade_order):
        """Quando o gateway recusa, o motivo e DELE, com o campo nomeado."""
        trade_order.recusa = {"ok": False, "comment": "invalid stops", "trade": True}
        resultado = mx.MT5ExecutionAdapter().execute(PEDIDO, explicit_authorization=True)
        assert resultado["ok"] is False
        assert "invalid stops" in str(resultado)

    def test_sem_autorizacao_nao_chega_ao_gateway(self, trade_order):
        """A guarda e no adaptador E no `_trade_order`. Nao e uma ou outra."""
        with pytest.raises(mx.MT5ExecutionError):
            mx.MT5ExecutionAdapter().execute(PEDIDO, explicit_authorization=False)
        assert trade_order.recebido is None

    def test_o_gate_mt5_continua_valendo(self, trade_order, monkeypatch):
        """
        Delegar NAO afrouxa o gate. `XAU_ENABLE_MT5_EXECUTION` desligado tem
        que barrar ANTES de chegar ao `_trade_order`.
        """
        monkeypatch.setattr(
            mx, "gate_blocked",
            lambda gate, broker: {"ok": False, "error": f"{gate} desligado"})
        resultado = mx.MT5ExecutionAdapter().execute(PEDIDO, explicit_authorization=True)
        assert trade_order.recebido is None
        assert "desligado" in resultado["error"]

    def test_prepare_exige_request_id_e_confirm(self):
        adaptador = mx.MT5ExecutionAdapter()
        with pytest.raises(mx.MT5ExecutionError):
            adaptador.prepare(symbol="BTCUSD", side="buy", order_type="market",
                              quantity=0.01, request_id="", confirm=True)
        with pytest.raises(mx.MT5ExecutionError):
            adaptador.prepare(symbol="BTCUSD", side="buy", order_type="market",
                              quantity=0.01, request_id="x", confirm=False)