"""Contrato dos adaptadores de execucao real.

Tres estados distintos, nenhum deles "nao implementado":

1. gate desligada (`XAU_ENABLE_<BROKER>_EXECUTION=0`)  -> blocked
2. gate ligada sem chave da corretora                  -> blocked, sem rede
3. gate ligada com chave + envio confirmado             -> executed

Nenhum teste desta pasta abre posicao: `conftest._bloqueia_rede_externa`
derruba qualquer conexao fora de loopback e o envio e substituido por stub.
"""
from __future__ import annotations

import pytest

from backend.binance_execution import BinanceExecutionAdapter, BinanceExecutionError
from backend.binance_client import BinanceClient
from backend.mexc_execution import MexcExecutionAdapter, MexcExecutionError
from backend.mexc_client import MexcClient
from backend.mt5_execution import MT5ExecutionAdapter, MT5ExecutionError


@pytest.mark.parametrize("adapter,error", [
    (MexcExecutionAdapter(), MexcExecutionError),
    (BinanceExecutionAdapter(), BinanceExecutionError),
    (MT5ExecutionAdapter(), MT5ExecutionError),
])
def test_adapters_require_manual_confirmation_and_request_id(adapter, error):
    with pytest.raises(error):
        adapter.prepare(symbol="BTCUSDT", side="buy", order_type="market", quantity=1, request_id="", confirm=False)


@pytest.mark.parametrize("adapter,error", [
    (MexcExecutionAdapter(), MexcExecutionError),
    (BinanceExecutionAdapter(), BinanceExecutionError),
    (MT5ExecutionAdapter(), MT5ExecutionError),
])
def test_adapters_reject_insufficient_balance(adapter, error):
    with pytest.raises(error):
        adapter.prepare(symbol="BTCUSDT", side="buy", order_type="market", quantity=2, request_id="req-1", confirm=True, available=1)


@pytest.mark.parametrize("adapter,client,gate", [
    (MexcExecutionAdapter(), MexcClient, "XAU_ENABLE_MEXC_EXECUTION"),
    (BinanceExecutionAdapter(), BinanceClient, "XAU_ENABLE_BINANCE_EXECUTION"),
    (MT5ExecutionAdapter(), None, "XAU_ENABLE_MT5_EXECUTION"),
])
def test_gate_desligada_bloqueia_sem_enviar(adapter, client, gate, monkeypatch):
    monkeypatch.setenv(gate, "0")
    order = adapter.prepare(symbol="BTCUSDT", side="buy", order_type="market",
                            quantity=1, request_id="req-safe", confirm=True, available=2)
    result = adapter.execute(order, explicit_authorization=True)
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["withdrawals_enabled"] is False


@pytest.mark.parametrize("adapter,client,gate", [
    (MexcExecutionAdapter(), MexcClient, "XAU_ENABLE_MEXC_EXECUTION"),
    (BinanceExecutionAdapter(), BinanceClient, "XAU_ENABLE_BINANCE_EXECUTION"),
])
def test_sem_credencial_nao_ha_envio(adapter, client, gate, monkeypatch):
    # Gate ligada (padrao) mas sem chave: o adaptador devolve o motivo antes de
    # qualquer requisicao, entao nao existe risco de ordem sem credencial.
    monkeypatch.delenv(gate, raising=False)
    monkeypatch.delenv(f"{client.__name__.replace('Client', '').upper()}_SPOT_API_KEY", raising=False)
    order = adapter.prepare(symbol="BTCUSDT", side="buy", order_type="limit", quantity=1,
                            price=100.0, request_id="req-credencial", confirm=True, available=2)
    result = adapter.execute(order, explicit_authorization=True)
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["code"] == "EXECUTION_NO_CREDENTIALS"
    assert result["withdrawals_enabled"] is False


@pytest.mark.parametrize("adapter,client,gate", [
    (MexcExecutionAdapter(), MexcClient, "XAU_ENABLE_MEXC_EXECUTION"),
    (BinanceExecutionAdapter(), BinanceClient, "XAU_ENABLE_BINANCE_EXECUTION"),
])
def test_liberado_envia_e_nao_reenvia_o_mesmo_request_id(adapter, client, gate, monkeypatch):
    monkeypatch.delenv(gate, raising=False)
    monkeypatch.setattr(client, "configured", property(lambda self: True))
    monkeypatch.setattr(client, "ticker", lambda self, symbol="": {"last": "100"})
    monkeypatch.setattr(client, "create_order",
                        lambda self, **kwargs: {"orderId": "42", "clientOrderId": kwargs["request_id"]})

    order = adapter.prepare(symbol="BTCUSDT", side="buy", order_type="limit", quantity=1,
                            price=100.0, request_id="req-unico", confirm=True, available=2)
    first = adapter.execute(order, explicit_authorization=True)
    assert first["ok"] is True
    assert first["status"] == "executed"
    assert first["ticket"] == "42"
    assert first["live_execution"] is True
    assert first["withdrawals_enabled"] is False

    again = adapter.execute(order, explicit_authorization=True)
    assert again["duplicate"] is True
    assert again["ticket"] == "42"


@pytest.mark.parametrize("adapter,client", [
    (MexcExecutionAdapter(), MexcClient),
    (BinanceExecutionAdapter(), BinanceClient),
])
def test_liberado_nao_envia_sem_preco_de_referencia(adapter, client, monkeypatch):
    # Sem preco nao da para calcular o nocional; a trava nao pode ser pulada.
    monkeypatch.setattr(client, "configured", property(lambda self: True))
    monkeypatch.setattr(client, "ticker", lambda self, symbol="": {})
    order = adapter.prepare(symbol="BTCUSDT", side="buy", order_type="market",
                            quantity=1, request_id="req-sem-preco", confirm=True, available=2)
    with pytest.raises(ValueError, match="preco de referencia"):
        adapter.execute(order, explicit_authorization=True)


def test_excecao_do_adaptador_nao_vira_recibo_de_sucesso(monkeypatch):
    from backend.execution_receipts import recall

    monkeypatch.setattr(BinanceClient, "configured", property(lambda self: True))
    monkeypatch.setattr(BinanceClient, "ticker", lambda self, symbol="": {"last": "100"})
    monkeypatch.setattr(BinanceClient, "create_order",
                        lambda self, **kwargs: (_ for _ in ()).throw(RuntimeError("rejeitada")))
    adapter = BinanceExecutionAdapter()
    order = adapter.prepare(symbol="BTCUSDT", side="buy", order_type="market", quantity=1,
                            request_id="req-falhou", confirm=True, available=2)
    result = adapter.execute(order, explicit_authorization=True)
    assert result["ok"] is False
    assert result["status"] == "rejected"
    assert recall("req-falhou")["ok"] is False
